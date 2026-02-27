from django.contrib import admin
from .models import StudentProfile

@admin.register(StudentProfile)
class StudentProgressAdmin(admin.ModelAdmin):
    verbose_name = "Student Progress"
    verbose_name_plural = "👨‍🎓 All Students Progress"
    
    list_display = [
        'student_name',
        'email',
        'institute',
        'department',
        'year',
        'tests_completed',
        'pretest_status',
        'listening_score',
        'reading_score',
        'speaking_score',
        'writing_score',
        'overall_score',
        'last_active',
    ]
    
    list_filter = ['institute', 'department', 'year', 'pretest_completed']
    search_fields = ['user__username', 'user__email', 'institute']
    
    def student_name(self, obj):
        return obj.user.username
    student_name.short_description = 'Student'
    
    def email(self, obj):
        return obj.user.email
    email.short_description = 'Email'
    
    def tests_completed(self, obj):
        completed = 0
        if obj.listening_completed: completed += 1
        if obj.reading_completed: completed += 1
        if obj.speaking_completed: completed += 1
        if obj.writing_completed: completed += 1
        return f"{completed}/4"
    tests_completed.short_description = 'Tests Done'
    
    def pretest_status(self, obj):
        return "✅ Completed" if obj.pretest_completed else "⏳ In Progress"
    pretest_status.short_description = 'Pretest Status'
    
    def listening_score(self, obj):
        from listening.models import TestResult
        result = TestResult.objects.filter(user=obj.user).first()
        return f"{result.percentage:.1f}%" if result else "—"
    listening_score.short_description = 'Listening'
    
    def reading_score(self, obj):
        from reading.models import ReadingResult
        result = ReadingResult.objects.filter(user=obj.user).first()
        return f"{result.percentage:.1f}%" if result else "—"
    reading_score.short_description = 'Reading'
    
    def speaking_score(self, obj):
        from speaking.models import TestSession
        session = TestSession.objects.filter(user=obj.user, completed_at__isnull=False).first()
        return f"{session.get_average_score():.1f}%" if session else "—"
    speaking_score.short_description = 'Speaking'
    
    def writing_score(self, obj):
        from writing.models import WritingTestResult
        result = WritingTestResult.objects.filter(user=obj.user).first()
        return f"{result.percentage:.1f}%" if result else "—"
    writing_score.short_description = 'Writing'
    
    def overall_score(self, obj):
        scores = []
        if obj.listening_completed:
            from listening.models import TestResult
            lr = TestResult.objects.filter(user=obj.user).first()
            if lr: scores.append(lr.percentage)
        
        if obj.reading_completed:
            from reading.models import ReadingResult
            rr = ReadingResult.objects.filter(user=obj.user).first()
            if rr: scores.append(rr.percentage)
        
        if obj.speaking_completed:
            from speaking.models import TestSession
            sr = TestSession.objects.filter(user=obj.user, completed_at__isnull=False).first()
            if sr: scores.append(sr.get_average_score())
        
        if obj.writing_completed:
            from writing.models import WritingTestResult
            wr = WritingTestResult.objects.filter(user=obj.user).first()
            if wr: scores.append(wr.percentage)
        
        if scores:
            avg = sum(scores) / len(scores)
            return f"{avg:.1f}%"
        return "—"
    overall_score.short_description = 'Overall'
    
    def last_active(self, obj):
        from listening.models import TestResult
        from reading.models import ReadingResult
        from speaking.models import TestSession
        from writing.models import WritingTestResult
        
        dates = []
        
        lr = TestResult.objects.filter(user=obj.user).order_by('-created_at').first()
        if lr: dates.append(lr.created_at)
        
        rr = ReadingResult.objects.filter(user=obj.user).order_by('-created_at').first()
        if rr: dates.append(rr.created_at)
        
        sr = TestSession.objects.filter(user=obj.user).order_by('-created_at').first()
        if sr: dates.append(sr.created_at)
        
        wr = WritingTestResult.objects.filter(user=obj.user).order_by('-created_at').first()
        if wr: dates.append(wr.created_at)
        
        if dates:
            latest = max(dates)
            return latest.strftime("%d %b %Y")
        return "Never"
    last_active.short_description = 'Last Active'