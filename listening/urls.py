# listening/urls.py
from django.urls import path
from . import views

app_name = 'listening'

urlpatterns = [
    # Home
    path('', views.index, name='index'),
    
    # Test preparation
    path('instructions/<int:test_id>/', views.instructions, name='instructions'),
    path('audio/<int:test_id>/', views.audio_passage, name='audio_passage'),
    path('test/<int:test_id>/start/', views.start_test, name='start_test'),
    
    # Questions - main questions page
    path('questions/<int:test_id>/', views.questions, name='questions'),
    
    # Alternative URL for backward compatibility
    path('test/<int:test_id>/question/<int:question_number>/', 
         views.questions, name='test_question'),
    
    # AJAX endpoints
    path('test/<int:test_id>/submit-answer/', views.submit_answer, name='submit_answer'),
    path('test/<int:test_id>/navigate/', views.navigate_question, name='navigate_question'),
    path('update-replay/', views.update_replay, name='update_replay'),
    
    # Test submission
    path('test/<int:test_id>/submit/', views.submit_test, name='submit_test'),
    
    # Results
    path('result/<int:result_id>/', views.result, name='result'),
    path('latest-result/', views.latest_result, name='latest_result'),
]