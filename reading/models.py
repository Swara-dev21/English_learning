from django.db import models

class Test(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.title

class Question(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE)
    question_text = models.TextField()
    option1 = models.CharField(max_length=200)
    option2 = models.CharField(max_length=200)
    option3 = models.CharField(max_length=200, blank=True)
    option4 = models.CharField(max_length=200, blank=True)
    correct_option = models.IntegerField(choices=[
        (1, 'Option 1'), (2, 'Option 2'), 
        (3, 'Option 3'), (4, 'Option 4')
    ])
    
    def __str__(self):
        return f"Q: {self.question_text[:50]}..."