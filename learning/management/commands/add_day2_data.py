from django.core.management.base import BaseCommand
from learning.models import (
    Lesson, ListeningActivity, SpeakingActivity, 
    ReadingActivity, WritingActivity, QuizQuestion
)

class Command(BaseCommand):
    help = 'Add Day 2 learning activities'

    def handle(self, *args, **options):
        
        # 1. Add Lesson Content
        lesson = Lesson.objects.create(
            level_type='beginner',
            day=2,
            title='Daily Routine - Morning to Evening',
            content='''
Today we will learn how to talk about daily routines. Daily routines are activities we do every day, like waking up, eating, studying, and sleeping.

Understanding and describing routines helps you:
- Talk about your day
- Understand others when they describe their day
- Build vocabulary for common actions
- Use present tense correctly

In English, we use Simple Present Tense to talk about daily routines because these are regular, repeated actions.
            ''',
            learning_objectives='Learn to describe morning routine, Understand daily activities vocabulary, Practice present tense for routines, Complete all LSRW activities',
            key_points='Use present tense for daily routines, Time expressions: morning, afternoon, evening, Common verbs: wake up, brush, eat, study, sleep'
        )
        self.stdout.write(self.style.SUCCESS('✓ Added Day 2 lesson'))

        # 2. Add Listening Activity
        listening = ListeningActivity.objects.create(
            level_type='beginner',
            day=2,
            sentence='Every morning, I wake up early, brush my teeth, and prepare myself for college.',
            meaning='The speaker is describing their daily morning routine.',
            test_question='What does the speaker do after waking up?',
            test_option_a='Goes to sleep',
            test_option_b='Brushes teeth',
            test_option_c='Watches TV',
            correct_answer='B'
        )
        self.stdout.write(self.style.SUCCESS('✓ Added Day 2 listening activity'))

        # 3. Add Speaking Activity
        speaking = SpeakingActivity.objects.create(
            level_type='beginner',
            day=2,
            sentence='In the evening, I usually complete my homework and then spend some time with my family.',
            sentence_parts='In the evening...,I usually complete my homework...,and then spend some time with my family.',
            test_task='Record yourself saying the full sentence'
        )
        self.stdout.write(self.style.SUCCESS('✓ Added Day 2 speaking activity'))

        # 4. Add Reading Activity
        reading = ReadingActivity.objects.create(
            level_type='beginner',
            day=2,
            paragraph='After attending all my classes, I return home, take some rest, and later revise what I learned during the day.',
            vocabulary='attending:going to,revise:study again',
            explanation='This is a daily routine described in present tense.',
            test_question='What does the person do after returning home?',
            test_option_a='Goes outside',
            test_option_b='Takes rest',
            test_option_c='Starts cooking',
            correct_answer='B'
        )
        self.stdout.write(self.style.SUCCESS('✓ Added Day 2 reading activity'))

        # 5. Add Writing Activity
        writing = WritingActivity.objects.create(
            level_type='beginner',
            day=2,
            structure='After coming home, I ______ and then I ______.',
            suggestions='eat food, take rest, study, watch TV, complete homework',
            example='After coming home, I take rest and then I study.',
            test_task='Write one sentence about your routine using the given structure'
        )
        self.stdout.write(self.style.SUCCESS('✓ Added Day 2 writing activity'))

        # 6. Add Additional Quiz Questions
        questions = [
            {
                'question': 'What tense is used to describe daily routines?',
                'a': 'Past Tense',
                'b': 'Present Tense',
                'c': 'Future Tense',
                'd': 'Continuous Tense',
                'correct': 'B',
                'explanation': 'We use Simple Present Tense for daily routines because they are regular, repeated actions.'
            },
            {
                'question': 'Which word means "to go to" or "to be present at"?',
                'a': 'Revise',
                'b': 'Attending',
                'c': 'Complete',
                'd': 'Prepare',
                'correct': 'B',
                'explanation': 'Attending means going to or being present at an event or place.'
            },
            {
                'question': 'What does "revise" mean in the reading passage?',
                'a': 'To write something new',
                'b': 'To study again',
                'c': 'To forget',
                'd': 'To ignore',
                'correct': 'B',
                'explanation': 'Revise means to study again or review what you have learned.'
            }
        ]
        
        for q in questions:
            QuizQuestion.objects.create(
                level_type='beginner',
                day=2,
                question_text=q['question'],
                option_a=q['a'],
                option_b=q['b'],
                option_c=q['c'],
                option_d=q['d'],
                correct_answer=q['correct'],
                explanation=q['explanation']
            )
        self.stdout.write(self.style.SUCCESS(f'✓ Added {len(questions)} quiz questions for Day 2'))

        self.stdout.write(self.style.SUCCESS('\n✅ Day 2 data added successfully!'))