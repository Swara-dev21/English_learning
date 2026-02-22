# reading/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from home_page.models import StudentProfile
from .models import Test, Question, ReadingUserResponse, ReadingResult


@login_required
def index(request):
    test = Test.objects.first()
    return render(request, 'reading/index.html', {'test': test})


@login_required
def test_page(request, test_id):
    test = get_object_or_404(Test, id=test_id)
    questions = Question.objects.filter(test=test).select_related('paragraph').order_by('order')

    context = {
        'test': test,
        'questions': questions,
    }
    return render(request, 'reading/test.html', context)


@login_required
def submit_test(request, test_id):
    if request.method == 'POST':

        profile, _ = StudentProfile.objects.get_or_create(user=request.user)

        if profile.reading_completed:
            messages.warning(request, "You have already completed the reading test.")
            return redirect('home_page:pretest_status')

        test = get_object_or_404(Test, id=test_id)
        questions = Question.objects.filter(test=test)

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
        if percentage < 40:
            level = "Basic"
            feedback = "Start with foundational reading exercises."
        elif percentage < 80:
            level = "Intermediate"
            feedback = "Good progress. Focus on weaker reading skills."
        else:
            level = "Advanced"
            feedback = "Excellent reading comprehension skills!"

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

        profile.reading_completed = True
        profile.update_pretest_status()

        messages.success(request, "Reading test completed successfully!")
        return redirect('reading:results', result_id=reading_result.id)

    return HttpResponseRedirect('/')


@login_required
def reading_results(request, result_id):
    result = get_object_or_404(ReadingResult, id=result_id)

    if result.user and result.user != request.user:
        messages.error(request, "You don't have permission to view these results.")
        return redirect('home_page:home')
    
    main_idea_percent = 100 if result.main_idea_score == 1 else 0
    lexical_percent = 100 if result.lexical_score == 1 else 0
    specific_percent = 100 if result.specific_score == 1 else 0
    organisation_percent = (result.organisation_score / 2) * 100

    #Get individual question results for summary grid
    questions = Question.objects.filter(test=result.test).order_by('order')
    responses = ReadingUserResponse.objects.filter(
        session_key=result.session_key,
        question__in=questions
    )
    
    results_list = []
    for q in questions:
        response = responses.filter(question=q).first()
        is_correct = False
        if response and response.selected_option == q.correct_option:
            is_correct = True
        results_list.append({
            'question': q,
            'is_correct': is_correct
        })

    context = {
        'result': result,
        'percentage': result.percentage,
        'score': result.score,
        'total': result.total,
        'level': result.level,
        'feedback': result.feedback,
        'main_idea_percent': main_idea_percent,
        'lexical_percent': lexical_percent,
        'specific_percent': specific_percent,
        'organisation_percent': organisation_percent,
        'results': results_list,
    }

    return render(request, 'reading/result.html', context)