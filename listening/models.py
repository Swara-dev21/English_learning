from django.db import models
from django.contrib.auth.models import User

class ListeningTest(models.Model):
    """Represents a complete listening test"""
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.title

class AudioQuestion(models.Model):
    """Each audio file and its associated question"""
    test = models.ForeignKey(ListeningTest, on_delete=models.CASCADE, related_name='questions')
    order = models.IntegerField(default=1)  # Order in test (1-5)
    
    # Audio file - store path to your static files
    audio_filename = models.CharField(max_length=200, help_text="Name of audio file in static folder")
    transcript = models.TextField(help_text="Full text of what's spoken in audio")
    
    # Question details
    question_text = models.TextField()
    explanation = models.TextField(blank=True, help_text="Explanation shown after test")
    
    def audio_url(self):
        """Generate URL to the audio file"""
        return f"/static/audio_test/audio/{self.audio_filename}"
    
    def __str__(self):
        return f"Question {self.order}: {self.question_text[:50]}..."

class AnswerOption(models.Model):
    """Answer choices for each question"""
    question = models.ForeignKey(AudioQuestion, on_delete=models.CASCADE, related_name='options')
    text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.text[:50]}... ({'Correct' if self.is_correct else 'Incorrect'})"

class UserResponse(models.Model):
    """Store user's answers"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=100, blank=True)  # For anonymous users
    question = models.ForeignKey(AudioQuestion, on_delete=models.CASCADE)
    selected_option = models.ForeignKey(AnswerOption, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = [['session_key', 'question']]
    
    def __str__(self):
        return f"Response to Q{self.question.order}: {self.selected_option.text[:20]}..."

class TestResult(models.Model):
    """Store complete test results"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=100, blank=True)
    test = models.ForeignKey(ListeningTest, on_delete=models.CASCADE)
    score = models.IntegerField(default=0)
    total_questions = models.IntegerField(default=5)
    completed_at = models.DateTimeField(auto_now_add=True)
    
    def percentage(self):
        return (self.score / self.total_questions) * 100 if self.total_questions > 0 else 0
    
    def __str__(self):
        return f"Result: {self.score}/{self.total_questions} ({self.percentage():.1f}%)"