# reading/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseRedirect, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from home_page.models import StudentProfile
from home_page.models import SuspiciousActivity
from .models import Test, Question, ReadingUserResponse, ReadingResult
from writing.models import WritingTest
import logging
import json
from django.views.decorators.csrf import csrf_exempt
import random
from home_page.models import SuspiciousActivity

logger = logging.getLogger(__name__)


def get_session_key(request):
    """Get or create session key for anonymous users"""
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


@login_required
@csrf_exempt
def log_suspicious_activity(request):
    """Log suspicious activities during the reading test"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Get session key for anonymous tracking
            if not request.session.session_key:
                request.session.create()
            
            # Create log entry
            SuspiciousActivity.objects.create(
                user=request.user if request.user.is_authenticated else None,
                session_key=request.session.session_key,
                activity_type=data.get('activity_type'),
                count=data.get('count', 1),
                question=data.get('question', 1),
                test_type='reading',
                time_away=data.get('time_away')
            )
            
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'Invalid request'}, status=400)


@login_required
def index(request):
    """Home page - show available test"""
    test = Test.objects.first()
    
    # Check if user has already completed the test
    if test and request.user.is_authenticated:
        existing_result = ReadingResult.objects.filter(user=request.user, test=test).first()
        if existing_result:
            messages.info(request, "You have already completed the reading test. View your results below.")
            return redirect('reading:latest_result')
    
    return render(request, 'reading/index.html', {'test': test})


@login_required
def start_test(request, test_id):
    """Start a new test - clear previous responses and shuffle questions"""
    test = get_object_or_404(Test, id=test_id)
    
    # Check if user has already completed the test
    existing_result = ReadingResult.objects.filter(user=request.user, test=test).first()
    if existing_result:
        messages.warning(request, "You have already completed this reading test.")
        return redirect('reading:results', result_id=existing_result.id)
    
    # Get or create profile (silently check pretest status)
    try:
        profile = StudentProfile.objects.get(user=request.user)
        if profile.reading_completed:
            messages.info(request, "You have already completed the reading section.")
            return redirect('reading:latest_result')
    except StudentProfile.DoesNotExist:
        profile = StudentProfile.objects.create(user=request.user)
    
    # Get session key
    session_key = get_session_key(request)
    
    # Delete any previous responses for this session
    ReadingUserResponse.objects.filter(
        session_key=session_key, 
        question__test=test
    ).delete()
    
    # Delete any previous test results for this session
    ReadingResult.objects.filter(
        session_key=session_key, 
        test=test
    ).delete()
    
    # Get all questions
    all_questions = list(Question.objects.filter(test=test).select_related('paragraph'))
    
    # Create shuffled order
    random.shuffle(all_questions)
    
    # Store shuffled question IDs in session
    question_ids = [q.id for q in all_questions]
    request.session[f'shuffled_questions_{test_id}'] = question_ids
    
    # Reset current question to 1
    request.session[f'current_question_{test_id}'] = 1
    
    # Initialize answered questions tracking
    request.session[f'answered_questions_{test_id}'] = []
    
    # Redirect to test page
    return redirect('reading:test_page', test_id=test_id)


@login_required
def test_page(request, test_id):
    """Display test page with progress tracking"""
    test = get_object_or_404(Test, id=test_id)
    
    # Check if user has already completed the test
    existing_result = ReadingResult.objects.filter(user=request.user, test=test).first()
    if existing_result:
        messages.info(request, "You have already completed this reading test.")
        return redirect('reading:results', result_id=existing_result.id)
    
    # Get session key
    session_key = get_session_key(request)
    
    # Get shuffled question IDs from session
    shuffled_ids = request.session.get(f'shuffled_questions_{test_id}')
    
    if not shuffled_ids:
        # If no shuffled order exists, create one now
        all_questions = list(Question.objects.filter(test=test).select_related('paragraph'))
        random.shuffle(all_questions)
        shuffled_ids = [q.id for q in all_questions]
        request.session[f'shuffled_questions_{test_id}'] = shuffled_ids
    else:
        # Get questions in shuffled order
        all_questions = []
        for q_id in shuffled_ids:
            try:
                q = Question.objects.get(id=q_id)
                all_questions.append(q)
            except Question.DoesNotExist:
                continue
    
    # DEBUG: Print to console to verify shuffle is working
    print(f"User: {request.user.username}")
    print(f"Shuffled Question IDs: {shuffled_ids}")
    
    total_questions = len(all_questions)
    
    # Get current question number from session or default to 1
    current_q = request.session.get(f'current_question_{test_id}', 1)
    
    # Get current question object (from shuffled list)
    current_question_obj = all_questions[current_q - 1] if all_questions else None
    
    # Get all responses for this session
    responses = ReadingUserResponse.objects.filter(
        session_key=session_key,
        question__test=test
    )
    
    # Create a dictionary of selected options by question id
    selected_options = {}
    answered_questions = set()
    
    for response in responses:
        answered_questions.add(response.question.id)
        selected_options[response.question.id] = response.selected_option
    
    # Update session with answered questions for progress tracking
    answered_ids = [q.id for q in responses]
    request.session[f'answered_questions_{test_id}'] = answered_ids
    
    # Calculate progress percentage based on answered questions
    answered_count = len(answered_questions)
    progress_percentage = int((answered_count / total_questions) * 100) if total_questions > 0 else 0
    
    # Group questions by paragraph for display
    paragraphs = []
    processed_paragraphs = set()
    
    for question in all_questions:
        para_id = question.paragraph.id
        if para_id not in processed_paragraphs:
            processed_paragraphs.add(para_id)
            # Get all questions from this paragraph that are in the shuffled list
            para_questions = [q for q in all_questions if q.paragraph.id == para_id]
            paragraphs.append({
                'paragraph': question.paragraph,
                'questions': para_questions
            })
    
    context = {
        'test': test,
        'all_questions': all_questions,
        'paragraphs': paragraphs,
        'total_questions': total_questions,
        'question_number': current_q,
        'current_question': current_question_obj,
        'selected_options': selected_options,
        'progress_percentage': progress_percentage,
        'answered_count': answered_count,
        'answered_questions': answered_questions,
        'shuffled_ids': shuffled_ids,  # Pass to template for debugging
    }
    
    return render(request, 'reading/test.html', context)


@login_required
@require_POST
def navigate_question(request, test_id):
    """Save current question number to session"""
    try:
        data = json.loads(request.body)
        question_number = data.get('question_number')
        
        # Validate question number
        test = get_object_or_404(Test, id=test_id)
        total_questions = Question.objects.filter(test=test).count()
        
        if question_number < 1 or question_number > total_questions:
            return JsonResponse({'error': 'Invalid question number'}, status=400)
        
        request.session[f'current_question_{test_id}'] = question_number
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_POST
def submit_answer(request, test_id):
    """Handle answer submission with progress tracking"""
    try:
        data = json.loads(request.body)
        question_id = data.get('question_id')
        selected_option = data.get('selected_option')
        
        question = get_object_or_404(Question, id=question_id, test_id=test_id)
        session_key = get_session_key(request)
        
        # Save or update response
        ReadingUserResponse.objects.update_or_create(
            session_key=session_key,
            question=question,
            defaults={
                'selected_option': selected_option,
                'user': request.user if request.user.is_authenticated else None
            }
        )
        
        # Update answered questions tracking
        answered_questions = request.session.get(f'answered_questions_{test_id}', [])
        if question_id not in answered_questions:
            answered_questions.append(question_id)
            request.session[f'answered_questions_{test_id}'] = answered_questions
        
        # Calculate progress percentage
        total_questions = Question.objects.filter(test_id=test_id).count()
        answered_count = len(answered_questions)
        progress_percentage = int((answered_count / total_questions) * 100) if total_questions > 0 else 0
        
        return JsonResponse({
            'success': True,
            'progress_percentage': progress_percentage,
            'answered_count': answered_count,
            'total_questions': total_questions
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def submit_test(request, test_id):
    """Submit the entire test and calculate results"""
    if request.method == 'POST':
        # Get or create profile
        profile, created = StudentProfile.objects.get_or_create(user=request.user)
        
        test = get_object_or_404(Test, id=test_id)
        
        # Check if user already has a result for this test
        existing_result = ReadingResult.objects.filter(user=request.user, test=test).first()
        if existing_result:
            logger.info(f"User {request.user.username} already has reading result {existing_result.id}")
            messages.info(request, "You have already completed this test. Viewing your previous results.")
            return redirect('reading:results', result_id=existing_result.id)
        
        # Get shuffled questions from session
        shuffled_ids = request.session.get(f'shuffled_questions_{test_id}')
        
        if shuffled_ids:
            # Get questions in shuffled order
            questions = []
            for q_id in shuffled_ids:
                try:
                    q = Question.objects.get(id=q_id)
                    questions.append(q)
                except Question.DoesNotExist:
                    continue
        else:
            # Fallback to regular order
            questions = list(Question.objects.filter(test=test))

        if not request.session.session_key:
            request.session.create()

        session_key = request.session.session_key

        # For 8 questions, each question is worth 12.5 marks (100/8 = 12.5)
        QUESTION_WEIGHT = 12.5
        total_weight = len(questions) * QUESTION_WEIGHT  # Should be 100
        earned_weight = 0

        # Parameter-wise tracking for skill analysis
        parameter_scores = {
            'MAIN_IDEA': 0,
            'VOCAB': 0,
            'DETAIL': 0,
            'LOGICAL': 0
        }

        parameter_totals = {
            'MAIN_IDEA': 0,
            'VOCAB': 0,
            'DETAIL': 0,
            'LOGICAL': 0
        }

        # Track correct answers count for each skill (for result display)
        main_idea_correct = 0
        lexical_correct = 0
        specific_correct = 0
        organisation_correct = 0

        # Process each question
        for question in questions:
            # Add to parameter totals
            parameter_totals[question.parameter_type] += 1  # Count questions per skill
            
            # Get user's answer from POST or from saved responses
            answer = request.POST.get(f'q{question.id}')
            
            # If not in POST, try to get from saved responses
            if not answer:
                try:
                    saved_response = ReadingUserResponse.objects.get(
                        session_key=session_key,
                        question=question
                    )
                    answer = saved_response.selected_option
                except ReadingUserResponse.DoesNotExist:
                    answer = None
            
            selected_option = int(answer) if answer and str(answer).isdigit() else None

            # Check if answer is correct
            if selected_option and selected_option == question.correct_option:
                earned_weight += QUESTION_WEIGHT
                parameter_scores[question.parameter_type] += 1  # Count correct per skill
                
                # Track per skill for result display
                if question.parameter_type == 'MAIN_IDEA':
                    main_idea_correct += 1
                elif question.parameter_type == 'VOCAB':
                    lexical_correct += 1
                elif question.parameter_type == 'DETAIL':
                    specific_correct += 1
                elif question.parameter_type == 'LOGICAL':
                    organisation_correct += 1

        # Calculate overall percentage (earned_weight should be between 0-100)
        percentage = earned_weight  # Since total_weight is 100
        
        # Calculate number of correct answers (for display)
        correct_count = main_idea_correct + lexical_correct + specific_correct + organisation_correct

        # Level classification
        if percentage < 60:
            level = "Basic"
            feedback = "Start with foundational reading exercises."
        elif percentage < 80:
            level = "Intermediate"
            feedback = "Good progress! Focus on weaker reading skills."
        else:
            level = "Advanced"
            feedback = "Excellent! Stay consistent to retain your skills."

        # Prepare skill breakdown text
        breakdown_text = "\n\nSkill Breakdown (out of 8 questions):\n"
        breakdown_text += f"• Main Idea: {main_idea_correct}/" + str(parameter_totals.get('MAIN_IDEA', 0)) + "\n"
        breakdown_text += f"• Vocabulary: {lexical_correct}/" + str(parameter_totals.get('VOCAB', 0)) + "\n"
        breakdown_text += f"• Specific Details: {specific_correct}/" + str(parameter_totals.get('DETAIL', 0)) + "\n"
        breakdown_text += f"• Logical/Organization: {organisation_correct}/" + str(parameter_totals.get('LOGICAL', 0)) + "\n"
        breakdown_text += f"\nTotal Correct: {correct_count}/8"

        # Save result
        reading_result = ReadingResult.objects.create(
            user=request.user,
            session_key=session_key,
            test=test,
            score=earned_weight,  # This will be out of 100
            total=100,  # Total possible score
            percentage=percentage,
            level=level,
            feedback=feedback + breakdown_text,
            main_idea_score=main_idea_correct,
            lexical_score=lexical_correct,
            specific_score=specific_correct,
            organisation_score=organisation_correct
        )

        logger.info(f"✅ Created reading result {reading_result.id} for user {request.user.username}")
        logger.info(f"📊 Score: {correct_count}/8 correct, {percentage:.1f}%")

        # Clear session data
        if f'shuffled_questions_{test_id}' in request.session:
            del request.session[f'shuffled_questions_{test_id}']
        if f'current_question_{test_id}' in request.session:
            del request.session[f'current_question_{test_id}']
        if f'answered_questions_{test_id}' in request.session:
            del request.session[f'answered_questions_{test_id}']

        # Update student profile
        profile.reading_completed = True
        profile.update_pretest_status()

        messages.success(request, "Reading test completed successfully!")
        
        # Store result ID in session for reference
        request.session['last_reading_result_id'] = reading_result.id
        request.session['reading_score'] = percentage
        
        # Redirect to active writing test
        try:
            writing_test = WritingTest.objects.filter(is_active=True).first()
            
            if writing_test:
                messages.info(request, "Now let's begin the writing test.")
                return redirect('writing:writing_test_home', test_id=writing_test.id)
            else:
                messages.warning(request, "No active writing test available. Please contact an administrator.")
                return redirect('reading:results', result_id=reading_result.id)
                
        except Exception as e:
            logger.error(f"Error redirecting to writing test: {e}")
            messages.warning(request, "There was an issue redirecting to the writing test.")
            return redirect('reading:results', result_id=reading_result.id)

    return HttpResponseRedirect('/')


@login_required
def latest_result(request):
    """Redirect to the most recent reading test result"""
    try:
        reading_result = ReadingResult.objects.filter(
            user=request.user
        ).order_by('-created_at').first()
        
        if reading_result:
            logger.info(f"✅ Found reading result: {reading_result.id} for user: {request.user.username}")
            
            # Verify ownership
            if reading_result.user != request.user:
                logger.warning(f"User {request.user.username} attempted to access result belonging to {reading_result.user.username}")
                messages.error(request, "You don't have permission to view these results.")
                return redirect('reading:index')
            
            return redirect('reading:results', result_id=reading_result.id)
        else:
            logger.info(f"❌ No reading result found for user: {request.user.username}")
            messages.info(request, "You haven't taken the reading test yet. Please take the test first.")
            return redirect('reading:index')
            
    except Exception as e:
        logger.error(f"❌ Error in latest_result: {str(e)}")
        messages.error(request, "An error occurred while loading your results.")
        return redirect('reading:index')


@login_required
def reading_results(request, result_id):
    """Display reading test results with proper data for 8 questions and ownership verification"""
    try:
        result = get_object_or_404(ReadingResult, id=result_id)
        
        # Verify ownership
        if result.user and result.user != request.user:
            logger.warning(f"User {request.user.username} attempted to access result {result_id} belonging to {result.user.username}")
            messages.error(request, "You don't have permission to view these results.")
            return redirect('home_page:home')
        
        logger.info(f"✅ Loading reading result {result_id} for user {request.user.username}")
        
        writing_test = WritingTest.objects.filter(is_active=True).first()
        
        questions = Question.objects.filter(test=result.test).order_by('paragraph__order', 'order')
        total_questions = questions.count()
        
        responses = ReadingUserResponse.objects.filter(
            session_key=result.session_key,
            question__in=questions
        )
        
        results_list = []
        for q in questions:
            response = responses.filter(question=q).first()
            is_correct = False
            user_answer = None
            
            if response:
                user_answer = response.selected_option
                if user_answer == q.correct_option:
                    is_correct = True
            
            results_list.append({
                'question': q,
                'is_correct': is_correct,
                'user_answer': user_answer,
                'correct_option': q.correct_option,
                'order': q.order,
                'paragraph_order': q.paragraph.order
            })
        
        correct_count = (result.main_idea_score + 
                        result.lexical_score + 
                        result.specific_score + 
                        result.organisation_score)
        
        main_idea_percent = (result.main_idea_score / 2) * 100 if result.main_idea_score else 0
        lexical_percent = (result.lexical_score / 2) * 100 if result.lexical_score else 0
        specific_percent = (result.specific_score / 2) * 100 if result.specific_score else 0
        organisation_percent = (result.organisation_score / 2) * 100 if result.organisation_score else 0
        
        feedback_lines = result.feedback.split('\n') if result.feedback else []
        
        # Calculate progress if session data exists
        answered_count = len(responses)
        progress_percentage = int((answered_count / total_questions) * 100) if total_questions > 0 else 0
        
        context = {
            'result': result,
            'test': result.test,
            'percentage': result.percentage,
            'score': correct_count,
            'total': total_questions,
            'level': result.level,
            'feedback': result.feedback,
            'feedback_lines': feedback_lines,
            'main_idea_percent': main_idea_percent,
            'lexical_percent': lexical_percent,
            'specific_percent': specific_percent,
            'organisation_percent': organisation_percent,
            'main_idea_score': result.main_idea_score,
            'lexical_score': result.lexical_score,
            'specific_score': result.specific_score,
            'organisation_score': result.organisation_score,
            'results': results_list,
            'writing_test': writing_test,
            'created_at': result.created_at,
            'total_questions': total_questions,
            'answered_count': answered_count,
            'progress_percentage': progress_percentage,
        }

        return render(request, 'reading/result.html', context)
        
    except Exception as e:
        logger.error(f"❌ Error loading reading result {result_id}: {str(e)}")
        messages.error(request, "An error occurred while loading your results.")
        return redirect('reading:index')


@login_required
def retry_test(request, test_id):
    """Allow user to retry a reading test"""
    test = get_object_or_404(Test, id=test_id)
    
    # Check if user has already completed the test
    existing_result = ReadingResult.objects.filter(user=request.user, test=test).first()
    if existing_result:
        # Option 1: Allow retake by deleting previous result
        # Uncomment the next two lines if you want to allow retakes
        # existing_result.delete()
        # messages.info(request, "Previous result cleared. You can now retake the test.")
        
        # Option 2: Prevent retake
        messages.warning(request, "You have already completed this test and cannot retake it.")
        return redirect('reading:results', result_id=existing_result.id)
    
    # Clear session data
    session_key = request.session.session_key
    if session_key:
        questions = Question.objects.filter(test=test)
        ReadingUserResponse.objects.filter(
            session_key=session_key,
            question__in=questions
        ).delete()
    
    # Clear session tracking data
    if f'shuffled_questions_{test_id}' in request.session:
        del request.session[f'shuffled_questions_{test_id}']
    if f'current_question_{test_id}' in request.session:
        del request.session[f'current_question_{test_id}']
    if f'answered_questions_{test_id}' in request.session:
        del request.session[f'answered_questions_{test_id}']
    
    messages.info(request, "You can now retake the reading test.")
    return redirect('reading:start_test', test_id=test_id)

@login_required
@csrf_exempt
def log_suspicious_activity(request):
    """Log suspicious activities during the writing test"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Get session key for anonymous tracking
            if not request.session.session_key:
                request.session.create()
            
            # Create log entry
            SuspiciousActivity.objects.create(
                user=request.user if request.user.is_authenticated else None,
                session_key=request.session.session_key,
                activity_type=data.get('activity_type'),
                count=data.get('count', 1),
                question=data.get('question', 1),
                test_type='writing',
                time_away=data.get('time_away')
            )
            
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)