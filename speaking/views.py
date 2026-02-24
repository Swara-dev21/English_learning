# speaking/views.py
from vosk import Model, KaldiRecognizer
import os
import uuid
import json
import subprocess
from django.conf import settings
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from home_page.models import StudentProfile
from home_page.decorators import pretest_access_required, ajax_pretest_check
import wave
import parselmouth
from difflib import SequenceMatcher
from .models import Recording, SpeakingResult

# Import advanced pronunciation engine (from friend's version)
from .pronunciation_engine import extract_mfcc, compare_mfcc, distance_to_score


# -------------------------------------------------
# MODEL PATH
# -------------------------------------------------
model_path = os.path.join(
    settings.BASE_DIR,
    "speaking",
    "model",
    "vosk-model-small-en-us-0.15"
)

model = None

def get_model():
    global model
    if model is None:
        if not os.path.exists(model_path):
            raise Exception("Vosk model folder not found")
        model = Model(model_path)
    return model


# -------------------------------------------------
# CONFIG
# -------------------------------------------------
REFERENCE_TEXTS = [
    " to improve skills speaking my pronunciation English learning am I",
    "sentence second my is this for practice",
    "with practice daily improves pronunciation English",
    "better you understand peoples helps speech clear",
    "without you speak fear when grows confidence"
]

REFERENCE_AUDIOS = [
    os.path.join(settings.BASE_DIR, "speaking", "reference_audio", "reference.wav"),
    os.path.join(settings.BASE_DIR, "speaking", "reference_audio", "reference2.wav"),
    os.path.join(settings.BASE_DIR, "speaking", "reference_audio", "reference3.wav"),
    os.path.join(settings.BASE_DIR, "speaking", "reference_audio", "reference4.wav"),
    os.path.join(settings.BASE_DIR, "speaking", "reference_audio", "reference5.wav")
]

MEDIA_DIR = os.path.join(settings.MEDIA_ROOT, "speaking", "recordings")
os.makedirs(MEDIA_DIR, exist_ok=True)


# -------------------------------------------------
# UTILS
# -------------------------------------------------

