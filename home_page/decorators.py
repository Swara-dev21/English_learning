# home_page/decorators.py
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse
from .models import StudentProfile

def pretest_completed_redirect(view_func):
    """
    Decorator to check if user has completed the entire pretest.
    If completed, redirect to pretest results page.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated:
            try:
                profile = StudentProfile.objects.get(user=request.user)
                if profile.pretest_completed:
                    messages.info(request, "You have already completed the pretest. View your results below.")
                    return redirect('home_page:pretest_results')
            except StudentProfile.DoesNotExist:
                # Create profile if it doesn't exist
                profile = StudentProfile.objects.create(user=request.user)
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def test_completed_redirect(test_name):
    """
    Decorator factory to check if a specific test is completed.
    Usage: @test_completed_redirect('listening')
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.user.is_authenticated:
                try:
                    profile = StudentProfile.objects.get(user=request.user)
                    test_completed = getattr(profile, f'{test_name}_completed', False)
                    
                    if test_completed:
                        messages.warning(
                            request, 
                            f"You have already completed the {test_name} test."
                        )
                        return redirect('home_page:pretest_status')
                except StudentProfile.DoesNotExist:
                    # Create profile if it doesn't exist
                    profile = StudentProfile.objects.create(user=request.user)
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def require_test_order(test_name):
    """
    Decorator factory to enforce test order.
    Enforces: Listening → Speaking → Reading → Writing
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.user.is_authenticated:
                try:
                    profile = StudentProfile.objects.get(user=request.user)
                    
                    # CORRECTED TEST ORDER
                    test_order = [
                        {'name': 'listening', 'url': 'listening:test_home'},
                        {'name': 'speaking', 'url': 'speaking:start'},      # Speaking SECOND
                        {'name': 'reading', 'url': 'reading:index'},        # Reading THIRD
                        {'name': 'writing', 'url': 'writing:writing_test_home'}
                    ]
                    
                    # Find current test index
                    current_index = None
                    for i, test in enumerate(test_order):
                        if test['name'] == test_name:
                            current_index = i
                            break
                    
                    if current_index is None:
                        return view_func(request, *args, **kwargs)
                    
                    # Check if all previous tests are completed
                    for i in range(current_index):
                        prev_test = test_order[i]
                        if not getattr(profile, f'{prev_test["name"]}_completed', False):
                            messages.warning(
                                request,
                                f"Please complete the {prev_test['name']} test first."
                            )
                            return redirect(prev_test['url'])
                            
                except StudentProfile.DoesNotExist:
                    profile = StudentProfile.objects.create(user=request.user)
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator



def pretest_access_required(test_name=None):
    """
    Combined decorator for complete pretest access control.
    Enforces: Listening → Speaking → Reading → Writing
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # First, ensure user is authenticated
            if not request.user.is_authenticated:
                return redirect('home_page:login')
            
            try:
                profile = StudentProfile.objects.get(user=request.user)
            except StudentProfile.DoesNotExist:
                profile = StudentProfile.objects.create(user=request.user)
            
            # Check if pretest is already completed
            if profile.pretest_completed:
                messages.info(request, "You have already completed the pretest. View your results below.")
                return redirect('home_page:pretest_results')
            
            # If test_name is provided, do additional checks
            if test_name:
                # Check if this specific test is already completed
                test_completed = getattr(profile, f'{test_name}_completed', False)
                if test_completed:
                    messages.warning(
                        request,
                        f"You have already completed the {test_name} test."
                    )
                    return redirect('home_page:pretest_status')
                
                # CORRECTED TEST ORDER: Listening → Speaking → Reading → Writing
                test_order = [
                    {'name': 'listening', 'url': 'listening:test_home'},
                    {'name': 'speaking', 'url': 'speaking:start'},      # Speaking SECOND
                    {'name': 'reading', 'url': 'reading:index'},        # Reading THIRD
                    {'name': 'writing', 'url': 'writing:writing_test_home'}
                ]
                
                # Find current test index
                current_index = None
                for i, test in enumerate(test_order):
                    if test['name'] == test_name:
                        current_index = i
                        break
                
                if current_index is not None:
                    # Check if all previous tests are completed
                    for i in range(current_index):
                        prev_test = test_order[i]
                        prev_completed = getattr(profile, f'{prev_test["name"]}_completed', False)
                        
                        if not prev_completed:
                            messages.warning(
                                request,
                                f"Please complete the {prev_test['name']} test first."
                            )
                            return redirect(prev_test['url'])
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def ajax_pretest_check(test_name=None):
    """
    Decorator for AJAX views to check pretest status.
    Returns JSON error response if check fails.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return JsonResponse({'error': 'Authentication required'}, status=401)
            
            try:
                profile = StudentProfile.objects.get(user=request.user)
            except StudentProfile.DoesNotExist:
                profile = StudentProfile.objects.create(user=request.user)
            
            # Check pretest completion
            if profile.pretest_completed:
                return JsonResponse({'error': 'Pretest already completed'}, status=403)
            
            # If test_name provided, check specific test
            if test_name:
                test_completed = getattr(profile, f'{test_name}_completed', False)
                if test_completed:
                    return JsonResponse(
                        {'error': f'{test_name.capitalize()} test already completed'}, 
                        status=403
                    )
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator