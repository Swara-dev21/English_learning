from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponseRedirect
from .models import Test, Question, ReadingUserResponse


def index(request):
    """Home page"""
    test = Test.objects.first()
    return render(request, 'reading/index.html', {'test': test})


def test_page(request, test_id):
    """Display test"""
    test = get_object_or_404(Test, id=test_id)
    questions = Question.objects.filter(test=test).order_by('id')

    context = {
        'test': test,
        'questions': questions,
    }
    return render(request, 'reading/test.html', context)


def submit_test(request, test_id):
    """Process test answers and store responses"""

    if request.method == 'POST':

        test = get_object_or_404(Test, id=test_id)
        questions = Question.objects.filter(test=test)

        # ✅ Ensure session exists
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

            # ✅ SAVE RESPONSE IN DATABASE
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

        percentage = (score / total * 100) if total > 0 else 0

        # Level logic
        if score <= 2:
            level = "Beginner"
            feedback = "Focus on reading comprehension practice"
        elif score <= 4:
            level = "Intermediate"
            feedback = "Good understanding, keep practicing"
        else:
            level = "Advanced"
            feedback = "Excellent reading skills!"

        context = {
            'test': test,
            'score': score,
            'total': total,
            'percentage': round(percentage, 2),
            'level': level,
            'feedback': feedback,
            'results': results,
        }

        return render(request, 'reading/result.html', context)

    return HttpResponseRedirect('/')
