# learning/urls.py
from django.urls import path
from . import views

app_name = 'learning'

urlpatterns = [
    # Level selection and overview
    path('level-selection/', views.level_selection, name='level_selection'),
    path('level/<str:level_name>/', views.level_overview, name='level_overview'),
     path('level/<str:level_name>/mark-intro-seen/', views.mark_intro_seen, name='mark_intro_seen'),
    
    # Daily lesson paths
    path('level/<str:level_name>/day/<int:day_number>/', views.day_detail, name='day_detail'),
    path('level/<str:level_name>/day/<int:day_number>/complete/<str:activity_type>/', views.complete_activity, name='complete_activity'),
    path('level/<str:level_name>/day/<int:day_number>/complete/', views.complete_day, name='complete_day'),
    path('level/<str:level_name>/day/<int:day_number>/collect-reward/', views.collect_reward, name='collect_reward'),

    # Add this with your other paths
     path('ai/evaluate/', views.ai_evaluate, name='ai_evaluate'),
    
    # ==================== ASSESSMENT URLs ====================
    # Main assessment endpoint (handles both GET and POST)
    path('level/<str:level_name>/final-test/', views.take_final_test, name='final_test'),
    
    # Alternative assessment endpoint (if you want to separate render and submit)
    path('level/<str:level_name>/take-test/', views.take_final_test, name='take_test'),
    
    # Test results
    path('level/<str:level_name>/result/', views.test_result, name='test_result'),
    
    # Certificate URLs
    path('level/<str:level_name>/certificate/', views.certificate_view, name='certificate'),
    path('level/<str:level_name>/certificate/generate/', views.generate_certificate_png, name='generate_certificate_png'),
    path('level/<str:level_name>/certificate/pdf/', views.generate_certificate_pdf, name='generate_certificate_pdf'),
    path('level/<str:level_name>/certificate/view/', views.view_certificate_png, name='view_certificate_png'),
    path('level/<str:level_name>/certificate/status/', views.certificate_status_api, name='certificate_status_api'),
    path('level/<str:level_name>/certificate/track-download/', views.track_certificate_download, name='track_certificate_download'),
    path('level/<str:level_name>/certificate/track-share/', views.track_certificate_share, name='track_certificate_share'),
    
    # Reset assessment (testing only)
    path('level/<str:level_name>/reset-test/', views.reset_test_status, name='reset_test_status'),
    
    # Legacy certificate endpoints
    path('certificate/<int:certificate_id>/downloaded/', views.mark_certificate_downloaded, name='certificate_downloaded'),
    path('certificate/<int:certificate_id>/shared/', views.mark_certificate_shared, name='certificate_shared'),

    # ==================== API ENDPOINTS ====================
    # Progress tracking
    path('api/progress/<str:level_name>/', views.get_progress_api, name='api_progress'),
    path('api/check-day/<str:level_name>/<int:day_number>/', views.check_day_completion, name='check_day_completion'),
    

    
    # Vocabulary
    path('api/save-vocabulary/', views.save_vocabulary, name='save_vocabulary'),
    

]