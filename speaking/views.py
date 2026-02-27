# speaking/views.py
import re
import os
import uuid
from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from home_page.models import StudentProfile
from home_page.decorators import pretest_access_required
from .models import TestSession
from .pronunciation_engine import pronunciation_engine, QUESTIONS
import traceback


def get_session_key(request):
    """Get or create session key for anonymous users"""
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


@login_required
#@pretest_access_required('speaking')  # Uncomment when decorator is ready
def start(request):
    """Start page for speaking test"""
    # Clear any existing session data
    request.session.pop('test_session_id', None)
    request.session.pop('scores', None)
    request.session.pop('feedback', None)
    request.session.pop('word_feedback', None)
    
    return render(request, 'speaking/start.html')


@login_required
#@pretest_access_required('speaking')
def initialize_test(request):
    """Initialize a new test session with database"""
    try:
        # Check if user has already completed the test
        try:
            profile = StudentProfile.objects.get(user=request.user)
            if profile.speaking_completed:
                messages.warning(request, "You have already completed the speaking test.")
                return redirect('speaking:latest_result')
        except StudentProfile.DoesNotExist:
            profile = StudentProfile.objects.create(user=request.user)
        
        # Create new session in database
        session_id = str(uuid.uuid4())
        test_session = TestSession.objects.create(
            session_id=session_id,
            user=request.user  # Link to authenticated user
        )
        
        # Store in Django session - convert sets to lists for JSON serialization
        request.session['test_session_id'] = session_id
        request.session['current_question'] = 1
        request.session['recordings'] = {}
        
        # Track answered questions for progress bar - store as list (JSON serializable)
        request.session['answered_questions'] = []  # Empty list instead of set
        request.session['q1_word_answers'] = []     # For Q1 word-level tracking
        
        print(f"✅ Test session created: {session_id} for user: {request.user.username}")
        
        return redirect('speaking:question', q_num=1)
        
    except Exception as e:
        print(f"❌ Error creating session: {str(e)}")
        traceback.print_exc()
        return render(request, 'speaking/error.html', {
            'error': f'Could not create test session: {str(e)}'
        })


@login_required
#@pretest_access_required('speaking')
def question(request, q_num):
    """Display question page with progress tracking"""
    # Check if test is in progress
    session_id = request.session.get('test_session_id')
    if not session_id:
        return redirect('speaking:start')
    
    # Verify session belongs to current user
    try:
        test_session = TestSession.objects.get(session_id=session_id)
        if test_session.user and test_session.user != request.user:
            messages.error(request, "You don't have permission to access this test session.")
            return redirect('speaking:start')
    except TestSession.DoesNotExist:
        return redirect('speaking:start')
    
    # Validate question number
    if q_num < 1 or q_num > 5:
        return redirect('speaking:result')
    
    # Get question data
    question_data = QUESTIONS.get(q_num)
    if not question_data:
        return redirect('speaking:result')
    
    # Get answered questions for progress tracking - convert to set for easy membership testing
    answered_questions = request.session.get('answered_questions', [])
    # Convert to set for efficient lookup in template
    answered_set = set(answered_questions) if answered_questions else set()
    
    # Calculate progress percentage
    total_questions = 5  # Q1 has 5 words, but we treat as 1 question for progress
    answered_count = len(answered_questions)
    progress_percentage = int((answered_count / total_questions) * 100) if total_questions > 0 else 0
    
    # For Q1, also track word-level progress
    word_progress = {}
    if q_num == 1:
        word_answers = request.session.get('q1_word_answers', [])
        word_progress = {
            'total': 5,
            'answered': len(word_answers),
            'percentage': int((len(word_answers) / 5) * 100) if word_answers else 0,
            'answered_words': set(word_answers)  # Convert to set for template
        }
    
    context = {
        'q_num': q_num,
        'question': question_data,
        'progress_percentage': progress_percentage,
        'answered_count': answered_count,
        'total_questions': total_questions,
        'answered_questions': answered_set,  # Pass the set to template
        'word_progress': word_progress,
    }
    
    return render(request, 'speaking/question.html', context)

