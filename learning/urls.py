from django.urls import path
from . import views

app_name = 'learning'

urlpatterns = [
    # Level selection and overview
    path('level-selection/', views.level_selection, name='level_selection'),
    path('level/<str:level_name>/', views.level_overview, name='level_overview'),
    
    # Daily lesson paths
    path('level/<str:level_name>/day/<int:day_number>/', views.day_detail, name='day_detail'),
    path('level/<str:level_name>/day/<int:day_number>/complete/<str:activity_type>/', 
         views.complete_activity, name='complete_activity'),
    path('level/<str:level_name>/day/<int:day_number>/complete/', 
         views.complete_day, name='complete_day'),
    
    # Final test and certificate
    path('level/<str:level_name>/final-test/', views.take_final_test, name='final_test'),
    path('level/<str:level_name>/take-test/', views.render_test_page, name='take_test'),  # ✅ ADD THIS
    path('level/<str:level_name>/result/', views.test_result, name='test_result'),
    path('level/<str:level_name>/certificate/', views.certificate_view, name='certificate'),
    
    # Certificate PNG generation endpoints
    path('level/<str:level_name>/certificate/generate/', views.generate_certificate_png, name='generate_certificate_png'),
    path('level/<str:level_name>/certificate/view/', views.view_certificate_png, name='view_certificate_png'),
    path('level/<str:level_name>/certificate/status/', views.certificate_status_api, name='certificate_status_api'),
    path('level/<str:level_name>/certificate/track-download/', views.track_certificate_download, name='track_certificate_download'),
    path('level/<str:level_name>/certificate/track-share/', views.track_certificate_share, name='track_certificate_share'),
    
    # Legacy endpoints
    path('certificate/<int:certificate_id>/downloaded/', views.mark_certificate_downloaded, name='certificate_downloaded'),
    path('certificate/<int:certificate_id>/shared/', views.mark_certificate_shared, name='certificate_shared'),

    # API endpoints
    path('api/progress/<str:level_name>/', views.get_progress_api, name='api_progress'),
]