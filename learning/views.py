from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.contrib import messages
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings
import json
import uuid
import random
import os
import io
from datetime import datetime, date
from PIL import Image, ImageDraw, ImageFont
from .models import (
    UserLearningProgress, DailyActivity, SavedVocabulary, UserCertificate,
    LevelAssessment, AssessmentQuestion, UserAssessmentAttempt  # Add these 3
)
import requests

def get_user_progress(user, level):
    """Helper function to get or create user progress"""
    progress, created = UserLearningProgress.objects.get_or_create(
        user=user,
        level=level,
        defaults={
            'completed_days': [],
            'current_day': 1,
            'streak_days': 0,
            'has_seen_intro': False
        }
    )
    return progress

@login_required
def level_selection(request):
    """Display level selection page based on pretest results"""
    profile = request.user.profile
    
    # Normalize level from profile
    user_level_from_profile = profile.level.strip().lower() if profile.level else 'beginner'
    pretest_completed = profile.pretest_completed
    
    # Get pretest score if available
    overall_percentage = 0
    if hasattr(profile, 'get_overall_pretest_score'):
        overall_percentage = profile.get_overall_pretest_score()
    
    # ========== CLEAN UNLOCK LOGIC (SAME AS PROFILE VIEW) ==========
    
    # Step 1: Pretest must be completed to unlock anything
    if not pretest_completed and overall_percentage == 0:
        # No pretest taken yet
        beginner_unlocked = False
        intermediate_unlocked = False
        advanced_unlocked = False
        user_level = 'beginner'
    
    else:
        # Determine user's level based on pretest score (if available) or profile level
        if overall_percentage >= 80:
            user_level = 'advanced'
        elif overall_percentage >= 60:
            user_level = 'intermediate'
        else:
            # Use profile level if score is 0 or below 60
            if overall_percentage == 0 and user_level_from_profile in ['intermediate', 'advanced']:
                user_level = user_level_from_profile
            else:
                user_level = 'beginner'
        
        # Beginner always unlocked after pretest
        beginner_unlocked = True
        
        # Intermediate logic
        if user_level in ['intermediate', 'advanced']:
            intermediate_unlocked = True
        else:  # beginner user
            # Get beginner progress to check if completed
            from learning.models import UserLearningProgress
            beginner_progress = UserLearningProgress.objects.filter(
                user=request.user, level='beginner'
            ).first()
            beginner_completed = beginner_progress.is_completed() if beginner_progress else False
            intermediate_unlocked = beginner_completed
        
        # Advanced logic
        if user_level == 'advanced':
            advanced_unlocked = True
        else:
            # Get intermediate progress to check if completed
            from learning.models import UserLearningProgress
            intermediate_progress = UserLearningProgress.objects.filter(
                user=request.user, level='intermediate'
            ).first()
            intermediate_completed = intermediate_progress.is_completed() if intermediate_progress else False
            advanced_unlocked = intermediate_completed
    
    # Get or create progress for each level (only if unlocked)
    beginner_progress = get_user_progress(request.user, 'beginner') if beginner_unlocked else None
    intermediate_progress = get_user_progress(request.user, 'intermediate') if intermediate_unlocked else None
    advanced_progress = get_user_progress(request.user, 'advanced') if advanced_unlocked else None
    
    context = {
        'user_level': user_level,  # 'beginner', 'intermediate', or 'advanced'
        'user_level_name': user_level.capitalize(),  # 'Beginner', 'Intermediate', 'Advanced'
        'beginner_unlocked': beginner_unlocked,
        'intermediate_unlocked': intermediate_unlocked,
        'advanced_unlocked': advanced_unlocked,
        'beginner_progress': beginner_progress,
        'intermediate_progress': intermediate_progress,
        'advanced_progress': advanced_progress,
    }
    return render(request, 'learning/level_selection.html', context)

@login_required
def level_overview(request, level_name):
    """Display the 30-day journey overview for a specific level"""
    if level_name not in ['beginner', 'intermediate', 'advanced']:
        messages.error(request, 'Invalid level selected.')
        return redirect('learning:level_selection')
    
    progress = get_user_progress(request.user, level_name)

    from .models import LevelAssessment
    try:
        assessment = LevelAssessment.objects.get(level=level_name)
        assessment_total_questions = assessment.total_questions
        assessment_passing_score = assessment.passing_score
        assessment_time_limit = assessment.time_limit_minutes
    except LevelAssessment.DoesNotExist:
        # Fallback defaults based on level
        if level_name == 'beginner':
            assessment_total_questions = 20
            assessment_passing_score = 15
            assessment_time_limit = 30
        elif level_name == 'intermediate':
            assessment_total_questions = 25
            assessment_passing_score = 20
            assessment_time_limit = 30
        else:  # advanced
            assessment_total_questions = 25
            assessment_passing_score = 18
            assessment_time_limit = 45
    
    celebrate_day = request.GET.get('completed')
    if celebrate_day:
        try:
            celebrate_day_num = int(celebrate_day)
            if 1 <= celebrate_day_num <= 30 and celebrate_day_num not in progress.completed_days:
                progress.complete_day(celebrate_day_num)
                progress.refresh_from_db()
        except (ValueError, TypeError):
            pass

    completed_set = set(progress.completed_days)
    computed_current_day = 31
    for d in range(1, 31):
        if d not in completed_set:
            computed_current_day = d
            break

    if progress.current_day != computed_current_day and computed_current_day <= 30:
        progress.current_day = computed_current_day
        progress.save()

    show_intro = not progress.has_seen_intro
    is_assessment = request.GET.get('assessment') == 'true'

    certificate = UserCertificate.objects.filter(user=request.user, level=level_name).first()


    day_titles = {}
    day_power_lines = {}
    for day in range(1, 31):
        day_titles[day] = get_day_title(level_name, day)
        day_power_lines[day] = get_day_power_line(level_name, day)

    is_completed = progress.is_completed()
    certificate_issued = progress.certificate_issued

    context = {
        'level': level_name,
        'level_display': level_name.capitalize(),
        'completed_count': len(progress.completed_days),
        'completed_days_list': progress.completed_days,
        'current_day': computed_current_day,
        'streak': progress.streak_days,
        'percentage': progress.completion_percentage(),
        'is_completed': is_completed,
        'certificate_issued': certificate_issued,
        'certificate_id': certificate.id if certificate else None,
        'day_titles': day_titles,
        'day_power_lines': day_power_lines,
        'user': request.user,
        'show_intro': show_intro,
        'is_assessment': is_assessment,
        # Assessment details - CRITICAL: These must be for the correct level
        'assessment_total_questions': assessment_total_questions,
        'assessment_passing_score': assessment_passing_score,
        'assessment_time_limit': assessment_time_limit,
        'has_passed_assessment': UserAssessmentAttempt.objects.filter(user=request.user, assessment=assessment, passed=True).exists() if 'assessment' in locals() else False,
        'collected_rewards': progress.collected_rewards,
    }

    return render(request, 'learning/level_overview.html', context)

