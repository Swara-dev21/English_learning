from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse,HttpResponseRedirect
from .models import Test, Question

def index(request):
    """Home page"""
    test = Test.objects.first()
    return render(request, 'reading/index.html', {'test': test})

def test_page(request, test_id):
    """Display test with step-by-step navigation"""
    test = get_object_or_404(Test, id=test_id)
    questions = Question.objects.filter(test=test).order_by('id')
    
    # Passage text without linebreaks for clean display
    passage = {
        'title': "Global warming",
        'content': "Engineering life is not only about studying machines, drawings, or technical subjects. It is also about developing important skills that help students become successful professionals. Diploma engineering students learn how to solve problems, work in teams, and manage time effectively during their academic life. One of the most important skills for an engineering student is problem-solving. Engineers often face real-life challenges where they must think logically and find practical solutions. Along with this, communication skills play a key role. Engineers need to explain their ideas clearly to supervisors, co-workers, and clients. Good communication helps avoid mistakes and improves teamwork. Time management is another essential skill in engineering life. Students have to balance classes, practical work, assignments, and exams. Managing time properly reduces stress and improves performance. Teamwork is equally important because most engineering projects are completed in groups. Working with others teaches cooperation, responsibility, and respect for different opinions. Finally, engineering life also teaches discipline and professionalism. Following rules, maintaining safety, and being punctual are habits that prepare students for industry life. These skills not only help students during their studies but also make them confident and successful engineers in the future."
    }
    
    context = {
        'test': test,
        'passage': passage,
        'questions': questions,
    }
    return render(request, 'reading/test.html', context)

def submit_test(request, test_id):
    """Process test answers"""
    if request.method == 'POST':
        test = get_object_or_404(Test, id=test_id)
        questions = Question.objects.filter(test=test)
        
        score = 0
        total = questions.count()
        results = []
        
        for question in questions:
            answer = request.POST.get(f'q{question.id}')
            is_correct = False
            
            if answer and answer.isdigit() and int(answer) == question.correct_option:
                score += 1
                is_correct = True
            
            results.append({
                'question': question,
                'selected': int(answer) if answer and answer.isdigit() else None,
                'correct_option': question.correct_option,
                'is_correct': is_correct
            })
        
        percentage = (score / total * 100) if total > 0 else 0
        
        # Determine level
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
    
    return HttpResponseRedirect('test_page', test_id=test_id)