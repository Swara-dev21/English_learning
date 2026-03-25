from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.utils import timezone
from django.contrib import messages
from django.http import JsonResponse
import json

# Import all your models
from .models import (
    UserProgress, 
    Lesson, 
    ListeningActivity, 
    SpeakingActivity, 
    ReadingActivity, 
    WritingActivity, 
    QuizQuestion
)


@login_required
def level_selection(request):
    user_level = request.user.profile.level
    context = {'user_level': user_level}
    return render(request, 'learning/level_selection.html', context)


@login_required
def beginner_instructions(request):
    user_level = request.user.profile.level
    if user_level == 'Beginner' or user_level == 'Intermediate' or user_level == 'Advanced':
        return render(request, 'learning/beginner_instructions.html')
    return redirect('learning:level_selection')


@login_required
def beginner_levels(request):
    """Display all beginner levels with progress and stars"""
    user_level = request.user.profile.level
    if user_level not in ['Beginner', 'Intermediate', 'Advanced']:
        return redirect('learning:level_selection')
    
    # Get user's completed levels from database
    levels_data = []
    user_progress = UserProgress.objects.filter(
        user=request.user, 
        level_type='beginner'
    )
    
    # Create a dictionary for quick lookup
    progress_dict = {p.day: p for p in user_progress}
    
    for i in range(1, 31):
        progress = progress_dict.get(i)
        if progress and progress.completed:
            levels_data.append({
                'day': i,
                'completed': True,
                'stars': progress.stars,
                'score': progress.score
            })
        else:
            levels_data.append({
                'day': i,
                'completed': False,
                'stars': 0,
                'score': 0
            })
    
    # Find the first uncompleted day to set as current level
    current_level = 1
    for level in levels_data:
        if not level['completed']:
            current_level = level['day']
            break
    
    context = {
        'levels_data': json.dumps(levels_data),
        'current_level': current_level,
        'user': request.user,
    }
    return render(request, 'learning/beginner_levels.html', context)


@login_required
def beginner_day(request, day_number):
    """Handle individual beginner days - dynamic template"""
    user_level = request.user.profile.level
    if user_level != 'Beginner':
        return redirect('learning:level_selection')
    
    # Check if day exists (1-30)
    if day_number < 1 or day_number > 30:
        return redirect('learning:beginner_levels')
    
    # Check if user has access to this day (previous days completed)
    user_progress = UserProgress.objects.filter(
        user=request.user,
        level_type='beginner'
    ).order_by('day')
    
    completed_days = [p.day for p in user_progress if p.completed]
    
    # Find the first uncompleted day
    next_day = 1
    for day in range(1, 31):
        if day not in completed_days:
            next_day = day
            break
    
    # If trying to access a day beyond next_day, redirect
    if day_number > next_day:
        messages.warning(request, f'Complete Day {next_day} first to unlock Day {day_number}!')
        return redirect('learning:beginner_levels')
    
    # Check if day is completed
    day_progress = user_progress.filter(day=day_number).first()
    is_completed = day_progress and day_progress.completed
    
    # ========== QUICK FIX: Use existing static template for Day 1 ==========
    if day_number == 1:
        # Use the existing beginner_day1.html template
        context = {
            'is_completed': is_completed,
            'score': day_progress.score if is_completed else 0,
            'stars': day_progress.stars if is_completed else 0,
        }
        return render(request, 'learning/beginner_day1.html', context)
    # ========== END QUICK FIX ==========
    
    # For days 2-30, use the dynamic template with database content
    # Get lesson content
    try:
        lesson = Lesson.objects.get(level_type='beginner', day=day_number)
    except Lesson.DoesNotExist:
        messages.info(request, f'Lesson for Day {day_number} is being prepared. Please check back soon!')
        return redirect('learning:beginner_levels')
    
    # Get activities for this day
    listening_activity = ListeningActivity.objects.filter(level_type='beginner', day=day_number).first()
    speaking_activity = SpeakingActivity.objects.filter(level_type='beginner', day=day_number).first()
    reading_activity = ReadingActivity.objects.filter(level_type='beginner', day=day_number).first()
    writing_activity = WritingActivity.objects.filter(level_type='beginner', day=day_number).first()
    
    # Get quiz questions
    quiz_questions = QuizQuestion.objects.filter(level_type='beginner', day=day_number)
    
    context = {
        'day_number': day_number,
        'lesson': lesson,
        'listening_activity': listening_activity,
        'speaking_activity': speaking_activity,
        'reading_activity': reading_activity,
        'writing_activity': writing_activity,
        'quiz_questions': quiz_questions,
        'is_completed': is_completed,
        'score': day_progress.score if is_completed else 0,
        'stars': day_progress.stars if is_completed else 0,
    }
    
    return render(request, 'learning/beginner_day_template.html', context)


