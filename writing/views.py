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
from spellchecker import SpellChecker
import nltk
import re
import json
import string
import traceback
from .models import WritingTest, WritingQuestion, WritingResponse, WritingTestResult

# Initialize tools once
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

# Try to import language_tool, but provide fallback if Java not available
try:
    import language_tool_python
    LANGUAGE_TOOL_AVAILABLE = True
    print("✅ LanguageTool imported successfully")
except (ImportError, ModuleNotFoundError) as e:
    LANGUAGE_TOOL_AVAILABLE = False
    print(f"⚠️ LanguageTool not available: {e}")
    print("⚠️ Grammar checking will use basic pattern matching instead")

# Lazy loading for grammar tool with fallback
_grammar_tool = None
def get_grammar_tool():
    global _grammar_tool
    if not LANGUAGE_TOOL_AVAILABLE:
        return None
    if _grammar_tool is None:
        try:
            _grammar_tool = language_tool_python.LanguageTool('en-US')
        except Exception as e:
            print(f"⚠️ Failed to initialize LanguageTool: {e}")
            return None
    return _grammar_tool

# Lazy loading for spell checker
_spell_checker = None
def get_spell_checker():
    global _spell_checker
    if _spell_checker is None:
        _spell_checker = SpellChecker()
    return _spell_checker

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
    if not request.session.session_key:
        request.session.create()
    session_key = request.session.session_key
    
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
    previous_response = WritingResponse.objects.filter(
        session_key=session_key, 
        question=question
    ).first()
    
    # Get next and previous question numbers
    next_question = question_number + 1 if question_number < total_questions else None
    prev_question = question_number - 1 if question_number > 1 else None
    
    # Calculate progress
    progress_percentage = int((question_number / total_questions) * 100)
    
    # Get ALL answered questions for this user/session
    # Get all responses for this test
    user_responses = WritingResponse.objects.filter(
        session_key=session_key,
        question__test=test
    ).values_list('question__order', flat=True)
    
    # Convert to list of integers
    answered_questions = list(user_responses)
    
    # Filter to ensure valid question numbers
    answered_questions = [q_num for q_num in answered_questions if 1 <= q_num <= total_questions]

    context = {
        'test': test,
        'question': question,
        'question_number': question_number,
        'total_questions': total_questions,
        'progress_percentage': progress_percentage,
        'next_question': next_question,
        'prev_question': prev_question,
        'previous_answer': previous_response.user_answer if previous_response else '',
        'answered_questions': answered_questions,
    }

    return render(request, 'writing/writing_question.html', context)


# ===== GRADING FUNCTIONS FOR THE 5 QUESTIONS =====

def count_sentences(text):
    """Count sentences in text"""
    from nltk.tokenize import sent_tokenize
    try:
        sentences = sent_tokenize(text)
        return len([s for s in sentences if s.strip()])
    except:
        # Fallback: count by punctuation
        return len([s for s in text.split('.') if s.strip()])

def count_words(text):
    """Count words in text"""
    words = text.split()
    return len(words)


def grade_fill_blanks(user_answer, question):
    """Grade Q1: Fill in the blanks (grammatical accuracy)"""
    # Expected format: "goes, are, a" or "goes,are,a"
    user_answer = user_answer.strip().lower()
    
    # Clean up the answer - remove spaces and split
    user_parts = [part.strip() for part in user_answer.replace(',', ' ').split() if part.strip()]
    
    # Expected answers from database (store as "goes, are, a")
    expected_parts = [part.strip().lower() for part in question.correct_answer.split(',')]
    
    correct_count = 0
    feedback = []
    
    for i, expected in enumerate(expected_parts):
        if i < len(user_parts):
            if user_parts[i] == expected:
                correct_count += 1
                # Don't add feedback for correct answers - we only show errors
            else:
                feedback.append(f"❌ Blank {i+1}: Expected '{expected}', you wrote '{user_parts[i]}'")
        else:
            feedback.append(f"❌ Blank {i+1}: Missing answer (expected '{expected}')")
    
    score = (correct_count / len(expected_parts)) * 100
    
    return {
        'score': round(score, 2),
        'feedback': feedback,  # Only errors, no correct items
        'needs_manual_review': False
    }


