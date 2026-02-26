from django.contrib import admin
from .models import TestSession, Student

class TestSessionInline(admin.TabularInline):
    """Shows a student's test history inside their profile page"""
    model = TestSession
    extra = 0
    # 'id' shows the series 1, 2, 3...
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
    The main Results table.
    'id' creates the series from 1 to n.
    """
    list_display = (
        'id',                # This creates the 1, 2, 3... series
        'student_name', 
        'q1_pct',            
        'q2_pct',            
        'q3_pct',            
        'q4_pct',            
        'q5_pct',            
        'overall_score_pct', 
        'performance_level', # Shows Basic, Intermediate, or Advanced
        'completed_at'
    )
    
    list_filter = ('completed_at',)
    search_fields = ('id', 'student__name', 'student__roll_number')
    
    # Use 'id' for ascending order (1 to n) 
    # Use '-id' if you want the newest (n) at the top
    ordering = ('id',) 

    # --- Formatting Methods ---

    def student_name(self, obj):
        return obj.student.name if obj.student else "Anonymous"
    student_name.short_description = 'Username'

    def q1_pct(self, obj): return f"{obj.q1_score:.1f}%"
    q1_pct.short_description = 'Word Pron.'

    def q2_pct(self, obj): return f"{obj.q2_score:.1f}%"
    q2_pct.short_description = 'Sentence Rearrange'

    def q3_pct(self, obj): return f"{obj.q3_score:.1f}%"
    q3_pct.short_description = 'Phrase Reading'

    def q4_pct(self, obj): return f"{obj.q4_score:.1f}%"
    q4_pct.short_description = 'Sentence Reading'

    def q5_pct(self, obj): return f"{obj.q5_score:.1f}%"
    q5_pct.short_description = 'Grammar'

    def overall_score_pct(self, obj):
        return f"{obj.get_average_score():.1f}%"
    overall_score_pct.short_description = 'Overall Score'

    def performance_level(self, obj):
        # Pulls the @property 'level' from models.py
        return obj.level
    performance_level.short_description = 'Level'