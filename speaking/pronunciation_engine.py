
"""
Pronunciation evaluation engine with Indian-accent optimized Swift model.
Heavy AI components are loaded only when transcription is first requested.
"""

import os
import math
import tempfile
import re

import numpy as np
import librosa
import soundfile as sf
import language_tool_python

from scipy.spatial.distance import euclidean
from scipy.ndimage import binary_dilation, binary_erosion
from fastdtw import fastdtw
from django.conf import settings


# ---------------------------------------------------------
# Lazy-loaded AI components
# ---------------------------------------------------------

grammar_tool = None
asr_pipeline = None


def get_grammar_tool():
    """Initialize the grammar checker only when needed."""
    global grammar_tool

    if grammar_tool is None:
        grammar_tool = language_tool_python.LanguageTool("en-US")

    return grammar_tool


def get_asr_pipeline():
    """Load the Whisper model only when transcription is requested."""
    global asr_pipeline

    if asr_pipeline is not None:
        return asr_pipeline

    import json
    import torch
    from transformers import (
        WhisperForConditionalGeneration,
        WhisperProcessor,
        pipeline,
    )

    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32

    local_model_path = os.path.join(
        settings.BASE_DIR,
        "speaking",
        "models",
        "swift_model",
    )

    model_name = "Oriserve/Whisper-Hindi2Hinglish-Swift"

    print(f"Loading Swift model on {device}...")

    # Prefer the local model if its configuration exists.
    if (
        os.path.isdir(local_model_path)
        and os.path.isfile(os.path.join(local_model_path, "config.json"))
    ):
        try:
            with open(
                os.path.join(local_model_path, "config.json"),
                "r",
                encoding="utf-8",
            ) as config_file:
                config = json.load(config_file)

            print(
                "Local model type:",
                config.get("model_type", "unknown"),
            )

            asr_model = WhisperForConditionalGeneration.from_pretrained(
                local_model_path,
                torch_dtype=torch_dtype,
                low_cpu_mem_usage=True,
            )

            processor = WhisperProcessor.from_pretrained(local_model_path)

            print("Local Swift model loaded.")

        except Exception as exc:
            print(f"Local model loading failed: {exc}")
            print("Falling back to the Hugging Face model.")

            asr_model = WhisperForConditionalGeneration.from_pretrained(
                model_name,
                torch_dtype=torch_dtype,
                low_cpu_mem_usage=True,
            )

            processor = WhisperProcessor.from_pretrained(model_name)

    else:
        print("Local model not found. Loading from Hugging Face.")

        asr_model = WhisperForConditionalGeneration.from_pretrained(
            model_name,
            torch_dtype=torch_dtype,
            low_cpu_mem_usage=True,
        )

        processor = WhisperProcessor.from_pretrained(model_name)

    asr_model.to(device)

    loaded_pipeline = pipeline(
        "automatic-speech-recognition",
        model=asr_model,
        tokenizer=processor.tokenizer,
        feature_extractor=processor.feature_extractor,
        torch_dtype=torch_dtype,
        device=device,
        generate_kwargs={
            "task": "transcribe",
            "language": "en",
        },
    )

    # Assign only after successful initialization.
    asr_pipeline = loaded_pipeline

    print("Swift model pipeline ready.")

    return asr_pipeline


# ---------------------------------------------------------
# Question data
# ---------------------------------------------------------