def grade_sentence_order(user_answer, question):
    """Grade Q2: Arrange sentences in logical order"""
    # Expected format: "C, B, A" or "CBA"
    user_answer = user_answer.strip().upper().replace(' ', '').replace(',', '')
    
    # Expected order from database (store as "C,B,A")
    expected = question.correct_answer.strip().upper().replace(' ', '').replace(',', '')
    
    if user_answer == expected:
        return {
            'score': 100,
            'feedback': [],  # No errors to show
            'needs_manual_review': False
        }
    
    # Check if user reversed it
    if user_answer == expected[::-1]:
        return {
            'score': 50,
            'feedback': ["⚠️ You have the correct order but reversed. The correct order is C, B, A"],
            'needs_manual_review': False
        }
    
    # Check partial correctness - first sentence
    if user_answer and len(user_answer) > 0 and user_answer[0] == expected[0]:
        return {
            'score': 33,
            'feedback': ["❌ Only the first sentence (C) is correct. Correct order: C, B, A"],
            'needs_manual_review': False
        }
    
    return {
        'score': 0,
        'feedback': ["❌ Incorrect order. The correct order is C, B, A"],
        'needs_manual_review': False
    }


def grade_rewrite_sentence(user_answer, question):
    """Grade Q3: Rewrite sentence with correct spelling and punctuation"""
    spell = get_spell_checker()
    
    user_text = user_answer.strip()
    expected = "Communication skills are important; however, students often ignore punctuation, grammar, and clarity."
    
    feedback = []
    score = 0
    mistake_count = 0
    
    # Create translator for removing punctuation
    translator = str.maketrans('', '', string.punctuation)
    
    # Common words that should never be flagged as spelling errors
    common_words = ['communication', 'skills', 'important', 'however', 'students', 'often', 
                   'ignore', 'punctuation', 'grammar', 'clarity', 'are', 'and', 'the', 'to']
    
    # 1. Spelling Check (40 points) - IMPROVED
    words = user_text.split()
    misspelled = []
    
    for word in words:
        # Clean the word - remove punctuation and convert to lowercase
        clean_word = word.translate(translator).lower()
        
        # Skip if it's a common word we know is correct
        if clean_word in common_words:
            continue
            
        # Skip if it's a single character or empty
        if len(clean_word) <= 1:
            continue
            
        # Check if word is in dictionary
        if clean_word not in spell:
            misspelled.append(word)  # Show original word with context
    
    if len(misspelled) == 0:
        score += 40
    else:
        # Show unique misspelled words (limit to 3)
        unique_errors = list(set([w.lower() for w in misspelled]))[:3]
        feedback.append(f"❌ Spelling errors: {', '.join(unique_errors)}")
        # Give partial credit
        correct_words = len(words) - len(misspelled)
        if correct_words > 0:
            spell_score = (correct_words / len(words)) * 40
            score += spell_score
        mistake_count += len(misspelled)
    
    # 2. Grammar Check (30 points) - Use pattern matching
    grammar_errors = []
    user_lower = user_text.lower()
    
    # Check for common errors in the original sentence
    if 'comunication' in user_lower:
        grammar_errors.append("❌ 'comunication' should be 'communication'")
    if 'punctution' in user_lower:
        grammar_errors.append("❌ 'punctution' should be 'punctuation'")
    if 'grammer' in user_lower:
        grammar_errors.append("❌ 'grammer' should be 'grammar'")
    if 'however' in user_lower and ';' not in user_text and ';' not in user_text:
        grammar_errors.append("❌ Use semicolon (;) before 'however'")
    
    if len(grammar_errors) == 0:
        score += 30
    else:
        deduction = min(25, len(grammar_errors) * 8)
        grammar_score = 30 - deduction
        score += grammar_score
        feedback.extend(grammar_errors[:3])
        mistake_count += len(grammar_errors)
    
    # 3. Capitalization (15 points)
    if user_text and user_text[0].isupper():
        score += 15
    else:
        feedback.append("❌ Start with capital letter")
        mistake_count += 1
    
    # 4. Punctuation (15 points)
    if user_text and user_text[-1] in ['.', '!', '?']:
        score += 15
    else:
        feedback.append("❌ End with proper punctuation (. or !)")
        mistake_count += 1
    
    # Ensure score is between 0-100
    final_score = round(min(100, max(0, score)), 2)
    
    return {
        'score': final_score,
        'feedback': feedback,  # Only errors
        'needs_manual_review': False
    }


