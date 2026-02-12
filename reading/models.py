from django.db import models

class Test(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()

    # ✅ Static paragraph field for reading tests
    paragraph = models.TextField(
        default=(
            "Engineering life is not only about studying machines, drawings, or technical subjects. It is also about developing important skills that help students become successful professionals. Diploma engineering students learn how to solve problems, work in teams, and manage time effectively during their academic life. One of the most important skills for an engineering student is problem-solving. Engineers often face real-life challenges where they must think logically and find practical solutions. Along with this, communication skills play a key role. Engineers need to explain their ideas clearly to supervisors, co-workers, and clients. Good communication helps avoid mistakes and improves teamwork. Time management is another essential skill in engineering life. Students have to balance classes, practical work, assignments, and exams. Managing time properly reduces stress and improves performance. Teamwork is equally important because most engineering projects are completed in groups. Working with others teaches cooperation, responsibility, and respect for different opinions. Finally, engineering life also teaches discipline and professionalism. Following rules, maintaining safety, and being punctual are habits that prepare students for industry life. These skills not only help students during their studies but also make them confident and successful engineers in the future."
        )
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Question(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE)
    question_text = models.TextField()
    option1 = models.CharField(max_length=200)
    option2 = models.CharField(max_length=200)
    option3 = models.CharField(max_length=200, blank=True)
    option4 = models.CharField(max_length=200, blank=True)
    correct_option = models.IntegerField(choices=[
        (1, 'Option 1'), 
        (2, 'Option 2'), 
        (3, 'Option 3'), 
        (4, 'Option 4')
    ])
    
    def __str__(self):
        return f"Q: {self.question_text[:50]}..."
