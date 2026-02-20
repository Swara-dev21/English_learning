# writing/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from home_page.models import StudentProfile
from home_page.decorators import pretest_access_required, ajax_pretest_check
from textblob import TextBlob
import re
import json
from .models import WritingTest, WritingQuestion, WritingResponse, WritingTestResult

def get_session_key(request):
    """Get or create session key for anonymous users"""
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key

@login_required
@pretest_access_required('writing')
def start_writing_test(request, test_id):
    """Start writing test directly"""
    writing_test = get_object_or_404(WritingTest, id=test_id, is_active=True)
    
    # Get session key
    session_key = get_session_key(request)
    
    # Delete any previous responses for this session
    WritingResponse.objects.filter(session_key=session_key, question__test=writing_test).delete()
    
    # Delete any previous test results for this session
    WritingTestResult.objects.filter(session_key=session_key, test=writing_test).delete()
    
    # Redirect to first question
    return redirect('writing:writing_question', test_id=writing_test.id, question_number=1)

@login_required
@pretest_access_required('writing')
def writing_test_home(request, test_id):
    """Writing test introduction page"""
    test = get_object_or_404(WritingTest, id=test_id, is_active=True)
    return render(request, 'writing/writing_home.html', {'test': test})

@login_required
@pretest_access_required('writing')
def writing_question(request, test_id, question_number):
    """Display a single writing question"""
    test = get_object_or_404(WritingTest, id=test_id, is_active=True)
    
    # Get the question
    try:
        question = WritingQuestion.objects.get(test=test, order=question_number)
    except WritingQuestion.DoesNotExist:
        return redirect('writing:writing_test_home', test_id=test.id)
    
    # Get total questions count
    total_questions = test.questions.count()
    
    # Check if we have a previous answer for this question
    session_key = get_session_key(request)
    previous_response = WritingResponse.objects.filter(
        session_key=session_key, 
        question=question
    ).first()
    
    # Get next and previous question numbers
    next_question = question_number + 1 if question_number < total_questions else None
    prev_question = question_number - 1 if question_number > 1 else None
    
    # Calculate progress
    progress_percentage = int((question_number / total_questions) * 100)
    
    context = {
        'test': test,
        'question': question,
        'question_number': question_number,
        'total_questions': total_questions,
        'progress_percentage': progress_percentage,
        'next_question': next_question,
        'prev_question': prev_question,
        'previous_answer': previous_response.user_answer if previous_response else '',
    }
    
    return render(request, 'writing/writing_question.html', context)

# ===== GRADING FUNCTIONS =====

def count_sentences(text):
    """Count sentences in text"""
    # Split by sentence endings
    sentences = re.split(r'[.!?]+', text)
    # Filter out empty strings
    sentences = [s.strip() for s in sentences if s.strip()]
    return len(sentences)

def count_words(text):
    """Count words in text"""
    words = text.split()
    return len(words)

def check_spelling(text):
    """Basic spelling check - returns list of potential errors"""
    common_words = {
        'the', 'a', 'an', 'and', 'but', 'or', 'for', 'nor', 'on', 'at', 'to', 
        'from', 'by', 'with', 'about', 'against', 'between', 'into', 'through',
        'during', 'before', 'after', 'above', 'below', 'of', 'in', 'out', 'over',
        'under', 'again', 'further', 'then', 'once', 'here', 'there', 'when',
        'where', 'why', 'how', 'all', 'any', 'both', 'each', 'few', 'more',
        'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own',
        'same', 'so', 'than', 'too', 'very', 'can', 'will', 'just', 'don',
        'should', 'now', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'my',
        'your', 'his', 'her', 'its', 'our', 'their', 'is', 'am', 'are', 'was',
        'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does',
        'did', 'doing', 'would', 'could', 'should', 'may', 'might', 'must',
        'shall', 'will', 'boy', 'football', 'park', 'playing', 'game', 'eat',
        'breakfast', 'morning', 'saw', 'elephant', 'zoo', 'like', 'apples'
    }
    
    words = text.lower().split()
    errors = []
    for word in words:
        # Clean the word
        word_clean = re.sub(r'[^\w\']', '', word)
        if word_clean and word_clean not in common_words and len(word_clean) > 2:
            if not any(word_clean.startswith(prefix) for prefix in ['i\'', 'you\'', 'he\'', 'she\'', 'it\'', 'we\'', 'they\'']):
                errors.append(word_clean)
    
    return errors[:5]

