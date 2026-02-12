from django.db import models
from django.contrib.auth.models import User


class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    institute = models.CharField(max_length=200)
    department = models.CharField(max_length=200)
    year = models.CharField(max_length=50)

    def __str__(self):
        return self.user.username
