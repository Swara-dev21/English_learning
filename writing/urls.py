from django.urls import path
from . import views

app_name = 'writing'  # Make sure this is set

urlpatterns = [
    path('test/<int:test_id>/', views.writing_test_home, name='writing_test_home'),
    path('test/<int:test_id>/start/', views.start_writing_test, name='start_writing_test'),
    path('test/<int:test_id>/question/<int:question_number>/', views.writing_question, name='writing_question'),
    path('test/<int:test_id>/save/<int:question_number>/', views.save_answer, name='save_answer'),
    path('test/<int:test_id>/submit/', views.submit_writing_test, name='submit_writing_test'),
    path('results/<int:result_id>/', views.writing_results, name='writing_results'),
]