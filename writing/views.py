from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import re
import json
from .models import WritingTest, WritingQuestion, WritingResponse, WritingTestResult

def get_session_key(request):
    """Get or create session key for anonymous users"""
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key

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

def writing_test_home(request, test_id):
    """Writing test introduction page"""
    test = get_object_or_404(WritingTest, id=test_id, is_active=True)
    return render(request, 'writing/writing_home.html', {'test': test})

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
    """Grade picture description question"""
    score = 0
    feedback = []
    
    # Check sentence count
    sentence_count = count_sentences(user_answer)
    if sentence_count >= question.min_sentences:
        score += 20
        feedback.append("✓ Minimum sentences met")
    else:
        feedback.append(f"✗ Need at least {question.min_sentences} sentences, you have {sentence_count}")
    
    # Check word count
    word_count = count_words(user_answer)
    if question.min_words <= word_count <= question.max_words:
        score += 20
        feedback.append("✓ Word count appropriate")
    else:
        feedback.append(f"✗ Word count should be {question.min_words}-{question.max_words}, you have {word_count}")
    
    # Check keywords
    missing_keywords = []
    user_answer_lower = user_answer.lower()
    for keyword in question.required_keywords:
        if keyword.lower() not in user_answer_lower:
            missing_keywords.append(keyword)
    
    if len(missing_keywords) == 0:
        score += 20
        feedback.append("✓ All keywords included")
    else:
        feedback.append(f"✗ Missing keywords: {', '.join(missing_keywords[:3])}")
        if len(missing_keywords) > 3:
            feedback.append(f"  ... and {len(missing_keywords)-3} more")
    
    # Check spelling
    spelling_errors = check_spelling(user_answer)
    if len(spelling_errors) == 0:
        score += 20
        feedback.append("✓ No spelling errors")
    else:
        feedback.append(f"✗ Potential spelling errors: {', '.join(spelling_errors[:3])}")
    
    # Manual review needed
    needs_manual_review = True
    score += 20  # Reserve 20 points for manual review
    feedback.append("✓ Submitted for review")
    
    return {
        'score': min(score, 100),
        'feedback': feedback,
        'needs_manual_review': needs_manual_review,
        'auto_score': score - 20,
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

@require_POST
def save_answer(request, test_id, question_number):
    """Save user's answer with auto-grading"""
    test = get_object_or_404(WritingTest, id=test_id)
    question = get_object_or_404(WritingQuestion, test=test, order=question_number)
    
    user_answer = request.POST.get('user_answer', '').strip()
    
    if not user_answer:
        return JsonResponse({'error': 'No answer provided'}, status=400)
    
    # Grade the answer (returns 0-100 score)
    grading_result = grade_writing_response(user_answer, question)
    
    # Convert 100-point score to 1-point score
    one_point_score = convert_to_one_point_score(grading_result['score'])
    
    # Save the response
    session_key = get_session_key(request)
    
    # Delete any previous response for this question
    WritingResponse.objects.filter(session_key=session_key, question=question).delete()
    
    # Create new response
    WritingResponse.objects.create(
        session_key=session_key,
        question=question,
        user_answer=user_answer,
        score=grading_result['score'],  # Keep 100-point score for feedback
        feedback=grading_result['feedback'],
        needs_manual_review=grading_result.get('needs_manual_review', False)
    )
    
    return JsonResponse({
        'success': True,
        'score': grading_result['score'],  # Return 100-point score for display
        'one_point_score': one_point_score,  # Add 1-point score
        'feedback': grading_result['feedback'],
        'needs_manual_review': grading_result.get('needs_manual_review', False)
    })

def submit_writing_test(request, test_id):
    """Submit the entire writing test and calculate results"""
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
    
    # Save test result (out of 5)
    test_result = WritingTestResult.objects.create(
        session_key=session_key,
        test=test,
        total_score=total_one_point_score,
        max_score=5  # Always 5
    )
    
    return redirect('writing:writing_results', result_id=test_result.id)

def writing_results(request, result_id):
    """Display writing test results"""
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
    
    # Prepare question data for template (only wrong answers)
    question_data = []
    for question in questions:
        response = responses_by_question.get(question.order)
        # Only include questions that were answered incorrectly (score < 100)
        if response and response.score < 100:
            question_data.append({
                'question': question,
                'response': response,
                'has_response': True,
                'score_100': response.score,  # Keep the 100-point score
            })
    
    context = {
        'result': result,
        'question_data': question_data,
        'percentage': result.percentage(),
        'wrong_answers_count': len(question_data),  # Count of wrong answers
    }
    
    return render(request, 'writing/writing_results.html', context)