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
            1: "Mastering Nuance",
            2: "Rhetorical Devices",
            3: "Academic Writing",
            4: "Research Presentation",
            5: "Debate & Argumentation",
            6: "Business Strategy Communication",
            7: "Week 1 Synthesis",
            8: "Literature Analysis",
            9: "Technical Specifications",
            10: "Executive Summaries",
            11: "Crisis Communication",
            12: "Persuasive Speaking",
            13: "Negotiation Mastery",
            14: "Cross-functional Leadership",
            15: "Advanced Grammar",
            16: "Editing & Proofreading",
            17: "Translation Skills",
            18: "Conference Presentation",
            19: "Mentoring Language",
            20: "Strategic Planning",
            21: "Week 3 Review",
            22: "Innovation Pitching",
            23: "Change Management",
            24: "Global Communication",
            25: "Thought Leadership",
            26: "Publishing & Writing",
            27: "Executive Presence",
            28: "Boardroom Communication",
            29: "Legacy Building",
            30: "Capstone Project & Celebration",
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
            1: "Mastery is not about knowing everything — it's about knowing what matters.",
            2: "The most powerful communicators make the complex feel simple.",
            3: "Academic writing is clarity dressed in precision.",
            4: "A great presentation doesn't inform — it transforms.",
            5: "In debate, the goal isn't to win — it's to find the truth.",
            6: "Strategy without communication is just a plan that never happens.",
            7: "Synthesis is the highest form of understanding.",
            8: "Literature teaches us the grammar of the human heart.",
            9: "Technical writing is the art of making the invisible visible.",
            10: "An executive summary respects everyone's time while delivering value.",
            11: "In crisis, clarity is compassion.",
            12: "Persuasion is the intersection of logic, emotion, and credibility.",
            13: "True negotiation creates value — it doesn't just divide it.",
            14: "Leadership communication is about alignment, not authority.",
            15: "Advanced grammar isn't about rules — it's about choices.",
            16: "Editing is where good writing becomes great writing.",
            17: "Translation is the art of carrying meaning across cultural bridges.",
            18: "A conference presentation is your ideas in their best light.",
            19: "Mentoring language builds capacity, not dependency.",
            20: "Strategic planning is storytelling with deadlines.",
            21: "Review is where reflection meets action.",
            22: "An innovation pitch is a promise of a better future.",
            23: "Change management communication turns resistance into readiness.",
            24: "Global communication respects difference while finding common ground.",
            25: "Thought leadership is having opinions that matter, backed by expertise.",
            26: "Publishing is how expertise becomes legacy.",
            27: "Executive presence is earned, not declared.",
            28: "Boardroom communication is precision under pressure.",
            29: "Legacy building is what you build that outlasts you.",
            30: "A capstone project proves you've transformed from learner to leader.",
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
def save_recording(request, level_name, day_number, activity_type):
    """Save audio recording for speaking/listening activities"""
    if 'audio' not in request.FILES:
        return JsonResponse({'success': False, 'error': 'No audio file provided'}, status=400)
    
    audio_file = request.FILES['audio']
    file_path = f'recordings/{request.user.id}/{level_name}/day{day_number}/{activity_type}_{timezone.now().timestamp()}.webm'
    saved_path = default_storage.save(file_path, ContentFile(audio_file.read()))
    
    activity, _ = DailyActivity.objects.get_or_create(
        user=request.user,
        level=level_name,
        day_number=day_number,
        activity_type=activity_type,
        defaults={'recording_url': saved_path}
    )
    activity.recording_url = saved_path
    activity.save()
    
    return JsonResponse({'success': True, 'url': saved_path})

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
def save_writing_response(request, level_name, day_number):
    """Save writing activity responses"""
    data = json.loads(request.body)
    response_data = data.get('response')
    
    activity, _ = DailyActivity.objects.get_or_create(
        user=request.user,
        level=level_name,
        day_number=day_number,
        activity_type='writing',
        defaults={'response_data': response_data}
    )
    activity.response_data = response_data
    activity.save()
    
    return JsonResponse({'success': True})

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
    
    TESTING_MODE = settings.DEBUG
    
    if TESTING_MODE:
        if not progress.is_completed():
            messages.info(request, f'⚠️ TESTING MODE: {level_name.capitalize()} assessment taken before completing all days.')
        
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
                messages.success(request, f'🎉 TESTING MODE: {level_name.capitalize()} assessment passed! Score: {score}/{total_questions} ({percentage:.1f}%) 🎉')
                
                progress.certificate_issued = True
                progress.certificate_issued_at = timezone.now()
                progress.save()
                
                certificate, created = UserCertificate.objects.get_or_create(
                    user=request.user,
                    level=level_name,
                    defaults={
                        'certificate_code': generate_certificate_code(request.user, level_name)
                    }
                )
                
                return redirect(f'/learning/level/{level_name}/result/?score={score}')
            else:
                messages.error(request, f'❌ TESTING MODE: Failed! Score: {score}/{total_questions} ({percentage:.1f}%). Need {assessment.passing_score}/{total_questions} to pass.')
                return redirect('learning:final_test', level_name=level_name)
        
        return render_test_page(request, level_name, assessment)
    
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
        return redirect('learning:certificate_view', level_name=level_name)
    
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
        'testing_mode': settings.DEBUG,
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

