from django.urls import path
from django.shortcuts import redirect
from . import views

app_name = 'writing'

urlpatterns = [
    # Redirect root to first test or admin will create tests
    path('', lambda request: redirect('admin:index'), name='home'),
    
    # Start writing test directly
    path('start/<int:test_id>/', views.start_writing_test, name='start_writing_test'),
    
    # Writing Test Pages
    path('test/<int:test_id>/', views.writing_test_home, name='writing_test_home'),
    path('test/<int:test_id>/question/<int:question_number>/', 
         views.writing_question, name='writing_question'),
    path('test/<int:test_id>/question/<int:question_number>/save/', 
         views.save_answer, name='save_answer'),
    path('test/<int:test_id>/submit/', 
         views.submit_writing_test, name='submit_writing_test'),
    
    # Results
    path('results/<int:result_id>/', 
         views.writing_results, name='writing_results'),
]