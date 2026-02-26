import re
import os
import uuid
from datetime import datetime
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from .models import TestSession
from .pronunciation_engine import pronunciation_engine, QUESTIONS


def start(request):
    # Only remove speaking-related session data
    request.session.pop('test_session_id', None)
    request.session.pop('scores', None)
    request.session.pop('feedback', None)
    request.session.pop('word_feedback', None)
    
    return render(request, 'speaking/start.html')

def initialize_test(request):
    """Initialize a new test session with database"""
    try:
        # Create new session in database
        session_id = str(uuid.uuid4())
        test_session = TestSession.objects.create(session_id=session_id)
        
        # Store in Django session
        request.session['test_session_id'] = session_id
        request.session['current_question'] = 1
        request.session['recordings'] = {}
        
        print(f"Created database session: {session_id}")  # Debug
        
        return redirect('speaking:question', q_num=1)
        
    except Exception as e:
        print(f"Error creating session: {e}")
        return render(request, 'speaking/error.html', {
            'error': f'Could not create test session: {str(e)}'
        })

def question(request, q_num):
    """Display question page"""
    # Check if test is in progress
    session_id = request.session.get('test_session_id')
    if not session_id:
        return redirect('speaking:start')
    
    # Validate question number
    if q_num < 1 or q_num > 5:
        return redirect('speaking:result')
    
    # Get question data
    question_data = QUESTIONS.get(q_num)
    if not question_data:
        return redirect('speaking:result')
    
    context = {
        'q_num': q_num,
        'question': question_data,
    }
    
    return render(request, 'speaking/question.html', context)

