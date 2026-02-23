# listening/urls.py
from django.urls import path
from . import views

app_name = 'listening'

urlpatterns = [
    # Main pages
    path('', views.index, name='index'),
    path('test/<int:test_id>/', views.start_test, name='start_test'),
    path('instructions/<int:test_id>/', views.instructions, name='instructions'),
    path('questions/<int:test_id>/', views.questions, name='questions'),
    path('result/<int:result_id>/', views.result, name='result'),
    path('latest-result/', views.latest_result, name='latest_result'),
    
    # AJAX endpoints
    path('update-replay/', views.update_replay, name='update_replay'),
    path('navigate-question/<int:test_id>/', views.navigate_question, name='navigate_question'),
    path('submit-answer/<int:test_id>/', views.submit_answer, name='submit_answer'),
    path('submit-test/<int:test_id>/', views.submit_test, name='submit_test'),
    
    # Legacy URLs (for backward compatibility)
    path('test/<int:test_id>/question/<int:question_number>/', 
         views.test_question, name='test_question'),
    path('results/<int:result_id>/', views.test_results, name='test_results'),
]