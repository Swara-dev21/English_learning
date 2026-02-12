from django.contrib import admin
from .models import ListeningTest, AudioQuestion, AnswerOption, UserResponse, TestResult

class AnswerOptionInline(admin.TabularInline):
    model = AnswerOption
    extra = 4

class AudioQuestionInline(admin.TabularInline):
    model = AudioQuestion
    extra = 0

@admin.register(ListeningTest)
class ListeningTestAdmin(admin.ModelAdmin):
    list_display = ['title', 'created_at', 'is_active']
    inlines = [AudioQuestionInline]

@admin.register(AudioQuestion)
class AudioQuestionAdmin(admin.ModelAdmin):
    list_display = ['order', 'question_text', 'test']
    list_filter = ['test']
    inlines = [AnswerOptionInline]

@admin.register(AnswerOption)
class AnswerOptionAdmin(admin.ModelAdmin):
    list_display = ['text', 'is_correct', 'question']
    list_filter = ['question__test', 'is_correct']

@admin.register(UserResponse)
class UserResponseAdmin(admin.ModelAdmin):
    list_display = ['session_key', 'question', 'selected_option', 'created_at']
    list_filter = ['question__test']

@admin.register(TestResult)
class TestResultAdmin(admin.ModelAdmin):
    list_display = ['session_key', 'test', 'score', 'total_questions', 'completed_at']
    list_filter = ['test']