def grade_spelling_mcq(user_answer, question):
    """Grade Q4: Choose correctly spelled word (multiple choice)"""
    # Expected format: "b, b, b" or "bbb"
    user_answer = user_answer.strip().lower().replace(' ', '').replace(',', '')
    
    # Expected answers from database (store as "b,b,b")
    expected = question.correct_answer.strip().lower().replace(' ', '').replace(',', '')
    
    # Check each answer
    correct_count = 0
    feedback = []
    
    for i, exp_char in enumerate(expected):
        if i < len(user_answer):
            if user_answer[i] == exp_char:
                correct_count += 1
                # Don't add feedback for correct answers
            else:
                feedback.append(f"❌ Question {i+1}: You chose '{user_answer[i]}', correct was '{exp_char}'")
        else:
            feedback.append(f"❌ Question {i+1}: Missing answer")
    
    score = (correct_count / len(expected)) * 100
    
    return {
        'score': round(score, 2),
        'feedback': feedback,  # Only errors
        'needs_manual_review': False
    }


def grade_paragraph_writing(user_answer, question):
    """
    Grade Q5: Write paragraph using clue words
    4 Rubrics: Grammatical Accuracy (25), Vocabulary (25), 
               Organization (25), Spelling/Punctuation (25)
    """
    from nltk.tokenize import sent_tokenize
    
    spell = get_spell_checker()
    
    user_text = user_answer.strip()
    clue_words = ["time management", "planning", "daily routine", "stress", "success"]
    
    # FEEDBACK STORAGE - ONLY ERRORS
    error_feedback = []
    mistake_count = 0
    
    # Create translator for removing punctuation
    translator = str.maketrans('', '', string.punctuation)
    
    # Common words that should never be flagged as spelling errors
    common_words = ['time', 'management', 'planning', 'daily', 'routine', 'stress', 'success', 
                   'and', 'the', 'to', 'is', 'are', 'was', 'were', 'have', 'has', 'had',
                   'important', 'essential', 'crucial', 'key', 'life', 'student', 'students',
                   'help', 'helps', 'helping', 'make', 'makes', 'making', 'overwhelming']
    
    # ===== RUBRIC 1: GRAMMATICAL ACCURACY (25 points) =====
    grammar_score = 25
    grammar_errors = []
    
    # Basic grammar checks (pattern matching)
    common_error_patterns = [
        (" is ", " are ", "Subject-verb agreement"),
        ("student is", "students are", "Plural/singular agreement"),
        (" dont", " don't", "Missing apostrophe"),
        (" doesnt", " doesn't", "Missing apostrophe"),
        ("cant", "can't", "Missing apostrophe"),
        ("wont", "won't", "Missing apostrophe"),
    ]
    
    grammar_error_count = 0
    for error_pattern, correction, desc in common_error_patterns:
        if error_pattern in user_text.lower():
            grammar_error_count += 1
            grammar_errors.append(f"❌ {desc}: '{error_pattern.strip()}' should be '{correction}'")
    
    if grammar_error_count > 0:
        deduction = min(15, grammar_error_count * 3)
        grammar_score -= deduction
        error_feedback.append(f"❌ Found {grammar_error_count} grammar issues")
        error_feedback.extend(grammar_errors[:3])
        mistake_count += grammar_error_count
    
    # ===== RUBRIC 2: VOCABULARY USE (25 points) =====
    vocab_score = 0
    user_lower = user_text.lower()
    
    # Check clue words (15 points)
    found_words = []
    missing_words = []
    for word in clue_words:
        if word in user_lower:
            found_words.append(word)
        else:
            missing_words.append(word)
    
    word_score = (len(found_words) / len(clue_words)) * 15
    vocab_score += word_score
    
    if len(found_words) < len(clue_words):
        error_feedback.append(f"❌ Missing clue words: {', '.join(missing_words)}")
        mistake_count += len(missing_words)
    
    # Check word variety (10 points)
    words = user_text.split()
    unique_words = len(set([w.lower() for w in words]))
    
    if unique_words >= 15:
        vocab_score += 10
    elif unique_words >= 10:
        vocab_score += 7
    elif unique_words >= 7:
        vocab_score += 5
    else:
        error_feedback.append(f"❌ Very limited vocabulary ({unique_words} unique words)")
        mistake_count += 1
    
    # ===== RUBRIC 3: ORGANIZATION & COHERENCE (25 points) =====
    org_score = 0
    
    # Sentence count (10 points)
    try:
        sentences = sent_tokenize(user_text)
    except:
        # Fallback: split by punctuation
        sentences = [s.strip() for s in user_text.replace('!', '.').replace('?', '.').split('.') if s.strip()]
    
    sentence_count = len(sentences)
    
    if 5 <= sentence_count <= 6:
        org_score += 10
    elif sentence_count >= 4:
        org_score += 7
        error_feedback.append(f"❌ Aim for 5-6 sentences (you wrote {sentence_count})")
        mistake_count += 1
    elif sentence_count >= 3:
        org_score += 5
        error_feedback.append(f"❌ Too few sentences ({sentence_count}), need 5-6")
        mistake_count += 1
    else:
        error_feedback.append(f"❌ Need 5-6 sentences (you wrote {sentence_count})")
        mistake_count += 1
    
    # Check for transition words (10 points)
    transitions = ['first', 'second', 'then', 'next', 'after', 'because', 'so', 'therefore', 'finally', 'also', 'however']
    found_transitions = [t for t in transitions if t in user_lower]
    
    if len(found_transitions) >= 3:
        org_score += 10
    elif len(found_transitions) >= 2:
        org_score += 7
    elif len(found_transitions) >= 1:
        org_score += 4
        error_feedback.append("❌ Add more transition words (first, then, finally)")
        mistake_count += 1
    else:
        error_feedback.append("❌ No transition words found")
        mistake_count += 1
    
    # Logical flow - check if starts with topic introduction (5 points)
    if sentences:
        first_sentence = sentences[0].lower()
        if any(word in first_sentence for word in ['time management', 'important', 'essential', 'crucial', 'key']):
            org_score += 5
        else:
            error_feedback.append("❌ Start with a clear topic introduction")
            org_score += 2
            mistake_count += 1
    else:
        error_feedback.append("❌ No sentences written")
        mistake_count += 1
    
    # ===== RUBRIC 4: SPELLING & PUNCTUATION (25 points) =====
    spell_score = 25
    spelling_errors = []
    
    # IMPROVED SPELLING CHECK
    words = user_text.split()
    misspelled = []
    
    for word in words:
        # Clean the word - remove punctuation
        clean_word = word.translate(translator).lower()
        
        # Skip common words
        if clean_word in common_words:
            continue
            
        # Skip if it's a single character or empty
        if len(clean_word) <= 1:
            continue
            
        # Check if word is in dictionary
        if clean_word not in spell:
            misspelled.append(word)
    
    if len(misspelled) > 0:
        # Show unique misspelled words (limit to 3)
        unique_errors = list(set([w.lower() for w in misspelled]))[:3]
        deduction = min(15, len(misspelled) * 2)  # Reduced penalty
        spell_score -= deduction
        error_feedback.append(f"❌ Possible spelling errors: {', '.join(unique_errors)}")
        mistake_count += len(misspelled)
    
    # Capitalization
    if not (user_text and user_text[0].isupper()):
        spell_score -= 5
        error_feedback.append("❌ Start with capital letter")
        mistake_count += 1
    
    # Ending punctuation
    if not (user_text and user_text[-1] in ['.', '!', '?']):
        spell_score -= 5
        error_feedback.append("❌ End with proper punctuation (. or !)")
        mistake_count += 1
    
    # ===== CALCULATE TOTAL SCORE =====
    total_score = grammar_score + vocab_score + org_score + spell_score
    
    # Ensure score is between 0-100
    total_score = round(max(0, min(100, total_score)), 2)
    
    # ===== DETERMINE LEVEL =====
    if total_score >= 90:
        level = "Advanced"
    elif total_score >= 75:
        level = "Intermediate"
    elif total_score >= 50:
        level = "Basic"
    else:
        level = "Beginner"
    
    # Only return error feedback (no ✅ items)
    return {
        'score': total_score,
        'feedback': error_feedback,  # Only errors
        'needs_manual_review': False,
        'level': level
    }


