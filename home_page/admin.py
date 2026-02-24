# home_page/admin.py
from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from django.urls import path
from django.shortcuts import redirect
from django.contrib import messages
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
    
    # ===== CUSTOM URLS FOR EXPORT BUTTON =====
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('export-results/', self.admin_site.admin_view(self.export_results_view), name='export_results'),
        ]
        return custom_urls + urls
    
    def export_results_view(self, request):
        """Redirect to the main export view"""
        return redirect('home_page:export_results')
    
    # ===== CUSTOM BUTTON IN ADMIN =====
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['export_button'] = True
        return super().changelist_view(request, extra_context=extra_context)
    
    # ===== OPTIONAL: Add export button to top of admin =====
    class Media:
        css = {
            'all': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css',)
        }