from vosk import Model, KaldiRecognizer
import os
import uuid
import json
import subprocess
from django.conf import settings
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
import wave
import parselmouth
from difflib import SequenceMatcher
from django.http import JsonResponse


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
    "I am learning English pronunciation to improve my speaking skills.",
    "This is my second sentence for practice.",
    "English pronunciation improves with daily practice.",
    "Clear speech helps people understand you better.",
    "Confidence grows when you speak without fear."
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
    return round(
        SequenceMatcher(None, ref.lower(), hyp.lower()).ratio() * 100,
        2
    )


# -------------------------------------------------
# PRONUNCIATION SCORE
# -------------------------------------------------

def pronunciation_score(student_wav, ref_wav):

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

    score = max(0, 100 - diff)

    # Clamp to 100 max
    score = min(score, 100)

    return round(score, 2)


# -------------------------------------------------
# ACCENT SCORE (FIXED SILENCE)
# -------------------------------------------------

def accent_score(student_wav, ref_wav):

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

    pitch_std_student = parselmouth.praat.call(
        pitch_student,
        "Get standard deviation",
        0,
        0,
        "Hertz"
    )

    pitch_std_ref = parselmouth.praat.call(
        pitch_ref,
        "Get standard deviation",
        0,
        0,
        "Hertz"
    )

    dur_student = snd_student.get_total_duration()
    dur_ref = snd_ref.get_total_duration()

    if dur_student == 0 or dur_ref == 0:
        return 0.0

    rate_ratio = min(dur_student, dur_ref) / max(dur_student, dur_ref)

    pitch_diff = abs(pitch_std_student - pitch_std_ref)

    pitch_score = max(0, 100 - pitch_diff)
    rhythm_score = rate_ratio * 100

    accent_final = (pitch_score * 0.6) + (rhythm_score * 0.4)

    accent_final = min(accent_final, 100)

    return round(accent_final, 2)


# -------------------------------------------------
# ADJUST PRONUNCIATION BY COMPLETENESS
# -------------------------------------------------

def adjusted_pronunciation_score(ref_text, recognized_text, praat_score):

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

def start(request):
    request.session['recordings'] = []
    request.session.modified = True
    return render(request, "speaking/start.html")


def question(request, q_index=0):

    if q_index >= len(REFERENCE_TEXTS):
        return render(request, "speaking/start.html")

    return render(
        request,
        "speaking/question.html",
        {
            "reference_text": REFERENCE_TEXTS[q_index],
            "question_index": q_index
        }
    )


@csrf_exempt
def record_question(request, q_index=0):

    if request.method == "POST":

        audio_file = request.FILES.get("audio")

        if not audio_file:
            return JsonResponse({"error": "No audio received"}, status=400)

        ext = audio_file.name.split(".")[-1]
        filename = f"rec_{uuid.uuid4().hex}.{ext}"
        filepath = os.path.join(MEDIA_DIR, filename)

        with open(filepath, "wb+") as f:
            for chunk in audio_file.chunks():
                f.write(chunk)

        wav_path = convert_to_wav(filepath)

        recordings = request.session.get('recordings', [])
        recordings.append({
            "wav": wav_path,
            "q_index": q_index
        })

        request.session['recordings'] = recordings
        request.session.modified = True

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

def result_final(request):

    recordings = request.session.get('recordings', [])
    results = []

    total_pron = 0
    total_accent = 0
    total_accuracy = 0

    for rec in recordings:

        q_idx = rec["q_index"]
        wav = rec["wav"]

        ref_text = REFERENCE_TEXTS[q_idx]
        ref_wav = REFERENCE_AUDIOS[q_idx]

        recognized_text = transcribe_audio(wav)

        # If nothing spoken → force 0
        if recognized_text.strip() == "":
            text_score = 0.0
            pron_score = 0.0
            acc_score = 0.0
        else:
            text_score = word_accuracy(ref_text, recognized_text)

            praat_score = pronunciation_score(wav, ref_wav)

            pron_score = adjusted_pronunciation_score(
                ref_text,
                recognized_text,
                praat_score
            )

            acc_score = accent_score(wav, ref_wav)

        final_score = round(
            (text_score + pron_score + acc_score) / 3,
            2
        )

        total_pron += pron_score
        total_accent += acc_score
        total_accuracy += text_score

        results.append({
            "question": ref_text,
            "recognized": recognized_text,
            "text_score": text_score,
            "pron_score": pron_score,
            "accent_score": acc_score,
            "final_score": final_score
        })

    count = len(results)

    if count > 0:
        avg_pronunciation = round(total_pron / count, 2)
        avg_accent = round(total_accent / count, 2)
        avg_accuracy = round(total_accuracy / count, 2)

        overall_score = round(
            (avg_pronunciation + avg_accent + avg_accuracy) / 3,
            2
        )
    else:
        avg_pronunciation = avg_accent = avg_accuracy = overall_score = 0

    return render(
        request,
        "speaking/result.html",
        {
            "results": results,
            "avg_pronunciation": avg_pronunciation,
            "avg_accent": avg_accent,
            "avg_accuracy": avg_accuracy,
            "overall_score": overall_score
        }
    )
