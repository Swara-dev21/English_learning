from django.shortcuts import render

def home(request):
    """Render the main homepage"""
    return render(request, 'home_page/home.html')

def login(request):
    """Login page (placeholder)"""
    return render(request, 'home_page/login.html')

def register(request):
    """Register page (placeholder)"""
    return render(request, 'home_page/register.html')