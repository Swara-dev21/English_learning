# reading/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from home_page.models import StudentProfile
from .models import Test, Question, ReadingUserResponse, ReadingResult
from writing.models import WritingTest
import logging

logger = logging.getLogger(__name__)

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from home_page.models import SuspiciousActivity

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
                test_type='reading',  # Specify it's reading test
                time_away=data.get('time_away')
            )
            
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def index(request):
    test = Test.objects.first()
    return render(request, 'reading/index.html', {'test': test})


@login_required
def test_page(request, test_id):
    test = get_object_or_404(Test, id=test_id)
    questions = Question.objects.filter(test=test).select_related('paragraph').order_by('order')
    
    # Check if user has already completed the test
    if ReadingResult.objects.filter(user=request.user, test=test).exists():
        messages.info(request, "You have already completed this reading test.")
        return redirect('reading:latest_result')

    context = {
        'test': test,
        'questions': questions,
    }
    return render(request, 'reading/test.html', context)


@login_required
def latest_result(request):
    """Redirect to the most recent reading test result"""
    try:
        # Find the most recent COMPLETED reading test for this user
        reading_result = ReadingResult.objects.filter(
            user=request.user
        ).order_by('-created_at').first()
        
        if reading_result:
            logger.info(f"✅ Found reading result: {reading_result.id} for user: {request.user.username}")
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
def submit_test(request, test_id):
    if request.method == 'POST':
        profile, _ = StudentProfile.objects.get_or_create(user=request.user)
        test = get_object_or_404(Test, id=test_id)
        questions = Question.objects.filter(test=test)

        # Check if user already has a result for this test
        existing_result = ReadingResult.objects.filter(user=request.user, test=test).first()
        if existing_result:
            logger.info(f"User {request.user.username} already has reading result {existing_result.id}")
            messages.info(request, "You have already completed this test. Viewing your previous results.")
            return redirect('reading:results', result_id=existing_result.id)

        if not request.session.session_key:
            request.session.create()

        session_key = request.session.session_key

        total_weight = 0
        earned_weight = 0

        # Parameter-wise tracking
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

        main_idea_score = 0
        lexical_score = 0
        specific_score = 0
        organisation_score = 0

        for question in questions:
            total_weight += question.weight
            parameter_totals[question.parameter_type] += question.weight

            answer = request.POST.get(f'q{question.id}')
            selected_option = int(answer) if answer and answer.isdigit() else None

            is_correct = False

            if selected_option and selected_option == question.correct_option:
                earned_weight += question.weight
                parameter_scores[question.parameter_type] += question.weight
                is_correct = True
   
                if question.parameter_type == 'MAIN_IDEA':
                    main_idea_score = 1
                elif question.parameter_type == 'VOCAB':
                    lexical_score = 1
                elif question.parameter_type == 'DETAIL':
                    specific_score = 1
                elif question.parameter_type == 'LOGICAL':
                    organisation_score += 1 

            if selected_option:
                ReadingUserResponse.objects.update_or_create(
                    session_key=session_key,
                    question=question,
                    defaults={
                        'selected_option': selected_option,
                        'user': request.user
                    }
                )

        # Calculate overall percentage
        percentage = (earned_weight / total_weight * 100) if total_weight > 0 else 0

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

        # Prepare parameter breakdown text (for storing in feedback)
        breakdown_text = "\nSkill Breakdown:\n"

        for key in parameter_scores:
            total = parameter_totals[key]
            score = parameter_scores[key]
            skill_percentage = (score / total * 100) if total > 0 else 0

            if skill_percentage >= 70:
                status = "Strong"
            elif skill_percentage >= 40:
                status = "Developing"
            else:
                status = "Needs Improvement"

            breakdown_text += f"{key} → {skill_percentage:.0f}% ({status})\n"

        # Save result
        reading_result = ReadingResult.objects.create(
            user=request.user,
            session_key=session_key,
            test=test,
            score=earned_weight,
            total=total_weight,
            percentage=percentage,
            level=level,
            feedback=feedback + breakdown_text,
            main_idea_score=main_idea_score,
            lexical_score=lexical_score,
            specific_score=specific_score,
            organisation_score=organisation_score
        )

        logger.info(f"✅ Created reading result {reading_result.id} for user {request.user.username}")

        profile.reading_completed = True
        profile.update_pretest_status()

        messages.success(request, "Reading test completed successfully!")
        
        # Store result ID in session for reference
        request.session['last_reading_result_id'] = reading_result.id
        request.session['reading_score'] = percentage
        
        # ===== REDIRECT TO ACTIVE WRITING TEST =====
        try:
            # Get the first active writing test
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
def reading_results(request, result_id):
    """Display reading test results with proper data"""
    try:
        # Get the result and verify ownership
        result = get_object_or_404(ReadingResult, id=result_id)
        
        # Security check
        if result.user and result.user != request.user:
            logger.warning(f"User {request.user.username} attempted to access result {result_id} belonging to {result.user.username}")
            messages.error(request, "You don't have permission to view these results.")
            return redirect('home_page:home')
        
        logger.info(f"✅ Loading reading result {result_id} for user {request.user.username}")
        
        # Get writing test for navigation
        writing_test = WritingTest.objects.filter(is_active=True).first()
        
        # Calculate parameter percentages
        main_idea_percent = 100 if result.main_idea_score == 1 else 0
        lexical_percent = 100 if result.lexical_score == 1 else 0
        specific_percent = 100 if result.specific_score == 1 else 0
        organisation_percent = (result.organisation_score / 2) * 100

        # Get individual question results for summary grid
        questions = Question.objects.filter(test=result.test).order_by('order')
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
                'correct_option': q.correct_option
            })

        # Calculate correct count (number of questions answered correctly)
        correct_count = result.main_idea_score + result.lexical_score + result.specific_score + result.organisation_score
        total_questions = 5  # Fixed total number of questions

        # Format feedback for display
        feedback_lines = result.feedback.split('\n') if result.feedback else []
        
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
            'results': results_list,
            'writing_test': writing_test,
            'created_at': result.created_at,
        }

        return render(request, 'reading/result.html', context)
        
    except Exception as e:
        logger.error(f"❌ Error loading reading result {result_id}: {str(e)}")
        messages.error(request, "An error occurred while loading your results.")
        return redirect('reading:index')


@login_required
def retry_test(request, test_id):
    """Allow user to retry a reading test (if configured to allow)"""
    test = get_object_or_404(Test, id=test_id)
    
    # Check if retry is allowed (you can add a field to Test model for this)
    if hasattr(test, 'allow_retry') and not test.allow_retry:
        messages.warning(request, "Retry is not allowed for this test.")
        return redirect('reading:latest_result')
    
    # Clear previous responses for this test
    session_key = request.session.session_key
    if session_key:
        questions = Question.objects.filter(test=test)
        ReadingUserResponse.objects.filter(
            session_key=session_key,
            question__in=questions
        ).delete()
    
    messages.info(request, "You can now retake the reading test.")
    return redirect('reading:test_page', test_id=test_id)