def grade_picture_description(user_answer, question):
    """
    Grade picture description for 1 mark.
    Returns: 1 (pass) or 0 (fail) with detailed grammar feedback
    """
    
    feedback = []
    grammar_mistakes = []
    user_answer_lower = user_answer.lower().strip()
    
    # ===== WORD COUNT CHECK =====
    word_count = count_words(user_answer)
    if word_count < question.min_words:
        grammar_mistakes.append(f"❌ Too short: Write at least {question.min_words} words (you wrote {word_count})")
    
    # ===== SENTENCE COUNT CHECK =====
    sentence_count = count_sentences(user_answer)
    if sentence_count < question.min_sentences:
        grammar_mistakes.append(f"❌ Need {question.min_sentences} complete sentences (you wrote {sentence_count})")
    
    # ===== KEYWORD CHECK =====
    required_keywords = question.required_keywords  # ['boy', 'football', 'park', 'playing', 'game']
    missing_keywords = []
    
    for keyword in required_keywords:
        if keyword.lower() not in user_answer_lower:
            missing_keywords.append(keyword)
    
    if missing_keywords:
        grammar_mistakes.append(f"❌ Missing keywords: {', '.join(missing_keywords)}")
    
    # ===== GRAMMAR CHECKS USING TEXTBLOB =====
    blob = TextBlob(user_answer)
    
    # Check for missing auxiliary verb (is/are)
    words = [word.lower() for word in blob.words]
    if 'playing' in words and 'is' not in words and 'are' not in words:
        grammar_mistakes.append("❌ Grammar: Use 'is playing' not just 'playing' (e.g., 'The boy is playing')")
    
    if 'enjoying' in words and 'is' not in words and 'are' not in words:
        grammar_mistakes.append("❌ Grammar: Use 'is enjoying' not just 'enjoying'")
    
    # Check parts of speech
    has_noun = any(tag.startswith('NN') for word, tag in blob.tags)  # Noun
    has_verb = any(tag.startswith('VB') for word, tag in blob.tags)  # Verb
    
    if not has_noun:
        grammar_mistakes.append("❌ Grammar: Missing a subject (who is doing the action?)")
    if not has_verb:
        grammar_mistakes.append("❌ Grammar: Missing a verb (what action is happening?)")
    
    # Check for article usage
    if 'boy' in words and 'the' not in words and 'a' not in words:
        grammar_mistakes.append("❌ Grammar: Use article with 'boy' (e.g., 'The boy' or 'A boy')")
    
    # Check capitalization
    if user_answer and user_answer[0].isupper() == False:
        grammar_mistakes.append("❌ Capitalization: Start sentence with capital letter")
    
    # Check punctuation
    if user_answer and user_answer[-1] not in ['.', '!', '?']:
        grammar_mistakes.append("❌ Punctuation: End sentence with . or !")
    
    # ===== DECISION =====
    if len(grammar_mistakes) == 0:
        # Perfect answer - 1 mark
        return {
            'score': 100,  # 100 for display (will be converted to 1 later)
            'feedback': ["✅ Perfect! Your description is grammatically correct!"],
            'needs_manual_review': False
        }
    else:
        # Failed - 0 marks with detailed feedback
        return {
            'score': 0,
            'feedback': [
                "❌ Your answer has grammar mistakes:",
                *grammar_mistakes[:5],  # Show top 5 mistakes
                "",
                "💡 Example of correct answer:",
                "The boy is playing football in the park. He is enjoying the game."
            ],
            'needs_manual_review': False
        }
    

def grade_auto_check_question(user_answer, question):
    """Grade questions with exact/multiple answer checking"""
    user_answer_clean = user_answer.strip().lower()
    
    # Check main correct answer
    if user_answer_clean == question.correct_answer.lower().strip():
        return {
            'score': 100,
            'feedback': ["✓ Correct answer!"],
            'needs_manual_review': False,
        }
    
    # Check acceptable answers
    for acceptable in question.acceptable_answers:
        if user_answer_clean == acceptable.lower().strip():
            return {
                'score': 100,
                'feedback': ["✓ Correct answer!"],
                'needs_manual_review': False,
            }
    
    # For dictation, allow some flexibility
    if question.question_type == 'dictation':
        # Remove punctuation and extra spaces for comparison
        user_clean = re.sub(r'[^\w\s]', '', user_answer).lower().strip()
        correct_clean = re.sub(r'[^\w\s]', '', question.correct_answer).lower().strip()
        
        if user_clean == correct_clean:
            return {
                'score': 100,
                'feedback': ["✓ Correct! (minor punctuation differences ignored)"],
                'needs_manual_review': False,
            }
        
        # Check if at least 80% of words match
        user_words = set(user_clean.split())
        correct_words = set(correct_clean.split())
        common_words = user_words.intersection(correct_words)
        
        if len(common_words) / len(correct_words) >= 0.8:
            return {
                'score': 80,
                'feedback': [f"✓ Almost correct! You got {len(common_words)} out of {len(correct_words)} words right."],
                'needs_manual_review': False,
            }
    
    return {
        'score': 0,
        'feedback': ["✗ Incorrect answer. Please review the question."],
        'needs_manual_review': False,
    }