@csrf_exempt
def submit_recording(request):
    """Handle audio recording submission"""
    if request.method != 'POST':
        return HttpResponseBadRequest('Only POST method allowed')
    
    session_id = request.session.get('test_session_id')
    if not session_id:
        return JsonResponse({'error': 'No active session'}, status=400)
    
    try:
        q_num = int(request.POST.get('q_num', 0))
        word_num = request.POST.get('word_num')
        
        if q_num < 1 or q_num > 5:
            return JsonResponse({'error': 'Invalid question number'}, status=400)
        
        audio_file = request.FILES.get('audio')
        if not audio_file:
            return JsonResponse({'error': 'No audio file provided'}, status=400)
        
        recordings_dir = os.path.join(settings.MEDIA_ROOT, 'recordings')
        os.makedirs(recordings_dir, exist_ok=True)
        
        fs = FileSystemStorage(location=recordings_dir)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Get or create test session
        test_session, created = TestSession.objects.get_or_create(session_id=session_id)
        
        # Q1 with individual words
        if q_num == 1 and word_num:
            word_num_int = int(word_num)
            filename = f"{session_id}_q1_word{word_num_int}_{timestamp}.wav"
            saved_path = fs.save(filename, audio_file)
            relative_path = f'recordings/{saved_path}'
            
            # Save to database
            setattr(test_session, f'q1_word{word_num_int}_recording', relative_path)
            test_session.save()
            
            print(f"✅ Q1 Word {word_num_int} saved: {relative_path}")
            
            next_word = word_num_int + 1 if word_num_int < 5 else None
            
            return JsonResponse({
                'success': True,
                'filename': saved_path,
                'word_num': word_num_int,
                'next_word': next_word,
                'q_num': q_num
            })
        
        # Q2-Q5
        else:
            filename = f"{session_id}_q{q_num}_{timestamp}.wav"
            saved_path = fs.save(filename, audio_file)
            relative_path = f'recordings/{saved_path}'
            
            setattr(test_session, f'q{q_num}_recording', relative_path)
            test_session.save()
            
            next_question = q_num + 1 if q_num < 5 else None
            
            return JsonResponse({
                'success': True,
                'filename': saved_path,
                'next_question': next_question
            })
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def process_results(request):
    """Process all recordings and generate scores with word-level feedback"""
    if request.method != 'POST':
        return HttpResponseBadRequest('Only POST method allowed')
    
    session_id = request.session.get('test_session_id')
    if not session_id:
        return JsonResponse({'error': 'No active session'}, status=400)
    
    try:
        test_session = TestSession.objects.get(session_id=session_id)
        
        scores = {}
        word_feedback = {}
        
        # ========== Q1 PROCESSING WITH RECOVERY ==========
        print("🔍 Checking for missing Q1 recordings...")
        import glob
        for w in range(1, 6):
            if not getattr(test_session, f'q1_word{w}_recording', None):
                pattern = os.path.join(
                    settings.MEDIA_ROOT,
                    'recordings',
                    f'{session_id}_q1_word{w}_*.wav'
                )
                files = glob.glob(pattern)
                if files:
                    rel_path = f'recordings/{os.path.basename(files[0])}'
                    setattr(test_session, f'q1_word{w}_recording', rel_path)
                    print(f"✅ Recovered Word {w}: {rel_path}")
        test_session.save()
        
        q1_word_results = []

        # Expected words
        expected_words = ['comfortable', 'vegetable', 'often', 'engineer', 'laboratory']
        
        for w in range(1, 6):
            word_field = f'q1_word{w}_recording'
            word_path = getattr(test_session, word_field)
            
            spoken_word = "Not recorded"
            correctness = 0
            pronunciation_score = 0
            total_score = 0
            
            if word_path:
                full_path = os.path.join(settings.MEDIA_ROOT, word_path)
                
                if os.path.exists(full_path):
                    
                    # 🔥 STEP 1: Transcribe student's word
                  
                    transcribed_text = pronunciation_engine.transcribe_audio(full_path)

            
                    spoken_word = re.sub(r'[^\w\s]', '', transcribed_text.lower()).strip()

                    expected_word = re.sub(r'[^\w\s]', '', expected_words[w-1].lower()).strip()
                    
                    # 🔥 STEP 2: Check correctness (10 marks)
                    if spoken_word == expected_word:
                        correctness = 10
                        
                        # 🔥 STEP 3: Pronunciation score (0-100 → convert to 0-10)
                        raw_pron_score = pronunciation_engine.score_q1_word(full_path, w)
                        pronunciation_score = round(raw_pron_score / 10, 1)
                        
                        # Final per word = 20
                        total_score = correctness + pronunciation_score
                        
                        print(f"✅ Word {w} correct | Pron: {pronunciation_score}/10 | Total: {total_score}/20")
                    else:
                        correctness = 0
                        pronunciation_score = 0
                        total_score = 0
                        print(f"❌ Word {w} incorrect (Spoken: {spoken_word})")
                
                else:
                    spoken_word = "File missing"
                    print(f"❌ Q1 Word {w}: File missing")
            else:
                spoken_word = "No recording"
                print(f"❌ Q1 Word {w}: No recording")
            
            word_result = {
                'position': w,
                'expected': expected_words[w-1],
                'spoken': spoken_word,
                'correctness_score': correctness,
                'pronunciation_score': pronunciation_score,
                'total': total_score
            }
            
            q1_word_results.append(word_result)
        
        # 🔥 Final Q1 Total (out of 100)
        q1_total = sum(word['total'] for word in q1_word_results)
        test_session.q1_score = q1_total
        scores['q1'] = q1_total
        word_feedback['q1'] = q1_word_results
        
        print(f"📊 Q1 Final Score: {q1_total}/100")
        
        
        # ========== Q2-Q5 PROCESSING (UNCHANGED) ==========
        for q_num in range(2, 6):
            recording_field = f'q{q_num}_recording'
            recording_path = getattr(test_session, recording_field)
            
            if recording_path:
                full_path = os.path.join(settings.MEDIA_ROOT, recording_path)
                if os.path.exists(full_path):
                    score, word_results = pronunciation_engine.score_recording(full_path, q_num)
                    scores[f'q{q_num}'] = score
                    word_feedback[f'q{q_num}'] = word_results
                    
                    setattr(test_session, f'q{q_num}_score', score)
                    print(f"✅ Q{q_num}: Score {score}")
                else:
                    print(f"❌ Q{q_num}: File missing")
                    scores[f'q{q_num}'] = 0
                    setattr(test_session, f'q{q_num}_score', 0)
            else:
                print(f"❌ Q{q_num}: No recording")
                scores[f'q{q_num}'] = 0
                setattr(test_session, f'q{q_num}_score', 0)
        
        test_session.completed_at = datetime.now()
        test_session.save()
        
        feedback = pronunciation_engine.generate_feedback(scores)
        
        request.session['scores'] = scores
        request.session['feedback'] = feedback
        request.session['word_feedback'] = word_feedback
        
        print(f"✅ Processed results: {scores}")
        
        return JsonResponse({
            'success': True,
            'redirect': '/result/'
        })
        
    except Exception as e:
        print(f"❌ Error processing results: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)
    
def result(request):
    """Display test results"""
    
    print("\n" + "="*50)
    print("🔍 RESULT PAGE ACCESSED")
    print("="*50)
    
    # Get scores from session
    scores = request.session.get('scores', {})
    feedback = request.session.get('feedback', {})
    word_feedback = request.session.get('word_feedback', {})
    
    print(f"📊 Scores: {scores}")
    print(f"📝 Word feedback keys: {word_feedback.keys()}")
    print(f"🔍 Q1 data exists: {'q1' in word_feedback}")
    
    if not scores:
        print("⚠️ No scores found - redirecting to start")
        return redirect('speaking:start')
    
    # Try to get the test session from database for additional info
    session_id = request.session.get('test_session_id')
    test_session = None
    if session_id:
        try:
            test_session = TestSession.objects.get(session_id=session_id)
        except TestSession.DoesNotExist:
            pass
    
    # ===== THIS IS THE NEW CODE THAT FIXES THE PROBLEM =====
    # Mark speaking test as completed in StudentProfile
    from home_page.models import StudentProfile
    try:
        profile = StudentProfile.objects.get(user=request.user)
        profile.speaking_completed = True
        profile.update_pretest_status()
        print(f"✅ Speaking marked as completed for user: {request.user.username}")
    except StudentProfile.DoesNotExist:
        print(f"⚠️ No profile found for user: {request.user.username}")
    except Exception as e:
        print(f"❌ Error updating profile: {e}")
    # ===== END OF NEW CODE =====
    
    context = {
        'scores': scores,
        'feedback': feedback,
        'word_feedback': word_feedback,
        'q1_score': scores.get('q1', 0),
        'q2_score': scores.get('q2', 0),
        'q3_score': scores.get('q3', 0),
        'q4_score': scores.get('q4', 0),
        'q5_score': scores.get('q5', 0),
        'average': feedback.get('average', 0),
        'level': feedback.get('level', 'N/A'),
        'message': feedback.get('message', ''),
        'session': test_session
    }
    
    print("✅ Rendering result page")
    return render(request, 'speaking/result.html', context)

def clear_session(request):
    request.session.pop('test_session_id', None)
    request.session.pop('scores', None)
    request.session.pop('feedback', None)
    request.session.pop('word_feedback', None)
    
    return redirect('start')

def error_page(request):
    """Display error page"""
    return render(request, 'speaking/error.html')