# ===== MAIN GRADING FUNCTION =====
def grade_writing_response(user_answer, question):
    """Main grading function that routes to specific grader"""
    
    # Map question types to grading functions
    if question.question_type == 'fill_blanks':
        return grade_fill_blanks(user_answer, question)
    elif question.question_type == 'sentence_order':
        return grade_sentence_order(user_answer, question)
    elif question.question_type == 'sentence_rewrite':
        return grade_rewrite_sentence(user_answer, question)
    elif question.question_type == 'spelling_mcq':
        return grade_spelling_mcq(user_answer, question)
    elif question.question_type == 'paragraph_writing':
        return grade_paragraph_writing(user_answer, question)
    else:
        # Fallback for old question types
        return {
            'score': 0,
            'feedback': ["❌ Question type not supported"],
            'needs_manual_review': True
        }


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
    try:
        grading_result = grade_writing_response(user_answer, question)
    except Exception as e:
        print(f"Error grading question {question_number}: {e}")
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
    
    # Save the response
    session_key = get_session_key(request)
    
    # Delete any previous response for this question
    WritingResponse.objects.filter(session_key=session_key, question=question).delete()
    
    # Create new response
    response = WritingResponse.objects.create(
        session_key=session_key,
        question=question,
        user_answer=user_answer,
        score=float(grading_result['score']),  # Ensure float
        feedback=grading_result['feedback'],
        needs_manual_review=grading_result.get('needs_manual_review', False)
    )
    
    # Return success confirmation with score
    return JsonResponse({
        'success': True,
        'score': float(grading_result['score']),  # Ensure float
        'feedback': grading_result['feedback'][:3]  # Return first 3 feedback items
    })


