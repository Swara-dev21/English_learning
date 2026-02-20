# listening/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseRedirect
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from home_page.models import StudentProfile
from home_page.decorators import pretest_access_required, ajax_pretest_check
from .models import ListeningTest, AudioQuestion, AnswerOption, UserResponse, TestResult
import uuid
import json


def get_session_key(request):
    """Get or create session key for anonymous users"""
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


def update_replay(request):
    """Update replay count via AJAX"""
    if request.method == 'POST':
        data = json.loads(request.body)
        request.session['replay_count'] = data.get('replay_count', 0)
        return JsonResponse({'success': True})
    return JsonResponse({'success': False})


@login_required
@pretest_access_required()  # Only checks if pretest is completed
def index(request):
    """Home page - show available tests (replaces test_home)"""
    tests = ListeningTest.objects.filter(is_active=True)
    # If only one test exists, you might want to show it directly
    test = tests.first() if tests.count() == 1 else None
    return render(request, 'listening/index.html', {'tests': tests, 'test': test})


@login_required
@pretest_access_required('listening')
def instructions(request, test_id):
    """Instructions page before starting test"""
    test = get_object_or_404(ListeningTest, id=test_id, is_active=True)
    
    # ✅ CHECK IF USER ALREADY COMPLETED THIS TEST
    existing_result = TestResult.objects.filter(user=request.user, test=test).first()
    if existing_result:
        messages.info(request, "You've already completed the listening test. Continuing to speaking test...")
        return redirect('speaking:index')  # Redirect to speaking test
    
    # Store test start time in session for timer
    request.session['test_start_time'] = request.session.get('test_start_time', 0)
    # Initialize replay count
    request.session['replay_count'] = 3
    
    context = {
        'test': test,
    }
    return render(request, 'listening/instructions.html', context)


@login_required
@pretest_access_required('listening')
def audio_passage(request, test_id):
    """Audio passage page with replay tracking"""
    test = get_object_or_404(ListeningTest, id=test_id, is_active=True)
    
    # ✅ CHECK IF USER ALREADY COMPLETED THIS TEST
    existing_result = TestResult.objects.filter(user=request.user, test=test).first()
    if existing_result:
        messages.info(request, "You've already completed the listening test. Continuing to speaking test...")
        return redirect('speaking:index')  # Redirect to speaking test
    
    # Get replay count from session
    replay_count = request.session.get('replay_count', 3)
    
    # Get the first question to access audio filename
    first_question = AudioQuestion.objects.filter(test=test).first()
    
    context = {
        'test': test,
        'replay_count': replay_count,
        'question': first_question,  # Pass question for audio filename
    }
    return render(request, 'listening/audio_passage.html', context)


@login_required
@pretest_access_required('listening')
def start_test(request, test_id):
    """Start a new test - clear previous responses and redirect to questions page"""
    test = get_object_or_404(ListeningTest, id=test_id, is_active=True)
    
    # ✅ CHECK IF USER ALREADY COMPLETED THIS TEST
    existing_result = TestResult.objects.filter(user=request.user, test=test).first()
    if existing_result:
        messages.info(request, "You've already completed the listening test. Continuing to speaking test...")
        return redirect('speaking:index')  # Redirect to speaking test
    
    # Get session key
    session_key = get_session_key(request)
    
    # Delete any previous responses for this session
    UserResponse.objects.filter(session_key=session_key, question__test=test).delete()
    
    # Delete any previous test results for this session
    TestResult.objects.filter(session_key=session_key, test=test).delete()
    
    # Initialize current question in session
    request.session[f'current_q_{test_id}'] = 1
    
    # Redirect to questions page
    return redirect('listening:questions', test_id=test_id)


