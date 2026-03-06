from django.urls import path
from . import views

app_name = 'reading'

urlpatterns = [
    path('', views.index, name='index'),
    # Specific patterns first (with extra path segments)
    path('test/<int:test_id>/start/', views.start_test, name='start_test'),
    path('test/<int:test_id>/submit/', views.submit_test, name='submit_test'),
    path('test/<int:test_id>/navigate/', views.navigate_question, name='navigate_question'),
    path('test/<int:test_id>/submit-answer/', views.submit_answer, name='submit_answer'),
    path('test/<int:test_id>/retry/', views.retry_test, name='retry_test'),
    # Generic pattern last (catches everything else)
    path('test/<int:test_id>/', views.test_page, name='test_page'),
    
    path('results/<int:result_id>/', views.reading_results, name='results'),
    path('log-activity/', views.log_suspicious_activity, name='log_activity'),
    path('latest-result/', views.latest_result, name='latest_result'),
]