def get_day_title(level, day):
    """Get title for each day based on level with dynamic themes"""
    titles = {
        'beginner': {
            1: "POWER ON: THE FOUNDATION",
            2: "THE MORNING ROUTINE",
            3: "BUILDING CONFIDENCE",
            4: "THE POWER OF LISTENING",
            5: "COURAGE & COMMUNICATION",
            6: "THE ART OF INTRODUCTION",
            7: "THE POWER OF PROGRESS",
            8: "THE ART OF ASKING",
            9: "THE POWER OF PARTICIPATION",
            10: "THE CLARITY CHECK",
            11: "THE GRATITUDE LOOP",
            12: "THE RESILIENCE ROUTINE",
            13: "THE CONSISTENCY CODE",
            14: "THE WEEK 2 REVIEW & RECOVERY",
            15: "THE SILENT COMMUNICATOR",
            16: "THE RADIANT CONNECTOR",
            17: "THE VISIONARY LEADER",
            18: "THE ARTICULATE ENGINEER",
            19: "THE ACTIVE LISTENER",
            20: "THE CONSISTENCY ARCHITECT",
            21: "THE CONFIDENT COMMUNICATOR",
            22: "THE STRATEGIC VISIONARY",
            23: "THE MOMENTUM BUILDER",
            24: "THE RESILIENT EXPERT",
            25: "THE ART OF PERSUASION",
            26: "THE STRATEGIC INQUIRY",
            27: "THE PUBLIC FORUM",
            28: "THE GRAND FINALE",
            29: "THE CONFIDENCE PEAK",
            30: "THE MASTERPIECE",
        },
        'intermediate': {
            1: "FROM BASIC TO INTERMEDIATE",
            2: "THE LOGIC ENGINE OF ENGLISH",
            3: "THE ART OF PROFESSIONAL RELAY",
            4: "MODALS OF DEDUCTION & PROBABILITY",
            5: "BUILDING COMPLEX SENTENCES",
            6: "THE LANGUAGE OF ANALYSIS",
            7: "WEEK 1 REVIEW & THE PRECISION AUDIT",
            8: "ADVANCED ACTIVE & PASSIVE VOICE",
            9: "THE SUBTLE ART",
            10: "COLLOCATIONS & WORD FAMILIES",
            11: "THE FLOW ARCHITECT",
            12: "THE DIPLOMAT'S TOOLKIT",
            13: "PROFESSIONAL EMAIL & FORMAL WRITING",
            14: "THE INTERMEDIATE AUDIT",
            15: "STRESS, INTONATION & CHUNKING",
            16: "PARAPHRASING & SUMMARISING",
            17: "INFERENCE & IMPLICATION",
            18: "GROUP DISCUSSIONS & DEBATES",
            19: "YOUR ENGINEERING DOMAIN",
            20: "CRITICAL ANALYSIS",
            21: "THE SYNTHESIS TEST",
            22: "THE ARGUMENT ESSAY",
            23: "STRUCTURE, DELIVERY & IMPACT",
            24: "COMPETENCY-BASED ANSWERS",
            25: "CLEFT SENTENCES & EMPHASIS",
            26: "REPORTS & PROPOSALS",
            27: "NEGOTIATION & CONFLICT RESOLUTION LANGUAGE",
            28: "THE ADVANCED INTEGRATION",
            29: "THE INTERMEDIATE CERTIFICATION TEST PREP",
            30: "THE FULL MASTERPIECE",
        },
        'advanced': {
            1: "COMMANDING AUTHORITY IN SPEECH",
            2: "MASTERING COMPLEX SENTENCE STRUCTURES",
            3: "THE ART OF PROFESSIONAL NEGOTIATION LANGUAGE",
            4: "TECHNICAL PRESENTATION MASTERY",
            5: "ADVANCED LISTENING --- READING BETWEEN THE LINES",
            6: "PRECISION VOCABULARY FOR TECHNICAL WRITING",
            7: "STORYTELLING FOR ENGINEERS",
            8: "GRAMMAR DEEP DIVE --- PERFECT TENSES IN PROFESSIONAL USE",
            9: "READING ACADEMIC AND TECHNICAL ENGLISH",
            10: "ADVANCED WRITING --- THE STRUCTURED ARGUMENT",
            11: "PROFESSIONAL EMAIL AND REPORT LANGUAGE",
            12: "SPOKEN GRAMMAR --- FLUENCY PATTERNS",
            13: "LISTENING FOR CRITICAL INFORMATION --- FILTERING NOISE",
            14: "MID-COURSE REVIEW AND SELF-ASSESSMENT",
            15: "ADVANCED READING --- INFERRING AUTHOR'S PURPOSE",
            16: "SPEAKING UNDER PRESSURE --- MANAGING DIFFICULT QUESTIONS",
            17: "THE LANGUAGE OF LEADERSHIP",
            18: "ADVANCED GRAMMAR --- PASSIVE VOICE MASTERY",
            19: "VOCABULARY IN CONTEXT --- ENGINEERING APPLICATIONS",
            20: "CRITICAL THINKING THROUGH LANGUAGE --- ARGUMENT ANALYSIS",
            21: "ADVANCED SPEAKING --- IMPROMPTU DELIVERY",
            22: "WRITING COMPLEX REPORTS --- STRUCTURE AND FLOW",
            23: "READING SPEED AND COMPREHENSION --- ADVANCED TECHNIQUES",
            24: "SOCIAL AND NETWORKING ENGLISH FOR PROFESSIONALS",
            25: "INTERVIEW AND VIVA LANGUAGE MASTERY",
            26: "ADVANCED IDIOMS AND FIXED EXPRESSIONS IN CONTEXT",
            27: "PRECISION WRITING --- EDITING AND PROOFREADING",
            28: "CROSS-CULTURAL COMMUNICATION IN TECHNICAL SETTINGS",
            29: "COMPLETE LANGUAGE INTEGRATION --- THE CAPSTONE DAY",
            30: "GRADUATION DAY --- YOUR ADVANCED COMMUNICATOR'S MANIFESTO"
}
    }
    return titles.get(level, {}).get(day, f"Day {day}")

