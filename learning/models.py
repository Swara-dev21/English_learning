from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class UserProgress(models.Model):
    """Track user progress for different levels"""
    
    LEVEL_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='progress')
    level_type = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='beginner')
    day = models.IntegerField()
    completed = models.BooleanField(default=False)
    score = models.IntegerField(default=0)
    stars = models.IntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['user', 'level_type', 'day']
        ordering = ['day']
    
    def __str__(self):
        return f"{self.user.username} - {self.level_type} Day {self.day} - {'Completed' if self.completed else 'Not Completed'}"

class Lesson(models.Model):
    """Store lesson content for each day"""
    
    LEVEL_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ]
    
    level_type = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='beginner')
    day = models.IntegerField()
    title = models.CharField(max_length=200)
    content = models.TextField()
    learning_objectives = models.TextField(blank=True)
    key_points = models.TextField(blank=True)
    examples = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['level_type', 'day']
        ordering = ['level_type', 'day']
    
    def __str__(self):
        return f"{self.level_type.title()} Day {self.day}: {self.title}"

class ListeningActivity(models.Model):
    """Store listening activities for each day"""
    
    level_type = models.CharField(max_length=20, choices=Lesson.LEVEL_CHOICES, default='beginner')
    day = models.IntegerField()
    sentence = models.TextField()
    meaning = models.TextField(blank=True)
    audio_file = models.FileField(upload_to='audio/listening/', blank=True, null=True)
    test_question = models.TextField()
    test_option_a = models.CharField(max_length=500)
    test_option_b = models.CharField(max_length=500)
    test_option_c = models.CharField(max_length=500)
    correct_answer = models.CharField(max_length=1, choices=[('A', 'A'), ('B', 'B'), ('C', 'C')])
    
    def __str__(self):
        return f"Listening - {self.level_type} Day {self.day}"

class SpeakingActivity(models.Model):
    """Store speaking activities for each day"""
    
    level_type = models.CharField(max_length=20, choices=Lesson.LEVEL_CHOICES, default='beginner')
    day = models.IntegerField()
    sentence = models.TextField()
    slow_audio = models.FileField(upload_to='audio/speaking/slow/', blank=True, null=True)
    normal_audio = models.FileField(upload_to='audio/speaking/normal/', blank=True, null=True)
    sentence_parts = models.TextField(help_text="Comma-separated parts of the sentence")
    test_task = models.TextField()
    
    def __str__(self):
        return f"Speaking - {self.level_type} Day {self.day}"

class ReadingActivity(models.Model):
    """Store reading activities for each day"""
    
    level_type = models.CharField(max_length=20, choices=Lesson.LEVEL_CHOICES, default='beginner')
    day = models.IntegerField()
    paragraph = models.TextField()
    audio_file = models.FileField(upload_to='audio/reading/', blank=True, null=True)
    vocabulary = models.TextField(help_text="Word:Meaning,Word:Meaning format")
    explanation = models.TextField()
    test_question = models.TextField()
    test_option_a = models.CharField(max_length=500)
    test_option_b = models.CharField(max_length=500)
    test_option_c = models.CharField(max_length=500)
    correct_answer = models.CharField(max_length=1, choices=[('A', 'A'), ('B', 'B'), ('C', 'C')])
    
    def __str__(self):
        return f"Reading - {self.level_type} Day {self.day}"

class WritingActivity(models.Model):
    """Store writing activities for each day"""
    
    level_type = models.CharField(max_length=20, choices=Lesson.LEVEL_CHOICES, default='beginner')
    day = models.IntegerField()
    structure = models.TextField()
    suggestions = models.TextField(help_text="Comma-separated suggestions")
    example = models.TextField()
    test_task = models.TextField()
    
    def __str__(self):
        return f"Writing - {self.level_type} Day {self.day}"

class QuizQuestion(models.Model):
    """Store quiz questions for each day"""
    
    LEVEL_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ]
    
    level_type = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='beginner')
    day = models.IntegerField()
    question_text = models.TextField()
    option_a = models.CharField(max_length=500)
    option_b = models.CharField(max_length=500)
    option_c = models.CharField(max_length=500)
    option_d = models.CharField(max_length=500)
    correct_answer = models.CharField(max_length=1, choices=[('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D')])
    explanation = models.TextField(blank=True)
    
    class Meta:
        ordering = ['level_type', 'day', 'id']
    
    def __str__(self):
        return f"{self.level_type} Day {self.day} - Q{self.id}"