@login_required
@pretest_access_required('writing')
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
    
    # Check if all questions are answered
    total_questions = test.questions.count()
    if responses.count() < total_questions:
        messages.warning(request, f"Please answer all {total_questions} questions before submitting.")
        return redirect('writing:writing_question', test_id=test_id, question_number=1)
    
    # Calculate total score out of 500
    total_score = sum(float(response.score) for response in responses)
    
    # Save test result
    test_result = WritingTestResult.objects.create(
        session_key=session_key,
        test=test,
        total_score=total_score,
        max_score=total_questions,
        user=request.user,
    )
    
    # Mark writing as completed
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
            # Check if answer is correct (score >= 80)
            is_correct = response.score >= 80
            
            question_data.append({
                'question': question,
                'response': response,
                'user_answer': response.user_answer,
                'score_100': response.score,
                'feedback': response.feedback if isinstance(response.feedback, list) else [],
                'is_correct': is_correct
            })
    
    # Count wrong answers
    wrong_answers_count = len([q for q in question_data if not q['is_correct']])
    
    context = {
        'result': result,
        'question_data': question_data,
        'percentage': result.percentage,
        'total_score': result.total_score,
        'max_score': result.max_score,
        'wrong_answers_count': wrong_answers_count,
        'level': result.level,
    }
    
    return render(request, 'writing/writing_results.html', context)