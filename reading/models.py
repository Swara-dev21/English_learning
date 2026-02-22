# reading/models.py
from django.db import models
from django.contrib.auth.models import User


class Test(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Paragraph(models.Model):
    """
    Each test can have multiple paragraphs.
    Q1 → Paragraph 1
    Q2 → Paragraph 2
    Q3 → Paragraph 3
    Q4 & Q5 → Same Paragraph (Paragraph 4)
    """
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name="paragraphs")
    order = models.IntegerField(default=1)
    content = models.TextField()

    def __str__(self):
        return f"{self.test.title} - Paragraph {self.order}"


class Question(models.Model):

    PARAMETER_CHOICES = [
        ('MAIN_IDEA', 'Comprehension of Main Idea'),
        ('VOCAB', 'Lexical Interpretation Skill'),
        ('DETAIL', 'Understanding of Specific Details'),
        ('LOGICAL', 'Understanding of Organisation & Logical Thoughts'),
    ]

    test = models.ForeignKey(Test, on_delete=models.CASCADE)
    paragraph = models.ForeignKey(Paragraph, on_delete=models.CASCADE, related_name="questions")
    order = models.IntegerField(default=1)
    question_text = models.TextField()

    # Parameter tagging (VERY IMPORTANT for rubric scoring)
    parameter_type = models.CharField(
        max_length=20,
        choices=PARAMETER_CHOICES
    )

    # Weight per question (default = 20%)
    weight = models.IntegerField(default=20)

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
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=100, blank=True)
    test = models.ForeignKey(Test, on_delete=models.CASCADE)

    score = models.IntegerField(default=0)
    total = models.IntegerField(default=0)
    percentage = models.FloatField(default=0)
    level = models.CharField(max_length=20, default="Basic")
    feedback = models.TextField(default="")

    created_at = models.DateTimeField(auto_now_add=True)

    main_idea_score = models.IntegerField(default=0)      
    lexical_score = models.IntegerField(default=0)        
    specific_score = models.IntegerField(default=0)       
    organisation_score = models.IntegerField(default=0) 

    def save(self, *args, **kwargs):
        if self.total > 0:
            self.percentage = (self.score / self.total) * 100
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user or 'Anonymous'} - {self.test.title} - {self.score}/{self.total}"