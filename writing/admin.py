# writing/admin.py
from django.contrib import admin
from .models import WritingTest, WritingQuestion, WritingResponse, WritingTestResult


@admin.register(WritingTest)
class WritingTestAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'created_at', 'is_active', 'question_count']
    list_display_links = ['id', 'title']
    list_filter = ['is_active', 'created_at']
    search_fields = ['title', 'description']
    list_editable = ['is_active']
    readonly_fields = ['created_at']  # Mark created_at as readonly
    
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


class WritingQuestionInline(admin.TabularInline):
    model = WritingQuestion
    extra = 1
    fields = ['order', 'question_type', 'prompt', 'correct_answer']
    ordering = ['order']


@admin.register(WritingQuestion)
class WritingQuestionAdmin(admin.ModelAdmin):
    list_display = ['id', 'test', 'order', 'question_type', 'short_prompt']
    list_display_links = ['id', 'short_prompt']
    list_filter = ['question_type', 'test']
    search_fields = ['prompt', 'correct_answer']
    list_editable = ['order']
    
    fieldsets = (
        ('📌 Question Information', {
            'fields': ('test', 'order', 'question_type', 'prompt', 'explanation')
        }),
        ('✅ Answer Key', {
            'fields': ('correct_answer', 'acceptable_answers'),
            'description': 'For Fill in Blanks: comma-separated answers (e.g., "goes, are, a")<br>For Sentence Order: letters with commas (e.g., "C, B, A")<br>For Spelling MCQ: letters (e.g., "b, b, b")'
        }),
        ('🖼️ Legacy Fields (Not used in new questions)', {
            'fields': ('picture_filename', 'required_keywords', 'min_sentences', 'min_words', 'max_words', 'audio_filename'),
            'classes': ('collapse',),
            'description': 'These fields are kept for backward compatibility only'
        }),
    )
    
    def short_prompt(self, obj):
        return obj.prompt[:50] + '...' if len(obj.prompt) > 50 else obj.prompt
    short_prompt.short_description = 'Prompt'


@admin.register(WritingResponse)
class WritingResponseAdmin(admin.ModelAdmin):
    list_display = ['id', 'question', 'user', 'session_key', 'score', 'needs_manual_review', 'created_at']
    list_display_links = ['id', 'question']
    list_filter = ['score', 'needs_manual_review', 'created_at', 'question__question_type']
    search_fields = ['session_key', 'user__username', 'user_answer']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Response Information', {
            'fields': ('user', 'session_key', 'question')
        }),
        ('Answer', {
            'fields': ('user_answer', 'score', 'feedback', 'needs_manual_review')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(WritingTestResult)
class WritingTestResultAdmin(admin.ModelAdmin):
    list_display = ['id', 'test', 'user', 'session_key', 'total_score', 'max_score', 'percentage_display', 'level', 'created_at']
    list_display_links = ['id', 'test']
    list_filter = ['level', 'created_at', 'test']
    search_fields = ['user__username', 'session_key']
    readonly_fields = ['created_at', 'percentage']
    
    fieldsets = (
        ('Result Information', {
            'fields': ('test', 'user', 'session_key')
        }),
        ('Score', {
            'fields': ('total_score', 'max_score', 'percentage', 'level')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def percentage_display(self, obj):
        return f"{obj.percentage:.1f}%"
    percentage_display.short_description = 'Percentage'