# home_page/middleware.py
from django.shortcuts import redirect
from django.urls import reverse  # ← ADD THIS IMPORT
from django.utils import timezone
from datetime import datetime
import json

class GlobalTimerMiddleware:
    """
    Middleware to enforce 20-minute global timer across all tests
    """
    def __init__(self, get_response):
        self.get_response = get_response
        # URLs that should bypass timer check
        self.bypass_urls = [
            '/login/', 
            '/register/', 
            '/pretest-results/',  # Allow results page
            '/admin/',
            '/logout/',
            '/profile/',
            '/static/',
            '/media/',
        ]

    def __call__(self, request):
        # Check if user is in active test session
        if 'test_start_time' in request.session:
            try:
                start_time = datetime.fromisoformat(request.session['test_start_time'])
                elapsed = (timezone.now() - start_time).total_seconds()
                
                # If more than 20 minutes have passed (1200 seconds)
                if elapsed > 1800:
                    # Clear test session
                    if 'test_start_time' in request.session:
                        del request.session['test_start_time']
                    
                    # Redirect to results with timeout flag (except for bypass URLs)
                    path = request.path
                    if not any(path.startswith(url) for url in self.bypass_urls):
                        # FIXED: Now reverse is imported
                        return redirect(f"{reverse('home_page:pretest_results')}?timeout=true")
            except (ValueError, KeyError):
                # If there's an error parsing the time, clear the session
                if 'test_start_time' in request.session:
                    del request.session['test_start_time']
        
        response = self.get_response(request)
        return response