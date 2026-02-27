"""
Pronunciation evaluation engine with Indian-accent optimized Swift model
"""
import os
import numpy as np
import librosa
from scipy.spatial.distance import euclidean
from fastdtw import fastdtw
from django.conf import settings
import tempfile
import soundfile as sf
from scipy.ndimage import binary_dilation, binary_erosion
import math
import torch
import re
from transformers import WhisperForConditionalGeneration, WhisperProcessor, pipeline

# Set device
device = "cuda:0" if torch.cuda.is_available() else "cpu"
torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32

# Path to your downloaded Swift model
local_model_path = "./speaking/models/swift_model"

print(f"Loading Indian-accent optimized Swift model from {local_model_path} on {device}...")

# Check what files are actually in the directory
import os
print("Files in model directory:", os.listdir(local_model_path)[:5])  # Show first 5 files

try:
    # Try loading with the specific configuration for OpenAI format
    from transformers import WhisperForConditionalGeneration, WhisperProcessor
    
    # Load config first to see what we're dealing with
    import json
    with open(os.path.join(local_model_path, 'config.json'), 'r') as f:
        config = json.load(f)
    print(f"Model type: {config.get('model_type', 'unknown')}")
    
    # Load the model
    asr_model = WhisperForConditionalGeneration.from_pretrained(
        local_model_path,
        torch_dtype=torch_dtype,
        low_cpu_mem_usage=True,
        ignore_mismatched_sizes=True  # This helps with format mismatches
    )
    
    # Load processor
    processor = WhisperProcessor.from_pretrained(local_model_path)
    
    print("✅ Model loaded successfully from local path!")
    
except Exception as e:
    print(f"⚠️ Local load failed: {e}")
    print("Falling back to Hugging Face model ID...")
    
    # Fall back to HF ID (will use cache)
    asr_model = WhisperForConditionalGeneration.from_pretrained(
        "Oriserve/Whisper-Hindi2Hinglish-Swift",
        torch_dtype=torch_dtype,
        low_cpu_mem_usage=True
    )
    processor = WhisperProcessor.from_pretrained("Oriserve/Whisper-Hindi2Hinglish-Swift")
    print("✅ Model loaded from Hugging Face cache!")

asr_model.to(device)

# Create pipeline
from transformers import pipeline

asr_pipeline = pipeline(
    "automatic-speech-recognition",
    model=asr_model,
    tokenizer=processor.tokenizer,
    feature_extractor=processor.feature_extractor,
    torch_dtype=torch_dtype,
    device=device,
    generate_kwargs={
        "task": "transcribe",
        "language": "en"
    }
)

print("✅ Swift model pipeline ready!")

# Question data structure
QUESTIONS = {
    1: {
        'title': 'Question 1: Word Pronunciation',
        'instruction': 'Read the following words aloud clearly:',
        'words': ['Comfortable', 'Vegetable', 'Often', 'Engineer', 'Laboratory'],
        'expected_words': ['comfortable', 'vegetable', 'often', 'engineer', 'laboratory'],
        'word_files': {
            'comfortable': 'word1.wav',
            'vegetable': 'word2.wav',
            'often': 'word3.wav',
            'engineer': 'word4.wav',
            'laboratory': 'word5.wav'
        },
        'weights': {
            'per_word': 20,
            'correctness': 10,
            'pronunciation': 10
        }
    },
    2: {
        'title': 'Question 2: Sentence Rearrangement',
        'instruction': 'Rearrange the words to make a correct sentence. Speak the sentence aloud.',
        'words': ['notebook', 'my', 'forgot', 'I', 'today'],
        'expected_words': ['i', 'forgot', 'my', 'notebook', 'today'],
        'reference': 'q2.wav',
        'weights': {
            'per_word': 20,
            'grammar': 10,
            'coherence': 10
        }
    },
    3: {
        'title': 'Question 3: Phrase Reading',
        'instruction': 'Read the following phrases aloud clearly.',
        'phrases': [
            'an honest answer',
            'practical exam schedule',
            'next week\'s test'
        ],
        'expected_words': ['an', 'honest', 'answer', 'practical', 'exam', 'schedule', 'next', 'week\'s', 'test'],
        'reference': 'q3.wav',
        'weights': {
            'per_word': 11.1,
            'correctness': 5.55,
            'fluency': 5.55
        }
    },
    4: {
        'title': 'Question 4: Sentence Reading',
        'instruction': 'Read the sentence silently. Then speak it aloud clearly.',
        'sentence': 'Safety rules must be followed in the laboratory.',
        'expected_words': ['safety', 'rules', 'must', 'be', 'followed', 'in', 'the', 'laboratory'],
        'reference': 'q4.wav',
        'weights': {
            'per_word': 12.5,
            'correctness': 6.25,
            'fluency': 6.25
        }
    },
    5: {
        'title': 'Question 5: Grammar Correction',
        'instruction': 'Correct the sentence and speak it aloud.',
        'incorrect_sentence': 'He go to college everyday.',
        'expected_words': ['he', 'goes', 'to', 'college', 'every', 'day'],
        'reference': 'q5.wav',
        'weights': {
            'per_word': 20,
            'correctness': 10,
            'grammar': 10
        }
    }
}

