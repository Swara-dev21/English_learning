# home_page/views.py
import csv
from django.http import HttpResponse
from django.contrib.admin.views.decorators import staff_member_required
from listening.models import TestResult as ListeningResult
from reading.models import ReadingResult
from speaking.models import SpeakingResult
from writing.models import WritingTestResult as WritingResult


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login as auth_login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.core.mail import send_mail
from django.urls import reverse
from django.conf import settings
from .forms import (
    StudentLoginForm, RegisterForm, ProfileUpdateForm, 
    PasswordChangeForm, PasswordResetRequestForm, PasswordResetConfirmForm
)
from .models import StudentProfile, PasswordResetToken
from django.contrib.auth.models import User


def student_login(request):
    """Student login view with next redirect support"""
    next_url = request.GET.get('next')

    if request.method == 'POST':
        form = StudentLoginForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data['user']
            auth_login(request, user)
            messages.success(request, f"Welcome {user.username}, you are now logged in!")
            return redirect(next_url or 'home_page:home')
        else:
            messages.error(request, "Please fix the errors below")
    else:
        form = StudentLoginForm()

    return render(request, 'home_page/login.html', {'form': form, 'next': next_url})


def home(request):
    """Home page view"""
    return render(request, 'home_page/home.html')


def register(request):
    """User registration view"""
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            email = form.cleaned_data['email']
            institute = form.cleaned_data['institute']
            department = form.cleaned_data['department']
            year = form.cleaned_data['year']
            password = form.cleaned_data['password']

            # Check if username already exists
            if User.objects.filter(username=username).exists():
                form.add_error('username', 'Username already exists.')
            else:
                # Create user
                user = User.objects.create_user(
                    username=username, 
                    email=email, 
                    password=password
                )
                
                # Create profile - use get_or_create to avoid duplicates
                profile, created = StudentProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        'institute': institute,
                        'department': department,
                        'year': year,
                        'listening_completed': False,
                        'reading_completed': False,
                        'speaking_completed': False,
                        'writing_completed': False,
                        'pretest_completed': False,
                    }
                )
                
                if not created:
                    # Update existing profile
                    profile.institute = institute
                    profile.department = department
                    profile.year = year
                    profile.save()

                messages.success(request, f"Hello {username}, registration successful! You can now take the pretest.")
                return redirect('home_page:login')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = RegisterForm()

    return render(request, 'home_page/register.html', {'form': form})


def logout_view(request):
    """Custom logout view"""
    logout(request)
    messages.success(request, "You have been successfully logged out.")
    return redirect('home_page:home')


@login_required
def profile_view(request):
    print("\n" + "="*50)
    print("PROFILE VIEW CALLED")
    print(f"Request method: {request.method}")
    print(f"POST data: {request.POST}")
    print("="*50 + "\n")
    
    profile = get_object_or_404(StudentProfile, user=request.user)

    if request.method == 'POST':
        print(f"update_profile in POST: {'update_profile' in request.POST}")
        print(f"change_password in POST: {'change_password' in request.POST}")
        
        if 'update_profile' in request.POST:
            print("PROFILE UPDATE FORM SUBMITTED")
            form = ProfileUpdateForm(request.POST, instance=profile)
            print(f"Form valid: {form.is_valid()}")
            if not form.is_valid():
                print(f"Form errors: {form.errors}")
            
            if form.is_valid():
                form.save()
                messages.success(request, "Your profile has been updated successfully!")
                return redirect('home_page:profile')
            # If invalid, continue to render with errors
        
        elif 'change_password' in request.POST:
            print("PASSWORD CHANGE FORM SUBMITTED")
            password_form = PasswordChangeForm(request.user, request.POST)
            print(f"Form valid: {password_form.is_valid()}")
            if not password_form.is_valid():
                print(f"Password errors: {password_form.errors}")
            
            if password_form.is_valid():
                user = request.user
                new_password = password_form.cleaned_data['new_password']
                user.set_password(new_password)
                user.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Your password has been changed successfully!")
                return redirect('home_page:profile')
            # If invalid, continue to render with errors
    
    # For GET requests or invalid POST, initialize both forms
    form = ProfileUpdateForm(instance=profile)
    password_form = PasswordChangeForm(request.user)

    return render(request, 'home_page/profile.html', {
        'form': form,
        'password_form': password_form,
        'profile': profile,
    })

    
