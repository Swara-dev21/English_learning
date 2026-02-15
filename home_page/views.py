from django.shortcuts import render, redirect ,get_object_or_404
from django.contrib.auth import login as auth_login
from django.contrib import messages
from .forms import StudentLoginForm, RegisterForm
from .models import StudentProfile
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.urls import reverse
from django.conf import settings
from django.utils import timezone
from .forms import StudentLoginForm, RegisterForm, PasswordResetRequestForm, PasswordResetConfirmForm
from .models import StudentProfile, PasswordResetToken


def student_login(request):
    """Student login view with next redirect support"""
    next_url = request.GET.get('next')  # Get the next URL if present

    if request.method == 'POST':
        form = StudentLoginForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data['user']
            auth_login(request, user)  # Log in the user
            messages.success(request, f"Welcome {user.username}, you are now logged in!")
            # Redirect to next URL if present, otherwise to home
            return redirect(next_url or 'home_page:home')
        else:
            messages.error(request, "Please fix the errors below")
    else:
        form = StudentLoginForm()

    return render(request, 'home_page/login.html', {'form': form, 'next': next_url})

def home(request):
    return render(request, 'home_page/home.html')

def register(request):
    form = RegisterForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            username = form.cleaned_data['username']
            email = form.cleaned_data['email']
            institute = form.cleaned_data['institute']
            department = form.cleaned_data['department']
            year = form.cleaned_data['year']
            password = form.cleaned_data['password']

            if User.objects.filter(username=username).exists():
                form.add_error('username', 'Username already exists.')
            else:
                user = User.objects.create_user(username=username, email=email, password=password)
                StudentProfile.objects.create(user=user, institute=institute, department=department, year=year)
                messages.success(request, f"Hello {username}, registration successful!")
                return redirect('home_page:home')
        else:
            # Only add one general error at top
            messages.error(request, "Please correct the errors below.")

    return render(request, 'home_page/register.html', {'form': form})

def password_reset_request(request):
    """View for requesting password reset"""
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
                # Redirect with success message
                return redirect(f"{reverse('home_page:login')}?reset_sent=true")
            except Exception as e:
                # For development: print the link to console
                print(f"\n\nPASSWORD RESET LINK: {reset_link}\n\n")
                return redirect(f"{reverse('home_page:login')}?reset_sent=true")
    else:
        form = PasswordResetRequestForm()
    
    return render(request, 'home_page/password_reset_request.html', {'form': form})

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