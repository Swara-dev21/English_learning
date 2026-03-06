from django.contrib import admin
from .models import Test, Paragraph, Question, ReadingUserResponse, ReadingResult


# ----------------------------
# Question Inline (inside Paragraph)
# ----------------------------
class QuestionInline(admin.TabularInline):
    """Show questions directly under their paragraph"""
    model = Question
    extra = 0  # Don't show extra empty forms by default
    fields = [
        'order',
        'question_text',
        'parameter_type',
        'option1',
        'option2',
        'option3',
        'option4',
        'correct_option'
    ]
    ordering = ['order']
    min_num = 1  # At least one question per paragraph


# ----------------------------
# Paragraph Admin
# ----------------------------
@admin.register(Paragraph)
class ParagraphAdmin(admin.ModelAdmin):
    list_display = ['id', 'test', 'order', 'question_count', 'short_content']
    list_filter = ['test']
    search_fields = ['content']
    inlines = [QuestionInline]  # Show questions inline
    ordering = ['test', 'order']

    def short_content(self, obj):
        return obj.content[:80] + "..." if len(obj.content) > 80 else obj.content
    short_content.short_description = "Paragraph Preview"
    
    def question_count(self, obj):
        return obj.questions.count()
    question_count.short_description = 'Questions'


# ----------------------------
# Test Admin
# ----------------------------
@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'created_at', 'paragraph_count', 'total_questions']
    list_display_links = ['id', 'title']
    search_fields = ['title', 'description']
    readonly_fields = ['created_at']  

    fieldsets = (
        ('Test Information', {
            'fields': ('title', 'description')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def paragraph_count(self, obj):
        return obj.paragraphs.count()
    paragraph_count.short_description = 'Paragraphs'
    
    def total_questions(self, obj):
        total = 0
        for paragraph in obj.paragraphs.all():
            total += paragraph.questions.count()
        return total
    total_questions.short_description = 'Total Questions'


# ----------------------------
# Question Admin
# ----------------------------
@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'order',
        'test',
        'paragraph_info',
        'parameter_type',
        'short_question',
        'correct_option'
    ]
    list_display_links = ['id', 'short_question']
    list_filter = ['test', 'paragraph', 'parameter_type', 'correct_option']
    search_fields = ['question_text']
    list_editable = ['order', 'parameter_type']
    ordering = ['test', 'paragraph__order', 'order']

    fieldsets = (
        ('Question Information', {
            'fields': ('test', 'paragraph', 'order', 'parameter_type', 'question_text')
        }),
        ('Options', {
            'fields': ('option1', 'option2', 'option3', 'option4')
        }),
        ('Correct Answer', {
            'fields': ('correct_option',)
        }),
    )

    def short_question(self, obj):
        return obj.question_text[:50] + "..." if len(obj.question_text) > 50 else obj.question_text
    short_question.short_description = "Question"
    
    def paragraph_info(self, obj):
        return f"P{obj.paragraph.order}" if obj.paragraph else "-"
    paragraph_info.short_description = "Para"


# ----------------------------
# User Response Admin
# ----------------------------
@admin.register(ReadingUserResponse)
class ReadingUserResponseAdmin(admin.ModelAdmin):
    
    def response_status(self, obj):
        """Display ✅ or ❌ based on correct/incorrect answer"""
        if obj.selected_option == obj.question.correct_option:
            return "✅ Correct"
        return "❌ Incorrect"
    response_status.short_description = "Status"
    response_status.admin_order_field = 'selected_option'

    list_display = [
        'id',
        'user',
        'session_key',
        'question_info',
        'selected_option',
        'response_status',
        'created_at'
    ]
    list_display_links = ['id', 'user']
    list_filter = ['question__test', 'question__parameter_type', 'created_at']
    search_fields = ['user__username', 'session_key']
    readonly_fields = ['created_at']
    ordering = ['-created_at']

    fieldsets = (
        ('User Information', {
            'fields': ('user', 'session_key')
        }),
        ('Response', {
            'fields': ('question', 'selected_option')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def question_info(self, obj):
        return f"Q{obj.question.order} (P{obj.question.paragraph.order})"
    question_info.short_description = "Question"


# ----------------------------
# Reading Result Admin
# ----------------------------
@admin.register(ReadingResult)
class ReadingResultAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'user',
        'test',
        'score_display',
        'percentage_display',
        'level',
        'questions_correct',
        'rubric_summary',
        'created_at'
    ]
    list_display_links = ['id', 'user']
    list_filter = ['test', 'level', 'created_at']
    search_fields = ['user__username', 'session_key']
    readonly_fields = ['created_at'] 

    fieldsets = (
        ('Result Information', {
            'fields': ('user', 'session_key', 'test')
        }),
        ('Score Details', {
            'fields': ('score', 'total', 'percentage', 'level', 'feedback')
        }),
        ('Rubric Scores (for 8 questions)', {
            'fields': ('main_idea_score', 'lexical_score', 'specific_score', 'organisation_score'),
            'classes': ('wide',),
            'description': 'These scores track correct answers per skill type'
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def percentage_display(self, obj):
        return f"{obj.percentage:.1f}%"
    percentage_display.short_description = "Percentage"
    
    def score_display(self, obj):
        return f"{obj.score}/{obj.total}"
    score_display.short_description = "Score"
    
    def questions_correct(self, obj):
        """Display number of correct questions out of 8"""
        # Sum up all rubric scores (each represents 1 correct question)
        total_correct = (obj.main_idea_score + 
                        obj.lexical_score + 
                        obj.specific_score + 
                        obj.organisation_score)
        return f"{total_correct}/8"
    questions_correct.short_description = "Correct"

    def rubric_summary(self, obj):
        summary = []
        if obj.main_idea_score:
            summary.append(f"📖M:{obj.main_idea_score}")
        if obj.lexical_score:
            summary.append(f"🔤L:{obj.lexical_score}")
        if obj.specific_score:
            summary.append(f"🔍D:{obj.specific_score}")
        if obj.organisation_score:
            summary.append(f"🧩O:{obj.organisation_score}")
        return " | ".join(summary) if summary else "No data"
    rubric_summary.short_description = "Rubric"