@login_required
def submit_quiz(request, day_number):
    """Handle quiz submission"""
    if request.method != 'POST':
        return redirect('learning:beginner_levels')
    
    # Get all questions for this day
    questions = QuizQuestion.objects.filter(level_type='beginner', day=day_number)
    
    if not questions.exists():
        messages.error(request, 'No quiz questions found for this day.')
        return redirect('learning:beginner_day', day_number=day_number)
    
    # Calculate score
    correct_count = 0
    total_questions = questions.count()
    
    for q in questions:
        user_answer = request.POST.get(f'question_{q.id}')
        if user_answer and user_answer.upper() == q.correct_answer:
            correct_count += 1
    
    # Calculate percentage
    score_percentage = int((correct_count / total_questions) * 100)
    
    # Calculate stars
    stars = calculate_stars(score_percentage)
    
    # Save progress
    UserProgress.objects.update_or_create(
        user=request.user,
        level_type='beginner',
        day=day_number,
        defaults={
            'completed': True,
            'score': score_percentage,
            'stars': stars,
            'completed_at': timezone.now()
        }
    )
    
    # Store results in session to show on result page
    request.session['quiz_result'] = {
        'day': day_number,
        'score': score_percentage,
        'stars': stars,
        'total_questions': total_questions,
        'correct_answers': correct_count
    }
    
    return redirect('learning:quiz_result', day_number=day_number)


@login_required
def quiz_result(request, day_number):
    """Show quiz result page"""
    result = request.session.get('quiz_result', None)
    
    if not result or result['day'] != day_number:
        return redirect('learning:beginner_levels')
    
    # Clear the result from session
    del request.session['quiz_result']
    
    context = {
        'day_number': day_number,
        'score': result['score'],
        'stars': result['stars'],
        'total_questions': result['total_questions'],
        'correct_answers': result['correct_answers'],
    }
    
    return render(request, 'learning/quiz_result.html', context)


@login_required
def beginner_day1(request):
    """Legacy view for Day 1 - kept for backward compatibility"""
    if request.user.profile.level != 'Beginner':
        return redirect('learning:level_selection')
    
    # Check if day is completed
    user_progress = UserProgress.objects.filter(
        user=request.user,
        level_type='beginner',
        day=1
    ).first()
    
    context = {
        'is_completed': user_progress and user_progress.completed,
        'score': user_progress.score if user_progress and user_progress.completed else 0,
        'stars': user_progress.stars if user_progress and user_progress.completed else 0,
    }
    return render(request, 'learning/beginner_day1.html', context)


@login_required
def intermediate_instructions(request):
    user_level = request.user.profile.level
    if user_level == 'Intermediate' or user_level == 'Advanced':
        return render(request, 'learning/intermediate_instructions.html')
    return redirect('learning:level_selection')


@login_required
def intermediate_day1(request):
    if request.user.profile.level != 'Intermediate':
        return redirect('learning:level_selection')
    return render(request, 'learning/intermediate_day1.html')


@login_required
def advanced_instructions(request):
    if request.user.profile.level != 'Advanced':
        return redirect('learning:level_selection')
    return render(request, 'learning/advanced_instructions.html')


@login_required
def advanced_day1(request):
    if request.user.profile.level != 'Advanced':
        return redirect('learning:level_selection')
    return render(request, 'learning/advanced_day1.html')


def calculate_stars(score):
    """Calculate stars based on score percentage"""
    try:
        score = int(score)
        if score >= 90:
            return 3
        elif score >= 70:
            return 2
        elif score >= 50:
            return 1
        return 0
    except (ValueError, TypeError):
        return 0