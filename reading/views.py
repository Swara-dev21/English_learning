# reading/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from home_page.models import StudentProfile
from home_page.decorators import pretest_access_required
from .models import Test, Question, ReadingUserResponse, ReadingResult

@login_required
#@pretest_access_required('reading')  # Full checks for reading test
def index(request):
    """Home page"""
    test = Test.objects.first()
    return render(request, 'reading/index.html', {'test': test})

@login_required
#@pretest_access_required('reading')
def test_page(request, test_id):
    """Display test"""
    test = get_object_or_404(Test, id=test_id)
    questions = Question.objects.filter(test=test).order_by('id')

    context = {
        'test': test,
        'questions': questions,
    }
    return render(request, 'reading/test.html', context)

@login_required
#@pretest_access_required('reading')
def submit_test(request, test_id):
    """Process test answers and store responses"""
    if request.method == 'POST':
        # Check pretest completion
        try:
            profile = StudentProfile.objects.get(user=request.user)
            if profile.pretest_completed:
                messages.info(request, "You have already completed the pretest.")
                return redirect('home_page:pretest_results')
            if profile.reading_completed:
                messages.warning(request, "You have already completed the reading test.")
                return redirect('home_page:pretest_status')
        except StudentProfile.DoesNotExist:
            profile = StudentProfile.objects.create(user=request.user)

        test = get_object_or_404(Test, id=test_id)
        questions = Question.objects.filter(test=test)

        # Ensure session exists
        if not request.session.session_key:
            request.session.create()

        session_key = request.session.session_key

        score = 0
        total = questions.count()
        results = []

        for question in questions:
            answer = request.POST.get(f'q{question.id}')
            selected_option = int(answer) if answer and answer.isdigit() else None
            is_correct = False

            if selected_option and selected_option == question.correct_option:
                score += 1
                is_correct = True

            # Save response in database
            if selected_option:
                ReadingUserResponse.objects.update_or_create(
                    session_key=session_key,
                    question=question,
                    defaults={
                        'selected_option': selected_option,
                        'user': request.user if request.user.is_authenticated else None
                    }
                )

            results.append({
                'question': question,
                'selected': selected_option,
                'correct_option': question.correct_option,
                'is_correct': is_correct
            })

          # Calculate percentage
            percentage = (score / total * 100) if total > 0 else 0

            # New level logic based on percentage
            if percentage < 40:  # 0-39% (0-1 correct)
                level = "Basic"
                feedback = "Start with foundational reading exercises"
            elif percentage < 80:  # 40-79% (2-3 correct)
                level = "Intermediate"
                feedback = "Good progress, keep practicing regularly"
            else:  # 80-100% (4-5 correct)
                level = "Advanced"
                feedback = "Excellent reading comprehension skills!"

                
        # ✅ SAVE READING RESULT TO DATABASE
        reading_result = ReadingResult.objects.create(
            user=request.user,
            session_key=session_key,
            test=test,
            score=score,
            total=total,
            percentage=percentage,
            level=level,
            feedback=feedback
        )

        # Mark reading as completed
        profile.reading_completed = True
        profile.update_pretest_status()
        
        messages.success(request, "Reading test completed successfully!")

        # Redirect to reading results page (create this view if needed)
        return redirect('reading:results', result_id=reading_result.id)

    return HttpResponseRedirect('/')


# ✅ ADD THIS RESULTS VIEW
@login_required
def reading_results(request, result_id):
    """Display reading test results"""
    result = get_object_or_404(ReadingResult, id=result_id)
    
    # Verify that the result belongs to this user
    if result.user and result.user != request.user:
        messages.error(request, "You don't have permission to view these results.")
        return redirect('home_page:home')
    
    context = {
        'result': result,
        'percentage': result.percentage,
        'score': result.score,
        'total': result.total,
        'level': result.level,
        'feedback': result.feedback,
    }
    
    return render(request, 'reading/result.html', context)