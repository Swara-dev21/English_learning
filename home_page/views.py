from django.shortcuts import render, redirect
from django.contrib.auth import login as auth_login
from django.contrib import messages
from .forms import StudentLoginForm, RegisterForm
from .models import StudentProfile
from django.contrib.auth.models import User

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
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            email = form.cleaned_data['email']
            institute = form.cleaned_data['institute']
            department = form.cleaned_data['department']
            year = form.cleaned_data['year']
            password = form.cleaned_data['password']

            if User.objects.filter(username=username).exists():
                messages.error(request, "Username already exists.")
                return render(request, 'home_page/register.html', {'form': form})

            user = User.objects.create_user(username=username, email=email, password=password)
            StudentProfile.objects.create(user=user, institute=institute, department=department, year=year)

            messages.success(request, f"Hello {username}, registration successful!")
            return redirect('home_page:home')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = RegisterForm()

    return render(request, 'home_page/register.html', {'form': form})