QUESTIONS = {
    1: {
        "title": "Question 1: Word Pronunciation",
        "instruction": "Read the following words aloud clearly:",
        "words": [
            "Comfortable",
            "Vegetable",
            "Often",
            "Engineer",
            "Laboratory",
        ],
        "expected_words": [
            "comfortable",
            "vegetable",
            "often",
            "engineer",
            "laboratory",
        ],
        "word_files": {
            "comfortable": "word1.wav",
            "vegetable": "word2.wav",
            "often": "word3.wav",
            "engineer": "word4.wav",
            "laboratory": "word5.wav",
        },
        "weights": {
            "per_word": 20,
            "correctness": 10,
            "pronunciation": 10,
        },
    },
    2: {
        "title": "Question 2: Sentence Rearrangement",
        "instruction": (
            "Rearrange the words to make a correct sentence. "
            "Speak the sentence aloud."
        ),
        "words": ["notebook", "my", "forgot", "I", "today"],
        "expected_words": ["i", "forgot", "my", "notebook", "today"],
        "reference": "q2.wav",
        "weights": {
            "per_word": 20,
            "grammar": 10,
            "coherence": 10,
        },
    },
    3: {
        "title": "Question 3: Phrase Reading",
        "instruction": "Read the following phrases aloud clearly.",
        "phrases": [
            "an honest answer",
            "practical exam schedule",
            "next week's test",
        ],
        "expected_words": [
            "an",
            "honest",
            "answer",
            "practical",
            "exam",
            "schedule",
            "next",
            "week's",
            "test",
        ],
        "reference": "q3.wav",
        "weights": {
            "per_word": 11.1,
            "correctness": 5.55,
            "fluency": 5.55,
        },
    },
    4: {
        "title": "Question 4: Sentence Reading",
        "instruction": (
            "Read the sentence silently. Then speak it aloud clearly."
        ),
        "sentence": "Safety rules must be followed in the laboratory.",
        "expected_words": [
            "safety",
            "rules",
            "must",
            "be",
            "followed",
            "in",
            "the",
            "laboratory",
        ],
        "reference": "q4.wav",
        "weights": {
            "per_word": 12.5,
            "correctness": 6.25,
            "fluency": 6.25,
        },
    },
    5: {
        "title": "Question 5: Grammar Correction",
        "instruction": "Correct the sentence and speak it aloud.",
        "incorrect_sentence": "He go to college everyday.",
        "expected_words": [
            "he",
            "goes",
            "to",
            "college",
            "every",
            "day",
        ],
        "reference": "q5.wav",
        "weights": {
            "per_word": 20,
            "correctness": 10,
            "grammar": 10,
        },
    },
}


# ---------------------------------------------------------
# Pronunciation engine
# ---------------------------------------------------------

