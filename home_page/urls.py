from django.urls import path
from . import views

app_name = 'home_page'

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.student_login, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('test-introduction/', views.test_introduction, name='test_introduction'),  # Add this line
    path('start-pretest/', views.start_pretest, name='start_pretest'),
    path('pretest-results/', views.pretest_results, name='pretest_results'),
    path('continue_pretest/', views.continue_pretest, name= 'continue_pretest'),
    path('password-reset/', views.password_reset_request, name='password_reset'),
    path('password-reset/<str:token>/', views.password_reset_confirm, name='password_reset_confirm'),
    path('export-results/', views.export_all_results_csv, name='export_results'),
]