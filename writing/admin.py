from django.contrib import admin
from .models import WritingTest, WritingQuestion, WritingResponse, WritingTestResult

@admin.register(WritingTest)
class WritingTestAdmin(admin.ModelAdmin):
    list_display = ['title', 'created_at', 'is_active']
    list_filter = ['is_active', 'created_at']
    search_fields = ['title', 'description']
    list_editable = ['is_active']
    fieldsets = (
        ('Test Information', {
            'fields': ('title', 'description', 'is_active')
        }),
    )


class WritingQuestionInline(admin.TabularInline):
    model = WritingQuestion
    extra = 1
    fields = ['order', 'question_type', 'prompt', 'correct_answer', 
              'picture_filename', 'audio_filename', 'required_keywords',
              'min_sentences', 'min_words', 'max_words']
    ordering = ['order']


@admin.register(WritingQuestion)
class WritingQuestionAdmin(admin.ModelAdmin):
    list_display = ['test', 'order', 'question_type', 'short_prompt', 'has_picture', 'has_audio']
    list_filter = ['question_type', 'test']
    search_fields = ['prompt', 'correct_answer']
    list_editable = ['order']
    
    fieldsets = (
        ('Question Information', {
            'fields': ('test', 'order', 'question_type', 'prompt')
        }),
        ('Answer Key', {
            'fields': ('correct_answer', 'acceptable_answers', 'explanation')
        }),
        ('Picture Description Settings', {
            'fields': ('picture_filename', 'required_keywords', 
                      'min_sentences', 'min_words', 'max_words'),
            'classes': ('collapse',),
            'description': 'Only applicable for Picture Description questions'
        }),
        ('Dictation Settings', {
            'fields': ('audio_filename',),
            'classes': ('collapse',),
            'description': 'Only applicable for Dictation questions'
        }),
    )
    
    def short_prompt(self, obj):
        return obj.prompt[:50] + '...' if len(obj.prompt) > 50 else obj.prompt
    short_prompt.short_description = 'Prompt'
    
    def has_picture(self, obj):
        return bool(obj.picture_filename)
    has_picture.boolean = True
    has_picture.short_description = 'Picture'
    
    def has_audio(self, obj):
        return bool(obj.audio_filename)
    has_audio.boolean = True
    has_audio.short_description = 'Audio'


@admin.register(WritingResponse)
class WritingResponseAdmin(admin.ModelAdmin):
    list_display = ['question', 'session_key', 'user', 'score', 'needs_manual_review', 'created_at']
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
    list_display = ['test', 'session_key', 'user', 'total_score', 'max_score', 'percentage_display', 'completed_at']
    list_filter = ['total_score', 'completed_at', 'test']
    search_fields = ['session_key', 'user__username']
    readonly_fields = ['completed_at']
    
    fieldsets = (
        ('Result Information', {
            'fields': ('test', 'user', 'session_key')
        }),
        ('Score', {
            'fields': ('total_score', 'max_score')
        }),
        ('Metadata', {
            'fields': ('completed_at',),
            'classes': ('collapse',)
        }),
    )
    
    def percentage_display(self, obj):
        percentage = obj.percentage()
        return f"{percentage:.1f}%"
    percentage_display.short_description = 'Percentage'