@login_required
@require_POST
@csrf_exempt
def submit_recording(request):
    """Handle audio recording submission with progress tracking"""
    session_id = request.session.get('test_session_id')
    if not session_id:
        return JsonResponse({'error': 'No active session'}, status=400)
    
    try:
        # Verify session belongs to current user
        test_session = get_object_or_404(TestSession, session_id=session_id)
        if test_session.user and test_session.user != request.user:
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
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
        
        # Track answered questions for progress bar - get as list
        answered_questions = request.session.get('answered_questions', [])
        if not isinstance(answered_questions, list):
            answered_questions = []
        
        # Q1 with individual words
        if q_num == 1 and word_num:
            word_num_int = int(word_num)
            filename = f"{session_id}_q1_word{word_num_int}_{timestamp}.wav"
            saved_path = fs.save(filename, audio_file)
            relative_path = f'recordings/{saved_path}'
            
            # Save to database
            setattr(test_session, f'q1_word{word_num_int}_recording', relative_path)
            test_session.save()
            
            # Track word-level answers for Q1 - use list
            q1_word_answers = request.session.get('q1_word_answers', [])
            if not isinstance(q1_word_answers, list):
                q1_word_answers = []
            
            if word_num_int not in q1_word_answers:
                q1_word_answers.append(word_num_int)
                request.session['q1_word_answers'] = q1_word_answers
            
            # If all 5 words are answered, mark Q1 as complete
            if len(q1_word_answers) == 5 and 1 not in answered_questions:
                answered_questions.append(1)
                request.session['answered_questions'] = answered_questions
            
            next_word = word_num_int + 1 if word_num_int < 5 else None
            
            return JsonResponse({
                'success': True,
                'filename': saved_path,
                'word_num': word_num_int,
                'next_word': next_word,
                'q_num': q_num,
                'word_progress': {
                    'answered': len(q1_word_answers),
                    'total': 5,
                    'percentage': int((len(q1_word_answers) / 5) * 100)
                }
            })
        
        # Q2-Q5
        else:
            filename = f"{session_id}_q{q_num}_{timestamp}.wav"
            saved_path = fs.save(filename, audio_file)
            relative_path = f'recordings/{saved_path}'
            
            setattr(test_session, f'q{q_num}_recording', relative_path)
            test_session.save()
            
            # Mark question as answered for progress
            if q_num not in answered_questions:
                answered_questions.append(q_num)
                request.session['answered_questions'] = answered_questions
            
            next_question = q_num + 1 if q_num < 5 else None
            
            # Calculate progress percentage
            total_questions = 5
            progress_percentage = int((len(answered_questions) / total_questions) * 100)
            
            return JsonResponse({
                'success': True,
                'filename': saved_path,
                'next_question': next_question,
                'progress_percentage': progress_percentage,
                'answered_count': len(answered_questions),
                'total_questions': total_questions
            })
        
    except Exception as e:
        print(f"❌ Error in submit_recording: {str(e)}")
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_POST
@csrf_exempt
def process_results(request):
    """Process all recordings and generate scores with word-level feedback"""
    session_id = request.session.get('test_session_id')
    if not session_id:
        return JsonResponse({'error': 'No active session'}, status=400)
    
    try:
        test_session = get_object_or_404(TestSession, session_id=session_id)
        
        # Verify session belongs to current user
        if test_session.user and test_session.user != request.user:
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        scores = {}
        word_feedback = {}
        
        # ========== Q1 PROCESSING ==========
        q1_word_results = []
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
                    # Transcribe student's word
                    transcribed_text = pronunciation_engine.transcribe_audio(full_path)
                    spoken_word = re.sub(r'[^\w\s]', '', transcribed_text.lower()).strip()
                    expected_word = re.sub(r'[^\w\s]', '', expected_words[w-1].lower()).strip()
                    
                    # Check correctness (10 marks)
                    if spoken_word == expected_word:
                        correctness = 10
                        
                        # Pronunciation score (0-100 → convert to 0-10)
                        raw_pron_score = pronunciation_engine.score_q1_word(full_path, w)
                        pronunciation_score = round(raw_pron_score / 10, 1)
                        
                        # Final per word = 20
                        total_score = correctness + pronunciation_score
                        
                        # Also save individual word score
                        setattr(test_session, f'q1_word{w}_score', total_score)
                else:
                    spoken_word = "File missing"
            else:
                spoken_word = "No recording"
            
            word_result = {
                'position': w,
                'expected': expected_words[w-1],
                'spoken': spoken_word,
                'correctness_score': correctness,
                'pronunciation_score': pronunciation_score,
                'total': total_score
            }
            
            q1_word_results.append(word_result)
        
        # Final Q1 Total (out of 100)
        q1_total = sum(word['total'] for word in q1_word_results)
        test_session.q1_score = q1_total
        scores['q1'] = q1_total
        word_feedback['q1'] = q1_word_results
        
        # ========== Q2-Q5 PROCESSING ==========
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
                else:
                    scores[f'q{q_num}'] = 0
                    setattr(test_session, f'q{q_num}_score', 0)
            else:
                scores[f'q{q_num}'] = 0
                setattr(test_session, f'q{q_num}_score', 0)
        
        # CRITICAL: Set completed_at timestamp
        test_session.completed_at = datetime.now()
        test_session.save()
        
        # Generate feedback
        feedback = pronunciation_engine.generate_feedback(scores)
        
        # Store in session
        request.session['scores'] = scores
        request.session['feedback'] = feedback
        request.session['word_feedback'] = word_feedback
        
        # Mark speaking test as completed in StudentProfile
        if request.user.is_authenticated:
            try:
                profile = StudentProfile.objects.get(user=request.user)
                profile.speaking_completed = True
                profile.update_pretest_status()
                print(f"✅ Speaking marked as completed for user: {request.user.username}")
                print(f"✅ Scores calculated: Q1={q1_total}, Q2={scores.get('q2', 0)}, Q3={scores.get('q3', 0)}, Q4={scores.get('q4', 0)}, Q5={scores.get('q5', 0)}")
            except StudentProfile.DoesNotExist:
                print(f"⚠️ No profile found for user: {request.user.username}")
            except Exception as e:
                print(f"❌ Error updating profile: {e}")
        
        # Clear session tracking data
        request.session.pop('answered_questions', None)
        request.session.pop('q1_word_answers', None)
        
        return JsonResponse({
            'success': True,
            'redirect': '/speaking/result/',
            'scores': scores  # Return scores for debugging
        })
        
    except TestSession.DoesNotExist:
        print(f"❌ Test session not found: {session_id}")
        return JsonResponse({'error': 'Test session not found'}, status=400)
    except Exception as e:
        print(f"❌ Error processing results: {str(e)}")
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def result(request):
    """Display test results with ownership verification"""
    scores = request.session.get('scores', {})
    feedback = request.session.get('feedback', {})
    word_feedback = request.session.get('word_feedback', {})
    
    if not scores:
        return redirect('speaking:start')
    
    # Verify that the results belong to the current user
    session_id = request.session.get('test_session_id')
    if session_id:
        try:
            test_session = TestSession.objects.get(session_id=session_id)
            if test_session.user and test_session.user != request.user:
                messages.error(request, "You don't have permission to view these results.")
                return redirect('speaking:start')
        except TestSession.DoesNotExist:
            pass
    
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
    }
    
    return render(request, 'speaking/result.html', context)


@login_required
def latest_result(request):
    """Redirect to the most recent test result"""
    session_key = get_session_key(request)
    
    # Find the most recent test session for this user
    test_session = TestSession.objects.filter(
        user=request.user,
        completed_at__isnull=False
    ).order_by('-completed_at').first()
    
    if test_session:
        # Store session data for result display
        scores = {}
        for q in range(1, 6):
            score = getattr(test_session, f'q{q}_score', 0)
            if score is not None:
                scores[f'q{q}'] = score
        
        # Generate feedback
        feedback = pronunciation_engine.generate_feedback(scores)
        
        # Store in session
        request.session['scores'] = scores
        request.session['feedback'] = feedback
        request.session['test_session_id'] = test_session.session_id
        
        return redirect('speaking:result')
    else:
        messages.warning(request, "No test results found.")
        return redirect('speaking:start')


def error_page(request):
    """Display error page"""
    return render(request, 'speaking/error.html')