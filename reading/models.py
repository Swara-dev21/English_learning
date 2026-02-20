# reading/models.py
from django.db import models
from django.contrib.auth.models import User

class Test(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    paragraph = models.TextField(
        default=(
            "Engineering life is not only about studying machines..."
        )
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class Question(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE)
    order = models.IntegerField(default=1)  # ✅ Added for ordering
    question_text = models.TextField()
    option1 = models.CharField(max_length=200)
    option2 = models.CharField(max_length=200)
    option3 = models.CharField(max_length=200, blank=True)
    option4 = models.CharField(max_length=200, blank=True)

    correct_option = models.IntegerField(choices=[
        (1, 'Option 1'),
        (2, 'Option 2'),
        (3, 'Option 3'),
        (4, 'Option 4'),
    ])

    def __str__(self):
        return f"Q{self.order}: {self.question_text[:50]}..."

class ReadingUserResponse(models.Model):
    """Store user's answers"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=100, blank=True)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_option = models.IntegerField(choices=[
        (1, 'Option 1'),
        (2, 'Option 2'),
        (3, 'Option 3'),
        (4, 'Option 4'),
    ])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['session_key', 'question']]

    def __str__(self):
        return f"Reading Response - Q{self.question.order} (Option {self.selected_option})"

class ReadingResult(models.Model):
    """Store complete reading test results"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=100, blank=True)
    test = models.ForeignKey(Test, on_delete=models.CASCADE)
    score = models.IntegerField(default=0)
    total = models.IntegerField(default=0)
    percentage = models.FloatField(default=0)
    level = models.CharField(max_length=20, default="Beginner")
    feedback = models.TextField(default="")
    created_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        if self.total > 0:
            self.percentage = (self.score / self.total) * 100
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.user or 'Anonymous'} - {self.test.title} - {self.score}/{self.total}"