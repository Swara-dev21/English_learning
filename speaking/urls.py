# speaking/urls.py
from django.urls import path
from . import views

app_name = 'speaking'

urlpatterns = [
    path('', views.start, name='start'),
    path('initialize-test/', views.initialize_test, name='initialize_test'),
    path('question/<int:q_num>/', views.question, name='question'),
    path('submit-recording/', views.submit_recording, name='submit_recording'),
    path('process-results/', views.process_results, name='process_results'),
    path('result/', views.result, name='result'),
    path('error/', views.error_page, name='error_page'),
]