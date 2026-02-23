# listening/admin.py
from django.contrib import admin
from django import forms
from .models import ListeningTest, AudioQuestion, AnswerOption, UserResponse, TestResult, QuestionType
import json

class AnswerOptionInline(admin.TabularInline):
    model = AnswerOption
    extra = 0
    fields = ['text', 'is_correct']
    
    def get_max_num(self, request, obj=None):
        if obj and obj.question_type == QuestionType.MCQ:
            return 4
        return 0

class AudioQuestionInline(admin.TabularInline):
    model = AudioQuestion
    extra = 0
    fields = ['order', 'question_type', 'audio_filename', 'question_text', 'transcript']

@admin.register(ListeningTest)
class ListeningTestAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'created_at', 'is_active', 'question_count']
    list_display_links = ['id', 'title']
    list_filter = ['is_active', 'created_at']
    search_fields = ['title', 'description']
    list_editable = ['is_active']
    inlines = [AudioQuestionInline]
    
    fieldsets = (
        ('Test Information', {
            'fields': ('title', 'description', 'is_active')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def question_count(self, obj):
        return obj.questions.count()
    question_count.short_description = 'Questions'

class AudioQuestionForm(forms.ModelForm):
    """Custom form for AudioQuestion to help with JSON formatting"""
    
    class Meta:
        model = AudioQuestion
        fields = '__all__'
    
    def clean_alternative_answers(self):
        """Validate that alternative_answers is proper JSON"""
        data = self.cleaned_data.get('alternative_answers')
        if data:
            if isinstance(data, str):
                try:
                    # Try to parse as JSON
                    parsed = json.loads(data)
                    if not isinstance(parsed, list):
                        raise forms.ValidationError("Alternative answers must be a JSON array")
                    return json.dumps(parsed, indent=2)
                except json.JSONDecodeError:
                    # If not valid JSON, try to split by commas
                    items = [item.strip() for item in data.split(',') if item.strip()]
                    return json.dumps(items, indent=2)
        return data

@admin.register(AudioQuestion)
class AudioQuestionAdmin(admin.ModelAdmin):
    form = AudioQuestionForm
    list_display = ['id', 'order', 'test', 'question_type', 'short_question', 'audio_filename', 'has_alternatives']
    list_display_links = ['id', 'short_question']
    list_filter = ['test', 'question_type']
    search_fields = ['question_text', 'transcript', 'correct_answer_text']
    list_editable = ['order', 'question_type']
    inlines = [AnswerOptionInline]
    
    fieldsets = (
        ('Question Information', {
            'fields': ('test', 'order', 'question_type', 'question_text', 'explanation')
        }),
        ('Audio & Transcript', {
            'fields': ('audio_filename', 'transcript')
        }),
        ('Typing Question Settings', {
            'fields': ('correct_answer_text', 'alternative_answers'),
            'classes': ('wide', 'extrapretty'),
            'description': '''
                <strong>For typing questions only:</strong><br>
                - <strong>Primary correct answer:</strong> The main expected answer (exact phrase)<br>
                - <strong>Alternative answers:</strong> JSON array of all possible correct answer phrases<br>
                <br>
                <strong>Example format for alternative_answers:</strong><br>
                <pre style="background: #f4f4f4; padding: 10px; border-radius: 5px;">
[
    "she was nervous",
    "her nervousness",
    "she felt nervous",
    "being nervous",
    "nerves",
    "anxiety"
]</pre>
                <br>
                <strong>Note:</strong> Answers are matched exactly after normalizing (lowercase, removing trailing punctuation).
                Single keywords are not recommended - use complete phrases instead.
            '''
        }),
        ('Legacy Settings', {
            'fields': ('keywords',),
            'classes': ('collapse',),
            'description': 'Deprecated: Use alternative_answers instead'
        }),
    )
    
    def get_inline_instances(self, request, obj=None):
        if obj and obj.question_type == QuestionType.MCQ:
            return super().get_inline_instances(request, obj)
        return []
    
    def short_question(self, obj):
        return obj.question_text[:50] + '...' if len(obj.question_text) > 50 else obj.question_text
    short_question.short_description = 'Question'
    
    def has_alternatives(self, obj):
        """Display whether the question has alternative answers"""
        if obj.is_mcq():
            return "—"
        alt_count = len(obj.get_alternative_answers_list())
        if obj.correct_answer_text and alt_count > 0:
            return f"✅ 1 primary + {alt_count} alternatives"
        elif obj.correct_answer_text:
            return f"✅ Primary only"
        elif alt_count > 0:
            return f"✅ {alt_count} alternatives"
        return "❌ No answers"
    has_alternatives.short_description = 'Answer Status'
    has_alternatives.boolean = False
    
    def save_model(self, request, obj, form, change):
        """Format alternative_answers as pretty JSON before saving"""
        if obj.alternative_answers:
            if isinstance(obj.alternative_answers, str):
                try:
                    # Try to parse as JSON to validate and pretty-print
                    parsed = json.loads(obj.alternative_answers)
                    if isinstance(parsed, list):
                        obj.alternative_answers = json.dumps(parsed, indent=2)
                except json.JSONDecodeError:
                    # If not valid JSON, try to split by commas
                    items = [item.strip() for item in obj.alternative_answers.split(',') if item.strip()]
                    obj.alternative_answers = json.dumps(items, indent=2)
        super().save_model(request, obj, form, change)

@admin.register(AnswerOption)
class AnswerOptionAdmin(admin.ModelAdmin):
    list_display = ['id', 'question', 'short_text', 'is_correct']
    list_display_links = ['id', 'short_text']
    list_filter = ['is_correct', 'question__test', 'question__question_type']
    search_fields = ['text']
    list_editable = ['is_correct']
    
    def get_queryset(self, request):
        return super().get_queryset(request).filter(question__question_type=QuestionType.MCQ)
    
    def short_text(self, obj):
        return obj.text[:50] + '...' if len(obj.text) > 50 else obj.text
    short_text.short_description = 'Answer Text'

@admin.register(UserResponse)
class UserResponseAdmin(admin.ModelAdmin):
    list_display = ['id', 'session_key', 'question', 'answer_summary', 'is_correct_display', 
                   'auto_graded_correct', 'matched_answer_display', 'created_at']
    list_display_links = ['id', 'session_key']
    list_filter = ['question__test', 'question__question_type', 'created_at', 'is_auto_graded', 'auto_graded_correct']
    search_fields = ['session_key', 'typed_answer', 'matched_answer']
    readonly_fields = ['created_at', 'matched_answer']
    list_editable = ['auto_graded_correct']
    
    fieldsets = (
        ('Session Information', {
            'fields': ('session_key',)
        }),
        ('Question', {
            'fields': ('question',)
        }),
        ('Response', {
            'fields': ('selected_option', 'typed_answer')
        }),
        ('Grading', {
            'fields': ('is_auto_graded', 'auto_graded_correct', 'matched_answer'),
            'description': 'Matched answer shows which answer pattern was matched during auto-grading'
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def answer_summary(self, obj):
        if obj.question and obj.question.is_mcq() and obj.selected_option:
            return f"MCQ: {obj.selected_option.text[:30]}"
        elif obj.question and obj.question.is_typing():
            return f"Typing: {obj.typed_answer[:30]}"
        return "No answer"
    answer_summary.short_description = 'Answer'
    
    def is_correct_display(self, obj):
        return obj.is_correct()
    is_correct_display.boolean = True
    is_correct_display.short_description = 'Correct?'
    
    def matched_answer_display(self, obj):
        return obj.matched_answer or "—"
    matched_answer_display.short_description = 'Matched Pattern'

# listening/admin.py - Update TestResultAdmin

@admin.register(TestResult)
class TestResultAdmin(admin.ModelAdmin):
    list_display = ['id', 'session_key', 'test', 'score', 'total_questions', 'percentage_display', 
                   'level', 'pending_grading', 'created_at']
    list_display_links = ['id', 'session_key']
    list_filter = ['test', 'pending_manual_grading', 'created_at', 'level']
    search_fields = ['session_key']
    readonly_fields = ['created_at', 'percentage']
    actions = ['recalculate_score']
    
    fieldsets = (
        ('Result Information', {
            'fields': ('session_key', 'test')
        }),
        ('Score', {
            'fields': ('score', 'total_questions', 'percentage', 'level', 'feedback', 'pending_manual_grading')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def percentage_display(self, obj):
        return f"{obj.percentage:.1f}%"
    percentage_display.short_description = 'Percentage'
    
    def pending_grading(self, obj):
        return obj.pending_manual_grading
    pending_grading.boolean = True
    pending_grading.short_description = 'Needs Grading'
    
    def recalculate_score(self, request, queryset):
        for result in queryset:
            responses = UserResponse.objects.filter(
                session_key=result.session_key,
                question__test=result.test
            )
            correct_count = sum(1 for r in responses if r.is_correct())
            result.score = correct_count
            result.percentage = (correct_count / result.total_questions * 100) if result.total_questions > 0 else 0
            result.save()
        self.message_user(request, f"{queryset.count()} results recalculated.")
    recalculate_score.short_description = "Recalculate scores"