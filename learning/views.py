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
import os
import io
from datetime import datetime, date
from PIL import Image, ImageDraw, ImageFont
from .models import UserLearningProgress, DailyActivity, SavedVocabulary, UserCertificate

def get_user_progress(user, level):
    """Helper function to get or create user progress"""
    progress, created = UserLearningProgress.objects.get_or_create(
        user=user,
        level=level,
        defaults={
            'completed_days': [],
            'current_day': 1,
            'streak_days': 0,
            'has_seen_intro': False  # Added default
        }
    )
    return progress

@login_required
def level_selection(request):
    """Display level selection page based on pretest results"""
    # Get user's overall score from profile
    profile = request.user.profile
    overall_percentage = profile.get_overall_pretest_score() if hasattr(profile, 'get_overall_pretest_score') else 0
    
    # Determine unlocked levels
    if overall_percentage >= 80:
        user_level = 'advanced'
        beginner_unlocked = True
        intermediate_unlocked = True
        advanced_unlocked = True
    elif overall_percentage >= 60:
        user_level = 'intermediate'
        beginner_unlocked = True
        intermediate_unlocked = True
        advanced_unlocked = False
    else:
        user_level = 'beginner'
        beginner_unlocked = True
        intermediate_unlocked = False
        advanced_unlocked = False
    
    # Get progress for each level
    beginner_progress = get_user_progress(request.user, 'beginner')
    intermediate_progress = get_user_progress(request.user, 'intermediate') if intermediate_unlocked else None
    advanced_progress = get_user_progress(request.user, 'advanced') if advanced_unlocked else None
    
    context = {
        'user_level_name': user_level,
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
    # Validate level
    if level_name not in ['beginner', 'intermediate', 'advanced']:
        messages.error(request, 'Invalid level selected.')
        return redirect('learning:level_selection')
    
    # Get or create user progress
    progress = get_user_progress(request.user, level_name)
    
    # ── AUTO-COMPLETE DAY FROM URL PARAM ──────────────────────────────────────
    # Day templates redirect with ?celebrate=true&completed=N after finishing a day.
    # If the API call failed (wrong URL in template), we catch it here and mark the day complete.
    celebrate_day = request.GET.get('completed')
    if celebrate_day:
        try:
            celebrate_day_num = int(celebrate_day)
            if 1 <= celebrate_day_num <= 30 and celebrate_day_num not in progress.completed_days:
                progress.complete_day(celebrate_day_num)  # updates current_day + streak in DB
                # Refresh from DB
                progress.refresh_from_db()
        except (ValueError, TypeError):
            pass

    # ── DERIVE CURRENT DAY FROM COMPLETED DAYS (not the stale DB field) ───────
    # This is the key fix: compute which day to show as "current" based on the
    # actual list of completed days, so even if the API call URL was wrong the
    # overview will correctly show the next unlocked day.
    completed_set = set(progress.completed_days)
    computed_current_day = 31  # default: all done
    for d in range(1, 31):
        if d not in completed_set:
            computed_current_day = d
            break

    # Keep the DB field in sync silently
    if progress.current_day != computed_current_day and computed_current_day <= 30:
        progress.current_day = computed_current_day
        progress.save()

    # ✅ NEW LOGIC: Intro + Assessment
    show_intro = not progress.has_seen_intro
    is_assessment = request.GET.get('assessment') == 'true'

    # Get certificate if issued
    certificate = UserCertificate.objects.filter(user=request.user, level=level_name).first()

    # Prepare day titles dictionary
    day_titles = {}
    for day in range(1, 31):
        day_titles[day] = get_day_title(level_name, day)

    # Check if level is completed and certificate issued
    is_completed = progress.is_completed()
    certificate_issued = progress.certificate_issued

    context = {
        'level': level_name,
        'level_display': level_name.capitalize(),
        'completed_count': len(progress.completed_days),
        'completed_days_list': progress.completed_days,
        'current_day': computed_current_day,   # ← use computed value, not stale DB field
        'streak': progress.streak_days,
        'percentage': progress.completion_percentage(),
        'is_completed': is_completed,
        'certificate_issued': certificate_issued,
        'certificate_id': certificate.id if certificate else None,
        'day_titles': day_titles,
        'user': request.user,

        # ✅ NEW CONTEXT VARIABLES
        'show_intro': show_intro,
        'is_assessment': is_assessment,
    }

    # ✅ MARK INTRO AS SEEN (only first time)
    if show_intro:
        progress.has_seen_intro = True
        progress.save()

    return render(request, 'learning/level_overview.html', context)

def get_day_title(level, day):
    """Get title for each day based on level"""
    titles = {
        'beginner': {
            1: "Introduction to English Basics",
            2: "Greetings and Introductions",
            3: "Basic Vocabulary - Family",
            4: "Basic Vocabulary - Daily Routines",
            5: "Simple Present Tense",
            6: "Present Continuous Tense",
            7: "Review Week 1",
            8: "Numbers and Counting",
            9: "Colors and Shapes",
            10: "Food and Drinks",
            11: "Weather and Seasons",
            12: "Simple Past Tense",
            13: "Past Continuous Tense",
            14: "Future Tense",
            15: "Modal Verbs",
            16: "Prepositions of Place",
            17: "Prepositions of Time",
            18: "Question Formation",
            19: "Making Requests",
            20: "Giving Directions",
            21: "Telephone English",
            22: "Email Writing Basics",
            23: "Review Week 3",
            24: "Describing People",
            25: "Describing Places",
            26: "Telling Stories",
            27: "Expressing Opinions",
            28: "Making Suggestions",
            29: "Apologizing and Thanking",
            30: "Final Review & Celebration",
        },
        'intermediate': {
            1: "Advanced Greetings & Small Talk",
            2: "Professional Email Writing",
            3: "Idioms and Expressions",
            4: "Present Perfect Tense",
            5: "Business Vocabulary",
            6: "Reported Speech",
            7: "Week 1 Review",
            8: "Conditional Sentences",
            9: "Passive Voice",
            10: "Presentation Skills",
            11: "Negotiation Language",
            12: "Phrasal Verbs",
            13: "Complex Sentences",
            14: "Argumentation & Debate",
            15: "Formal Letter Writing",
            16: "Interview Preparation",
            17: "Technical Documentation",
            18: "Meeting Participation",
            19: "Cross-cultural Communication",
            20: "Project Management Terms",
            21: "Week 3 Review",
            22: "Abstract Thinking",
            23: "Persuasive Writing",
            24: "Leadership Communication",
            25: "Critical Analysis",
            26: "Storytelling Techniques",
            27: "Public Speaking",
            28: "Networking Skills",
            29: "Professional Etiquette",
            30: "Final Project & Review",
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

@login_required
def day_detail(request, level_name, day_number):
    """Display a specific day's learning content - TESTING MODE (no access restrictions)"""
    # Validate level and day
    if level_name not in ['beginner', 'intermediate', 'advanced']:
        messages.error(request, 'Invalid level selected.')
        return redirect('learning:level_selection')
    
    if day_number < 1 or day_number > 30:
        messages.error(request, 'Invalid day number.')
        return redirect('learning:level_overview', level_name=level_name)
    
    # Get or create user progress
    progress = get_user_progress(request.user, level_name)
    
    # NO ACCESS CHECK - ALL DAYS ARE ACCESSIBLE FOR TESTING
    
    # Get completed activities for this day
    completed_activities = DailyActivity.objects.filter(
        user=request.user,
        level=level_name,
        day_number=day_number,
        completed=True
    ).values_list('activity_type', flat=True)
    
    # Prepare sentences for speaking activity
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
    
    # Template path: learning/beginner/day1.html
    template_name = f'learning/{level_name}/day{day_number}.html'
    
    return render(request, template_name, context)

def get_sentences_for_day(level_name, day_number):
    """Get speaking sentences for specific day and level"""
    # Default sentences for Day 11 (Beginner)
    default_sentences = [
        (1, "Thank you for the explanation! It was very insightful."),
        (2, "Currently, I am implementing the changes we discussed."),
        (3, "I am striving to complete the draft by this evening."),
        (4, "I was analysing the data when you arrived."),
        (5, "I am truly indebted for your guidance."),
    ]
    
    # You can customize sentences for each day here
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
            
            # Check if all activities for this day are complete
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
    """Mark an entire day as complete and unlock next day"""
    progress = get_user_progress(request.user, level_name)
    
    # Verify all activities are completed
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
    
    # Mark day as complete
    if progress.complete_day(day_number):
        # Check if level is now complete
        level_completed = progress.is_completed()
        
        return JsonResponse({
            'success': True,
            'day_completed': day_number,
            'next_day': progress.current_day if not level_completed else None,
            'level_completed': level_completed,
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
    
    # Update or create activity with recording URL
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
    
    # TESTING MODE: Allow multiple attempts and auto-pass for testing
    TESTING_MODE = True  # Keep True for testing, False for production
    
    if TESTING_MODE:
        # For testing: Allow access even if not completed all days
        if not progress.is_completed():
            messages.info(request, '⚠️ TESTING MODE: Assessment taken before completing all days.')
        
        if request.method == 'POST':
            # Process test answers
            score, total_questions = process_final_test_answers(request.POST, level_name)
            percentage = (score / total_questions) * 100
            
            # Always pass in testing mode (or check score if you want)
            # For testing, we'll auto-pass regardless of score
            messages.success(request, f'🎉 TESTING MODE: Assessment passed! Score: {score}/{total_questions} ({percentage:.1f}%) 🎉')
            
            # Update progress - mark certificate as issued for testing
            progress.certificate_issued = True
            progress.certificate_issued_at = timezone.now()
            progress.save()
            
            # Create or update certificate
            certificate, created = UserCertificate.objects.get_or_create(
                user=request.user,
                level=level_name,
                defaults={
                    'certificate_code': generate_certificate_code(request.user, level_name)
                }
            )
            
            # Redirect to result page with score
            return redirect(f'/learning/level/{level_name}/result/?score={score}')
        
        # ✅ CHANGED: GET request - redirect to overview with assessment mode
        return redirect(f'/learning/level/{level_name}/?assessment=true')
    
    # PRODUCTION MODE (when TESTING_MODE = False)
    if not progress.is_completed():
        messages.warning(request, '⚠️ You must complete all 30 days before taking the final test.')
        return redirect('learning:level_overview', level_name=level_name)
    
    if request.method == 'POST':
        score, total_questions = process_final_test_answers(request.POST, level_name)
        percentage = (score / total_questions) * 100
        passing_percentage = 75  # Updated to 75% (15/20)
        
        if percentage >= passing_percentage:
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
            
            # Redirect to result page with score
            return redirect(f'/learning/level/{level_name}/result/?score={score}')
        else:
            messages.error(request, f'❌ You scored {score}/{total_questions} ({percentage:.1f}%). Minimum passing score is {passing_percentage}%. Please review and try again.')
            return redirect('learning:final_test', level_name=level_name)
    
    # ✅ CHANGED: GET request - redirect to overview with assessment mode
    return redirect(f'/learning/level/{level_name}/?assessment=true')

@login_required
def render_test_page(request, level_name):
    """Render the actual test page (after modal confirmation)"""
    progress = get_user_progress(request.user, level_name)
    
    context = {
        'level': level_name,
        'level_display': level_name.capitalize(),
        'progress': progress,
        'testing_mode': True if settings.DEBUG else False,
    }
    template_path = f'learning/{level_name}/final_test.html'
    return render(request, template_path, context)

@login_required
def certificate_view(request, level_name):
    """Display certificate page - only if all requirements are met"""
    progress = get_user_progress(request.user, level_name)
    
    # Check requirements
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

# Paths to your template and fonts
TEMPLATE_PATH = r"D:\English_learning\learning\static\learning\images\certificate_template.png"
FONT_PATH_NAME = r"D:\English_learning\learning\static\learning\images\Cinzel-VariableFont_wght.ttf"
FONT_PATH_DATE = r"D:\English_learning\learning\static\learning\images\Montserrat-VariableFont_wght.ttf"

@login_required
def generate_certificate_png(request, level_name):
    """Generate PNG certificate using template with precise positioning"""
    try:
        # Open template
        if not os.path.exists(TEMPLATE_PATH):
            return JsonResponse({'error': 'Template not found'}, status=500)

        img = Image.open(TEMPLATE_PATH).convert("RGB")
        draw = ImageDraw.Draw(img)

        img_width, img_height = img.size

        # USER DATA
        user_name = request.user.get_full_name() or request.user.username
        today = datetime.today().strftime("%d %B %Y")

        certificate = UserCertificate.objects.filter(user=request.user, level=level_name).first()
        cert_code = certificate.certificate_code if certificate else generate_certificate_code(request.user, level_name)

        # FONTS (Dynamic sizing for name)
        name_font_size = 72

        # Auto reduce font size if name is long
        while name_font_size > 40:
            name_font = ImageFont.truetype(FONT_PATH_NAME, name_font_size)
            bbox = draw.textbbox((0, 0), user_name, font=name_font)
            text_width = bbox[2] - bbox[0]

            if text_width < img_width * 0.7:
                break
            name_font_size -= 2

        date_font = ImageFont.truetype(FONT_PATH_DATE, 36)
        id_font = ImageFont.truetype(FONT_PATH_DATE, 30)

        # COLOR - Same premium dark blue everywhere
        main_color = (31, 58, 95)

        # NAME - Centered on gold line
        bbox = draw.textbbox((0, 0), user_name, font=name_font)
        text_width = bbox[2] - bbox[0]

        x_name = (img_width - text_width) // 2
        y_name = int(img_height * 0.445)

        draw.text((x_name, y_name), user_name, fill=main_color, font=name_font)

        # DATE - LEFT SIDE
        date_text = f"Date Issued: {today}"
        x_date = int(img_width * 0.12)
        y_date = int(img_height * 0.88)
        draw.text((x_date, y_date), date_text, fill=main_color, font=date_font)

        # CERTIFICATE ID - RIGHT SIDE
        id_text = f"Certificate ID: {cert_code}"
        bbox = draw.textbbox((0, 0), id_text, font=id_font)
        text_width = bbox[2] - bbox[0]
        x_id = img_width - text_width - int(img_width * 0.08)
        y_id = int(img_height * 0.88)
        draw.text((x_id, y_id), id_text, fill=main_color, font=id_font)

        # SAVE IMAGE
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG', dpi=(300, 300))
        img_buffer.seek(0)

        # Save in DB
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
    """View existing certificate PNG - returns actual PNG image"""
    certificate = UserCertificate.objects.filter(
        user=request.user,
        level=level_name
    ).first()

    if certificate and certificate.certificate_image:
        return HttpResponse(certificate.certificate_image, content_type='image/png')
    else:
        return generate_certificate_png(request, level_name)

def generate_fallback_certificate(request, level_name, progress, certificate):
    """Generate a simple fallback certificate if template is missing"""
    try:
        # Create a new image
        img = Image.new('RGB', (1200, 800), color='white')
        draw = ImageDraw.Draw(img)
        
        # Draw border
        draw.rectangle([10, 10, 1190, 790], outline='#d4af37', width=5)
        draw.rectangle([20, 20, 1180, 780], outline='#d4af37', width=2)
        
        # Draw title
        try:
            font_title = ImageFont.truetype(FONT_PATH_REGULAR, 48)
            font_name = ImageFont.truetype(FONT_PATH_REGULAR, 60)
            font_text = ImageFont.truetype(FONT_PATH_REGULAR, 24)
        except:
            font_title = ImageFont.load_default()
            font_name = ImageFont.load_default()
            font_text = ImageFont.load_default()
        
        # Title
        title = "CERTIFICATE OF GRADUATION"
        bbox = draw.textbbox((0, 0), title, font=font_title)
        text_x = (1200 - (bbox[2] - bbox[0])) // 2
        draw.text((text_x, 80), title, fill='#2d3748', font=font_title)
        
        # Subtitle
        subtitle = "This certificate is proudly presented to"
        bbox = draw.textbbox((0, 0), subtitle, font=font_text)
        text_x = (1200 - (bbox[2] - bbox[0])) // 2
        draw.text((text_x, 200), subtitle, fill='#718096', font=font_text)
        
        # Name
        user_name = request.user.get_full_name() or request.user.username
        bbox = draw.textbbox((0, 0), user_name, font=font_name)
        text_x = (1200 - (bbox[2] - bbox[0])) // 2
        draw.text((text_x, 280), user_name, fill='#d4af37', font=font_name)
        
        # Description
        desc = f"For successfully completing the 30-Day {level_name.capitalize()} English Learning Journey"
        bbox = draw.textbbox((0, 0), desc, font=font_text)
        text_x = (1200 - (bbox[2] - bbox[0])) // 2
        draw.text((text_x, 400), desc, fill='#4a5568', font=font_text)
        
        # Date
        today = datetime.now().strftime("%B %d, %Y")
        draw.text((100, 650), f"Date: {today}", fill='#718096', font=font_text)
        
        # Level
        draw.text((100, 700), f"Level: {level_name.capitalize()}", fill='#718096', font=font_text)
        
        # Certificate code
        code = certificate.certificate_code if certificate else generate_certificate_code(request.user, level_name)
        draw.text((1200 - 300, 700), f"Code: {code}", fill='#718096', font=font_text)
        
        # Save to memory
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
    """API to check certificate availability status - NO REDIRECTS"""
    progress = get_user_progress(request.user, level_name)
    certificate = UserCertificate.objects.filter(
        user=request.user,
        level=level_name
    ).first()
    
    # Determine what actions are allowed
    all_days_completed = progress.is_completed()
    test_passed = progress.certificate_issued
    has_certificate = certificate is not None and certificate.certificate_image is not None
    
    # Determine status message and available actions
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

def process_final_test_answers(post_data, level_name):
    """Process final test answers and return score and total questions"""
    
    # Updated answer key for 20 questions (removed Q3, Q7, Q8, Q14, Q22)
    answer_key = {
        'q1': 'b', 'q2': 'b', 'q4': 'b', 'q5': 'a', 'q6': 'b',
        'q9': 'b', 'q10': 'b', 'q11': 'b', 'q12': 'c', 'q13': 'b',
        'q15': 'b', 'q16': 'b', 'q17': 'b', 'q18': 'b', 'q19': 'b',
        'q20': 'b', 'q21': 'b', 'q23': 'b', 'q24': 'b', 'q25': 'b'
    }
    
    total_questions = len(answer_key)  # This will be 20
    score = 0
    
    for question, correct_answer in answer_key.items():
        user_answer = post_data.get(question, '').lower()
        if user_answer == correct_answer:
            score += 1
    
    return score, total_questions

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
    """Display test results"""
    context = {
        'level': level_name,
        'level_display': level_name.capitalize(),
    }
    return render(request, f'learning/{level_name}/result.html', context)

@login_required
def reset_test_status(request, level_name):
    """TESTING ONLY: Reset assessment and certificate status"""
    if not settings.DEBUG:
        return JsonResponse({'error': 'Only available in debug mode'}, status=403)
    
    progress = get_user_progress(request.user, level_name)
    progress.certificate_issued = False
    progress.certificate_issued_at = None
    progress.save()
    
    # Optionally delete certificate image
    certificate = UserCertificate.objects.filter(user=request.user, level=level_name).first()
    if certificate:
        certificate.certificate_image = None
        certificate.save()
    
    return JsonResponse({'success': True, 'message': 'Assessment status reset for testing'})