@login_required
@pretest_access_required('listening')
def questions(request, test_id):
    """Display questions page - shows current question with audio player"""
    test = get_object_or_404(ListeningTest, id=test_id, is_active=True)
    
    # ✅ CHECK IF USER ALREADY COMPLETED THIS TEST
    existing_result = TestResult.objects.filter(user=request.user, test=test).first()
    if existing_result:
        messages.info(request, "You've already completed the listening test. Continuing to speaking test...")
        return redirect('speaking:start')  # Redirect to speaking test
    
    # Get current question number from session or default to 1
    question_number = request.session.get(f'current_q_{test_id}', 1)
    
    # Get the question
    try:
        question = AudioQuestion.objects.get(test=test, order=question_number)
    except AudioQuestion.DoesNotExist:
        messages.error(request, "Question not found.")
        return redirect('listening:index')
    
    # Get all questions for this test
    all_questions = AudioQuestion.objects.filter(test=test).order_by('order')
    total_questions = all_questions.count()
    
    # Calculate progress percentage
    progress_percentage = int((question_number / total_questions) * 100) if total_questions > 0 else 0
    
    # Get session key and previous response
    session_key = get_session_key(request)
    previous_response = UserResponse.objects.filter(
        session_key=session_key, 
        question=question
    ).first()
    
    # Navigation
    next_question = question_number + 1 if question_number < total_questions else None
    prev_question = question_number - 1 if question_number > 1 else None
    
    # Get replay count from session
    replay_count = request.session.get('replay_count', 3)
    
    # Prepare questions list with answered status for dots navigation
    questions_status = []
    for q in all_questions:
        has_response = UserResponse.objects.filter(
            session_key=session_key, 
            question=q
        ).exists()
        questions_status.append({
            'order': q.order,
            'answered': has_response,
            'active': q.order == question_number
        })
    
    # Get selected option ID if exists
    selected_option_id = None
    if previous_response and previous_response.selected_option:
        selected_option_id = previous_response.selected_option.id
    
    context = {
        'test': test,
        'question': question,  # Current question
        'all_questions': all_questions,  # ALL questions
        'questions_status': questions_status,
        'question_number': question_number,
        'total_questions': total_questions,
        'progress_percentage': progress_percentage,
        'next_question': next_question,
        'prev_question': prev_question,
        'selected_option': selected_option_id,
        'replay_count': replay_count,
    }
    
    return render(request, 'listening/questions.html', context)


