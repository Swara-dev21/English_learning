# speaking/admin.py
from django.contrib import admin
from .models import Recording, SpeakingResult


@admin.register(Recording)
class RecordingAdmin(admin.ModelAdmin):
    list_display = ['id', 'student_name', 'score', 'created_at', 'short_text']
    list_display_links = ['id', 'student_name']
    list_filter = ['created_at']
    search_fields = ['student_name', 'text_to_read']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Recording Information', {
            'fields': ('student_name', 'audio_file', 'text_to_read')
        }),
        ('Results', {
            'fields': ('score', 'mispronounced_words')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def short_text(self, obj):
        return obj.text_to_read[:50] + '...' if len(obj.text_to_read) > 50 else obj.text_to_read
    short_text.short_description = 'Text to Read'


@admin.register(SpeakingResult)
class SpeakingResultAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'overall_score', 'avg_pronunciation', 'avg_accent', 'avg_accuracy', 'created_at']
    list_display_links = ['id', 'user']
    list_filter = ['created_at']
    search_fields = ['user__username', 'session_key']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Result Information', {
            'fields': ('user', 'session_key')
        }),
        ('Scores', {
            'fields': ('overall_score', 'avg_pronunciation', 'avg_accent', 'avg_accuracy')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )