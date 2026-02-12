from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.sessions.backends.db import SessionStore
from .models import ListeningTest, AudioQuestion, AnswerOption, UserResponse, TestResult
import uuid

def get_session_key(request):
    """Get or create session key for anonymous users"""
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key

def test_home(request):
    """Home page - show available tests"""
    tests = ListeningTest.objects.filter(is_active=True)
    return render(request, 'listening/test_home.html', {'tests': tests})

def start_test(request, test_id):
    """Start a new test - clear previous responses and redirect to first question"""
    test = get_object_or_404(ListeningTest, id=test_id, is_active=True)
    
    # Get session key
    session_key = get_session_key(request)
    
    # Delete any previous responses for this session
    UserResponse.objects.filter(session_key=session_key, question__test=test).delete()
    
    # Delete any previous test results for this session
    TestResult.objects.filter(session_key=session_key, test=test).delete()
    
    # Redirect to first question
    return redirect('listening:test_question', test_id=test_id, question_number=1)

def test_question(request, test_id, question_number):
    """Display a single question"""
    test = get_object_or_404(ListeningTest, id=test_id, is_active=True)
    
    # Get the question
    try:
        question = AudioQuestion.objects.get(test=test, order=question_number)
    except AudioQuestion.DoesNotExist:
        return redirect('test_home')
    
    # Get total questions count
    total_questions = test.questions.count()
    
    # Calculate progress percentage
    progress_percentage = int((question_number / total_questions) * 100)
    
    # Check if we have a previous answer for this question
    session_key = get_session_key(request)
    previous_response = UserResponse.objects.filter(
        session_key=session_key, 
        question=question
    ).first()
    
    # Get next and previous question numbers
    next_question = question_number + 1 if question_number < total_questions else None
    prev_question = question_number - 1 if question_number > 1 else None
    
    context = {
        'test': test,
        'question': question,
        'question_number': question_number,
        'total_questions': total_questions,
        'progress_percentage': progress_percentage,  # Add this
        'next_question': next_question,
        'prev_question': prev_question,
        'selected_option': previous_response.selected_option_id if previous_response else None,
    }
    
    return render(request, 'listening/test_question.html', context)

@require_POST
def submit_answer(request, test_id, question_number):
    """Handle answer submission via AJAX"""
    test = get_object_or_404(ListeningTest, id=test_id)
    question = get_object_or_404(AudioQuestion, test=test, order=question_number)
    
    option_id = request.POST.get('option_id')
    if not option_id:
        return JsonResponse({'error': 'No option selected'}, status=400)
    
    try:
        selected_option = AnswerOption.objects.get(id=option_id, question=question)
    except AnswerOption.DoesNotExist:
        return JsonResponse({'error': 'Invalid option'}, status=400)
    
    # Save the response
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

def submit_test(request, test_id):
    """Submit the entire test and calculate results"""
    if request.method != 'POST':
        return redirect('test_question', test_id=test_id, question_number=1)
    
    test = get_object_or_404(ListeningTest, id=test_id)
    session_key = get_session_key(request)
    
    # Calculate score
    responses = UserResponse.objects.filter(
        session_key=session_key, 
        question__test=test
    )
    
    correct_count = 0
    total_questions = test.questions.count()
    
    for response in responses:
        if response.selected_option.is_correct:
            correct_count += 1
    
    # Save test result
    test_result = TestResult.objects.create(
        session_key=session_key,
        test=test,
        score=correct_count,
        total_questions=total_questions
    )
    
    return redirect('listening:test_results', result_id=test_result.id)

def test_results(request, result_id):
    """Display test results"""
    result = get_object_or_404(TestResult, id=result_id)
    
    # Get all responses for this test
    responses = UserResponse.objects.filter(
        session_key=result.session_key,
        question__test=result.test
    ).select_related('question', 'selected_option')
    
    # Create a dictionary of responses by question ORDER (not ID)
    responses_by_question = {}
    for r in responses:
        responses_by_question[r.question.order] = r
    
    # Get all questions with their correct answers
    questions = AudioQuestion.objects.filter(test=result.test).order_by('order')
    
    context = {
        'result': result,
        'questions': questions,
        'responses_by_question': responses_by_question,
        'percentage': result.percentage(),
    }
    
    return render(request, 'listening/test_results.html', context)