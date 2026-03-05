from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import secrets
class SuspiciousActivity(models.Model):
    ACTIVITY_TYPES = [
        ('tab_switch', 'Tab Switch'),
        ('fullscreen_exit', 'Fullscreen Exit'),
        ('window_blur', 'Window Blur'),
        ('too_fast', 'Answered Too Fast'),
        ('away_from_keyboard', 'Away from Keyboard'),
        ('right_click', 'Right Click Attempt'),
        ('copy_attempt', 'Copy Attempt'),
        ('dev_tools', 'Developer Tools Attempt'),
    ]
    
    TEST_TYPES = [
        ('reading', 'Reading Test'),
        ('writing', 'Writing Test'),
        ('listening', 'Listening Test'),
        ('speaking', 'Speaking Test'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=100, null=True, blank=True)
    activity_type = models.CharField(max_length=50, choices=ACTIVITY_TYPES)
    count = models.IntegerField(default=1)
    question = models.IntegerField(default=1)
    test_type = models.CharField(max_length=20, choices=TEST_TYPES)
    time_away = models.IntegerField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = "Suspicious Activities"
    
    def __str__(self):
        return f"{self.user} - {self.activity_type} - {self.test_type} Q{self.question}"


class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    
    # Profile information
    institute = models.CharField(max_length=200)
    department = models.CharField(max_length=200)
    year = models.CharField(max_length=50)
    
    # Pretest tracking fields
    listening_completed = models.BooleanField(default=False)
    reading_completed = models.BooleanField(default=False)
    speaking_completed = models.BooleanField(default=False)
    writing_completed = models.BooleanField(default=False)
    pretest_completed = models.BooleanField(default=False)
    pretest_completed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return self.user.username
    
    def update_pretest_status(self):
        """Check if all tests are completed"""
        if all([self.listening_completed, self.reading_completed, 
                self.speaking_completed, self.writing_completed]):
            self.pretest_completed = True
            self.pretest_completed_at = timezone.now()
        else:
            self.pretest_completed = False
            self.pretest_completed_at = None
        self.save()
    
    def get_next_test(self):
        """Return the next incomplete test URL name"""
        if not self.listening_completed:
            return 'listening:test_home'
        elif not self.speaking_completed:
            return 'speaking:start'
        elif not self.reading_completed:
            return 'reading:index'
        elif not self.writing_completed:
            return 'writing:writing_test_home'
        return None
    
    @property
    def completed_tests(self):
        """Return number of completed tests"""
        return sum([
            self.listening_completed,
            self.reading_completed,
            self.speaking_completed,
            self.writing_completed
        ])


class PasswordResetToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def is_valid(self):
        return not self.is_used and self.expires_at > timezone.now()

    @classmethod
    def generate_token(cls, user):
        # Invalidate old tokens
        cls.objects.filter(user=user, is_used=False).update(is_used=True)
        
        # Create new token
        token = secrets.token_urlsafe(32)
        expires_at = timezone.now() + timezone.timedelta(hours=1)
        return cls.objects.create(
            user=user,
            token=token,
            expires_at=expires_at
        )

    def __str__(self):
        return f"Reset token for {self.user.username}"