TEMPLATE_PATH = r"D:\English_learning\learning\static\learning\images\certificate_template.png"
FONT_PATH_NAME = r"D:\English_learning\learning\static\learning\images\Cinzel-VariableFont_wght.ttf"
FONT_PATH_DATE = r"D:\English_learning\learning\static\learning\images\Montserrat-VariableFont_wght.ttf"

@login_required
def generate_certificate_png(request, level_name):
    """Generate PNG certificate using template"""
    try:
        if not os.path.exists(TEMPLATE_PATH):
            return JsonResponse({'error': 'Template not found'}, status=500)

        img = Image.open(TEMPLATE_PATH).convert("RGB")
        draw = ImageDraw.Draw(img)

        img_width, img_height = img.size

        user_name = request.user.get_full_name() or request.user.username
        today = datetime.today().strftime("%d %B %Y")

        certificate = UserCertificate.objects.filter(user=request.user, level=level_name).first()
        cert_code = certificate.certificate_code if certificate else generate_certificate_code(request.user, level_name)

        name_font_size = 72

        while name_font_size > 40:
            name_font = ImageFont.truetype(FONT_PATH_NAME, name_font_size)
            bbox = draw.textbbox((0, 0), user_name, font=name_font)
            text_width = bbox[2] - bbox[0]

            if text_width < img_width * 0.7:
                break
            name_font_size -= 2

        date_font = ImageFont.truetype(FONT_PATH_DATE, 36)
        id_font = ImageFont.truetype(FONT_PATH_DATE, 30)

        main_color = (31, 58, 95)

        bbox = draw.textbbox((0, 0), user_name, font=name_font)
        text_width = bbox[2] - bbox[0]

        x_name = (img_width - text_width) // 2
        y_name = int(img_height * 0.445)

        draw.text((x_name, y_name), user_name, fill=main_color, font=name_font)

        date_text = f"Date Issued: {today}"
        x_date = int(img_width * 0.12)
        y_date = int(img_height * 0.88)
        draw.text((x_date, y_date), date_text, fill=main_color, font=date_font)

        id_text = f"Certificate ID: {cert_code}"
        bbox = draw.textbbox((0, 0), id_text, font=id_font)
        text_width = bbox[2] - bbox[0]
        x_id = img_width - text_width - int(img_width * 0.08)
        y_id = int(img_height * 0.88)
        draw.text((x_id, y_id), id_text, fill=main_color, font=id_font)

        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG', dpi=(300, 300))
        img_buffer.seek(0)

        certificate, created = UserCertificate.objects.get_or_create(
            user=request.user,
            level=level_name,
            defaults={'certificate_code': cert_code}
        )

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
        
        # Call Groq API
        headers = {
            'Authorization': f'Bearer {GROQ_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model':'llama-3.3-70b-versatile',
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
            
            return JsonResponse({
                'success': True,
                'score': ai_output.get('score', 50),
                'correct': ai_output.get('correct', False),
                'feedback': ai_output.get('feedback', 'Good attempt!'),
                'suggestion': ai_output.get('suggestion', 'Keep practicing!')
            })
        else:
            return JsonResponse({
                'success': False,
                'feedback': 'AI service error. Please try again.',
                'suggestion': 'Check your connection and retry.'
            }, status=500)
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'feedback': f'Error: {str(e)[:100]}',
            'suggestion': 'Please try again.'
        }, status=500)