def convert_to_wav(input_path):
    """Convert audio file to WAV format for processing"""
    output_path = input_path.rsplit(".", 1)[0] + ".wav"

    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-ac", "1",
        "-ar", "16000",
        "-sample_fmt", "s16",
        output_path
    ]

    subprocess.run(
        cmd,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    return output_path


def transcribe_audio(wav_path):
    """Transcribe audio using Vosk model"""
    wf = wave.open(wav_path, "rb")
    model_instance = get_model()
    rec = KaldiRecognizer(model_instance, wf.getframerate())

    result_text = ""

    while True:
        data = wf.readframes(4000)
        if len(data) == 0:
            break
        if rec.AcceptWaveform(data):
            res = json.loads(rec.Result())
            result_text += " " + res.get("text", "")

    final_res = json.loads(rec.FinalResult())
    result_text += " " + final_res.get("text", "")

    return result_text.strip()


def word_accuracy(ref, hyp):
    """Calculate word accuracy using sequence matching"""
    return round(
        SequenceMatcher(None, ref.lower(), hyp.lower()).ratio() * 100,
        2
    )


# -------------------------------------------------
# PRONUNCIATION SCORE (Praat-based)
# -------------------------------------------------

def pronunciation_score_praat(student_wav, ref_wav):
    """Calculate pronunciation score using Praat pitch analysis"""
    snd_student = parselmouth.Sound(student_wav)

    duration = snd_student.get_total_duration()
    intensity = snd_student.to_intensity()

    mean_intensity = parselmouth.praat.call(
        intensity,
        "Get mean",
        0,
        0
    )

    # Silence check
    if duration < 0.5 or mean_intensity < 40:
        return 0.0

    snd_ref = parselmouth.Sound(ref_wav)

    pitch_student = snd_student.to_pitch()
    pitch_ref = snd_ref.to_pitch()

    mean_student = parselmouth.praat.call(
        pitch_student,
        "Get mean",
        0,
        0,
        "Hertz"
    )

    mean_ref = parselmouth.praat.call(
        pitch_ref,
        "Get mean",
        0,
        0,
        "Hertz"
    )

    diff = abs(mean_student - mean_ref)

    # Smoother scoring (from friend's version)
    score = 100 * (1 / (1 + (diff / 50)))
    score = min(max(score, 0), 100)

    return round(score, 2)


# -------------------------------------------------
# ACCENT SCORE
# -------------------------------------------------

def accent_score(student_wav, ref_wav, text_score):
    """Calculate accent score based on pitch variation and rhythm"""
    snd_student = parselmouth.Sound(student_wav)
    snd_ref = parselmouth.Sound(ref_wav)

    # ---- Silence Detection ----
    duration = snd_student.get_total_duration()
    intensity = snd_student.to_intensity()
    mean_intensity = parselmouth.praat.call(intensity, "Get mean", 0, 0)

    # 🚨 If silence or wrong sentence → return 0
    if duration < 0.5 or mean_intensity < 40 or text_score < 50:
        return 0.0

    # ---- Duration Rhythm ----
    dur_student = duration
    dur_ref = snd_ref.get_total_duration()

    rhythm_score = (
        min(dur_student, dur_ref) / max(dur_student, dur_ref)
    ) * 100

    # ---- Pitch Variation ----
    pitch_student = snd_student.to_pitch()
    pitch_ref = snd_ref.to_pitch()

    pitch_std_student = parselmouth.praat.call(
        pitch_student, "Get standard deviation", 0, 0, "Hertz"
    )

    pitch_std_ref = parselmouth.praat.call(
        pitch_ref, "Get standard deviation", 0, 0, "Hertz"
    )

    pitch_diff = abs(pitch_std_student - pitch_std_ref)
    pitch_score = max(0, 100 - pitch_diff)

    accent_final = (pitch_score * 0.6) + (rhythm_score * 0.4)

    return round(min(accent_final, 100), 2)


# -------------------------------------------------
# ADJUST PRONUNCIATION BY COMPLETENESS
# -------------------------------------------------

def adjusted_pronunciation_score(ref_text, recognized_text, praat_score):
    """Adjust pronunciation score based on word completeness"""
    ref_words = ref_text.lower().split()
    spoken_words = recognized_text.lower().split()

    total_words = len(ref_words)
    spoken_words_count = len(spoken_words)

    if total_words == 0:
        return 0.0

    completeness = spoken_words_count / total_words

    # ✅ DO NOT allow completeness above 1
    completeness = min(completeness, 1)

    adjusted_score = praat_score * completeness

    # ✅ Clamp final pronunciation to max 100
    adjusted_score = min(adjusted_score, 100)

    return round(adjusted_score, 2)


# -------------------------------------------------
# VIEWS
# -------------------------------------------------

@login_required
@pretest_access_required('speaking')
def start(request):
    """Start speaking test - clear session recordings"""
    request.session['recordings'] = []
    request.session.modified = True
    return render(request, "speaking/start.html")


@login_required
@pretest_access_required('speaking')
def question(request, q_index=0):
    """Display speaking question"""
    if q_index >= len(REFERENCE_TEXTS):
        return redirect('speaking:start')

    return render(
        request,
        "speaking/question.html",
        {
            "reference_text": REFERENCE_TEXTS[q_index],
            "question_index": q_index,
            "total_questions": len(REFERENCE_TEXTS)
        }
    )


@csrf_exempt
@login_required
@ajax_pretest_check('speaking')
def record_question(request, q_index=0):
    """Record and save speaking response with enhanced scoring"""
    if request.method == "POST":
        
        # 🔒 PREVENT DUPLICATE SUBMISSION FOR SAME QUESTION (from friend's version)
        recordings = request.session.get('recordings', [])
        
        if any(r.get("question") == REFERENCE_TEXTS[q_index] for r in recordings):
            next_index = q_index + 1
            if next_index < len(REFERENCE_TEXTS):
                return JsonResponse({
                    "next_url": f"/speaking/question/{next_index}/"
                })
            else:
                return JsonResponse({
                    "next_url": "/speaking/result/"
                })

        audio_file = request.FILES.get("audio")

        if not audio_file:
            return JsonResponse({"error": "No audio received"}, status=400)

        # Save uploaded audio
        ext = audio_file.name.split(".")[-1]
        filename = f"rec_{uuid.uuid4().hex}.{ext}"
        filepath = os.path.join(MEDIA_DIR, filename)

        with open(filepath, "wb+") as f:
            for chunk in audio_file.chunks():
                f.write(chunk)

        wav_path = convert_to_wav(filepath)

        # -------------------------------
        # PROCESS AUDIO WITH ENHANCED SCORING
        # -------------------------------

        ref_text = REFERENCE_TEXTS[q_index]
        ref_wav = REFERENCE_AUDIOS[q_index]

        recognized_text = transcribe_audio(wav_path)

        # Initialize scores
        text_score = 0.0
        pron_score = 0.0
        acc_score = 0.0
        mfcc_score = 0.0
        g2p_score = 0.0
        dtw_distance = 0.0
        dtw_score = 0.0

        if recognized_text.strip() != "":
            # Text accuracy score
            text_score = word_accuracy(ref_text, recognized_text)

            # Praat-based pronunciation score
            praat_score = pronunciation_score_praat(wav_path, ref_wav)

            # MFCC-based pronunciation score (from friend's version)
            mfcc_distance = compare_mfcc(ref_wav, wav_path)
            mfcc_score = distance_to_score(mfcc_distance)

            # DTW metrics (from friend's version)
            dtw_distance = round(mfcc_distance, 2)
            dtw_score = 100 / (1 + (dtw_distance / 40))
            dtw_score = round(max(0, min(100, dtw_score)), 2)

            # G2P score approximation (from friend's version)
            g2p_score = round(text_score * 0.9, 2)

            # Combine Praat and MFCC for better pronunciation scoring
            combined_pron_score = (praat_score * 0.6) + (mfcc_score * 0.4)

            # Adjust for completeness
            pron_score = adjusted_pronunciation_score(
                ref_text,
                recognized_text,
                combined_pron_score
            )

            # Accent score
            acc_score = accent_score(wav_path, ref_wav, text_score)

        # Final overall score (weighted average)
        final_score = round((text_score + pron_score + acc_score) / 3, 2)

        # -------------------------------
        # STORE RESULT
        # -------------------------------

        recordings = request.session.get('recordings', [])
        recordings.append({
            "question": ref_text,
            "recognized": recognized_text,
            "text_score": text_score,
            "pron_score": pron_score,
            "accent_score": acc_score,
            "final_score": final_score,
            "mfcc_score": round(mfcc_score, 2),
            "g2p_score": round(g2p_score, 2),
            "dtw_distance": dtw_distance,
            "dtw_score": dtw_score
        })

        request.session['recordings'] = recordings
        request.session.modified = True

        # Determine next step
        next_index = q_index + 1

        if next_index < len(REFERENCE_TEXTS):
            return JsonResponse({
                "next_url": f"/speaking/question/{next_index}/"
            })
        else:
            return JsonResponse({
                "next_url": "/speaking/result/"
            })

    return JsonResponse({"error": "Invalid request"}, status=400)


# -------------------------------------------------
# RESULT VIEW
# -------------------------------------------------

@login_required
def result_final(request):
    """Display speaking test results and mark as completed"""
    results = request.session.get('recordings', [])

    # Calculate averages for all score types
    total_pron = 0
    total_accent = 0
    total_accuracy = 0
    total_mfcc = 0
    total_g2p = 0
    total_dtw_score = 0

    for res in results:
        total_pron += res["pron_score"]
        total_accent += res["accent_score"]
        total_accuracy += res["text_score"]
        total_mfcc += res["mfcc_score"]
        total_g2p += res["g2p_score"]
        total_dtw_score += res["dtw_score"]

    count = len(results)

    if count > 0:
        avg_pronunciation = round(total_pron / count, 2)
        avg_accent = round(total_accent / count, 2)
        avg_accuracy = round(total_accuracy / count, 2)
        avg_mfcc = round(total_mfcc / count, 2)
        avg_g2p = round(total_g2p / count, 2)
        avg_dtw_score = round(total_dtw_score / count, 2)

        # Enhanced overall score using all metrics
        overall_score = round(
            (avg_pronunciation + avg_accent + avg_accuracy +
             avg_mfcc + avg_g2p + avg_dtw_score) / 6,
            2
        )
    else:
        avg_pronunciation = avg_accent = avg_accuracy = 0.0
        avg_mfcc = avg_g2p = avg_dtw_score = overall_score = 0.0

    # Determine level based on overall score
    if overall_score < 40:
        level = "Basic"
    elif overall_score < 70:
        level = "Intermediate"
    else:
        level = "Advanced"

    # ✅ SAVE SPEAKING RESULT TO DATABASE
    speaking_result = SpeakingResult.objects.create(
        user=request.user,
        session_key=request.session.session_key,
        overall_score=overall_score,
        avg_pronunciation=avg_pronunciation,
        avg_accent=avg_accent,
        avg_accuracy=avg_accuracy,
        level=level
    )

    # Mark speaking as completed in profile (silently - no messages or redirects)
    try:
        profile = StudentProfile.objects.get(user=request.user)
        profile.speaking_completed = True
        profile.update_pretest_status()
        # REMOVED: messages.success(request, "Speaking test completed successfully!")
    except StudentProfile.DoesNotExist:
        # Silently handle profile not found - no warning message
        pass

    response = render(
        request,
        "speaking/result.html",
        {
            "results": results,
            "avg_pronunciation": avg_pronunciation,
            "avg_accent": avg_accent,
            "avg_accuracy": avg_accuracy,
            "avg_mfcc": avg_mfcc,
            "avg_g2p": avg_g2p,
            "avg_dtw_score": avg_dtw_score,
            "overall_score": overall_score,
            "result_id": speaking_result.id,
            "level": level
        }
    )

    # Clear session after displaying results
    request.session['recordings'] = []
    request.session.modified = True

    return response


@login_required
def latest_result(request):
    """Redirect to most recent speaking result"""
    result = SpeakingResult.objects.filter(user=request.user).last()
    if result:
        return redirect('speaking:result_detail', result_id=result.id)
    else:
        messages.warning(request, "No speaking test results found.")
        return redirect('speaking:start')


@login_required
def result_detail(request, result_id):
    """View details of a specific speaking result"""
    result = get_object_or_404(SpeakingResult, id=result_id, user=request.user)
    
    # Get session data if available
    results = []
    if result.session_key:
        # Try to get detailed results from session (if still available)
        pass
    
    return render(request, 'speaking/result_detail.html', {
        'result': result,
        'results': results
    })