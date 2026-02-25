# listening/models.py
from django.db import models
import re
import json
from django.contrib.auth.models import User

class QuestionType(models.TextChoices):
    MCQ = 'MCQ', 'Multiple Choice'
    TYPING = 'TYPING', 'Manual Typing'

class ListeningTest(models.Model):
    """Represents a complete listening test"""
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.title
    
    def question_count(self):
        return self.questions.count()

class AudioQuestion(models.Model):
    """Each audio file and its associated question"""
    test = models.ForeignKey(ListeningTest, on_delete=models.CASCADE, related_name='questions')
    order = models.IntegerField(default=1)  # Order in test (1-5)
    
    # Question type
    question_type = models.CharField(
        max_length=10,
        choices=QuestionType.choices,
        default=QuestionType.MCQ
    )
    
    # Audio file
    audio_filename = models.CharField(max_length=200, help_text="Name of audio file in static folder")
    transcript = models.TextField(help_text="Full text of what's spoken in audio")
    
    # Question details
    question_text = models.TextField()
    explanation = models.TextField(blank=True, help_text="Explanation shown after test")
    
    # For typing questions - PRIMARY ANSWER FIELDS
    correct_answer_text = models.TextField(blank=True, null=True, 
        help_text="Primary correct answer for typing questions (exact phrase matching)")
    
    alternative_answers = models.TextField(blank=True, null=True,
        help_text="JSON list of alternative correct answer phrases (e.g., ['she was nervous', 'her nervousness', 'anxiety'])")
    
    # Legacy field - kept for backward compatibility but not actively used
    keywords = models.TextField(blank=True, 
        help_text="DEPRECATED: Use alternative_answers instead")
    
    def audio_url(self):
        """Generate URL to the audio file"""
        return f"/static/listening/audio/{self.audio_filename}"
    
    def is_mcq(self):
        return self.question_type == QuestionType.MCQ
    
    def is_typing(self):
        return self.question_type == QuestionType.TYPING
    
    def get_keyword_list(self):
        """Convert keywords string to list (legacy method)"""
        if self.keywords:
            return [k.strip().lower() for k in self.keywords.split(',') if k.strip()]
        return []
    
    def get_alternative_answers_list(self):
        """Convert alternative_answers JSON to list"""
        if self.alternative_answers:
            try:
                # If it's already a list, return as is
                if isinstance(self.alternative_answers, list):
                    return self.alternative_answers
                # If it's a string, try to parse JSON
                return json.loads(self.alternative_answers)
            except (json.JSONDecodeError, TypeError):
                # If JSON parsing fails, try to split by commas (legacy format)
                if isinstance(self.alternative_answers, str) and ',' in self.alternative_answers:
                    return [ans.strip() for ans in self.alternative_answers.split(',')]
                return []
        return []
    
    def __str__(self):
        return f"Question {self.order}: {self.question_text[:50]}..."

class AnswerOption(models.Model):
    """Answer choices for each question (only for MCQ)"""
    question = models.ForeignKey(AudioQuestion, on_delete=models.CASCADE, related_name='options')
    text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.text[:50]}... ({'Correct' if self.is_correct else 'Incorrect'})"