def get_day_power_line(level, day):
    """Get power line/motivational quote for each day based on level"""
    power_lines = {
        'beginner': {
            1: "You don't have to be a master to start, but you have to start to become a master.",
            2: "Every new morning is a fresh chance—what you do today builds who you become tomorrow.",
            3: "Confidence is not being perfect; it is the courage to start even when you are nervous.",
            4: "To speak well, you must first learn to hear what is not being said.",
            5: "Fear is a reaction; courage is a decision. Every mistake is just data for your future success.",
            6: "You never get a second chance to make a first impression. Speak with clarity, lead with confidence.",
            7: "Transformation is a marathon, not a sprint. Celebrate the small wins, for they are the building blocks of a masterpiece.",
            8: "He who asks a question is a fool for five minutes; he who does not ask a question remains a fool forever.",
            9: "The only bad question is the one that remains unasked.",
            10: "The single biggest problem in communication is the illusion that it has taken place.",
            11: "Gratitude is the most exquisite form of courtesy.",
            12: "Fall seven times, stand up eight. Success is not final, failure is not fatal: it is the courage to continue that counts.",
            13: "We are what we repeatedly do. Excellence, then, is not an act, but a habit.",
            14: "Reviewing what you have learned is like sharpening a saw; it makes the next cut much easier.",
            15: "Your posture is the first sentence you speak to a room.",
            16: "Peace begins with a smile, and so does a successful conversation.",
            17: "Confidence is not 'they will like me.' Confidence is 'I will be fine if they don't.'",
            18: "Clear speech is the mirror of a clear mind.",
            19: "Nature gave us two ears and one mouth so that we can listen twice as much as we speak.",
            20: "Small daily improvements over time lead to stunning results.",
            21: "You don't have to be perfect to start, but you have to start to be perfect.",
            22: "Setting goals is the first step in turning the invisible into the visible.",
            23: "Success is a series of small wins that eventually lead to a massive victory.",
            24: "Failure is simply the opportunity to begin again, this time more intelligently.",
            25: "To be clear is to be kind. To be vague is to be unkind.",
            26: "The quality of your life is determined by the quality of the questions you ask.",
            27: "Personal development is the conviction that you can learn, grow, and transcend your current limits.",
            28: "The way we communicate with others and with ourselves ultimately determines the quality of our lives.",
            29: "Confidence is built on delivered results, not on promises.",
            30: "Your words are the vehicle of your leadership; drive them with precision and purpose.",
        },
        'intermediate': {
            1: "You have already crossed the first bridge. Now let's build a highway.",
            2: "If you master conditionals, you master the art of possibility.",
            3: "A great communicator doesn't just speak --- they accurately convey what others have said.",
            4: "The ability to express degrees of certainty is the mark of a critical thinker.",
            5: "A complex sentence does not mean a confusing sentence --- it means a complete one.",
            6: "Analysis is the bridge between observation and understanding.",
            7: "Week 1 is complete. You have laid the grammar architecture. Now inspect it for cracks.",
            8: "The Passive Voice is not weakness --- it is a tool of precision and diplomacy.",
            9: "The choice between -ing and 'to' is not random --- it reveals your mastery of nuance.",
            10: "Knowing a word is useful. Knowing how to combine it with others is power.",
            11: "Without discourse markers, your ideas are bricks. With them, they become a building.",
            12: "To hedge is not to hide --- it is to be honest about the limits of what you know.",
            13: "A well-crafted email is a letter of recommendation you send yourself.",
            14: "Two weeks in. You are no longer a basic speaker. But are you ready to prove it?",
            15: "It is not WHAT you say but WHERE you place the stress that changes the meaning.",
            16: "To paraphrase well is to prove you understood. To summarise well is to prove you can lead.",
            17: "What is left unsaid often carries more weight than what is spoken aloud.",
            18: "The ability to think and speak simultaneously is a skill --- and like all skills, it can be trained.",
            19: "The engineer who can explain a technical concept to a non-expert is worth ten who cannot.",
            20: "Reading critically is not about finding flaws --- it is about understanding the argument being made.",
            21: "Three weeks. You have moved from grammar drills to genuine intellectual communication.",
            22: "An argument essay is not a fight --- it is an organised exploration of a complex question.",
            23: "A presentation is not a report read aloud --- it is a performance with a purpose.",
            24: "Preparation is not cheating --- it is the difference between a good answer and a great one.",
            25: "Emphasis is not about volume --- it is about architecture.",
            26: "A well-written report changes decisions. A poorly written one is ignored.",
            27: "Negotiation is not about winning --- it is about finding the most workable solution.",
            28: "Four weeks. You are no longer learning English --- you are using it to think.",
            29: "Revision is not repetition --- it is the transformation of learned knowledge into permanent skill.",
            30: "You came here to improve your English. You leave with the language of a professional.",
        },
        'advanced': {
            1: "Your voice is not just sound --- it is your signature in every room you enter.",
            2: "Simple sentences tell. Complex sentences persuade.",
            3: "Every negotiation is a conversation between two futures. Choose your words with that awareness.",
            4: "Data without delivery is just noise. Be the signal.",
            5: "What is not said is often more important than what is said.",
            6: "Every unnecessary word is a credibility leak. Plug it.",
            7: "Facts inform. Stories transform. Master both.",
            8: "Perfect tenses show not just what happened --- but what it means now.",
            9: "The more you read precisely, the more precisely you think.",
            10: "An argument without structure is an opinion. Structure makes it a case.",
            11: "Your email is your handshake in a world you cannot see.",
            12: "Fluency is not speed. It is the absence of unintended pauses.",
            13: "Experts listen for what matters. Everyone else listens to everything.",
            14: "Progress is not linear --- it is cumulative. Every day adds to your foundation.",
            15: "Reading is not receiving. It is a conversation with the writer's intent.",
            16: "The question is not the problem. Your response to it is your opportunity.",
            17: "Leaders do not merely direct --- they elevate everyone around them through language.",
            18: "The passive voice does not hide action --- it redirects focus to what matters most.",
            19: "A word without context is a tool without purpose.",
            20: "Language is not just how you communicate --- it is how you think.",
            21: "The ability to think on your feet is the rarest professional skill. Develop it deliberately.",
            22: "A report is not a dump of information --- it is a guided journey for the reader.",
            23: "Read faster, understand deeper. These are not opposites --- they are partners.",
            24: "Careers are built in conversations that most people consider small talk.",
            25: "Every question in a viva or interview is an invitation to demonstrate your thinking.",
            26: "Idioms are shortcuts to cultural fluency. Use them wisely.",
            27: "The first draft shows thinking. The edited draft shows professionalism.",
            28: "In a global team, cultural intelligence is as important as technical intelligence.",
            29: "You do not learn a language to speak it --- you speak it to become it.",
            30: "Thirty days ago you were prepared. Today you are equipped. Tomorrow you will lead."
        }
    }
    return power_lines.get(level, {}).get(day, "Keep pushing forward! Every day is a step toward mastery.")

