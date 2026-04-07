from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from datetime import date

class UserLearningProgress(models.Model):
    LEVEL_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='learning_progress')
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES)
    completed_days = models.JSONField(default=list)  # List of completed day numbers
    current_day = models.IntegerField(default=1, validators=[MinValueValidator(1), MaxValueValidator(30)])
    streak_days = models.IntegerField(default=0)
    last_completed_date = models.DateField(null=True, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Certificate related
    certificate_issued = models.BooleanField(default=False)
    certificate_issued_at = models.DateTimeField(null=True, blank=True)
    
    # 👇 ADD THIS NEW FIELD
    has_seen_intro = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['user', 'level']
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.level} - Day {self.current_day}"
    
    def completion_percentage(self):
        return (len(self.completed_days) / 30) * 100
    
    def is_completed(self):
        return len(self.completed_days) >= 30
    
    def get_next_day(self):
        """Get next uncompleted day number"""
        for day in range(1, 31):
            if day not in self.completed_days:
                return day
        return None
    
    def can_access_day(self, day_number):
        """Check if user can access a specific day"""
        # Day 1 is always accessible
        if day_number == 1:
            return True
        # Can only access if previous day is completed
        return (day_number - 1) in self.completed_days
    
    def complete_day(self, day_number):
        """Mark a day as complete and update progress"""
        if day_number not in self.completed_days:
            self.completed_days.append(day_number)
            self.completed_days.sort()
            
            # Update current day to next uncompleted day
            next_day = self.get_next_day()
            if next_day:
                self.current_day = next_day
            
            # Update streak
            today = date.today()
            if self.last_completed_date:
                days_diff = (today - self.last_completed_date).days
                if days_diff == 1:
                    self.streak_days += 1
                elif days_diff > 1:
                    self.streak_days = 1
            else:
                self.streak_days = 1
            
            self.last_completed_date = today
            
            # Check if all days completed
            if self.is_completed() and not self.completed_at:
                self.completed_at = timezone.now()
            
            self.save()
            return True
        return False


class DailyActivity(models.Model):
    """Track detailed activity completion per day"""
    ACTIVITY_TYPES = [
        ('listening', 'Listening'),
        ('speaking', 'Speaking'),
        ('reading', 'Reading'),
        ('writing', 'Writing'),
        ('vocabulary', 'Vocabulary'),
        ('grammar', 'Grammar'),
        ('game', 'Game'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    level = models.CharField(max_length=20)
    day_number = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(30)])
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # For storing recordings or responses
    recording_url = models.URLField(null=True, blank=True)
    response_data = models.JSONField(null=True, blank=True)
    
    class Meta:
        unique_together = ['user', 'level', 'day_number', 'activity_type']
        ordering = ['day_number', 'activity_type']


class SavedVocabulary(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_vocabulary')
    word = models.CharField(max_length=100)
    saved_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'word']
        ordering = ['-saved_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.word}"


class UserCertificate(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='certificates')
    level = models.CharField(max_length=20, choices=UserLearningProgress.LEVEL_CHOICES)
    certificate_code = models.CharField(max_length=100, unique=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    downloaded = models.BooleanField(default=False)
    shared = models.BooleanField(default=False)
    
    # PNG certificate storage
    certificate_image = models.BinaryField(null=True, blank=True)
    download_count = models.IntegerField(default=0)
    share_count = models.IntegerField(default=0)
    
    class Meta:
        unique_together = ['user', 'level']
    
    def __str__(self):
        return f"Certificate for {self.user.username} - {self.level}"