class UserResponse(models.Model):
    """Store user's answers"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=100)  # For anonymous users
    question = models.ForeignKey(AudioQuestion, on_delete=models.CASCADE)
    
    # For MCQ questions
    selected_option = models.ForeignKey(AnswerOption, on_delete=models.CASCADE, null=True, blank=True)
    
    # For typing questions
    typed_answer = models.TextField(blank=True)
    
    # Grading information
    is_auto_graded = models.BooleanField(default=False)
    auto_graded_correct = models.BooleanField(default=False)
    matched_answer = models.TextField(blank=True, help_text="Which answer pattern was matched")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = [['session_key', 'question']]
    
    def get_answer_display(self):
        if self.question.is_mcq() and self.selected_option:
            return self.selected_option.text
        elif self.question.is_typing():
            return self.typed_answer or "No answer provided"
        return "No answer"
    
    def username_display(self):
        """Return username if user exists, otherwise 'Anonymous'"""
        return self.user.username if self.user else 'Anonymous'
    username_display.short_description = 'Username'
    
    def normalize_text(self, text):
        """
        Normalize text for comparison:
        - Convert to lowercase
        - Remove extra whitespace
        - Remove punctuation at the end
        - But preserve internal punctuation that's part of the phrase
        """
        if not text:
            return ""
        
        # Convert to string and strip
        text = str(text).strip()
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove trailing period, comma, question mark, exclamation mark
        text = re.sub(r'[.,!?;:]$', '', text)
        
        # Remove extra whitespace (multiple spaces to single space)
        text = ' '.join(text.split())
        
        return text
    
    def is_correct(self):
        """
        Determine if the answer is correct based on question type.
        For typing questions, checks against:
        1. Primary correct_answer_text (exact match after normalization)
        2. Alternative answers list (exact match after normalization)
        """
        if self.question.is_mcq():
            return self.selected_option and self.selected_option.is_correct
        
        elif self.question.is_typing():
            if not self.typed_answer:
                return False
            
            # Normalize the user's answer
            user_answer = self.normalize_text(self.typed_answer)
            
            # STRATEGY 1: Check against primary correct_answer_text
            if self.question.correct_answer_text:
                correct_text = self.normalize_text(self.question.correct_answer_text)
                if user_answer == correct_text:
                    self.matched_answer = f"Exact match with primary answer: '{self.question.correct_answer_text}'"
                    self.is_auto_graded = True
                    self.auto_graded_correct = True
                    return True
            
            # STRATEGY 2: Check against alternative answers list
            alt_answers = self.question.get_alternative_answers_list()
            if alt_answers:
                for alt in alt_answers:
                    alt_normalized = self.normalize_text(alt)
                    if user_answer == alt_normalized:
                        self.matched_answer = f"Matched alternative: '{alt}'"
                        self.is_auto_graded = True
                        self.auto_graded_correct = True
                        return True
            
            # STRATEGY 3: Legacy keyword matching (only if no alternatives found)
            # This is kept for backward compatibility
            keywords = self.question.get_keyword_list()
            if keywords and not alt_answers:
                user_answer_lower = self.typed_answer.lower()
                matched = []
                for keyword in keywords:
                    if keyword in user_answer_lower:
                        matched.append(keyword)
                
                if matched:
                    self.matched_answer = f"Matched keywords: {', '.join(matched)}"
                    self.is_auto_graded = True
                    self.auto_graded_correct = True
                    return True
            
            # If we get here, no match found
            self.is_auto_graded = True
            self.auto_graded_correct = False
            return False
        
        return False
    
    def save(self, *args, **kwargs):
        """Auto-grade typing questions on save"""
        if self.question.is_typing():
            # Call is_correct() to perform grading
            self.is_correct()
        super().save(*args, **kwargs)
    
    def __str__(self):
        if self.question.is_mcq():
            answer = self.selected_option.text[:20] if self.selected_option else "No answer"
        else:
            answer = self.typed_answer[:20] + "..." if self.typed_answer else "No answer"
        return f"Response to Q{self.question.order}: {answer}"


class TestResult(models.Model):
    """Store complete test results"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=100)
    test = models.ForeignKey(ListeningTest, on_delete=models.CASCADE)
    score = models.IntegerField(default=0)
    total_questions = models.IntegerField(default=5)
    percentage = models.FloatField(default=0)
    level = models.CharField(max_length=20, blank=True)
    feedback = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Track pending manual grading
    pending_manual_grading = models.BooleanField(default=False)
    
    def save(self, *args, **kwargs):
        if self.total_questions > 0 and self.percentage == 0:
            self.percentage = (self.score / self.total_questions) * 100
        super().save(*args, **kwargs)
    
    def username_display(self):
        """Return username if user exists, otherwise 'Anonymous'"""
        return self.user.username if self.user else 'Anonymous'
    username_display.short_description = 'Username'
    
    def get_pending_typing_questions(self):
        """Get typing questions that need manual grading"""
        responses = UserResponse.objects.filter(
            session_key=self.session_key,
            question__test=self.test,
            question__question_type=QuestionType.TYPING
        )
        return [r for r in responses if not r.is_auto_graded]
    
    def __str__(self):
        return f"Result: {self.score}/{self.total_questions} ({self.percentage:.1f}%)"