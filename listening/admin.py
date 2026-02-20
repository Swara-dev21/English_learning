# listening/admin.py
from django.contrib import admin
from .models import ListeningTest, AudioQuestion, AnswerOption, UserResponse, TestResult


class AnswerOptionInline(admin.TabularInline):
    """Inline admin for answer options"""
    model = AnswerOption
    extra = 4
    fields = ['text', 'is_correct']
    classes = ['collapse']


class AudioQuestionInline(admin.TabularInline):
    """Inline admin for audio questions"""
    model = AudioQuestion
    extra = 0
    fields = ['order', 'audio_filename', 'question_text', 'transcript']
    classes = ['collapse']
    show_change_link = True


@admin.register(ListeningTest)
class ListeningTestAdmin(admin.ModelAdmin):
    """Admin for Listening Test model"""
    list_display = ['id', 'title', 'created_at', 'is_active', 'question_count']
    list_display_links = ['id', 'title']
    list_filter = ['is_active', 'created_at']
    search_fields = ['title', 'description']
    list_editable = ['is_active']
    list_per_page = 25
    date_hierarchy = 'created_at'
    inlines = [AudioQuestionInline]
    
    fieldsets = (
        ('Test Information', {
            'fields': ('title', 'description', 'is_active'),
            'description': 'Basic information about the listening test'
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at']
    
    def question_count(self, obj):
        """Display number of questions in the test"""
        count = obj.questions.count()
        return f"{count} Question{'s' if count != 1 else ''}"
    question_count.short_description = 'Questions'
    question_count.admin_order_field = 'questions__count'


@admin.register(AudioQuestion)
class AudioQuestionAdmin(admin.ModelAdmin):
    """Admin for Audio Question model"""
    list_display = ['id', 'order', 'test', 'short_question', 'audio_filename', 'has_options']
    list_display_links = ['id', 'short_question']
    list_filter = ['test', 'test__is_active']
    search_fields = ['question_text', 'transcript']
    list_editable = ['order']
    list_per_page = 25
    inlines = [AnswerOptionInline]
    
    fieldsets = (
        ('Question Information', {
            'fields': ('test', 'order', 'question_text', 'explanation'),
            'description': 'Main question details'
        }),
        ('Audio & Transcript', {
            'fields': ('audio_filename', 'transcript'),
            'description': 'Audio file and transcript',
            'classes': ('wide',)
        }),
    )
    
    def short_question(self, obj):
        """Truncate long questions for display"""
        return obj.question_text[:50] + '...' if len(obj.question_text) > 50 else obj.question_text
    short_question.short_description = 'Question'
    
    def has_options(self, obj):
        """Check if question has answer options"""
        count = obj.options.count()
        return f"{count} option{'s' if count != 1 else ''}"
    has_options.short_description = 'Options'
    has_options.admin_order_field = 'options__count'


@admin.register(AnswerOption)
class AnswerOptionAdmin(admin.ModelAdmin):
    """Admin for Answer Option model"""
    list_display = ['id', 'question', 'short_text', 'is_correct', 'question_test']
    list_display_links = ['id', 'short_text']
    list_filter = ['is_correct', 'question__test']
    search_fields = ['text', 'question__question_text']
    list_editable = ['is_correct']
    list_per_page = 50
    
    fieldsets = (
        ('Option Information', {
            'fields': ('question', 'text', 'is_correct'),
            'description': 'Answer option details'
        }),
    )
    
    def short_text(self, obj):
        """Truncate long answers for display"""
        return obj.text[:50] + '...' if len(obj.text) > 50 else obj.text
    short_text.short_description = 'Answer Text'
    
    def question_test(self, obj):
        """Show which test the question belongs to"""
        return obj.question.test
    question_test.short_description = 'Test'
    question_test.admin_order_field = 'question__test'


@admin.register(UserResponse)
class UserResponseAdmin(admin.ModelAdmin):
    """Admin for User Response model"""
    list_display = ['id', 'user_info', 'question', 'selected_option_text', 'is_correct_answer', 'created_at']
    list_display_links = ['id', 'user_info']
    list_filter = ['question__test', 'created_at', 'selected_option__is_correct']
    search_fields = ['user__username', 'session_key', 'question__question_text']
    readonly_fields = ['created_at']
    list_per_page = 50
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'session_key'),
            'description': 'User who submitted the response'
        }),
        ('Response Details', {
            'fields': ('question', 'selected_option'),
            'description': 'Question and selected answer'
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def user_info(self, obj):
        """Display user or session info"""
        if obj.user:
            return f"{obj.user.username} (User)"
        elif obj.session_key:
            return f"{obj.session_key[:10]}... (Session)"
        return "Anonymous"
    user_info.short_description = 'User/Session'
    
    def selected_option_text(self, obj):
        """Display selected option text"""
        return obj.selected_option.text[:30] + '...' if len(obj.selected_option.text) > 30 else obj.selected_option.text
    selected_option_text.short_description = 'Selected Option'
    
    def is_correct_answer(self, obj):
        """Check if answer was correct"""
        return obj.selected_option.is_correct
    is_correct_answer.short_description = 'Correct?'
    is_correct_answer.boolean = True


@admin.register(TestResult)
class TestResultAdmin(admin.ModelAdmin):
    """Admin for Test Result model"""
    list_display = ['id', 'user_info', 'test', 'score_display', 'total_questions', 
                    'percentage_display', 'completed_at']  # Changed from created_at to completed_at
    list_display_links = ['id', 'user_info']
    list_filter = ['test', 'completed_at']  # Changed from created_at to completed_at
    search_fields = ['user__username', 'session_key', 'test__title']
    readonly_fields = ['completed_at', 'percentage']  # Changed from created_at to completed_at
    list_per_page = 50
    date_hierarchy = 'completed_at'  # Changed from created_at to completed_at
    
    fieldsets = (
        ('Result Information', {
            'fields': ('user', 'session_key', 'test'),
            'description': 'Test and user information'
        }),
        ('Score Details', {
            'fields': ('score', 'total_questions', 'percentage'),
            'description': 'Scoring information',
            'classes': ('wide',)
        }),
        ('Metadata', {
            'fields': ('completed_at',),  # Changed from created_at to completed_at
            'classes': ('collapse',)
        }),
    )
    
    def user_info(self, obj):
        """Display user or session info"""
        if obj.user:
            return f"{obj.user.username} (User)"
        elif obj.session_key:
            return f"{obj.session_key[:10]}... (Session)"
        return "Anonymous"
    user_info.short_description = 'User/Session'
    
    def score_display(self, obj):
        """Display score with emoji indicator"""
        if obj.score == obj.total_questions:
            return f"✅ {obj.score}/{obj.total_questions}"
        elif obj.score >= obj.total_questions * 0.7:
            return f"👍 {obj.score}/{obj.total_questions}"
        else:
            return f"📝 {obj.score}/{obj.total_questions}"
    score_display.short_description = 'Score'
    
    def percentage_display(self, obj):
        """Display formatted percentage"""
        return f"{obj.percentage:.1f}%"
    percentage_display.short_description = 'Percentage'
    percentage_display.admin_order_field = 'percentage'
    
    def completed_at(self, obj):
        """Display completed timestamp"""
        return obj.completed_at  # Changed from created_at to completed_at
    completed_at.short_description = 'Completed'
    completed_at.admin_order_field = 'completed_at'  # Changed from created_at to completed_at