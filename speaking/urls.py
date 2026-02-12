from django.urls import path
from speaking import views

urlpatterns = [
    path("start/", views.start, name="start_speaking_test"),
    path("question/<int:q_index>/", views.question, name="question"),
    path("record/<int:q_index>/", views.record_question, name="record_question"),
    path("result/", views.result_final, name="result_final"),

]