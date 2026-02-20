# home_page/context_processors.py
from .models import StudentProfile

def user_profile_context(request):
    """Add user profile and pretest status to template context"""
    context = {
        'user_logged_in': request.user.is_authenticated,
        'pretest_completed': False,
        'user_profile': None,
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
    
    return context