@login_required
def day_detail(request, level_name, day_number):
    """Display a specific day's learning content"""
    if level_name not in ['beginner', 'intermediate', 'advanced']:
        messages.error(request, 'Invalid level selected.')
        return redirect('learning:level_selection')
    
    if day_number < 1 or day_number > 30:
        messages.error(request, 'Invalid day number.')
        return redirect('learning:level_overview', level_name=level_name)
    
    progress = get_user_progress(request.user, level_name)
    
    completed_activities = DailyActivity.objects.filter(
        user=request.user,
        level=level_name,
        day_number=day_number,
        completed=True
    ).values_list('activity_type', flat=True)
    
    sentences = get_sentences_for_day(level_name, day_number)
    
    context = {
        'level': level_name,
        'day': day_number,
        'day_title': get_day_title(level_name, day_number),
        'completed_activities': list(completed_activities),
        'completed_count': len(completed_activities),
        'progress': progress,
        'sentences': sentences,
    }
    
    template_name = f'learning/{level_name}/day{day_number}.html'
    return render(request, template_name, context)

def get_sentences_for_day(level_name, day_number):
    """Get speaking sentences for specific day and level"""
    default_sentences = [
        (1, "Thank you for the explanation! It was very insightful."),
        (2, "Currently, I am implementing the changes we discussed."),
        (3, "I am striving to complete the draft by this evening."),
        (4, "I was analysing the data when you arrived."),
        (5, "I am truly indebted for your guidance."),
    ]
    return default_sentences

@login_required
@require_http_methods(["POST"])
def complete_activity(request, level_name, day_number, activity_type):
    """Mark a specific activity as complete"""
    try:
        activity, created = DailyActivity.objects.get_or_create(
            user=request.user,
            level=level_name,
            day_number=day_number,
            activity_type=activity_type,
            defaults={'completed': False}
        )
        
        if not activity.completed:
            activity.completed = True
            activity.completed_at = timezone.now()
            activity.save()
            
            all_activities = ['listening', 'speaking', 'reading', 'writing', 'vocabulary', 'grammar', 'game']
            completed_count = DailyActivity.objects.filter(
                user=request.user,
                level=level_name,
                day_number=day_number,
                completed=True
            ).count()
            
            all_completed = completed_count >= len(all_activities)
            
            return JsonResponse({
                'success': True,
                'all_activities_completed': all_completed,
                'completed_count': completed_count,
                'total_activities': len(all_activities)
            })
        
        return JsonResponse({'success': True, 'already_completed': True})
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@login_required
@require_http_methods(["POST"])
def complete_day(request, level_name, day_number):
    """Mark an entire day as complete (NO STAR ADDED HERE)"""
    progress = get_user_progress(request.user, level_name)
    
    all_activities = ['listening', 'speaking', 'reading', 'writing', 'vocabulary', 'grammar', 'game']
    completed_activities = DailyActivity.objects.filter(
        user=request.user,
        level=level_name,
        day_number=day_number,
        completed=True
    ).count()
    
    if completed_activities < len(all_activities):
        return JsonResponse({
            'success': False,
            'error': 'Please complete all activities first',
            'completed': completed_activities,
            'total': len(all_activities)
        }, status=400)
    
    # ✅ ONLY mark day as completed - NO STAR ADDED HERE
    if day_number not in progress.completed_days:
        progress.completed_days.append(day_number)
        progress.completed_days.sort()
        
        # Update current day
        next_day = progress.get_next_day()
        if next_day:
            progress.current_day = next_day
        
        # Update streak
        today = date.today()
        if progress.last_completed_date:
            days_diff = (today - progress.last_completed_date).days
            if days_diff == 1:
                progress.streak_days += 1
            elif days_diff > 1:
                progress.streak_days = 1
        else:
            progress.streak_days = 1
        
        progress.last_completed_date = today
        
        # Check if all days completed
        if progress.is_completed() and not progress.completed_at:
            progress.completed_at = timezone.now()
        
        progress.save()  # ✅ NO STAR ADDED HERE
        
        return JsonResponse({
            'success': True,
            'day_completed': day_number,
            'next_day': progress.current_day if not progress.is_completed() else None,
            'level_completed': progress.is_completed(),
            'completed_days': len(progress.completed_days),
            'percentage': progress.completion_percentage(),
            'streak': progress.streak_days,
        })
    
    return JsonResponse({'success': False, 'error': 'Day already completed'}, status=400)



@login_required
@require_http_methods(["POST"])
def save_vocabulary(request):
    """Save a word to user's vocabulary collection"""
    data = json.loads(request.body)
    word = data.get('word')
    
    if not word:
        return JsonResponse({'success': False, 'error': 'No word provided'}, status=400)
    
    saved_word, created = SavedVocabulary.objects.get_or_create(
        user=request.user,
        word=word
    )
    
    if created:
        return JsonResponse({'success': True, 'message': f'"{word}" saved to your vocabulary!'})
    else:
        return JsonResponse({'success': True, 'message': f'"{word}" is already in your vocabulary'})



