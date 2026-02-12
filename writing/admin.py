from django.contrib import admin
from .models import WritingTest, WritingQuestion, WritingResponse, WritingTestResult

class WritingQuestionInline(admin.TabularInline):
    model = WritingQuestion
    extra = 0
    fields = ['order', 'question_type', 'prompt', 'correct_answer']
    show_change_link = True

@admin.register(WritingTest)
class WritingTestAdmin(admin.ModelAdmin):
    inlines = [WritingQuestionInline]
    search_fields = ['title', 'description']

@admin.register(WritingQuestion)
class WritingQuestionAdmin(admin.ModelAdmin):
    list_display = ['id', 'order', 'question_type', 'prompt_short', 'test']  # Added 'id' as first
    list_display_links = ['id']  # Added this line
    list_editable = ['order']  # Now 'order' is not first, so it's OK
    list_filter = ['test', 'question_type']
    search_fields = ['prompt', 'correct_answer']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('test', 'order', 'question_type', 'prompt', 'correct_answer', 'acceptable_answers', 'explanation')
        }),
        ('Picture Description Settings', {
            'fields': ('picture_filename', 'required_keywords', 'min_sentences', 'min_words', 'max_words'),
            'classes': ('collapse',),
        }),
        ('Dictation Settings', {
            'fields': ('audio_filename',),
            'classes': ('collapse',),
        }),
    )
    
    def prompt_short(self, obj):
        return obj.prompt[:50] + '...' if len(obj.prompt) > 50 else obj.prompt
    prompt_short.short_description = 'Prompt'

@admin.register(WritingResponse)
class WritingResponseAdmin(admin.ModelAdmin):
    list_display = ['id', 'session_key_short', 'question', 'user_answer_short', 'score', 'needs_manual_review', 'created_at']
    list_filter = ['question__test', 'needs_manual_review', 'question__question_type']
    search_fields = ['user_answer', 'session_key']
    
    def session_key_short(self, obj):
        return obj.session_key[:10] + '...' if obj.session_key else 'Anonymous'
    session_key_short.short_description = 'User'
    
    def user_answer_short(self, obj):
        return obj.user_answer[:50] + '...' if len(obj.user_answer) > 50 else obj.user_answer
    user_answer_short.short_description = 'Answer'

@admin.register(WritingTestResult)
class WritingTestResultAdmin(admin.ModelAdmin):
    list_display = ['id', 'session_key_short', 'test', 'score_display', 'percentage', 'completed_at']
    list_filter = ['test', 'completed_at']
    
    def session_key_short(self, obj):
        return obj.session_key[:10] + '...' if obj.session_key else 'Anonymous'
    session_key_short.short_description = 'User'
    
    def score_display(self, obj):
        return f"{obj.total_score}/5"  # Show as X/5
    score_display.short_description = 'Score'
    
    def percentage(self, obj):
        return f"{obj.percentage():.1f}%"
    percentage.short_description = 'Percentage'