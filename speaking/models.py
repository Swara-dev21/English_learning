from django.db import models

class Recording(models.Model):
    student_name = models.CharField(max_length=100, default="Student")
    audio_file = models.FileField(upload_to='speaking/recordings/')
    text_to_read = models.TextField()
    score = models.FloatField(null=True, blank=True)
    mispronounced_words = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student_name} - {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