@login_required
def test_introduction(request):
    """Show test introduction page before starting the pretest"""
    profile = get_object_or_404(StudentProfile, user=request.user)
    
    # If user already completed the test, redirect to results
    if profile.pretest_completed:
        messages.info(request, "You've already completed the pretest. View your results below.")
        return redirect('home_page:pretest_results')
    
    return render(request, 'home_page/test_introduction.html')


@login_required
def start_pretest(request):
    """Redirect to the first incomplete test"""
    profile = get_object_or_404(StudentProfile, user=request.user)
    
    if profile.pretest_completed:
        messages.info(request, "You've already completed the pretest. View your results below.")
        return redirect('home_page:pretest_results')
    
    # CORRECT ORDER: Listening → Speaking → Reading → Writing
    if not profile.listening_completed:
        return redirect('listening:index')
    elif not profile.speaking_completed:      # Speaking SECOND
        return redirect('speaking:start')
    elif not profile.reading_completed:       # Reading THIRD
        return redirect('reading:index')
    elif not profile.writing_completed:        # Writing LAST
        # Get the first active writing test
        from writing.models import WritingTest
        writing_test = WritingTest.objects.filter(is_active=True).first()
        if writing_test:
            return redirect('writing:writing_test_home', test_id=writing_test.id)
        else:
            messages.error(request, "No writing test available.")
            return redirect('home_page:home')
    else:
        # All tests completed but pretest_completed flag not set
        profile.pretest_completed = True
        profile.pretest_completed_at = timezone.now()
        profile.save()
        return redirect('home_page:pretest_results')


@login_required
def continue_pretest(request):
    """Redirect to the next incomplete test - same as start_pretest"""
    return start_pretest(request)