@login_required
def take_final_test(request, level_name):
    """Display and process final test before certificate"""
    progress = get_user_progress(request.user, level_name)
    
    # ✅ FIX: Get the assessment for the specific level
    # Try to get existing assessment first
    try:
        assessment = LevelAssessment.objects.get(level=level_name)
    except LevelAssessment.DoesNotExist:
        # Create default assessment if it doesn't exist
        if level_name == 'beginner':
            passing_score = 15
            total_q = 20
        elif level_name == 'intermediate':
            passing_score = 20
            total_q = 25
        else:  # advanced
            passing_score = 18
            total_q = 25
            
        assessment = LevelAssessment.objects.create(
            level=level_name,
            title=f'{level_name.capitalize()} Final Assessment',
            passing_score=passing_score,
            time_limit_minutes=30 if level_name != 'advanced' else 45,
            total_questions=total_q,
            is_active=True
        )
    
    # Check if assessment has questions
    question_count = assessment.get_question_count()
    
    # ✅ If no questions exist for this level, show error
    if question_count == 0:
        messages.error(request, f'No questions found for {level_name} level assessment. Please contact support.')
        return redirect('learning:level_overview', level_name=level_name)
    
    # Production mode logic
    if not progress.is_completed():
        messages.warning(request, '⚠️ You must complete all 30 days before taking the final test.')
        return redirect('learning:level_overview', level_name=level_name)
    
    # Check if user has already passed
    existing_attempt = UserAssessmentAttempt.objects.filter(
        user=request.user,
        assessment=assessment,
        passed=True
    ).first()
    
    if existing_attempt:
        messages.info(request, f'✅ You have already passed this assessment with {existing_attempt.score}/{existing_attempt.total_questions}.')
        return redirect('learning:test_result', level_name=level_name)
    
    if request.method == 'POST':
        score, total_questions = process_assessment_answers(request.POST, assessment)
        percentage = (score / total_questions) * 100
        
        # Save attempt
        attempt = UserAssessmentAttempt.objects.create(
            user=request.user,
            assessment=assessment,
            level=level_name,
            score=score,
            total_questions=total_questions,
            percentage=percentage,
            passed=percentage >= assessment.passing_score,
            answers=dict(request.POST),
            completed_at=timezone.now()
        )
        
        if percentage >= assessment.passing_score:
            certificate, created = UserCertificate.objects.get_or_create(
                user=request.user,
                level=level_name,
                defaults={
                    'certificate_code': generate_certificate_code(request.user, level_name)
                }
            )
            
            progress.certificate_issued = True
            progress.certificate_issued_at = timezone.now()
            progress.save()
            
            # ========== AUTOMATIC LEVEL PROGRESSION ==========
            # Update profile level to the next stage
            profile = request.user.profile
            if level_name == 'beginner' and profile.level.lower() == 'beginner':
                profile.level = 'intermediate'
                profile.save()
            elif level_name == 'intermediate' and profile.level.lower() == 'intermediate':
                profile.level = 'advanced'
                profile.save()

            
            messages.success(request, f'🎉 Congratulations! You passed with {score}/{total_questions} ({percentage:.1f}%)! 🎉')
            return redirect(f'/learning/level/{level_name}/result/?score={score}')
        else:
            messages.error(request, f'❌ You scored {score}/{total_questions} ({percentage:.1f}%). Minimum passing score is {assessment.passing_score}/{total_questions} ({assessment.passing_score/total_questions*100:.0f}%). Please review and try again.')
            return redirect('learning:final_test', level_name=level_name)
    
    return render_test_page(request, level_name, assessment)


# Then replace your existing render_test_page function with this:
def render_test_page(request, level_name, assessment):
    """Render the dynamic test page with shuffled questions"""
    questions = assessment.get_questions()
    
    # Safety check for empty assessment
    if not questions.exists():
        messages.error(request, 'No questions found for this assessment. Please contact support.')
        return redirect('learning:level_overview', level_name=level_name)
    
    # Get or create session seed for consistent shuffling (optional)
    session_seed_key = f'assessment_{level_name}_seed'
    if session_seed_key not in request.session:
        # Generate random seed for this user's session
        request.session[session_seed_key] = random.randint(1, 10000)
        request.session.modified = True
    
    # Use session seed for reproducible shuffling (same order on page refresh)
    seed = request.session[session_seed_key]
    random.seed(seed)
    
    # Convert to list and shuffle questions
    questions_list = list(questions)
    random.shuffle(questions_list)  # 👈 THIS IS THE MAIN CHANGE
    
    # Convert questions to JSON for the template (options remain in original order)
    questions_data = []
    for q in questions_list:
        questions_data.append({
            'id': q.id,
            'text': q.text,
            'options': [{'letter': opt[0], 'text': opt[1]} for opt in q.get_options()],
            'correct': q.correct_answer  # Original correct answer (a, b, c, d)
        })
    
    # Reset random seed
    random.seed()
    
    context = {
        'level': level_name,
        'level_display': level_name.capitalize(),
        'assessment': assessment,
        'questions': questions_list,
        'questions_json': json.dumps(questions_data),
        'testing_mode': False,
    }
    return render(request, 'learning/final_test.html', context)

def process_assessment_answers(post_data, assessment):
    """Process assessment answers and return score"""
    questions = assessment.get_questions()
    score = 0
    
    for question in questions:
        # Look for answer with key format 'q_{question.id}'
        user_answer = post_data.get(f'q_{question.id}', '').lower()
        if user_answer == question.correct_answer:
            score += 1
    
    return score, questions.count()

@login_required
def certificate_view(request, level_name):
    """Display certificate page"""
    progress = get_user_progress(request.user, level_name)
    
    if not progress.is_completed():
        messages.error(request, '❌ You must complete all 30 days before accessing your certificate.')
        return redirect('learning:level_overview', level_name=level_name)
    
    if not progress.certificate_issued:
        messages.error(request, '❌ You must pass the final test before accessing your certificate.')
        return redirect('learning:final_test', level_name=level_name)
    
    certificate = get_object_or_404(UserCertificate, user=request.user, level=level_name)
    
    context = {
        'level': level_name,
        'certificate': certificate,
        'user_name': request.user.get_full_name() or request.user.username,
        'completion_date': progress.completed_at,
        'certificate_date': certificate.issued_at,
        'can_download': True,
    }
    return render(request, 'learning/certificate.html', context)

# Certificate paths and fonts
IMAGE_DIR = os.path.join(settings.BASE_DIR, 'learning', 'static', 'learning', 'images')
FONT_NAME_PATH = os.path.join(IMAGE_DIR, 'Cantiqe Italic.ttf')
FONT_OTHER_PATH = os.path.join(IMAGE_DIR, 'Montserrat-Italic-VariableFont_wght.ttf')


