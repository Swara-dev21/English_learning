# learning/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import UserLearningProgress, DailyActivity, SavedVocabulary, UserCertificate

@admin.register(UserLearningProgress)
class UserLearningProgressAdmin(admin.ModelAdmin):
    list_display = ['user', 'level', 'current_day', 'completed_days_count', 'streak_days', 'completion_percentage', 'certificate_status']
    list_filter = ['level', 'certificate_issued', 'started_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['completed_days_count', 'completion_percentage']
    
    def completed_days_count(self, obj):
        return len(obj.completed_days)
    completed_days_count.short_description = 'Days Completed'
    
    def completion_percentage(self, obj):
        return f"{obj.completion_percentage():.1f}%"
    completion_percentage.short_description = 'Progress'
    
    def certificate_status(self, obj):
        if obj.certificate_issued:
            return format_html('<span style="color: green;">✓ Issued</span>')
        elif obj.is_completed():
            return format_html('<span style="color: orange;">⚠ Ready to Issue</span>')
        return format_html('<span style="color: gray;">Not Available</span>')
    certificate_status.short_description = 'Certificate'

@admin.register(DailyActivity)
class DailyActivityAdmin(admin.ModelAdmin):
    list_display = ['user', 'level', 'day_number', 'activity_type', 'completed', 'completed_at']
    list_filter = ['level', 'activity_type', 'completed', 'completed_at']
    search_fields = ['user__username']

@admin.register(SavedVocabulary)
class SavedVocabularyAdmin(admin.ModelAdmin):
    list_display = ['user', 'word', 'saved_at']
    list_filter = ['saved_at']
    search_fields = ['user__username', 'word']

@admin.register(UserCertificate)
class UserCertificateAdmin(admin.ModelAdmin):
    list_display = ['user', 'level', 'certificate_code', 'issued_at', 'downloaded', 'shared']
    list_filter = ['level', 'issued_at', 'downloaded', 'shared']
    search_fields = ['user__username', 'certificate_code']