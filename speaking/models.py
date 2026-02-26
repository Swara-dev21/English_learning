from django.db import models

class Student(models.Model):
    name = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    roll_number = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def get_latest_score(self):
        """Get the most recent test score average"""
        latest_session = self.test_sessions.order_by('-completed_at').first()
        if latest_session:
            return latest_session.get_average_score()
        return None
    
    def __str__(self):
        return f"{self.name} ({self.roll_number})" if self.name else f"Student {self.roll_number}"


class TestSession(models.Model):
    session_id = models.CharField(max_length=100, unique=True)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, null=True, blank=True, related_name='test_sessions')
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Q1 fields
    q1_word1_recording = models.CharField(max_length=500, blank=True)
    q1_word2_recording = models.CharField(max_length=500, blank=True)
    q1_word3_recording = models.CharField(max_length=500, blank=True)
    q1_word4_recording = models.CharField(max_length=500, blank=True)
    q1_word5_recording = models.CharField(max_length=500, blank=True)
    
    q1_word1_score = models.FloatField(default=0)
    q1_word2_score = models.FloatField(default=0)
    q1_word3_score = models.FloatField(default=0)
    q1_word4_score = models.FloatField(default=0)
    q1_word5_score = models.FloatField(default=0)
    
    # Main Question Scores
    q1_score = models.FloatField(default=0) # Word Pronunciation
    q2_score = models.FloatField(default=0) # Sentence Rearrangement
    q3_score = models.FloatField(default=0) # Phrase Reading
    q4_score = models.FloatField(default=0) # Sentence Reading
    q5_score = models.FloatField(default=0) # Grammar Correction

    # Audio file paths for Q2-Q5
    q2_recording = models.CharField(max_length=500, blank=True)
    q3_recording = models.CharField(max_length=500, blank=True)
    q4_recording = models.CharField(max_length=500, blank=True)
    q5_recording = models.CharField(max_length=500, blank=True)
    
    def get_average_score(self):
        scores = [self.q1_score, self.q2_score, self.q3_score, self.q4_score, self.q5_score]
        return sum(scores) / 5 if scores else 0

    @property
    def level(self):
        """Logic: 1-45 Basic, 46-75 Intermediate, 76+ Advanced"""
        avg = self.get_average_score()
        if avg <= 45:
            return "Basic"
        elif avg <= 75:
            return "Intermediate"
        else:
            return "Advanced"

    def __str__(self):
        return f"Session {self.session_id} - {self.student.name if self.student else 'Unknown'}"