@login_required
@ajax_pretest_check('listening')
@require_POST
def submit_answer(request, test_id):
    """Handle answer submission via AJAX"""
    try:
        data = json.loads(request.body)
        question_id = data.get('question_id')
        option_id = data.get('option_id')
        
        if not question_id or not option_id:
            return JsonResponse({'error': 'Missing data'}, status=400)
        
        question = get_object_or_404(AudioQuestion, id=question_id, test_id=test_id)
        selected_option = get_object_or_404(AnswerOption, id=option_id, question=question)
        
        session_key = get_session_key(request)
        
        # Delete any previous response for this question
        UserResponse.objects.filter(session_key=session_key, question=question).delete()
        
        # Create new response
        UserResponse.objects.create(
            session_key=session_key,
            question=question,
            selected_option=selected_option
        )
        
        return JsonResponse({'success': True})
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def navigate_question(request, test_id):
    """Navigate to a specific question (for prev/next buttons)"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            question_number = data.get('question_number')
            
            if question_number:
                request.session[f'current_q_{test_id}'] = question_number
                return JsonResponse({'success': True})
            
            return JsonResponse({'error': 'Question number missing'}, status=400)
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    return JsonResponse({'error': 'Invalid request method'}, status=400)


@login_required
def submit_test(request, test_id):
    """Submit the entire test and calculate results"""
    if request.method != 'POST':
        return redirect('listening:questions', test_id=test_id)
    
    test = get_object_or_404(ListeningTest, id=test_id)
    session_key = get_session_key(request)
    
    # ✅ CHECK IF ALREADY SUBMITTED
    existing_result = TestResult.objects.filter(user=request.user, test=test).first()
    if existing_result:
        messages.info(request, "Test already completed. Continuing to speaking test...")
        return redirect('speaking:start')  # Redirect to speaking test
    
    # Get all responses for this test
    responses = UserResponse.objects.filter(session_key=session_key, question__test=test)
    
    # Calculate score
    correct_count = 0
    total_questions = test.questions.count()
    
    for response in responses:
        if response.selected_option.is_correct:
            correct_count += 1
    
    # Create test result
    test_result = TestResult.objects.create(
        session_key=session_key,
        test=test,
        score=correct_count,
        total_questions=total_questions,
        user=request.user
    )
    
    # Mark listening as completed in profile
    try:
        profile = StudentProfile.objects.get(user=request.user)
        profile.listening_completed = True
        profile.update_pretest_status()
        messages.success(request, "Listening test completed successfully!")
    except StudentProfile.DoesNotExist:
        messages.warning(request, "Test completed, but profile not found.")
    
    # Clear session data for this test
    if f'current_q_{test_id}' in request.session:
        del request.session[f'current_q_{test_id}']
    
    # ✅ REDIRECT TO SPEAKING TEST
    return redirect('listening:result', result_id=test_result.id)

@login_required
def result(request, result_id):
    """Display listening test results (replaces test_results)"""
    result = get_object_or_404(TestResult, id=result_id)
    
    # Verify that the result belongs to this user
    if result.user and result.user != request.user:
        messages.error(request, "You don't have permission to view these results.")
        return redirect('listening:index')
    
    # Get all responses for this test
    responses = UserResponse.objects.filter(
        session_key=result.session_key,
        question__test=result.test
    ).select_related('question', 'selected_option')
    
    # Create a dictionary of responses by question order
    responses_by_question = {r.question.order: r for r in responses}
    
    # Get all questions
    questions = AudioQuestion.objects.filter(test=result.test).order_by('order')
    
    # Prepare detailed results for template
    detailed_results = []
    correct_count = 0
    incorrect_count = 0
    
    for question in questions:
        response = responses_by_question.get(question.order)
        is_correct = False
        
        if response and response.selected_option.is_correct:
            is_correct = True
            correct_count += 1
        elif response:
            incorrect_count += 1
        else:
            incorrect_count += 1  # Count unanswered as incorrect
        
        # Get all options for this question
        options = AnswerOption.objects.filter(question=question)
        
        # Get correct option text
        correct_option = options.filter(is_correct=True).first()
        
        detailed_results.append({
            'question': question,
            'response': response,
            'has_response': response is not None,
            'is_correct': is_correct,
            'options': options,
            'selected_option_id': response.selected_option_id if response else None,
            'selected_option_text': response.selected_option.text if response else None,
            'correct_option_id': correct_option.id if correct_option else None,
            'correct_option_text': correct_option.text if correct_option else None,
        })
    
    # Calculate percentage
    percentage = (result.score / result.total_questions * 100) if result.total_questions > 0 else 0
    
    # Determine level and feedback based on score
    if result.score <= 2:
        level = "Beginner"
        feedback = "Focus on listening comprehension practice. Try to listen to English audio daily."
    elif result.score <= 4:
        level = "Intermediate"
        feedback = "Good understanding! Keep practicing to improve further."
    else:
        level = "Advanced"
        feedback = "Excellent listening skills! You have strong comprehension abilities."
    
    context = {
    'result': result,
    'test': result.test,
    'questions': questions,
    'detailed_results': detailed_results,  # This is what you should use in template
    'percentage': round(percentage, 1),
    'score': result.score,
    'total': result.total_questions,
    'correct_count': correct_count,
    'incorrect_count': incorrect_count,
    'level': level,
    'feedback': feedback,
}
    
    return render(request, 'listening/result.html', context)


@login_required
def latest_result(request):
    """Redirect to the most recent test result"""
    result = TestResult.objects.filter(user=request.user).last()
    if result:
        return redirect('listening:result', result_id=result.id)
    else:
        messages.warning(request, "No results found.")
        return redirect('listening:index')