class SimpleGrammarChecker:
    """
    Simple rule-based grammar checker for common English errors
    """
    def __init__(self):
        # Subject-verb agreement rules for common pronouns
        self.subject_verb_rules = {
            ('he', 'go'): 'goes',
            ('she', 'go'): 'goes',
            ('it', 'go'): 'goes',
            ('he', 'do'): 'does',
            ('she', 'do'): 'does',
            ('it', 'do'): 'does',
            ('he', 'have'): 'has',
            ('she', 'have'): 'has',
            ('it', 'have'): 'has',
            ('he', 'was'): 'was',
            ('she', 'was'): 'was',
            ('it', 'was'): 'was',
            ('they', 'was'): 'were',
            ('we', 'was'): 'were',
            ('he', 'is'): 'is',
            ('she', 'is'): 'is',
            ('it', 'is'): 'is',
            ('they', 'is'): 'are',
            ('we', 'is'): 'are',
        }
        
        # Common verb forms
        self.irregular_verbs = {
            'go': 'went',
            'see': 'saw',
            'eat': 'ate',
            'drink': 'drank',
            'run': 'ran',
            'come': 'came',
            'become': 'became',
            'begin': 'began',
            'break': 'broke',
            'bring': 'brought',
            'buy': 'bought',
            'catch': 'caught',
            'choose': 'chose',
            'do': 'did',
            'draw': 'drew',
            'dream': 'dreamt',
            'drive': 'drove',
            'fall': 'fell',
            'feel': 'felt',
            'fight': 'fought',
            'find': 'found',
            'fly': 'flew',
            'forget': 'forgot',
            'forgive': 'forgave',
            'freeze': 'froze',
            'get': 'got',
            'give': 'gave',
            'have': 'had',
            'hear': 'heard',
            'hide': 'hid',
            'hold': 'held',
            'keep': 'kept',
            'know': 'knew',
            'lead': 'led',
            'leave': 'left',
            'lend': 'lent',
            'let': 'let',
            'lose': 'lost',
            'make': 'made',
            'mean': 'meant',
            'meet': 'met',
            'pay': 'paid',
            'put': 'put',
            'read': 'read',
            'ride': 'rode',
            'ring': 'rang',
            'rise': 'rose',
            'say': 'said',
            'see': 'saw',
            'sell': 'sold',
            'send': 'sent',
            'shake': 'shook',
            'shine': 'shone',
            'shoot': 'shot',
            'show': 'showed',
            'shut': 'shut',
            'sing': 'sang',
            'sink': 'sank',
            'sit': 'sat',
            'sleep': 'slept',
            'speak': 'spoke',
            'spend': 'spent',
            'stand': 'stood',
            'steal': 'stole',
            'swim': 'swam',
            'take': 'took',
            'teach': 'taught',
            'tell': 'told',
            'think': 'thought',
            'throw': 'threw',
            'understand': 'understood',
            'wake': 'woke',
            'wear': 'wore',
            'win': 'won',
            'write': 'wrote'
        }
        
        # Articles (a/an/the) rules
        self.article_rules = {
            'a': ['consonant_sound'],
            'an': ['vowel_sound']
        }
        
        # Preposition rules
        self.common_prepositions = ['in', 'on', 'at', 'to', 'for', 'with', 'by', 'from', 'of']
        
    def check_subject_verb_agreement(self, words):
        """
        Check for subject-verb agreement errors
        Returns list of errors with positions and corrections
        """
        errors = []
        
        for i in range(len(words) - 1):
            # Check patterns like "He go", "She do", etc.
            if i < len(words) - 1 and words[i] in ['he', 'she', 'it', 'they', 'we']:
                subject = words[i]
                verb = words[i + 1]
                
                # Check if this subject-verb pair has a rule
                key = (subject, verb)
                if key in self.subject_verb_rules:
                    expected = self.subject_verb_rules[key]
                    errors.append({
                        'position': i + 1,
                        'word': verb,
                        'expected': expected,
                        'rule': 'subject_verb_agreement',
                        'message': f"'{subject}' should be followed by '{expected}', not '{verb}'"
                    })
        
        return errors
    
    def check_verb_tense(self, words, context=None):
        """
        Check for incorrect verb tense usage
        """
        errors = []
        
        # Simple check for past tense indicators
        time_indicators = ['yesterday', 'last', 'ago', 'previous']
        
        for i, word in enumerate(words):
            # If there's a past time indicator, check nearby verbs
            if word in time_indicators:
                # Check previous word (might be a verb)
                if i > 0 and words[i-1] in self.irregular_verbs:
                    # Should be past tense
                    expected = self.irregular_verbs[words[i-1]]
                    if words[i-1] != expected:
                        errors.append({
                            'position': i-1,
                            'word': words[i-1],
                            'expected': expected,
                            'rule': 'verb_tense',
                            'message': f"With time indicator '{word}', use past tense '{expected}'"
                        })
        
        return errors
    
    def check_article_usage(self, words):
        """
        Check for a/an/article usage errors
        """
        errors = []
        
        vowels = ['a', 'e', 'i', 'o', 'u']
        
        for i, word in enumerate(words):
            if word == 'a' and i < len(words) - 1:
                next_word = words[i + 1]
                if next_word and next_word[0] in vowels:
                    errors.append({
                        'position': i,
                        'word': 'a',
                        'expected': 'an',
                        'rule': 'article_usage',
                        'message': f"Use 'an' before vowel sound, not 'a'"
                    })
            elif word == 'an' and i < len(words) - 1:
                next_word = words[i + 1]
                if next_word and next_word[0] not in vowels:
                    errors.append({
                        'position': i,
                        'word': 'an',
                        'expected': 'a',
                        'rule': 'article_usage',
                        'message': f"Use 'a' before consonant sound, not 'an'"
                    })
        
        return errors
    
    def check_grammar(self, text):
        """
        Main method to check grammar of a text
        Returns list of grammar errors
        """
        words = text.lower().split()
        all_errors = []
        
        # Apply different grammar checks
        all_errors.extend(self.check_subject_verb_agreement(words))
        all_errors.extend(self.check_verb_tense(words))
        all_errors.extend(self.check_article_usage(words))
        
        return all_errors
    
    def get_grammar_score_for_q5(self, spoken_words, expected_words):
        """
        Specialized scoring for Question 5
        Returns grammar score out of 10
        """
        grammar_score = 0
        
        # For Q5, we know the expected correction: "He go" -> "He goes"
        if len(spoken_words) >= 2:
            # Check if subject "he" is followed by correct verb form
            if spoken_words[0] == 'he' and spoken_words[1] == 'goes':
                grammar_score = 10
            elif spoken_words[0] == 'he' and spoken_words[1] == 'go':
                grammar_score = 5  # Partial credit for recognizing need for change
            elif len(spoken_words) > 1 and spoken_words[1] in ['go', 'goes']:
                grammar_score = 3  # Small credit for using a verb
        
        return grammar_score

