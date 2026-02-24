# listening/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseRedirect
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from home_page.models import StudentProfile
from home_page.decorators import pretest_access_required
from .models import ListeningTest, AudioQuestion, AnswerOption, UserResponse, TestResult, QuestionType
import json
import random

def get_session_key(request):
    """Get or create session key for anonymous users"""
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key

@login_required
#@pretest_access_required('listening')  # Uncomment when decorator is ready
def index(request):
    """Home page - show available test"""
    test = ListeningTest.objects.filter(is_active=True).first()
    return render(request, 'listening/index.html', {'test': test})

@login_required
#@pretest_access_required('listening')
def instructions(request, test_id):
    """Show test instructions"""
    test = get_object_or_404(ListeningTest, id=test_id, is_active=True)
    return render(request, 'listening/instructions.html', {'test': test})

@login_required
#@pretest_access_required('listening')
def questions(request, test_id):
    """Display all questions on one page"""
    test = get_object_or_404(ListeningTest, id=test_id, is_active=True)
    session_key = get_session_key(request)
    
    # Get shuffled question IDs from session or create new shuffle
    shuffled_ids = request.session.get(f'shuffled_questions_{test_id}')
    
    if not shuffled_ids:
        # First time - create shuffled order
        all_questions = list(AudioQuestion.objects.filter(test=test))
        random.shuffle(all_questions)
        shuffled_ids = [q.id for q in all_questions]
        request.session[f'shuffled_questions_{test_id}'] = shuffled_ids
    else:
        # Get questions in shuffled order
        all_questions = []
        for q_id in shuffled_ids:
            try:
                q = AudioQuestion.objects.get(id=q_id)
                all_questions.append(q)
            except AudioQuestion.DoesNotExist:
                continue
    
    total_questions = len(all_questions)
    
    # Get current question number from session or default to 1
    current_q = request.session.get(f'current_question_{test_id}', 1)
    
    # Get current question object (from shuffled list)
    current_question_obj = all_questions[current_q - 1] if all_questions else None
    
    # Get all responses for this session
    responses = UserResponse.objects.filter(
        session_key=session_key,
        question__test=test
    )
    
    # Create a dictionary of selected options by question id
    selected_options = {}
    typed_answers = {}
    answered_questions = set()
    
    for response in responses:
        answered_questions.add(response.question.id)
        if response.question.is_mcq() and response.selected_option:
            selected_options[response.question.id] = response.selected_option.id
        elif response.question.is_typing():
            typed_answers[response.question.id] = response.typed_answer
    
    # Initialize replay counts dictionary in session if not exists
    if f'replay_counts_{test_id}' not in request.session:
        # Initialize with 3 replays for each question
        replay_counts = {}
        for q in all_questions:
            replay_counts[str(q.id)] = 3
        request.session[f'replay_counts_{test_id}'] = replay_counts
    
    # Get replay counts for all questions
    replay_counts = request.session.get(f'replay_counts_{test_id}', {})
    
    # Get replay count for current question
    current_replay_count = 3
    if current_question_obj and str(current_question_obj.id) in replay_counts:
        current_replay_count = replay_counts[str(current_question_obj.id)]
    
    # Calculate progress percentage based on answered questions
    answered_count = len(answered_questions)
    progress_percentage = int((answered_count / total_questions) * 100) if total_questions > 0 else 0
    
    context = {
        'test': test,
        'all_questions': all_questions,
        'total_questions': total_questions,
        'question_number': current_q,
        'current_question': current_question_obj,
        'replay_count': current_replay_count,
        'replay_counts': replay_counts,
        'selected_options': selected_options,
        'typed_answers': typed_answers,
        'progress_percentage': progress_percentage,
        'answered_count': answered_count,
        'answered_questions': answered_questions,
    }
    return render(request, 'listening/questions.html', context)

@require_POST
def update_replay(request):
    """Update replay count for a specific question via AJAX"""
    data = json.loads(request.body)
    replay_count = data.get('replay_count')
    test_id = data.get('test_id')
    question_id = data.get('question_id')
    
    if test_id and question_id:
        replay_counts = request.session.get(f'replay_counts_{test_id}', {})
        replay_counts[str(question_id)] = replay_count
        request.session[f'replay_counts_{test_id}'] = replay_counts
        return JsonResponse({'success': True, 'replay_count': replay_count})
    
    return JsonResponse({'success': False, 'error': 'Missing parameters'})

