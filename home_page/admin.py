# home_page/admin.py
from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from .models import StudentProfile


class StudentProfileInline(admin.StackedInline):
    model = StudentProfile
    can_delete = False
    extra = 0
    fields = ['institute', 'department', 'year', 
              'listening_completed', 'reading_completed', 
              'speaking_completed', 'writing_completed', 
              'pretest_completed', 'pretest_completed_at']


class CustomUserAdmin(UserAdmin):
    inlines = (StudentProfileInline,)
    list_display = ['username', 'email', 'first_name', 'last_name', 'is_staff', 'date_joined']
    list_filter = ['is_staff', 'is_superuser', 'is_active', 'groups']


# Re-register User with custom admin
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'institute', 'department', 'year', 
                    'listening_completed', 'reading_completed', 
                    'speaking_completed', 'writing_completed', 
                    'pretest_completed', 'pretest_completed_at']
    list_display_links = ['id', 'user']
    list_filter = ['institute', 'department', 'year', 
                   'listening_completed', 'reading_completed', 
                   'speaking_completed', 'writing_completed', 
                   'pretest_completed']
    search_fields = ['user__username', 'user__email', 'institute', 'department']
    readonly_fields = ['pretest_completed_at']
    list_editable = ['listening_completed', 'reading_completed', 
                     'speaking_completed', 'writing_completed', 
                     'pretest_completed']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Academic Information', {
            'fields': ('institute', 'department', 'year')
        }),
        ('Pretest Progress', {
            'fields': ('listening_completed', 'reading_completed', 
                      'speaking_completed', 'writing_completed',
                      'pretest_completed', 'pretest_completed_at'),
            'classes': ('collapse',)
        }),
    )