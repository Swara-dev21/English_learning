from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('test/<int:test_id>/', views.test_page, name='test_page'),
    path('test/<int:test_id>/submit/', views.submit_test, name='submit_test'),
]