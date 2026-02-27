from django.contrib import admin
from .models import TestSession, Student

class TestSessionInline(admin.TabularInline):
    """Shows a student's test history inside their profile page"""
    model = TestSession
    extra = 0
    fields = ['id', 'q1_score', 'q2_score', 'q3_score', 'q4_score', 'q5_score', 'get_level', 'completed_at']
    readonly_fields = fields
    can_delete = False
    
    def get_level(self, obj):
        return obj.level
    get_level.short_description = 'Performance Level'

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    """The main Student list view"""
    list_display = ('name', 'roll_number', 'get_latest_avg', 'test_count', 'created_at')
    search_fields = ('name', 'roll_number', 'email')
    inlines = [TestSessionInline]

    def get_latest_avg(self, obj):
        score = obj.get_latest_score()
        return f"{score:.1f}%" if score is not None else "No tests"
    get_latest_avg.short_description = 'Latest Score'

    def test_count(self, obj):
        return obj.test_sessions.count()
    test_count.short_description = 'Tests Taken'


@admin.register(TestSession)
class TestSessionAdmin(admin.ModelAdmin):
    """
    The main Results table showing Django users instead of Student model
    """
    list_display = (
        'id',
        'get_username',
        'completed_at',
        'overall_score_pct',
        'performance_level',
        'q1_pct',
        'q2_pct',
        'q3_pct',
        'q4_pct',
        'q5_pct',
        'mispronounced_words',
        'grammar_status',
    )
    
    list_filter = ('completed_at',)
    search_fields = ('id', 'user__username', 'user__email')
    
    ordering = ('id',)

    def get_username(self, obj):
        """Get username from the Django user field"""
        if obj.user:
            return obj.user.username
        return "Anonymous"
    get_username.short_description = 'Username'
    get_username.admin_order_field = 'user__username'

    def q1_pct(self, obj): 
        return f"{obj.q1_score:.1f}%"
    q1_pct.short_description = 'Word Pron.'

    def q2_pct(self, obj): 
        return f"{obj.q2_score:.1f}%"
    q2_pct.short_description = 'Sentence Rearrange'

    def q3_pct(self, obj): 
        return f"{obj.q3_score:.1f}%"
    q3_pct.short_description = 'Phrase Reading'

    def q4_pct(self, obj): 
        return f"{obj.q4_score:.1f}%"
    q4_pct.short_description = 'Sentence Reading'

    def q5_pct(self, obj): 
        return f"{obj.q5_score:.1f}%"
    q5_pct.short_description = 'Grammar'

    def overall_score_pct(self, obj):
        return f"{obj.get_average_score():.1f}%"
    overall_score_pct.short_description = 'Overall Score'

    def performance_level(self, obj):
        return obj.level
    performance_level.short_description = 'Level'
    
    def mispronounced_words(self, obj):
        """List words that were mispronounced in Q1"""
        expected = ['comfortable', 'vegetable', 'often', 'engineer', 'laboratory']
        mispronounced = []
        
        for i, word in enumerate(expected, 1):
            # Check if word was recorded and score is low
            word_field = f'q1_word{i}_recording'
            recording = getattr(obj, word_field, '')
            
            if recording:  # If they attempted the word
                score_field = f'q1_word{i}_score'
                score = getattr(obj, score_field, 20)  # Default to 20 if not set
                
                # If score is less than 15 out of 20 (75%), mark as mispronounced
                if score < 15:
                    mispronounced.append(word)
        
        return ", ".join(mispronounced) if mispronounced else "None"
    mispronounced_words.short_description = 'Mispronounced'
    
    def grammar_status(self, obj):
        """Show if Q5 grammar was correct (binary)"""
        if obj.q5_score >= 90:  # Near perfect
            return "✅ Correct"
        elif obj.q5_score > 0:
            return f"⚠️ {obj.q5_score:.0f}%"
        return "❌ Wrong"
    grammar_status.short_description = 'Grammar'