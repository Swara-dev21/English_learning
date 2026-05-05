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
    collected_rewards = models.JSONField(default=list)  # 👈 ADD THIS NEW FIELD
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

    def claim_reward(self, day_number):
        """Claim a star reward for a completed day (separate from day completion)"""
        if day_number in self.completed_days and day_number not in self.collected_rewards:
            self.collected_rewards.append(day_number)
            self.collected_rewards.sort()
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
    
class LevelAssessment(models.Model):
    """Stores assessment configuration for each level"""
    LEVEL_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ]
    
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, unique=True)
    title = models.CharField(max_length=200, default="Final Assessment")
    description = models.TextField(blank=True, help_text="Instructions for the assessment")
    passing_score = models.IntegerField(default=15, help_text="Minimum score to pass")
    time_limit_minutes = models.IntegerField(default=30, help_text="Time limit in minutes")
    total_questions = models.IntegerField(default=20, help_text="Number of questions")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['level']
        verbose_name = "Level Assessment"
        verbose_name_plural = "Level Assessments"
    
    def __str__(self):
        return f"{self.get_level_display()} Assessment"
    
    def get_questions(self):
        """Get all questions for this assessment"""
        return self.questions.filter(is_active=True).order_by('order')
    
    def get_question_count(self):
        return self.get_questions().count()
    
    def save(self, *args, **kwargs):
        # Auto-update total_questions when saving
        if self.pk:
            self.total_questions = self.get_question_count()
        super().save(*args, **kwargs)


class AssessmentQuestion(models.Model):
    """Individual questions for assessments"""
    assessment = models.ForeignKey(LevelAssessment, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField(help_text="Question text")
    option_a = models.CharField(max_length=500, help_text="Option A")
    option_b = models.CharField(max_length=500, help_text="Option B")
    option_c = models.CharField(max_length=500, blank=True, help_text="Option C (optional)")
    option_d = models.CharField(max_length=500, blank=True, help_text="Option D (optional)")
    correct_answer = models.CharField(
        max_length=1,
        choices=[('a', 'A'), ('b', 'B'), ('c', 'C'), ('d', 'D')],
        help_text="Correct answer letter"
    )
    explanation = models.TextField(blank=True, help_text="Explanation of the correct answer")
    order = models.IntegerField(default=0, help_text="Display order")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'id']
        verbose_name = "Assessment Question"
        verbose_name_plural = "Assessment Questions"
    
    def __str__(self):
        return f"Q{self.order}: {self.text[:50]}..."
    
    def get_options(self):
        """Return list of (letter, text) tuples for non-empty options"""
        options = []
        if self.option_a:
            options.append(('a', self.option_a))
        if self.option_b:
            options.append(('b', self.option_b))
        if self.option_c:
            options.append(('c', self.option_c))
        if self.option_d:
            options.append(('d', self.option_d))
        return options


class UserAssessmentAttempt(models.Model):
    """Track user's assessment attempts"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assessment_attempts')
    assessment = models.ForeignKey(LevelAssessment, on_delete=models.CASCADE, related_name='attempts')
    level = models.CharField(max_length=20, choices=LevelAssessment.LEVEL_CHOICES)
    score = models.IntegerField(default=0)
    total_questions = models.IntegerField(default=0)
    percentage = models.FloatField(default=0)
    passed = models.BooleanField(default=False)
    answers = models.JSONField(default=dict, help_text="Stores user's answers")
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    time_taken_seconds = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-completed_at']
        verbose_name = "User Assessment Attempt"
        verbose_name_plural = "User Assessment Attempts"
    
    def __str__(self):
        return f"{self.user.username} - {self.get_level_display()} - {self.score}/{self.total_questions}"
    
    def save(self, *args, **kwargs):
        # Auto-calculate percentage
        if self.total_questions > 0:
            self.percentage = (self.score / self.total_questions) * 100
        super().save(*args, **kwargs)