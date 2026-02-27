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
import language_tool_python
import torch
import re
from transformers import WhisperForConditionalGeneration, WhisperProcessor, pipeline

# Initialize grammar checker
# grammar_tool = language_tool_python.LanguageTool('en-US')

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

class PronunciationEngine:
    def __init__(self):
        self.sample_rate = 16000
        self.n_mfcc = 13
        self.max_expected_distance = 20000
        self.voice_threshold = 0.001
        self.silence_threshold = 0.005
        
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
    
        transcribed_text = self.transcribe_audio(student_audio_path)
        spoken_words = transcribed_text.lower().split()
        
        # 🔥 ADD THESE 3 LINES HERE - RIGHT AFTER split()
        import re
        spoken_words = [re.sub(r'[^\w\s]', '', w) for w in spoken_words]
        print(f"🧹 Cleaned words for Q2: {spoken_words}")  # Debug
        
        expected = QUESTIONS[2]['expected_words']
        word_results = []
        total_score = 0
        
        for i in range(5):
            word_result = {
                'position': i + 1,
                'expected': expected[i],
                'spoken': spoken_words[i] if i < len(spoken_words) else '[silence]',
                'grammar_score': 0,
                'coherence_score': 0,
                'total': 0
            }
            
            if i < len(spoken_words) and spoken_words[i] in expected:
                word_result['grammar_score'] = 10
            
            if i < len(spoken_words) and spoken_words[i] == expected[i]:
                word_result['coherence_score'] = 10
            
            word_result['total'] = word_result['grammar_score'] + word_result['coherence_score']
            total_score += word_result['total']
            word_results.append(word_result)
        
        return word_results, total_score
        
    def score_q3_phrases(self, student_audio_path):
    
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
            
            if word_result['correctness_score'] > 0:
                word_result['fluency_score'] = 5.55
            elif spoken != '[silence]':
                word_result['fluency_score'] = 2.77
            
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
            
            if i < len(spoken_words) and i < len(expected) and spoken_words[i] == expected[i]:
                word_result['correctness_score'] = 6.25
                word_result['fluency_score'] = 6.25
            elif i < len(spoken_words):
                word_result['fluency_score'] = 3.12
            
            word_result['total'] = round(word_result['correctness_score'] + word_result['fluency_score'], 2)
            total_score += word_result['total']
            word_results.append(word_result)
        
        return word_results, total_score
    
    def score_q5_grammar(self, student_audio_path):
        """Score Q5: 5 words, each 20% (10% correctness + 10% grammar)"""
        transcribed_text = self.transcribe_audio(student_audio_path)
        spoken_words = transcribed_text.lower().split()
        
        expected = QUESTIONS[5]['expected_words']
        word_results = []
        total_score = 0
        
        for i in range(5):
            word_result = {
                'position': i + 1,
                'expected': expected[i],
                'spoken': spoken_words[i] if i < len(spoken_words) else '[silence]',
                'correctness_score': 0,
                'grammar_score': 0,
                'total': 0
            }
            
            if i < len(spoken_words) and spoken_words[i] == expected[i]:
                word_result['correctness_score'] = 10
            
            if i < len(spoken_words):
                if i == 1:  # Second word should be "goes"
                    if spoken_words[i] in ['goes', 'go']:
                        word_result['grammar_score'] = 10 if spoken_words[i] == 'goes' else 5
                else:
                    if spoken_words[i] in expected:
                        word_result['grammar_score'] = 10
            
            word_result['total'] = word_result['correctness_score'] + word_result['grammar_score']
            total_score += word_result['total']
            word_results.append(word_result)
        
        return word_results, total_score
    
    def score_recording(self, student_audio_path, question_number):
        """Main scoring function - for Q2-Q5 only"""
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
        
        # Score based on question type (Q2-Q5 only)
        if question_number == 2:
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
        avg_score = sum(scores.values()) / len(scores)
        
        if avg_score >= 85:
            level = "Excellent"
            message = "Your pronunciation and grammar are excellent!"
        elif avg_score >= 70:
            level = "Good"
            message = "Good job! Minor improvements needed."
        elif avg_score >= 50:
            level = "Fair"
            message = "You're doing well. Focus on problem areas."
        else:
            level = "Needs Practice"
            message = "Keep practicing! Focus on speaking clearly."
        
        return {
            'level': level,
            'message': message,
            'average': round(avg_score, 2)
        }

# Create singleton instance
pronunciation_engine = PronunciationEngine()