def grade_writing_response(user_answer, question):
    """Main grading function that routes to specific grader"""
    if question.question_type == 'picture_description':
        return grade_picture_description(user_answer, question)
    else:
        return grade_auto_check_question(user_answer, question)

def convert_to_one_point_score(score_100):
    """Convert 100-point score to 1-point score (for 5 questions)"""
    if score_100 == 100:
        return 1
    elif score_100 >= 50:
        return 0.5
    else:
        return 0

@login_required
@ajax_pretest_check('writing')
@require_POST
def save_answer(request, test_id, question_number):
    """Save user's answer with auto-grading"""
    test = get_object_or_404(WritingTest, id=test_id)
    question = get_object_or_404(WritingQuestion, test=test, order=question_number)
    
    user_answer = request.POST.get('user_answer', '').strip()
    
    if not user_answer:
        return JsonResponse({'error': 'No answer provided'}, status=400)
    
    # Grade the answer
    grading_result = grade_writing_response(user_answer, question)
    
    # Convert 100-point score to 1-point score
    one_point_score = convert_to_one_point_score(grading_result['score'])
    
    # Save the response
    session_key = get_session_key(request)
    
    # Delete any previous response for this question
    WritingResponse.objects.filter(session_key=session_key, question=question).delete()
    
    # Create new response - STORE FEEDBACK IN DATABASE
    response = WritingResponse.objects.create(
        session_key=session_key,
        question=question,
        user_answer=user_answer,
        score=grading_result['score'],
        feedback=grading_result['feedback'],  # Save feedback in database
        needs_manual_review=grading_result.get('needs_manual_review', False)
    )
    
    # Return ONLY success confirmation - NO FEEDBACK during test
    return JsonResponse({
        'success': True,
        'score': grading_result['score'],
        'one_point_score': one_point_score,
        # NO feedback field here!
    })

@login_required
@pretest_access_required('writing')
def submit_writing_test(request, test_id):
    """Submit the entire writing test and calculate results - FINAL SWITCH"""
    if request.method != 'POST':
        return redirect('writing:writing_question', test_id=test_id, question_number=1)
    
    test = get_object_or_404(WritingTest, id=test_id)
    session_key = get_session_key(request)
    
    # Get all responses for this test
    responses = WritingResponse.objects.filter(
        session_key=session_key, 
        question__test=test
    )
    
    # Calculate total score out of 5
    total_one_point_score = 0
    for response in responses:
        total_one_point_score += convert_to_one_point_score(response.score)

    percentage = (total_one_point_score / 5) * 100
    
    # ✅ APPLY YOUR 3-LEVEL LOGIC HERE (0-40% Basic, 40-80% Intermediate, 80-100% Advanced)
    if percentage < 40:
        level = "Basic"
    elif percentage < 80:
        level = "Intermediate"
    else:
        level = "Advanced"
    
    # Save test result (out of 5)
    test_result = WritingTestResult.objects.create(
        session_key=session_key,
        test=test,
        total_score=total_one_point_score,
        max_score=5,
        user=request.user,
        level = level
    )
    
    # ===== FINAL SWITCH - MARK WRITING AS COMPLETED =====
    profile = StudentProfile.objects.get(user=request.user)
    profile.writing_completed = True
    
    # Check if this was the last test
    if all([profile.listening_completed, profile.reading_completed, 
            profile.speaking_completed, profile.writing_completed]):
        profile.pretest_completed = True
        profile.pretest_completed_at = timezone.now()
        profile.save()
        messages.success(request, "🎉 Congratulations! You have completed all pretest sections!")
    else:
        profile.update_pretest_status()
        messages.success(request, "Writing test completed successfully!")
    # ==================================================
    
    return redirect('writing:writing_results', result_id=test_result.id)

@login_required
def writing_results(request, result_id):
    """Display writing test results with feedback"""
    result = get_object_or_404(WritingTestResult, id=result_id)
    
    # Get all responses for this test
    responses = WritingResponse.objects.filter(
        session_key=result.session_key,
        question__test=result.test
    ).select_related('question').order_by('question__order')
    
    # Create a dictionary of responses by question order
    responses_by_question = {r.question.order: r for r in responses}
    
    # Get all questions
    questions = WritingQuestion.objects.filter(test=result.test).order_by('order')
    
    # Prepare question data with feedback
    question_data = []
    for question in questions:
        response = responses_by_question.get(question.order)
        if response:
            question_data.append({
                'question': question,
                'response': response,
                'user_answer': response.user_answer,
                'score_100': response.score,
                'feedback': response.feedback,  # Get feedback from database
                'is_correct': response.score == 100
            })
    
    context = {
        'result': result,
        'question_data': question_data,
        'percentage': result.percentage, 
        'total_score': result.total_score,
        'max_score': result.max_score,
        'wrong_answers_count': len([q for q in question_data if not q['is_correct']]),
        'level' : result.level, 
    }
    
    return render(request, 'writing/writing_results.html', context)