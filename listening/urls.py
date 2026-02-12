from django.urls import path
from . import views

app_name = 'listening'

urlpatterns = [
     path('', views.test_home, name='test_home'),
    path('test/<int:test_id>/', views.start_test, name='start_test'),
    path('test/<int:test_id>/question/<int:question_number>/', 
         views.test_question, name='test_question'),
    path('test/<int:test_id>/question/<int:question_number>/submit/', 
         views.submit_answer, name='submit_answer'),
    path('test/<int:test_id>/submit/', views.submit_test, name='submit_test'),
    path('results/<int:result_id>/', views.test_results, name='test_results'),
]