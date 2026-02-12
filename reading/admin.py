from django.contrib import admin
from .models import Test, Question

# Inline for showing Questions within Test in admin
class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1  # Number of empty forms to display

# Admin for Test
@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_at')
    search_fields = ('title', 'description')
    inlines = [QuestionInline]

# Admin for Question
@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('question_text', 'test', 'correct_option')
    list_filter = ('test', 'correct_option')
    search_fields = ('question_text',)
