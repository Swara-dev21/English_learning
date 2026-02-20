from django.urls import path
from . import views

app_name = 'reading'

urlpatterns = [
    path('', views.index, name='index'),
    path('test/<int:test_id>/', views.test_page, name='test_page'),
    path('test/<int:test_id>/submit/', views.submit_test, name='submit_test'),
    path('results/<int:result_id>/', views.reading_results, name='results'), 
]