class PronunciationEngine:
    def __init__(self):
        self.sample_rate = 16000
        self.n_mfcc = 13
        self.max_expected_distance = 20000
        self.voice_threshold = 0.001
        self.silence_threshold = 0.005
        self.grammar_checker = SimpleGrammarChecker()
        
    def transcribe_audio(self, audio_path):
        """
        Transcribe audio using Swift model optimized for Indian accents
        """
        try:
            result = asr_pipeline(audio_path)
            return result["text"].strip().lower()
        except Exception as e:
            print(f"Transcription error: {e}")
            return ""
    
    def extract_mfcc(self, audio_path):
        """Extract MFCC features for pronunciation scoring"""
        try:
            y, sr = librosa.load(audio_path, sr=self.sample_rate)
            if np.max(np.abs(y)) > 0:
                y = y / np.max(np.abs(y))
            
            mfcc = librosa.feature.mfcc(
                y=y, sr=sr, n_mfcc=self.n_mfcc,
                n_fft=2048, hop_length=512, n_mels=128
            )
            
            mfcc_delta = librosa.feature.delta(mfcc)
            mfcc_delta2 = librosa.feature.delta(mfcc, order=2)
            features = np.vstack([mfcc, mfcc_delta, mfcc_delta2])
            
            return features.T
        except Exception as e:
            print(f"MFCC extraction error: {e}")
            return None
    
    def calculate_dtw_distance(self, features1, features2):
        """Calculate DTW distance between features"""
        if features1 is None or features2 is None:
            return float('inf')
        try:
            distance, _ = fastdtw(features1, features2, dist=euclidean)
            return distance
        except:
            return float('inf')
    
    def normalize_distance(self, distance):
        """
        Normalize DTW distance to a 0-100 score using exponential decay
        """
        if distance == float('inf'):
            return 0
        
        # Use exponential decay for better score distribution
        raw_score = 100 * math.exp(-distance / self.max_expected_distance)
        
        # Ensure score is between 0 and 100
        return max(0, min(100, raw_score))
    
    def get_pronunciation_score(self, student_audio, expected_word):
        """Get pronunciation score for a word (0-10)"""
        try:
            ref_folder = os.path.join(settings.BASE_DIR, 'speaking', 'reference_audio')
            word_file = {
                'comfortable': 'word1.wav',
                'vegetable': 'word2.wav',
                'often': 'word3.wav',
                'engineer': 'word4.wav',
                'laboratory': 'word5.wav'
            }.get(expected_word, '')
            
            if not word_file:
                return 5
            
            ref_path = os.path.join(ref_folder, word_file)
            if not os.path.exists(ref_path):
                return 5
            
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                sf.write(tmp.name, student_audio, self.sample_rate)
                student_feat = self.extract_mfcc(tmp.name)
            
            ref_feat = self.extract_mfcc(ref_path)
            
            if student_feat is None or ref_feat is None:
                os.unlink(tmp.name)
                return 0
            
            distance = self.calculate_dtw_distance(student_feat, ref_feat)
            os.unlink(tmp.name)
            
            raw_score = 10 * math.exp(-distance / self.max_expected_distance)
            return max(0, min(10, raw_score))
            
        except Exception as e:
            print(f"Pronunciation score error: {e}")
            return 0
    
    def score_q1_word(self, word_audio_path, word_number):
        """Score a single Q1 word by comparing with its reference file"""
        try:
            ref_path = os.path.join(settings.BASE_DIR, 'speaking', 'reference_audio', f'word{word_number}.wav')
            
            # Check if files exist
            if not os.path.exists(word_audio_path):
                print(f"Student word audio not found: {word_audio_path}")
                return 0
            
            if not os.path.exists(ref_path):
                print(f"Reference file not found: {ref_path}")
                return 0
            
            # Extract features
            student_feat = self.extract_mfcc(word_audio_path)
            ref_feat = self.extract_mfcc(ref_path)
            
            if student_feat is None or ref_feat is None:
                return 0
            
            # Calculate DTW distance
            distance = self.calculate_dtw_distance(student_feat, ref_feat)
            
            # Convert to score
            score = self.normalize_distance(distance)
            
            return round(score, 2)
            
        except Exception as e:
            print(f"Error scoring Q1 word {word_number}: {e}")
            return 0
    
    def score_q2_sentence(self, student_audio_path):
        """Score Q2: 5 words, each 20% (10% grammar + 10% coherence)"""
        transcribed_text = self.transcribe_audio(student_audio_path)
        spoken_words = transcribed_text.lower().split()
        
        # Clean words of punctuation
        spoken_words = [re.sub(r'[^\w\s]', '', w) for w in spoken_words]
        print(f"🧹 Cleaned words for Q2: {spoken_words}")  # Debug
        
        expected = QUESTIONS[2]['expected_words']
        word_results = []
        total_score = 0
        
        # Use grammar checker for additional insights
        grammar_errors = self.grammar_checker.check_grammar(transcribed_text)
        grammar_error_positions = [e['position'] for e in grammar_errors]
        
        for i in range(5):
            word_result = {
                'position': i + 1,
                'expected': expected[i],
                'spoken': spoken_words[i] if i < len(spoken_words) else '[silence]',
                'grammar_score': 0,
                'coherence_score': 0,
                'total': 0
            }
            
            # Grammar score: 10 if word is in expected set (any position)
            if i < len(spoken_words) and spoken_words[i] in expected:
                word_result['grammar_score'] = 10
            
            # Coherence score: 10 if word is in correct position
            if i < len(spoken_words) and spoken_words[i] == expected[i]:
                word_result['coherence_score'] = 10
            
            # Deduct points if this position has a grammar error
            if i in grammar_error_positions:
                word_result['grammar_score'] = max(0, word_result['grammar_score'] - 5)
            
            word_result['total'] = word_result['grammar_score'] + word_result['coherence_score']
            total_score += word_result['total']
            word_results.append(word_result)
        
        return word_results, total_score
        
    def score_q3_phrases(self, student_audio_path):
        """Score Q3: 9 words, each 11.1% (5.55% correctness + 5.55% fluency)"""
        transcribed_text = self.transcribe_audio(student_audio_path)
        spoken_words = transcribed_text.lower().split()
        
        expected = QUESTIONS[3]['expected_words']
        word_results = []
        total_score = 0
        
        # Try different alignments to find best match
        from difflib import SequenceMatcher
        
        # Find best alignment
        best_alignment = 0
        best_score = 0
        
        for offset in [-2, -1, 0, 1, 2]:  # Try shifts
            matched = 0
            for i in range(len(expected)):
                idx = i + offset
                if 0 <= idx < len(spoken_words) and spoken_words[idx] == expected[i]:
                    matched += 1
            if matched > best_score:
                best_score = matched
                best_alignment = offset
        
        print(f"Best alignment offset: {best_alignment}")
        
        for i in range(9):
            spoken_idx = i + best_alignment
            spoken = spoken_words[spoken_idx] if 0 <= spoken_idx < len(spoken_words) else '[silence]'
            
            word_result = {
                'position': i + 1,
                'expected': expected[i],
                'spoken': spoken,
                'correctness_score': 5.55 if spoken == expected[i] else 0,
                'fluency_score': 5.55 if spoken != '[silence]' else 0,
                'total': 0
            }
            
            # Fluency: if they spoke something (even if wrong), give partial fluency credit
            if word_result['correctness_score'] > 0:
                word_result['fluency_score'] = 5.55
            elif spoken != '[silence]':
                word_result['fluency_score'] = 2.77  # Partial credit for attempting
            
            word_result['total'] = round(word_result['correctness_score'] + word_result['fluency_score'], 2)
            total_score += word_result['total']
            word_results.append(word_result)
        
        return word_results, total_score
    
    def score_q4_sentence(self, student_audio_path):
        """Score Q4: 8 words, each 12.5% (6.25% correctness + 6.25% fluency)"""
        transcribed_text = self.transcribe_audio(student_audio_path)
        spoken_words = transcribed_text.lower().split()
        
        expected = QUESTIONS[4]['expected_words']
        word_results = []
        total_score = 0
        
        for i in range(8):
            word_result = {
                'position': i + 1,
                'expected': expected[i] if i < len(expected) else '',
                'spoken': spoken_words[i] if i < len(spoken_words) else '[silence]',
                'correctness_score': 0,
                'fluency_score': 0,
                'total': 0
            }
            
            # Correctness score
            if i < len(spoken_words) and i < len(expected) and spoken_words[i] == expected[i]:
                word_result['correctness_score'] = 6.25
            
            # Fluency score - partial credit for attempting
            if i < len(spoken_words):
                word_result['fluency_score'] = 3.12 if word_result['correctness_score'] == 0 else 6.25
            elif i < len(spoken_words):
                word_result['fluency_score'] = 3.12
            
            word_result['total'] = round(word_result['correctness_score'] + word_result['fluency_score'], 2)
            total_score += word_result['total']
            word_results.append(word_result)
        
        return word_results, total_score
    
    def score_q5_grammar(self, student_audio_path):
        """Score Q5: 6 words, each 20% (10% correctness + 10% grammar)"""
        transcribed_text = self.transcribe_audio(student_audio_path)
        spoken_words = transcribed_text.lower().split()
        
        expected = QUESTIONS[5]['expected_words']
        word_results = []
        total_score = 0
        
        # Get grammar score from specialized checker
        grammar_score_q5 = self.grammar_checker.get_grammar_score_for_q5(spoken_words, expected)
        
        for i in range(6):
            spoken = spoken_words[i] if i < len(spoken_words) else '[silence]'
            
            word_result = {
                'position': i + 1,
                'expected': expected[i],
                'spoken': spoken,
                'correctness_score': 0,
                'grammar_score': 0,
                'total': 0
            }
            
            # Correctness score: 10 if exact match
            if i < len(spoken_words) and spoken == expected[i]:
                word_result['correctness_score'] = 10
            
            # Grammar score: Distribute the overall grammar score across words
            # For Q5, grammar is mostly about the verb form (position 2)
            if i == 1:  # The verb position (goes)
                if spoken == 'goes':
                    word_result['grammar_score'] = 10
                elif spoken == 'go':
                    word_result['grammar_score'] = 5  # Partial credit
            else:
                # Other positions get full grammar score if correct
                if i < len(spoken_words) and spoken in expected:
                    word_result['grammar_score'] = 10
                elif spoken != '[silence]':
                    word_result['grammar_score'] = 5  # Partial for attempting
            
            word_result['total'] = word_result['correctness_score'] + word_result['grammar_score']
            total_score += word_result['total']
            word_results.append(word_result)
        
        return word_results, total_score
    
    def score_recording(self, student_audio_path, question_number):
        """Main scoring function - for Q1-Q5"""
        if not os.path.exists(student_audio_path):
            return 0, []
        
        # Check for silence
        try:
            y, sr = librosa.load(student_audio_path, sr=self.sample_rate)
            energy = librosa.feature.rms(y=y)[0]
            if np.max(energy) < self.silence_threshold:
                return 0, []
        except:
            return 0, []
        
        # Score based on question type
        if question_number == 1:
            # Q1 handled separately in the view
            return 0, []
        elif question_number == 2:
            word_results, total = self.score_q2_sentence(student_audio_path)
        elif question_number == 3:
            word_results, total = self.score_q3_phrases(student_audio_path)
        elif question_number == 4:
            word_results, total = self.score_q4_sentence(student_audio_path)
        elif question_number == 5:
            word_results, total = self.score_q5_grammar(student_audio_path)
        else:
            return 0, []
        
        return round(total, 2), word_results
    
    def generate_feedback(self, scores):
        """Generate overall feedback"""
        if not scores:
            return {
                'level': 'No Data',
                'message': 'No scores available',
                'average': 0
            }
        
        avg_score = sum(scores.values()) / len(scores)
        
        if avg_score >= 85:
            level = "Excellent"
            message = "Your pronunciation and grammar are excellent! You have a strong command of English."
        elif avg_score >= 70:
            level = "Good"
            message = "Good job! You're doing well. Focus on the specific words and grammar rules where you lost points."
        elif avg_score >= 50:
            level = "Fair"
            message = "You're making progress. Pay attention to word order, verb forms, and speaking clearly."
        else:
            level = "Needs Practice"
            message = "Keep practicing! Focus on speaking clearly and using correct grammar. Try to practice each word multiple times."
        
        return {
            'level': level,
            'message': message,
            'average': round(avg_score, 2)
        }
    
    def get_grammar_tips(self, question_number, word_results):
        """Generate grammar tips based on errors"""
        tips = []
        
        if question_number == 2:
            # Tips for sentence rearrangement
            expected_order = QUESTIONS[2]['expected_words']
            tips.append("💡 Tip: The correct word order should be: " + " ".join(expected_order))
            tips.append("💡 Tip: In English, the subject usually comes before the verb.")
        
        elif question_number == 5:
            # Tips for grammar correction
            tips.append("💡 Tip: With 'he', 'she', or 'it', verbs usually end with 's' or 'es'.")
            tips.append("💡 Tip: 'He goes' is correct, not 'He go'.")
            tips.append("💡 Tip: 'Everyday' is an adjective; use 'every day' for frequency.")
        
        return tips

# Create singleton instance
pronunciation_engine = PronunciationEngine()