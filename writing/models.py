# writing/models.py
from django.db import models
from django.contrib.auth.models import User

class WritingTest(models.Model):
    """Represents a complete writing test"""
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.title

class WritingQuestion(models.Model):
    """Each writing question with its type and requirements"""
    QUESTION_TYPES = [
        ('picture_description', 'Picture Description'),
        ('tense_change', 'Tense Change'),
        ('article_complete', 'Article Completion'),
        ('dictation', 'Dictation'),
        ('grammar_correction', 'Grammar Correction'),
    ]
    
    test = models.ForeignKey(WritingTest, on_delete=models.CASCADE, related_name='questions')
    order = models.IntegerField(default=1)
    question_type = models.CharField(max_length=50, choices=QUESTION_TYPES)
    
    # Common fields
    prompt = models.TextField()
    correct_answer = models.TextField(help_text="Main correct answer for auto-checking")
    acceptable_answers = models.JSONField(default=list, blank=True, help_text="List of other acceptable answers in JSON format")
    explanation = models.TextField(blank=True)
    
    # For picture description only
    picture_filename = models.CharField(max_length=200, blank=True, help_text="Name of image file in static folder")
    required_keywords = models.JSONField(default=list, blank=True, help_text="Keywords that should be present")
    min_sentences = models.IntegerField(default=2)
    min_words = models.IntegerField(default=15)
    max_words = models.IntegerField(default=50)
    
    # For dictation only
    audio_filename = models.CharField(max_length=200, blank=True, help_text="Name of audio file for dictation")
    
    def __str__(self):
        return f"Q{self.order}: {self.question_type} - {self.prompt[:50]}..."
    
    def picture_url(self):
        """Generate URL to the picture file"""
        if self.picture_filename:
            return f"/static/writing_test/images/{self.picture_filename}"
        return ""
    
    def audio_url(self):
        """Generate URL to the audio file"""
        if self.audio_filename:
            return f"/static/writing_test/audio/{self.audio_filename}"
        return ""

class WritingResponse(models.Model):
    """Store user's written answers"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=100, blank=True)
    question = models.ForeignKey(WritingQuestion, on_delete=models.CASCADE)
    user_answer = models.TextField()
    score = models.IntegerField(default=0, help_text="Score out of 100")
    feedback = models.JSONField(default=list, blank=True, help_text="List of feedback points")
    needs_manual_review = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = [['session_key', 'question']]
    
    def __str__(self):
        return f"Response to Q{self.question.order}: {self.user_answer[:50]}..."

class WritingTestResult(models.Model):
    """Store complete writing test results"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=100, blank=True)
    test = models.ForeignKey(WritingTest, on_delete=models.CASCADE)
    total_score = models.FloatField(default=0)
    max_score = models.IntegerField(default=5)
    percentage = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    level = models.CharField(max_length=20, blank=True, null=True)
    
    def save(self, *args, **kwargs):
        # Calculate percentage first
        if self.max_score > 0:
            self.percentage = (self.total_score / self.max_score) * 100
        
            
        super().save(*args, **kwargs)
    
    def score_out_of_5(self):
        """Return score formatted as X/5"""
        return f"{self.total_score}/{self.max_score}"
    
    def __str__(self):
        return f"Writing Result: {self.total_score}/{self.max_score} ({self.percentage:.1f}%) - {self.level}"