# reading/admin.py
from django.contrib import admin
from .models import Test, Question, ReadingUserResponse, ReadingResult


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1
    fields = ['order', 'question_text', 'option1', 'option2', 'option3', 'option4', 'correct_option']


@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'created_at', 'question_count']
    list_display_links = ['id', 'title']
    search_fields = ['title', 'description']
    inlines = [QuestionInline]
    
    fieldsets = (
        ('Test Information', {
            'fields': ('title', 'description', 'paragraph')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def question_count(self, obj):
        return obj.question_set.count()
    question_count.short_description = 'Questions'


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['id', 'order', 'test', 'short_question', 'correct_option']
    list_display_links = ['id', 'short_question']
    list_filter = ['test', 'correct_option']
    search_fields = ['question_text']
    list_editable = ['order']
    
    fieldsets = (
        ('Question Information', {
            'fields': ('test', 'order', 'question_text')
        }),
        ('Options', {
            'fields': ('option1', 'option2', 'option3', 'option4')
        }),
        ('Correct Answer', {
            'fields': ('correct_option',)
        }),
    )
    
    def short_question(self, obj):
        return obj.question_text[:50] + '...' if len(obj.question_text) > 50 else obj.question_text
    short_question.short_description = 'Question'


@admin.register(ReadingUserResponse)
class ReadingUserResponseAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'session_key', 'question', 'selected_option', 'created_at']
    list_display_links = ['id', 'user']
    list_filter = ['question__test', 'created_at']
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


@admin.register(ReadingResult)
class ReadingResultAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'test', 'score', 'total', 'percentage_display', 'level', 'created_at']
    list_display_links = ['id', 'user']
    list_filter = ['test', 'level', 'created_at']
    search_fields = ['user__username', 'session_key']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Result Information', {
            'fields': ('user', 'session_key', 'test')
        }),
        ('Score', {
            'fields': ('score', 'total', 'percentage', 'level', 'feedback')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def percentage_display(self, obj):
        return f"{obj.percentage:.1f}%"
    percentage_display.short_description = 'Percentage'