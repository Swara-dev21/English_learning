# speaking/models.py
from django.db import models
from django.contrib.auth.models import User

class Recording(models.Model):
    student_name = models.CharField(max_length=100, default="Student")
    audio_file = models.FileField(upload_to='speaking/recordings/')
    text_to_read = models.TextField()
    score = models.FloatField(null=True, blank=True)
    mispronounced_words = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student_name} - {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}"

class SpeakingResult(models.Model):
    """Store complete speaking test results"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=100, blank=True)
    overall_score = models.FloatField(default=0)
    avg_pronunciation = models.FloatField(default=0)
    avg_accent = models.FloatField(default=0)
    avg_accuracy = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    level = models.CharField(max_length=20, blank=True, null=True)
    
    def __str__(self):
        user_display = self.user.username if self.user else 'Anonymous'
        return f"{user_display} - Score: {self.overall_score}%"