@require_POST
def navigate_question(request, test_id):
    """Save current question number to session"""
    data = json.loads(request.body)
    question_number = data.get('question_number')
    request.session[f'current_question_{test_id}'] = question_number
    return JsonResponse({'success': True})

@require_POST
def submit_answer(request, test_id):
    """Handle answer submission for both MCQ and typing questions"""
    data = json.loads(request.body)
    question_id = data.get('question_id')
    option_id = data.get('option_id')
    typed_answer = data.get('typed_answer', '').strip()
    
    question = get_object_or_404(AudioQuestion, id=question_id, test_id=test_id)
    session_key = get_session_key(request)
    
    # Delete previous response
    UserResponse.objects.filter(session_key=session_key, question=question).delete()
    
    if question.is_mcq() and option_id:
        # Handle MCQ submission
        try:
            selected_option = AnswerOption.objects.get(id=option_id, question=question)
            UserResponse.objects.create(
                session_key=session_key,
                question=question,
                selected_option=selected_option,
                user=request.user if request.user.is_authenticated else None
            )
        except AnswerOption.DoesNotExist:
            return JsonResponse({'error': 'Invalid option'}, status=400)
            
    elif question.is_typing() and typed_answer:
        # Handle typing submission
        UserResponse.objects.create(
            session_key=session_key,
            question=question,
            typed_answer=typed_answer,
            user=request.user if request.user.is_authenticated else None
        )
    
    return JsonResponse({'success': True})

@login_required
#@pretest_access_required('listening')
def submit_test(request, test_id):
    """Submit the entire test and calculate results"""
    if request.method != 'POST':
        return redirect('listening:questions', test_id=test_id)
    
    # Get or create profile (silently check pretest status but don't act on it)
    try:
        profile = StudentProfile.objects.get(user=request.user)
        if profile.pretest_completed:
            messages.info(request, "You have already completed the pretest.")
            return redirect('home_page:pretest_results')
        if profile.listening_completed:
            messages.warning(request, "You have already completed the listening test.")
            return redirect('listening:latest_result')
    except StudentProfile.DoesNotExist:
        profile = StudentProfile.objects.create(user=request.user)
        pretest_completed = False
    
    test = get_object_or_404(ListeningTest, id=test_id)
    session_key = get_session_key(request)
    
    responses = UserResponse.objects.filter(session_key=session_key, question__test=test)
    
    correct_count = 0
    total_questions = test.questions.count()
    needs_manual_grading = False
    
    # Calculate score
    for response in responses:
        if response.is_correct():
            correct_count += 1
        elif response.question.is_typing() and not response.is_auto_graded:
            needs_manual_grading = True
    
    # Calculate percentage
    percentage = (correct_count / total_questions * 100) if total_questions > 0 else 0
    
    # Determine level based on percentage
    if percentage < 40:
        level = "Basic"
        feedback = "Start with foundational listening exercises"
    elif percentage < 80:
        level = "Intermediate"
        feedback = "Good progress, keep practicing regularly"
    else:
        level = "Advanced"
        feedback = "Excellent ,Regular practice will keep you sharp."
    
    # Create test result
    test_result = TestResult.objects.create(
        session_key=session_key,
        test=test,
        score=correct_count,
        total_questions=total_questions,
        percentage=percentage,
        level=level,
        feedback=feedback,
        pending_manual_grading=needs_manual_grading,
        user=request.user 
    )
    
    # Update existing responses to link to user
    UserResponse.objects.filter(session_key=session_key, question__test=test).update(user=request.user)
    
    # Clear session data
    if f'replay_counts_{test_id}' in request.session:
        del request.session[f'replay_counts_{test_id}']
    if f'current_question_{test_id}' in request.session:
        del request.session[f'current_question_{test_id}']
    if f'shuffled_questions_{test_id}' in request.session:
        del request.session[f'shuffled_questions_{test_id}']
    
    # Mark listening as completed
    profile.listening_completed = True
    profile.update_pretest_status()
    
    # Only show test completion messages, no pretest messages
    if needs_manual_grading:
        messages.info(request, "Your typing answers will be graded by an instructor.")
    else:
        messages.success(request, "Listening test completed successfully!")
    
    return redirect('listening:result', result_id=test_result.id)