@login_required
def pretest_results(request):
    """Show combined pretest results"""
    from listening.models import TestResult as ListeningResult
    from reading.models import ReadingResult
    from speaking.models import SpeakingResult
    from writing.models import WritingTestResult as WritingResult
    
    profile = get_object_or_404(StudentProfile, user=request.user)
    
    if not profile.pretest_completed:
        if all([profile.listening_completed, profile.reading_completed, 
                profile.speaking_completed, profile.writing_completed]):
            profile.pretest_completed = True
            profile.pretest_completed_at = timezone.now()
            profile.save()
        else:
            messages.warning(request, "Please complete all pretest sections first.")
            return redirect('home_page:start_pretest')
    
    # Get latest results
    listening_result = ListeningResult.objects.filter(user=request.user).first()
    reading_result = ReadingResult.objects.filter(user=request.user).first()
    speaking_result = SpeakingResult.objects.filter(user=request.user).first()
    writing_result = WritingResult.objects.filter(user=request.user).first()


    completion_date = None
    if writing_result:
        completion_date = writing_result.created_at
    elif profile.pretest_completed_at:
        completion_date = profile.pretest_completed_at
    
    # Calculate percentages for each section
    # Listening: Convert 3/5 to 60%
    if listening_result:
        listening_result.percentage = (listening_result.score / listening_result.total_questions) * 100
    else:
        listening_result = None
    
    # Reading: Already has percentage field but ensure it's calculated
    if reading_result:
        if not hasattr(reading_result, 'percentage') or reading_result.percentage is None:
            reading_result.percentage = (reading_result.score / reading_result.total) * 100
    else:
        reading_result = None
    
    # Speaking: Already has overall_score as percentage
    if speaking_result:
        # Ensure all speaking metrics are floats
        speaking_result.avg_pronunciation = float(speaking_result.avg_pronunciation)
        speaking_result.avg_accent = float(speaking_result.avg_accent)
        speaking_result.avg_accuracy = float(speaking_result.avg_accuracy)
        speaking_result.overall_score = float(speaking_result.overall_score)
    else:
        speaking_result = None
    
    # Writing: Convert 0/5 to 0%
    if writing_result:
        writing_result.percentage = (writing_result.total_score / 5) * 100
    else:
        writing_result = None
    
    # Calculate overall score (weighted average of all sections)
    total_weighted_score = 0
    total_weight = 0
    
    # Listening (weight: 1)
    if listening_result:
        total_weighted_score += listening_result.percentage
        total_weight += 1
    
    # Reading (weight: 1)
    if reading_result:
        total_weighted_score += reading_result.percentage
        total_weight += 1
    
    # Speaking (weight: 1)
    if speaking_result:
        total_weighted_score += speaking_result.overall_score
        total_weight += 1
    
    # Writing (weight: 1)
    if writing_result:
        total_weighted_score += writing_result.percentage
        total_weight += 1
    
    # Calculate overall percentage (average of all sections)
    if total_weight > 0:
        overall_percentage = total_weighted_score / total_weight
    else:
        overall_percentage = 0
    
    # Also keep the original overall_score if needed (sum of raw scores)
    total_raw_score = 0
    if listening_result:
        total_raw_score += listening_result.score
    if reading_result:
        total_raw_score += reading_result.score
    if speaking_result:
        total_raw_score += speaking_result.overall_score / 20  # Convert percentage to /5 scale
    if writing_result:
        total_raw_score += writing_result.total_score
    
    overall_raw_score = round(total_raw_score, 1)
    
    context = {
        'profile': profile,
        'listening_result': listening_result,
        'reading_result': reading_result,
        'speaking_result': speaking_result,
        'writing_result': writing_result,
        'overall_score': overall_raw_score,  # Keep original for backward compatibility
        'overall_percentage': round(overall_percentage, 1),  # New overall percentage
        'listening_percentage': listening_result.percentage if listening_result else 0,
        'reading_percentage': reading_result.percentage if reading_result else 0,
        'speaking_percentage': speaking_result.overall_score if speaking_result else 0,
        'writing_percentage': writing_result.percentage if writing_result else 0,
        'completion_date': completion_date, 
    }
    
    return render(request, 'home_page/pretest_results.html', context)


<<<<<<< HEAD

=======
>>>>>>> 376fed1df717dc0e57a1511600a231bcfa8b3e2d
def password_reset_request(request):
    """View for requesting password reset"""
    
    # Check if user just came back to this page after requesting a reset
    show_already_sent_message = request.session.pop('reset_email_sent', False)
    
    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            user = User.objects.get(email=email)
            
            # Generate reset token
            reset_token = PasswordResetToken.generate_token(user)
            
            # Build reset link
            reset_link = request.build_absolute_uri(
                reverse('home_page:password_reset_confirm', args=[reset_token.token])
            )
            
            # Send email (for development, print to console)
            try:
                send_mail(
                    subject='Password Reset Request',
                    message=f'''Hello {user.username},

You requested a password reset for your Student Portal account.

Click the link below to reset your password:
{reset_link}

This link will expire in 1 hour.

If you didn't request this, please ignore this email.

Thanks,
Student Portal Team''',
                    from_email='noreply@studentportal.com',
                    recipient_list=[email],
                    fail_silently=False,
                )
                # Store in session that email was sent
                request.session['reset_email_sent'] = True
                # Redirect with success message
                return redirect(f"{reverse('home_page:login')}?reset_sent=true")
            except Exception as e:
                # For development: print the link to console
                print(f"\n\nPASSWORD RESET LINK: {reset_link}\n\n")
                request.session['reset_email_sent'] = True
                return redirect(f"{reverse('home_page:login')}?reset_sent=true")
    else:
        form = PasswordResetRequestForm()
    
    return render(request, 'home_page/password_reset_request.html', {
        'form': form,
        'show_already_sent_message': show_already_sent_message
    })


