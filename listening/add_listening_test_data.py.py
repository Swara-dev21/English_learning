# Correct script for your current models
from listening.models import ListeningTest, AudioQuestion, AnswerOption

print("=" * 60)
print("🎧 ADDING LISTENING TEST DATA")
print("=" * 60)

# Delete existing test
test = ListeningTest.objects.filter(title="English Listening Test - Grammar").first()
if test:
    # Delete related questions and options first (cascade should handle this, but being explicit)
    AudioQuestion.objects.filter(test=test).delete()
    test.delete()
    print("🗑️  Removed existing test and related data")

# Create test
test = ListeningTest.objects.create(
    title="English Listening Test - Grammar",
    description="Test your grammar and listening skills with 5 questions",
    is_active=True
)
print(f"✅ Created test: {test.title} (ID: {test.id})")

# ============================================
# CREATE QUESTIONS AND ANSWER OPTIONS
# ============================================
print("\n" + "-" * 40)
print("CREATING QUESTIONS")
print("-" * 40)

# Question 1
q1 = AudioQuestion.objects.create(
    test=test,
    order=1,
    audio_filename="sarah_story.mp3",
    transcript="Hi, my name is Sarah. I work at a bookstore downtown. I usually start work at 9 AM, but tomorrow I need to come in early at 8:30 because we're receiving a big shipment of new books. I'm really excited because we're getting the new mystery novels from my favorite author. After work, I'm meeting my friend Mark for coffee at The Daily Grind café around 5:30 PM.",
    question_text="What time does Sarah usually start work?",
    explanation="Sarah mentions she usually starts work at 9 AM."
)
AnswerOption.objects.create(question=q1, text="8:00 AM", is_correct=False)
AnswerOption.objects.create(question=q1, text="9:00 AM", is_correct=True)
AnswerOption.objects.create(question=q1, text="8:30 AM", is_correct=False)
AnswerOption.objects.create(question=q1, text="9:30 AM", is_correct=False)
print(f"✅ Q1: {q1.question_text}")

# Question 2
q2 = AudioQuestion.objects.create(
    test=test,
    order=2,
    audio_filename="sarah_story.mp3",
    transcript="",
    question_text="Why does Sarah need to come in early tomorrow?",
    explanation="She needs to come early because of a big shipment of new books."
)
AnswerOption.objects.create(question=q2, text="For a meeting", is_correct=False)
AnswerOption.objects.create(question=q2, text="Because of a big shipment", is_correct=True)
AnswerOption.objects.create(question=q2, text="To meet a friend", is_correct=False)
AnswerOption.objects.create(question=q2, text="For training", is_correct=False)
print(f"✅ Q2: {q2.question_text}")

# Question 3
q3 = AudioQuestion.objects.create(
    test=test,
    order=3,
    audio_filename="sarah_story.mp3",
    transcript="",
    question_text="How does Sarah feel about the new shipment?",
    explanation="She says she's really excited about the new books."
)
AnswerOption.objects.create(question=q3, text="Annoyed", is_correct=False)
AnswerOption.objects.create(question=q3, text="Worried", is_correct=False)
AnswerOption.objects.create(question=q3, text="Excited", is_correct=True)
AnswerOption.objects.create(question=q3, text="Indifferent", is_correct=False)
print(f"✅ Q3: {q3.question_text}")

# Question 4
q4 = AudioQuestion.objects.create(
    test=test,
    order=4,
    audio_filename="sarah_story.mp3",
    transcript="",
    question_text="What type of books is Sarah excited about?",
    explanation="She's excited about the new mystery novels from her favorite author."
)
AnswerOption.objects.create(question=q4, text="Science fiction", is_correct=False)
AnswerOption.objects.create(question=q4, text="Romance novels", is_correct=False)
AnswerOption.objects.create(question=q4, text="Mystery novels", is_correct=True)
AnswerOption.objects.create(question=q4, text="Biographies", is_correct=False)
print(f"✅ Q4: {q4.question_text}")

# Question 5
q5 = AudioQuestion.objects.create(
    test=test,
    order=5,
    audio_filename="sarah_story.mp3",
    transcript="",
    question_text="Where is Sarah meeting her friend after work?",
    explanation="She's meeting her friend Mark at The Daily Grind café."
)
AnswerOption.objects.create(question=q5, text="At a restaurant", is_correct=False)
AnswerOption.objects.create(question=q5, text="At a bookstore", is_correct=False)
AnswerOption.objects.create(question=q5, text="At a café called The Daily Grind", is_correct=True)
AnswerOption.objects.create(question=q5, text="At home", is_correct=False)
print(f"✅ Q5: {q5.question_text}")

# ============================================
# SUMMARY
# ============================================
print("\n" + "=" * 60)
print("🎉 LISTENING TEST DATA ADDED SUCCESSFULLY!")
print("=" * 60)
print(f"📊 Test: {test.title} (ID: {test.id})")
print(f"📝 Total Questions: {AudioQuestion.objects.filter(test=test).count()}/5")
total_options = AnswerOption.objects.filter(question__test=test).count()
print(f"🔘 Total Answer Options: {total_options} (4 per question)")
print("=" * 60)