@login_required
def result(request, result_id):
    """Display test results"""
    result = get_object_or_404(TestResult, id=result_id)
    
    # Verify that the result belongs to this user
    if result.user and result.user != request.user:
        messages.error(request, "You don't have permission to view these results.")
        return redirect('home_page:home')
    
    # Get all responses for this test
    responses = UserResponse.objects.filter(
        session_key=result.session_key,
        question__test=result.test
    ).select_related('question', 'selected_option')
    
    # Create a dictionary of responses by question order
    responses_by_question = {r.question.order: r for r in responses}
    
    # Get all questions
    questions = AudioQuestion.objects.filter(test=result.test).order_by('order')
    
    # Prepare question data for template
    question_data = []
    correct_count = 0
    incorrect_count = 0
    mcq_correct = 0
    mcq_total = 0
    typing_correct = 0
    typing_total = 0
    typing_pending = []
    
    for question in questions:
        response = responses_by_question.get(question.order)
        is_correct = response.is_correct() if response else False
        needs_grading = (question.is_typing() and response and 
                        not response.is_auto_graded)
        
        if is_correct:
            correct_count += 1
        else:
            incorrect_count += 1
        
        if question.is_mcq():
            mcq_total += 1
            if is_correct:
                mcq_correct += 1
        else:  # typing
            typing_total += 1
            if is_correct:
                typing_correct += 1
            elif needs_grading:
                typing_pending.append(question.order)
        
        # Get user's answer
        user_answer = ""
        if response:
            if question.is_mcq() and response.selected_option:
                user_answer = response.selected_option.text
            elif question.is_typing():
                user_answer = response.typed_answer
        
        # Get correct answer for display
        correct_answer = ""
        if question.is_mcq():
            correct_option = question.options.filter(is_correct=True).first()
            if correct_option:
                correct_answer = correct_option.text
        elif question.correct_answer_text:
            correct_answer = question.correct_answer_text
        
        question_data.append({
            'question': question,
            'response': response,
            'has_response': response is not None,
            'is_correct': is_correct,
            'user_answer': user_answer,
            'correct_answer': correct_answer,
            'needs_grading': needs_grading,
        })
    
    context = {
        'result': result,
        'questions': questions,
        'question_data': question_data,
        'score': result.score,
        'total': result.total_questions,
        'percentage': result.percentage,
        'correct_count': correct_count,
        'incorrect_count': incorrect_count,
        'mcq_correct': mcq_correct,
        'mcq_total': mcq_total,
        'typing_correct': typing_correct,
        'typing_total': typing_total,
        'typing_pending': typing_pending,
        'level': result.level,
        'feedback': result.feedback,
        'needs_manual_grading': result.pending_manual_grading,
        'detailed_results': question_data,
    }
    
    return render(request, 'listening/result.html', context)

@login_required
#@pretest_access_required('listening')
def start_test(request, test_id):
    """Start a new test - clear previous responses and shuffle questions"""
    test = get_object_or_404(ListeningTest, id=test_id, is_active=True)
    
    # Get session key
    session_key = get_session_key(request)
    
    # Delete any previous responses for this session
    UserResponse.objects.filter(session_key=session_key, question__test=test).delete()
    
    # Delete any previous test results for this session
    TestResult.objects.filter(session_key=session_key, test=test).delete()
    
    # Get all questions and create shuffled order
    all_questions = list(AudioQuestion.objects.filter(test=test))
    random.shuffle(all_questions)
    
    # Store shuffled question IDs in session
    question_ids = [q.id for q in all_questions]
    request.session[f'shuffled_questions_{test_id}'] = question_ids
    
    # Reset replay counts for each question
    replay_counts = {}
    for q in all_questions:
        replay_counts[str(q.id)] = 3
    request.session[f'replay_counts_{test_id}'] = replay_counts
    
    # Reset current question to 1
    request.session[f'current_question_{test_id}'] = 1
    
    # Redirect to instructions
    return redirect('listening:instructions', test_id=test_id)

def test_question(request, test_id, question_number):
    """Legacy view - redirect to questions page"""
    test = get_object_or_404(ListeningTest, id=test_id)
    request.session[f'current_question_{test_id}'] = question_number
    return redirect('listening:questions', test_id=test_id)

def test_results(request, result_id):
    """Legacy view - redirect to result page"""
    return redirect('listening:result', result_id=result_id)

@login_required
def latest_result(request):
    """Redirect to the most recent test result"""
    session_key = get_session_key(request)
    result = TestResult.objects.filter(session_key=session_key, user=request.user).last()
    if result:
        return redirect('listening:result', result_id=result.id)
    else:
        messages.warning(request, "No results found.")
        return redirect('listening:index')