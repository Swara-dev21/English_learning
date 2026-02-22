from django.contrib import admin
from .models import Test, Paragraph, Question, ReadingUserResponse, ReadingResult


# ----------------------------
# Paragraph Admin
# ----------------------------
@admin.register(Paragraph)
class ParagraphAdmin(admin.ModelAdmin):
    list_display = ['id', 'test', 'order', 'short_content']
    list_filter = ['test']
    search_fields = ['content']

    def short_content(self, obj):
        return obj.content[:80] + "..." if len(obj.content) > 80 else obj.content
    short_content.short_description = "Paragraph Preview"


# ----------------------------
# Question Inline (inside Test)
# ----------------------------
class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1
    fields = [
        'order',
        'paragraph',
        'parameter_type',
        'question_text',
        'option1',
        'option2',
        'option3',
        'option4',
        'correct_option'
    ]

# ----------------------------
# Test Admin
# ----------------------------
@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'created_at', 'question_count']
    list_display_links = ['id', 'title']
    search_fields = ['title', 'description']
    inlines = [QuestionInline]
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

    def question_count(self, obj):
        return obj.question_set.count()
    question_count.short_description = 'Questions'


# ----------------------------
# Question Admin
# ----------------------------
@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'order',
        'test',
        'paragraph',
        'parameter_type',
        'short_question',
        'correct_option'
    ]
    list_display_links = ['id', 'short_question']
    list_filter = ['test', 'paragraph', 'parameter_type', 'correct_option']
    search_fields = ['question_text']
    list_editable = ['order', 'parameter_type']

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
        'question',
        'selected_option',
        'response_status',
        'created_at'
    ]
    list_display_links = ['id', 'user']
    list_filter = ['question__test', 'question__parameter_type', 'created_at']
    search_fields = ['user__username', 'session_key']
    readonly_fields = ['created_at']

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

# ----------------------------
# Reading Result Admin
# ----------------------------
@admin.register(ReadingResult)
class ReadingResultAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'user',
        'test',
        'score',
        'total',
        'percentage_display',
        'level',
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
        ('Rubric Scores', {
            'fields': ('main_idea_score', 'lexical_score', 'specific_score', 'organisation_score'),
            'classes': ('wide',)
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def percentage_display(self, obj):
        return f"{obj.percentage:.1f}%"
    percentage_display.short_description = "Percentage"

    def rubric_summary(self, obj):
        summary = []
        if obj.main_idea_score:
            summary.append("📖M")
        if obj.lexical_score:
            summary.append("🔤L")
        if obj.specific_score:
            summary.append("🔍D")
        if obj.organisation_score == 2:
            summary.append("🧩O(2)")
        elif obj.organisation_score == 1:
            summary.append("🧩O(1)")
        else:
            summary.append("🧩O(0)")
        return " | ".join(summary) if summary else "No data"
    rubric_summary.short_description = "Rubric"