@login_required
def generate_certificate_png(request, level_name):
    """Generate PNG certificate with optimized speed and feedback saving"""
    # 1. Quick check if we already have this certificate saved
    from .models import UserCertificate
    certificate = UserCertificate.objects.filter(user=request.user, level=level_name).first()
    
    # Return immediately if image exists to save processing time
    if certificate and certificate.certificate_image:
        return HttpResponse(certificate.certificate_image, content_type='image/png')

    if request.method == 'POST':
        try:
            import json
            data = json.loads(request.body)
            rating = data.get('rating', 3)
            comment = data.get('feedback', '')
            
            from .models import UserFeedback
            UserFeedback.objects.create(
                user=request.user,
                level=level_name,
                rating=rating,
                comment=comment,
                created_at=timezone.now()
            )
        except Exception as e:
            print(f"Error saving feedback: {e}")

    try:


        # 1. Map level to template image
        template_map = {
            'beginner': 'Beginner_level.png',
            'intermediate': 'Intermediate_level.png',
            'advanced': 'Advance_level.png'
        }
        template_file = template_map.get(level_name.lower(), 'Beginner_level.png')
        template_path = os.path.join(IMAGE_DIR, template_file)

        if not os.path.exists(template_path):
            return JsonResponse({'error': f'Template not found at {template_path}'}, status=500)

        # 2. Open template
        img = Image.open(template_path).convert("RGB")
        draw = ImageDraw.Draw(img)

        # 3. Gather dynamic data
        user_name = (request.user.get_full_name() or request.user.username).upper()
        
        # Get profile for department and institute
        try:
            profile = request.user.profile
            dept_name = profile.department or ""
            inst_name = profile.institute or ""
        except:
            dept_name = ""
            inst_name = ""
            
        today = datetime.today().strftime("%d %B %Y")
        
        # Get or create certificate for ID and code
        certificate, created = UserCertificate.objects.get_or_create(
            user=request.user,
            level=level_name,
            defaults={'certificate_code': generate_certificate_code(request.user, level_name)}
        )
        # Format ID as 4-digit number (e.g., 0001)
        cert_id_display = f"{certificate.id:04d}"
        # 4. Define drawing parameters (Coordinates and Limits)
        # Using your latest requested parameters:
        name_pos = (1000, 736) # Center point
        name_max_width = 750
        name_size = 75
        
        dept_pos = (556, 885) 
        dept_max_width = 490
        dept_size = 40
        
        inst_pos = (554, 1014) 
        inst_max_width = 620
        inst_size = 40
        
        date_pos = (310, 1234)
        date_max_width = 400
        date_size = 34
        
        id_pos = (1466, 1224)
        id_max_width = 300
        id_size = 34





        # 5. Load and Draw Fonts with size adjustment
        def draw_text_fit(text, pos, max_width, initial_size, font_path, fill_color, anchor="mm", is_bold=False):
            size = initial_size
            font = ImageFont.truetype(font_path, size)
            while size > 10:
                bbox = draw.textbbox((0, 0), text, font=font)
                if (bbox[2] - bbox[0]) <= max_width:
                    break
                size -= 4
                font = ImageFont.truetype(font_path, size)

            
            if is_bold:
                # Faux-bold: Draw twice with 1px offset
                draw.text((pos[0], pos[1]), text, fill=fill_color, font=font, anchor=anchor)
                draw.text((pos[0] + 1, pos[1]), text, fill=fill_color, font=font, anchor=anchor)
            else:
                draw.text(pos, text, fill=fill_color, font=font, anchor=anchor)

        main_color = (0, 0, 0) # Black text

        # Name (Centered)
        draw_text_fit(user_name, name_pos, name_max_width, name_size, FONT_NAME_PATH, main_color, anchor="mm")
        
        # Department (Left-ish but adjusted) - BOLD
        draw_text_fit(dept_name, dept_pos, dept_max_width, dept_size, FONT_OTHER_PATH, main_color, anchor="la", is_bold=True)
        
        # Institute (Left-ish but adjusted) - BOLD
        draw_text_fit(inst_name, inst_pos, inst_max_width, inst_size, FONT_OTHER_PATH, main_color, anchor="la", is_bold=True)
        
        # Date - BOLD
        draw_text_fit(today, date_pos, date_max_width, date_size, FONT_OTHER_PATH, main_color, anchor="la", is_bold=True)
        
        # Certificate ID - BOLD
        draw_text_fit(cert_id_display, id_pos, id_max_width, id_size, FONT_OTHER_PATH, main_color, anchor="la", is_bold=True)




        # 7. Save and return
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG', dpi=(300, 300))
        img_buffer.seek(0)


        certificate.certificate_image = img_buffer.getvalue()
        certificate.save()

        return HttpResponse(img_buffer.getvalue(), content_type='image/png')

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def view_certificate_png(request, level_name):
    """View existing certificate PNG"""
    certificate = UserCertificate.objects.filter(
        user=request.user,
        level=level_name
    ).first()

    if certificate and certificate.certificate_image:
        return HttpResponse(certificate.certificate_image, content_type='image/png')
    else:
        return generate_certificate_png(request, level_name)

def generate_fallback_certificate(request, level_name, progress, certificate):
    """Generate a simple fallback certificate"""
    try:
        img = Image.new('RGB', (1200, 800), color='white')
        draw = ImageDraw.Draw(img)
        
        draw.rectangle([10, 10, 1190, 790], outline='#d4af37', width=5)
        draw.rectangle([20, 20, 1180, 780], outline='#d4af37', width=2)
        
        try:
            font_title = ImageFont.truetype(FONT_PATH_DATE, 48)
            font_name = ImageFont.truetype(FONT_PATH_DATE, 60)
            font_text = ImageFont.truetype(FONT_PATH_DATE, 24)
        except:
            font_title = ImageFont.load_default()
            font_name = ImageFont.load_default()
            font_text = ImageFont.load_default()
        
        title = "CERTIFICATE OF GRADUATION"
        bbox = draw.textbbox((0, 0), title, font=font_title)
        text_x = (1200 - (bbox[2] - bbox[0])) // 2
        draw.text((text_x, 80), title, fill='#2d3748', font=font_title)
        
        subtitle = "This certificate is proudly presented to"
        bbox = draw.textbbox((0, 0), subtitle, font=font_text)
        text_x = (1200 - (bbox[2] - bbox[0])) // 2
        draw.text((text_x, 200), subtitle, fill='#718096', font=font_text)
        
        user_name = request.user.get_full_name() or request.user.username
        bbox = draw.textbbox((0, 0), user_name, font=font_name)
        text_x = (1200 - (bbox[2] - bbox[0])) // 2
        draw.text((text_x, 280), user_name, fill='#d4af37', font=font_name)
        
        desc = f"For successfully completing the 30-Day {level_name.capitalize()} English Learning Journey"
        bbox = draw.textbbox((0, 0), desc, font=font_text)
        text_x = (1200 - (bbox[2] - bbox[0])) // 2
        draw.text((text_x, 400), desc, fill='#4a5568', font=font_text)
        
        today = datetime.now().strftime("%B %d, %Y")
        draw.text((100, 650), f"Date: {today}", fill='#718096', font=font_text)
        draw.text((100, 700), f"Level: {level_name.capitalize()}", fill='#718096', font=font_text)
        
        code = certificate.certificate_code if certificate else generate_certificate_code(request.user, level_name)
        draw.text((1200 - 300, 700), f"Code: {code}", fill='#718096', font=font_text)
        
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        if certificate:
            certificate.certificate_image = img_buffer.getvalue()
            certificate.save()
        else:
            certificate = UserCertificate.objects.create(
                user=request.user,
                level=level_name,
                certificate_code=generate_certificate_code(request.user, level_name),
                certificate_image=img_buffer.getvalue()
            )
        
        response = HttpResponse(img_buffer.getvalue(), content_type='image/png')
        response['Content-Disposition'] = f'attachment; filename="graduation_certificate_{level_name}_{request.user.username}.png"'
        return response
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error generating fallback certificate: {str(e)}',
            'code': 'FALLBACK_ERROR'
        }, status=500)

