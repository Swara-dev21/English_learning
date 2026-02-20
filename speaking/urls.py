from django.urls import path
from speaking import views

app_name = "speaking"

urlpatterns = [
    path("start/", views.start, name="start"),
    path("question/<int:q_index>/", views.question, name="question"),
    path("record/<int:q_index>/", views.record_question, name="record_question"),
    path("result/", views.result_final, name="result"),

]