class PronunciationEngine:
    def __init__(self):
        self.sample_rate = 16000
        self.n_mfcc = 13
        self.max_expected_distance = 20000
        self.voice_threshold = 0.001
        self.silence_threshold = 0.005

    def transcribe_audio(self, audio_path):
        """Transcribe audio. Uses Groq if GROQ_API_KEY is set, else the local model."""
        api_key = os.environ.get("GROQ_API_KEY")
        if api_key:
            return self._transcribe_with_groq(audio_path, api_key)

        try:
            result = get_asr_pipeline()(audio_path)
            return result["text"].strip().lower()
        except Exception as exc:
            print(f"Transcription error: {exc}")
            return ""

    def _transcribe_with_groq(self, audio_path, api_key):
        """Send the recording to Groq's hosted Whisper."""
        import requests

        try:
            with open(audio_path, "rb") as audio_file:
                response = requests.post(
                    "https://api.groq.com/openai/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    files={"file": (os.path.basename(audio_path), audio_file)},
                    data={
                        "model": "whisper-large-v3-turbo",
                        "language": "en",
                        "response_format": "json",
                        "temperature": "0",
                    },
                    timeout=30,
                )

            if response.status_code != 200:
                print(f"Groq error {response.status_code}: {response.text[:300]}")
                return ""

            return response.json().get("text", "").strip().lower()

        except Exception as exc:
            print(f"Groq transcription error: {exc}")
            return ""

    def extract_mfcc(self, audio_path):
        """Extract MFCC features for pronunciation scoring."""
        try:
            y, sr = librosa.load(audio_path, sr=self.sample_rate)

            if y.size == 0:
                return None

            max_amplitude = np.max(np.abs(y))
            if max_amplitude > 0:
                y = y / max_amplitude

            mfcc = librosa.feature.mfcc(
                y=y,
                sr=sr,
                n_mfcc=self.n_mfcc,
                n_fft=2048,
                hop_length=512,
                n_mels=128,
            )

            mfcc_delta = librosa.feature.delta(mfcc)
            mfcc_delta2 = librosa.feature.delta(mfcc, order=2)

            features = np.vstack([mfcc, mfcc_delta, mfcc_delta2])

            return features.T

        except Exception as exc:
            print(f"MFCC extraction error: {exc}")
            return None

    def calculate_dtw_distance(self, features1, features2):
        """Calculate DTW distance between features."""
        if features1 is None or features2 is None:
            return float("inf")

        try:
            distance, _ = fastdtw(
                features1,
                features2,
                dist=euclidean,
            )
            return distance
        except Exception as exc:
            print(f"DTW calculation error: {exc}")
            return float("inf")

    def normalize_distance(self, distance):
        """Normalize DTW distance to a score between 0 and 100."""
        if distance == float("inf"):
            return 0

        raw_score = 100 * math.exp(
            -distance / self.max_expected_distance
        )

        return max(0, min(100, raw_score))

    def get_pronunciation_score(self, student_audio, expected_word):
        """Get pronunciation score for a word (0-10)."""
        tmp_name = None

        try:
            ref_folder = os.path.join(
                settings.BASE_DIR,
                "speaking",
                "reference_audio",
            )

            word_file = {
                "comfortable": "word1.wav",
                "vegetable": "word2.wav",
                "often": "word3.wav",
                "engineer": "word4.wav",
                "laboratory": "word5.wav",
            }.get(expected_word)

            if not word_file:
                return 5

            ref_path = os.path.join(ref_folder, word_file)

            if not os.path.exists(ref_path):
                return 5

            with tempfile.NamedTemporaryFile(
                suffix=".wav",
                delete=False,
            ) as tmp:
                tmp_name = tmp.name

            sf.write(tmp_name, student_audio, self.sample_rate)

            student_feat = self.extract_mfcc(tmp_name)
            ref_feat = self.extract_mfcc(ref_path)

            if student_feat is None or ref_feat is None:
                return 0

            distance = self.calculate_dtw_distance(
                student_feat,
                ref_feat,
            )

            raw_score = 10 * math.exp(
                -distance / self.max_expected_distance
            )

            return max(0, min(10, raw_score))

        except Exception as exc:
            print(f"Pronunciation score error: {exc}")
            return 0

        finally:
            if tmp_name and os.path.exists(tmp_name):
                try:
                    os.unlink(tmp_name)
                except OSError:
                    pass

    def score_q1_word(self, word_audio_path, word_number):
        """Score a Q1 word against its reference audio."""
        try:
            ref_path = os.path.join(
                settings.BASE_DIR,
                "speaking",
                "reference_audio",
                f"word{word_number}.wav",
            )

            if not os.path.exists(word_audio_path):
                print(f"Student word audio not found: {word_audio_path}")
                return 0

            if not os.path.exists(ref_path):
                print(f"Reference file not found: {ref_path}")
                return 0

            student_feat = self.extract_mfcc(word_audio_path)
            ref_feat = self.extract_mfcc(ref_path)

            if student_feat is None or ref_feat is None:
                return 0

            distance = self.calculate_dtw_distance(
                student_feat,
                ref_feat,
            )

            score = self.normalize_distance(distance)

            # Preserve the existing minimum scores for these words.
            if word_number in [2, 4]:
                score = max(score, 5)

            return round(score, 2)

        except Exception as exc:
            print(f"Error scoring Q1 word {word_number}: {exc}")
            return 0

    def score_q2_sentence(self, student_audio_path):
        transcribed_text = self.transcribe_audio(student_audio_path)
        spoken_words = transcribed_text.lower().split()

        spoken_words = [
            re.sub(r"[^\w\s]", "", word)
            for word in spoken_words
        ]

        print(f"Cleaned words for Q2: {spoken_words}")

        expected = QUESTIONS[2]["expected_words"]
        word_results = []
        total_score = 0

        for i in range(5):
            word_result = {
                "position": i + 1,
                "expected": expected[i],
                "spoken": (
                    spoken_words[i]
                    if i < len(spoken_words)
                    else "[silence]"
                ),
                "grammar_score": 0,
                "coherence_score": 0,
                "total": 0,
            }

            if i < len(spoken_words) and spoken_words[i] in expected:
                word_result["grammar_score"] = 10

            if i < len(spoken_words) and spoken_words[i] == expected[i]:
                word_result["coherence_score"] = 10

            word_result["total"] = (
                word_result["grammar_score"]
                + word_result["coherence_score"]
            )

            total_score += word_result["total"]
            word_results.append(word_result)

        return word_results, total_score

    def score_q3_phrases(self, student_audio_path):
        transcribed_text = self.transcribe_audio(student_audio_path)
        spoken_words = transcribed_text.lower().split()

        expected = QUESTIONS[3]["expected_words"]
        word_results = []
        total_score = 0

        best_alignment = 0
        best_score = 0

        for offset in [-2, -1, 0, 1, 2]:
            matched = 0

            for i in range(len(expected)):
                idx = i + offset

                if (
                    0 <= idx < len(spoken_words)
                    and spoken_words[idx] == expected[i]
                ):
                    matched += 1

            if matched > best_score:
                best_score = matched
                best_alignment = offset

        print(f"Best alignment offset: {best_alignment}")

        for i in range(9):
            spoken_idx = i + best_alignment

            spoken = (
                spoken_words[spoken_idx]
                if 0 <= spoken_idx < len(spoken_words)
                else "[silence]"
            )

            word_result = {
                "position": i + 1,
                "expected": expected[i],
                "spoken": spoken,
                "correctness_score": (
                    5.55 if spoken == expected[i] else 0
                ),
                "fluency_score": (
                    5.55 if spoken != "[silence]" else 0
                ),
                "total": 0,
            }

            if word_result["correctness_score"] > 0:
                word_result["fluency_score"] = 5.55
            elif spoken != "[silence]":
                word_result["fluency_score"] = 2.77

            word_result["total"] = round(
                word_result["correctness_score"]
                + word_result["fluency_score"],
                2,
            )

            total_score += word_result["total"]
            word_results.append(word_result)

        return word_results, total_score

    def score_q4_sentence(self, student_audio_path):
        """Score Q4: 8 words, each with correctness and fluency."""
        transcribed_text = self.transcribe_audio(student_audio_path)
        spoken_words = transcribed_text.lower().split()

        expected = QUESTIONS[4]["expected_words"]
        word_results = []
        total_score = 0

        for i in range(8):
            word_result = {
                "position": i + 1,
                "expected": expected[i] if i < len(expected) else "",
                "spoken": (
                    spoken_words[i]
                    if i < len(spoken_words)
                    else "[silence]"
                ),
                "correctness_score": 0,
                "fluency_score": 0,
                "total": 0,
            }

            if (
                i < len(spoken_words)
                and i < len(expected)
                and spoken_words[i] == expected[i]
            ):
                word_result["correctness_score"] = 6.25
                word_result["fluency_score"] = 6.25

            elif i < len(spoken_words):
                word_result["fluency_score"] = 3.12

            word_result["total"] = round(
                word_result["correctness_score"]
                + word_result["fluency_score"],
                2,
            )

            total_score += word_result["total"]
            word_results.append(word_result)

        return word_results, total_score

    def score_q5_grammar(self, student_audio_path):
        """Score Q5: correctness and grammar."""
        transcribed_text = self.transcribe_audio(student_audio_path)
        spoken_words = transcribed_text.lower().split()

        expected = QUESTIONS[5]["expected_words"]
        word_results = []
        total_score = 0

        for i in range(5):
            word_result = {
                "position": i + 1,
                "expected": expected[i],
                "spoken": (
                    spoken_words[i]
                    if i < len(spoken_words)
                    else "[silence]"
                ),
                "correctness_score": 0,
                "grammar_score": 0,
                "total": 0,
            }

            if i < len(spoken_words) and spoken_words[i] == expected[i]:
                word_result["correctness_score"] = 10

            if i < len(spoken_words):
                if i == 1:
                    if spoken_words[i] in ["goes", "go"]:
                        word_result["grammar_score"] = (
                            10 if spoken_words[i] == "goes" else 5
                        )
                elif spoken_words[i] in expected:
                    word_result["grammar_score"] = 10

            word_result["total"] = (
                word_result["correctness_score"]
                + word_result["grammar_score"]
            )

            total_score += word_result["total"]
            word_results.append(word_result)

        return word_results, total_score

    def score_recording(self, student_audio_path, question_number):
        """Main scoring function for Q2-Q5."""
        if not os.path.exists(student_audio_path):
            return 0, []

        try:
            y, sr = librosa.load(
                student_audio_path,
                sr=self.sample_rate,
            )

            if y.size == 0:
                return 0, []

            energy = librosa.feature.rms(y=y)[0]

            if energy.size == 0 or np.max(energy) < self.silence_threshold:
                return 0, []

        except Exception as exc:
            print(f"Audio validation error: {exc}")
            return 0, []

        if question_number == 2:
            word_results, total = self.score_q2_sentence(
                student_audio_path
            )
        elif question_number == 3:
            word_results, total = self.score_q3_phrases(
                student_audio_path
            )
        elif question_number == 4:
            word_results, total = self.score_q4_sentence(
                student_audio_path
            )
        elif question_number == 5:
            word_results, total = self.score_q5_grammar(
                student_audio_path
            )
        else:
            return 0, []

        return round(total, 2), word_results

    def generate_feedback(self, scores):
        """Generate overall feedback."""
        if not scores:
            return {
                "level": "Needs Practice",
                "message": "Complete a speaking assessment to receive feedback.",
                "average": 0,
            }

        avg_score = sum(scores.values()) / len(scores)

        if avg_score >= 85:
            level = "Excellent"
            message = "Your pronunciation and grammar are excellent!"
        elif avg_score >= 70:
            level = "Good"
            message = "Good job! Minor improvements needed."
        elif avg_score >= 60:
            level = "Fair"
            message = "You're doing well. Focus on problem areas."
        else:
            level = "Needs Practice"
            message = "Keep practicing! Focus on speaking clearly."

        return {
            "level": level,
            "message": message,
            "average": round(avg_score, 2),
        }


# ---------------------------------------------------------
# Singleton instance
# ---------------------------------------------------------

pronunciation_engine = PronunciationEngine()