@login_required
def generate_certificate_pdf(request, level_name):
    """Generate a PDF version of the certificate for download"""
    # 1. Get user progress to check if they passed
    progress = get_user_progress(request.user, level_name)
    if not progress.is_completed():
         # Check assessment specifically
         asm = UserAssessmentAttempt.objects.filter(user=request.user, level=level_name, passed=True).first()
         if not asm:
            return HttpResponse("Assessment not passed", status=403)

    # 2. Get or generate the certificate image
    certificate = UserCertificate.objects.filter(user=request.user, level=level_name).first()
    
    if not certificate or not certificate.certificate_image:
        # If no image in DB, we need to generate it
        # We reuse the PNG generation logic but don't return the HttpResponse
        # Instead we get the image data
        response = generate_certificate_png(request, level_name)
        if isinstance(response, JsonResponse):
            return response
        certificate = UserCertificate.objects.filter(user=request.user, level=level_name).first()

    if not certificate or not certificate.certificate_image:
        return HttpResponse("Failed to generate certificate image", status=500)

    # 3. Convert PNG to PDF using PIL
    try:
        img_data = certificate.certificate_image
        img = Image.open(io.BytesIO(img_data)).convert("RGB")
        
        pdf_buffer = io.BytesIO()
        img.save(pdf_buffer, format='PDF', resolution=300.0)
        pdf_buffer.seek(0)
        
        # 4. Return as PDF download
        response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="English_Learning_Certificate_{level_name.capitalize()}.pdf"'
        
        # Update progress flag if not already set
        if not progress.certificate_issued:
            progress.certificate_issued = True
            progress.certificate_issued_at = timezone.now()
            progress.save()
            
        return response
    except Exception as e:
        return JsonResponse({'error': f'PDF conversion failed: {str(e)}'}, status=500)


@login_required
def certificate_status_api(request, level_name):
    """API to check certificate availability status"""
    progress = get_user_progress(request.user, level_name)
    certificate = UserCertificate.objects.filter(
        user=request.user,
        level=level_name
    ).first()
    
    all_days_completed = progress.is_completed()
    test_passed = progress.certificate_issued
    has_certificate = certificate is not None and certificate.certificate_image is not None
    
    if has_certificate:
        status = 'available'
        message = 'Your graduation certificate is ready!'
        action = 'view'
    elif all_days_completed and test_passed:
        status = 'ready_to_generate'
        message = 'Congratulations! You can now generate your graduation certificate.'
        action = 'generate'
    elif all_days_completed and not test_passed:
        status = 'test_required'
        message = 'Complete the final assessment to get your graduation certificate.'
        action = 'take_test'
    else:
        status = 'locked'
        remaining_days = 30 - len(progress.completed_days)
        message = f'Complete all 30 days to unlock your graduation certificate. ({remaining_days} days remaining)'
        action = 'complete_days'
    
    return JsonResponse({
        'success': True,
        'status': status,
        'message': message,
        'action': action,
        'has_certificate': has_certificate,
        'has_completed_days': all_days_completed,
        'has_passed_test': test_passed,
        'progress_percentage': progress.completion_percentage(),
        'completed_days': len(progress.completed_days),
        'total_days': 30,
        'certificate_issued': progress.certificate_issued,
    })

@login_required
@require_http_methods(["POST"])
def track_certificate_download(request, level_name):
    """Track certificate download count"""
    certificate = UserCertificate.objects.filter(
        user=request.user,
        level=level_name
    ).first()
    
    if certificate:
        certificate.download_count += 1
        certificate.downloaded = True
        certificate.save()
        return JsonResponse({'success': True, 'download_count': certificate.download_count})
    
    return JsonResponse({'success': False, 'error': 'Certificate not found'}, status=404)

@login_required
@require_http_methods(["POST"])
def track_certificate_share(request, level_name):
    """Track certificate share count"""
    certificate = UserCertificate.objects.filter(
        user=request.user,
        level=level_name
    ).first()
    
    if certificate:
        certificate.share_count += 1
        certificate.shared = True
        certificate.save()
        return JsonResponse({'success': True, 'share_count': certificate.share_count})
    
    return JsonResponse({'success': False, 'error': 'Certificate not found'}, status=404)

def generate_certificate_code(user, level):
    """Generate unique certificate code"""
    import hashlib
    import time
    unique_string = f"{user.id}_{level}_{time.time()}_{user.username}"
    return hashlib.md5(unique_string.encode()).hexdigest()[:12].upper()


@login_required
def get_progress_api(request, level_name):
    """API endpoint to get current progress"""
    progress = get_user_progress(request.user, level_name)
    return JsonResponse({
        'completed_days': progress.completed_days,
        'current_day': progress.current_day,
        'streak': progress.streak_days,
        'percentage': progress.completion_percentage(),
        'is_completed': progress.is_completed(),
        'certificate_issued': progress.certificate_issued,
    })


@login_required
def check_day_completion(request, level_name, day_number):
    """Check if a specific day is completed"""
    progress = get_user_progress(request.user, level_name)
    is_completed = day_number in progress.completed_days
    
    return JsonResponse({
        'success': True,
        'day': day_number,
        'is_completed': is_completed,
        'completed_days_count': len(progress.completed_days),
    })
@login_required
def mark_certificate_downloaded(request, certificate_id):
    """Legacy: Track when user downloads certificate"""
    certificate = get_object_or_404(UserCertificate, id=certificate_id, user=request.user)
    certificate.downloaded = True
    certificate.download_count += 1
    certificate.save()
    return JsonResponse({'success': True})

@login_required
def mark_certificate_shared(request, certificate_id):
    """Legacy: Track when user shares certificate"""
    certificate = get_object_or_404(UserCertificate, id=certificate_id, user=request.user)
    certificate.shared = True
    certificate.share_count += 1
    certificate.save()
    return JsonResponse({'success': True})

