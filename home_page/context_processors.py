# home_page/context_processors.py
from .models import StudentProfile
from django.utils import timezone
from datetime import datetime

def user_profile_context(request):
    """Add user profile, pretest status, and display name to template context"""
    context = {
        'user_logged_in': request.user.is_authenticated,
        'pretest_completed': False,
        'user_profile': None,
        'display_name': '',  # Add display_name to context
    }
    
    if request.user.is_authenticated:
        try:
            profile = StudentProfile.objects.get(user=request.user)
            context['user_profile'] = profile
            context['pretest_completed'] = profile.pretest_completed
        except StudentProfile.DoesNotExist:
            # Create profile if it doesn't exist (shouldn't happen with signals)
            profile = StudentProfile.objects.create(user=request.user)
            context['user_profile'] = profile
            context['pretest_completed'] = False
        
        # Add display_name logic here
        username = request.user.username
        if username and ' ' in username:
            # Take first name if there's a space
            context['display_name'] = username.split()[0]
        else:
            # Use full username if no space
            context['display_name'] = username
    
    return context


def global_timer(request):
    """
    Context processor to add global timer to all templates
    """
    timer_data = {
        'timer_active': False,
        'time_remaining': 1800,  # 20 minutes in seconds
        'minutes': 30,
        'seconds': 0,
        'percentage': 100,
        'is_expired': False,
        'formatted_time': '30:00'
    }
    
    if request.user.is_authenticated and 'test_start_time' in request.session:
        try:
            start_time = datetime.fromisoformat(request.session['test_start_time'])
            elapsed = (timezone.now() - start_time).total_seconds()
            remaining = max(0, 1800 - int(elapsed))
            percentage = (remaining / 1800) * 100
            
            # Format as MM:SS
            minutes = remaining // 60
            seconds = remaining % 60
            formatted = f"{minutes:02d}:{seconds:02d}"
            
            timer_data.update({
                'timer_active': True,
                'time_remaining': remaining,
                'minutes': minutes,
                'seconds': seconds,
                'percentage': percentage,
                'is_expired': remaining <= 0,
                'formatted_time': formatted
            })
        except (ValueError, KeyError):
            # If there's an error parsing the time, clear the session
            if 'test_start_time' in request.session:
                del request.session['test_start_time']
    
    return {'global_timer': timer_data}