def password_reset_confirm(request, token):
    """View for confirming password reset with token"""
    # Get valid token
    reset_token = get_object_or_404(PasswordResetToken, token=token, is_used=False)
    
    # Check if token expired
    if reset_token.expires_at < timezone.now():
        return redirect(f"{reverse('home_page:password_reset_request')}?expired=true")
    
    if request.method == 'POST':
        form = PasswordResetConfirmForm(request.POST)
        if form.is_valid():
            # Update password
            new_password = form.cleaned_data['new_password']
            user = reset_token.user
            user.set_password(new_password)
            user.save()
            
            # Mark token as used
            reset_token.is_used = True
            reset_token.save()
            
            # Redirect to login with success message
            return redirect(f"{reverse('home_page:login')}?reset_success=true")
    else:
        form = PasswordResetConfirmForm()
    
    return render(request, 'home_page/password_reset_confirm.html', {
        'form': form,
        'token': token,
        'email': reset_token.user.email
    })

@staff_member_required
def export_all_results_csv(request):
    """Export all student results in CSV format for analysis - Clean version"""
    
    # Create HttpResponse with CSV header
    response = HttpResponse(
        content_type='text/csv',
        headers={'Content-Disposition': 'attachment; filename="lsrw_student_results_clean.csv"'},
    )
    
    writer = csv.writer(response)
    
    # Write header row - CLEAN VERSION
    writer.writerow([
        'Student_ID',
        'Student_Name',
        'Email',
        'Institute',
        'Department',
        'Year',
        'Listening_%',
        'Speaking_%',
        'Reading_%',
        'Writing_%',
        'Overall_%',
        'Overall_Level'
    ])
    
    # Get all users who have a profile
    users = User.objects.filter(profile__isnull=False).select_related('profile')
    
    for user in users:
        profile = user.profile
        
        # ----- LISTENING -----
        listening = ListeningResult.objects.filter(user=user).first()
        if listening and listening.score is not None:
            listening_percentage = round((listening.score / listening.total_questions * 100), 1)
        else:
            listening_percentage = 0
        
        # ----- READING -----
        reading = ReadingResult.objects.filter(user=user).first()
        if reading and reading.score is not None:
            reading_percentage = round((reading.score / reading.total * 100), 1)
        else:
            reading_percentage = 0
        
        # ----- SPEAKING (Average of pronunciation, accent, accuracy) -----
        speaking = SpeakingResult.objects.filter(user=user).first()
        if speaking:
            # Speaking already has overall_score which is average of all three
            speaking_percentage = round(speaking.overall_score, 1)
        else:
            speaking_percentage = 0
        
        # ----- WRITING (Convert 0-500 to percentage) -----
        writing = WritingResult.objects.filter(user=user).first()
        if writing and writing.total_score is not None:
            writing_percentage = round((writing.total_score / 500 * 100), 1)
        else:
            writing_percentage = 0
        
        # Calculate overall percentage (average of all 4 skills)
        valid_scores = []
        if listening_percentage > 0: valid_scores.append(listening_percentage)
        if speaking_percentage > 0: valid_scores.append(speaking_percentage)
        if reading_percentage > 0: valid_scores.append(reading_percentage)
        if writing_percentage > 0: valid_scores.append(writing_percentage)
        
        if valid_scores:
            overall_percentage = round(sum(valid_scores) / len(valid_scores), 1)
        else:
            overall_percentage = 0
        
        # Determine overall level
        if overall_percentage < 40:
            overall_level = 'Beginner'
        elif overall_percentage < 75:
            overall_level = 'Intermediate'
        else:
            overall_level = 'Advanced'
        
        # Write row - CLEAN VERSION
        writer.writerow([
            user.id,
            user.username,
            user.email,
            profile.institute,
            profile.department,
            profile.year,
            f"{listening_percentage}%",
            f"{speaking_percentage}%",
            f"{reading_percentage}%",
            f"{writing_percentage}%",
            f"{overall_percentage}%",
            overall_level
        ])
    
    return response