@login_required
def test_result(request, level_name):
    """Display test results with dynamic values"""
    # Get the assessment for this level
    assessment = LevelAssessment.objects.filter(level=level_name).first()
    
    # Get score from URL parameter
    score = request.GET.get('score', 0)
    
    context = {
        'level': level_name,
        'level_display': level_name.capitalize(),
        'total_questions': assessment.total_questions if assessment else 20,
        'passing_score': assessment.passing_score if assessment else 15,
        'user_score': score,
    }
    return render(request, 'learning/result.html', context)

@login_required
def reset_test_status(request, level_name):
    """TESTING ONLY: Reset assessment and certificate status"""
    if not settings.DEBUG:
        return JsonResponse({'error': 'Only available in debug mode'}, status=403)
    
    progress = get_user_progress(request.user, level_name)
    progress.certificate_issued = False
    progress.certificate_issued_at = None
    progress.save()
    
    certificate = UserCertificate.objects.filter(user=request.user, level=level_name).first()
    if certificate:
        certificate.certificate_image = None
        certificate.save()
    
    return JsonResponse({'success': True, 'message': 'Assessment status reset for testing'})

@login_required
@require_http_methods(["POST"])
def mark_intro_seen(request, level_name):
    """Mark that the user has seen the intro for a specific level"""
    try:
        progress = get_user_progress(request.user, level_name)
        progress.has_seen_intro = True
        progress.save()
        
        return JsonResponse({
            'success': True, 
            'message': f'Intro marked as seen for {level_name} level'
        })
    except Exception as e:
        return JsonResponse({
            'success': False, 
            'error': str(e)
        }, status=500)

@login_required
@require_http_methods(["POST"])
def collect_reward(request, level_name, day_number):
    """Claim a star reward for a completed day (stars only increase when user explicitly claims)"""
    progress = get_user_progress(request.user, level_name)

    if progress.claim_reward(day_number):
        return JsonResponse({
            'success': True,
            'stars': len(progress.collected_rewards),
            'day': day_number,
            'message': f'⭐ Star collected for Day {day_number}!'
        })

    # Determine why it failed
    if day_number not in progress.completed_days:
        return JsonResponse({'success': False, 'error': 'Day not completed yet'}, status=400)

    return JsonResponse({
        'success': False,
        'error': 'Reward already collected for this day',
        'already_collected': True
    }, status=400)

GROQ_API_KEY = "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"

@login_required
@csrf_exempt
def ai_evaluate(request):
    """
    Generic AI evaluation endpoint for all days.
    Receives text and system prompt from frontend, calls Groq API, returns score and feedback.
    Implements model rotation to handle rate limits.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=400)
    
    try:
        data = json.loads(request.body)
        user_text = data.get('text', '')
        task_type = data.get('task_type', 'general')
        day_number = data.get('day_number', 0)
        level = data.get('level', 'intermediate')
        
        # Get custom system prompt from frontend, or use default
        system_prompt = data.get('system_prompt', None)
        
        if not user_text:
            return JsonResponse({
                'success': False,
                'feedback': 'No text provided for evaluation.',
                'suggestion': 'Please speak clearly and try again.'
            })
        
        # Default system prompt if not provided
        if not system_prompt:
            system_prompt = f"""You are an English teacher evaluating a student's response for Day {day_number} ({level} level).
                Task type: {task_type}
                Evaluate based on grammar, vocabulary, and clarity.
                Return ONLY a JSON object with:
                {{"score": 0-100, "correct": true/false, "feedback": "short feedback (max 15 words)", "suggestion": "improvement tip (max 15 words)"}}
                Be encouraging. Keep feedback VERY SHORT."""
        
        # List of models to try in order (handles rate limits)
        models = [
            'llama-3.3-70b-versatile',
            'llama-3.1-70b-versatile',
            'mixtral-8x7b-32768',
            'llama-3.1-8b-instant'
        ]
        
        last_error = None
        for model_name in models:
            try:
                # Call Groq API
                headers = {
                    'Authorization': f'Bearer {GROQ_API_KEY}',
                    'Content-Type': 'application/json'
                }
                
                payload = {
                    'model': model_name,
                    'messages': [
                        {'role': 'system', 'content': system_prompt},
                        {'role': 'user', 'content': f"Student's response: {user_text}\n\nEvaluate this response."}
                    ],
                    'temperature': 0.3,
                    'max_tokens': 300,
                    'response_format': {'type': 'json_object'}
                }
                
                response = requests.post(
                    'https://api.groq.com/openai/v1/chat/completions',
                    headers=headers,
                    json=payload,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    ai_output = json.loads(result['choices'][0]['message']['content'])
                    
                    # Merging AI output into the response while keeping defaults
                    response_data = {
                        'success': True,
                        'score': ai_output.get('score', 50),
                        'correct': ai_output.get('correct', False),
                        'feedback': ai_output.get('feedback', 'Good attempt!'),
                        'suggestion': ai_output.get('suggestion', 'Keep practicing!'),
                        'model_used': model_name
                    }
                    response_data.update(ai_output)
                    return JsonResponse(response_data)
                
                elif response.status_code == 429:
                    print(f"GROQ RATE LIMIT (429) for {model_name}. Trying next model...")
                    last_error = response.text
                    continue  # Try next model
                
                else:
                    print(f"GROQ API ERROR ({response.status_code}) for {model_name}: {response.text}")
                    last_error = response.text
                    continue # Try next model or fail at end
                    
            except Exception as e:
                print(f"GROQ REQUEST EXCEPTION for {model_name}: {str(e)}")
                last_error = str(e)
                continue
        
        # If we get here, all models failed
        return JsonResponse({
            'success': False,
            'feedback': 'The AI evaluation service is currently busy.',
            'suggestion': 'We are processing many requests. Please try again in a moment.',
            'debug_info': last_error
        }, status=200) # Use 200 to allow UI to handle it gracefully
            
    except Exception as e:
        print(f"AI EVALUATION TOP-LEVEL EXCEPTION: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'feedback': 'Something went wrong with the evaluation.',
            'suggestion': 'Please refresh the page and try again.',
            'debug_info': str(e)
        }, status=200)

@login_required
def toolkit_tool(request, tool_name):
    """Render a specific advanced tool from the toolkit"""
    tool_map = {
        'grammar-hacks': 'tool1.html',
        'crossword': 'tool2.html',
        'word-search': 'tool3.html',
        'idiom-challenge': 'tool4.html',
        'grammar-detective': 'tool5.html',
        'word-association': 'tool6.html',
        'sentence-transform': 'tool7.html',
        'register-remix': 'tool8.html',
    }
    template = tool_map.get(tool_name)
    if not template:
        return redirect('learning:level_overview', level_name='advanced')
    
    return render(request, f'learning/Advanced/tools/{template}', {
        'level': 'advanced',
        'tool_name': tool_name
    })
