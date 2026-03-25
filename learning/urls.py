from django.urls import path
from . import views

app_name = 'learning'

urlpatterns = [
    path('level-selection/', views.level_selection, name='level_selection'),
    path('beginner/', views.beginner_instructions, name='beginner_instructions'),
    path('beginner/levels/', views.beginner_levels, name='beginner_levels'),
    path('beginner/day/<int:day_number>/', views.beginner_day, name='beginner_day'),
    path('beginner/day/<int:day_number>/submit/', views.submit_quiz, name='submit_quiz'),
    path('beginner/day/<int:day_number>/result/', views.quiz_result, name='quiz_result'),
    path('beginner/day1/', views.beginner_day1, name='beginner_day1'),
    path('intermediate/', views.intermediate_instructions, name='intermediate_instructions'),
    path('intermediate/day1/', views.intermediate_day1, name='intermediate_day1'),
    path('advanced/', views.advanced_instructions, name='advanced_instructions'),
    path('advanced/day1/', views.advanced_day1, name='advanced_day1'),
]