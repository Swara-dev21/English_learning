import librosa
import numpy as np
from fastdtw import fastdtw
from scipy.spatial.distance import euclidean


def extract_mfcc(audio_path):

    # Load audio
    y, sr = librosa.load(audio_path, sr=16000)

    # Remove silence
    y, _ = librosa.effects.trim(y)

    # Normalize volume
    y = librosa.util.normalize(y)

    # Extract MFCC
    mfcc = librosa.feature.mfcc(
        y=y,
        sr=sr,
        n_mfcc=13
    )

    # Mean normalization (VERY IMPORTANT)
    mfcc = mfcc - np.mean(mfcc, axis=1, keepdims=True)

    return mfcc



def compare_mfcc(reference_path, user_path):
    """
    Compare two audio files using MFCC + DTW
    Returns normalized distance score
    """

    # extract MFCC features
    mfcc_ref = extract_mfcc(reference_path)
    mfcc_user = extract_mfcc(user_path)

    # transpose for DTW
    mfcc_ref = mfcc_ref.T
    mfcc_user = mfcc_user.T

    # Safety check (avoid empty audio issue)
    if mfcc_ref.shape[0] < 5 or mfcc_user.shape[0] < 5:
        return 50000  # safe high distance (will give low but not zero score)

    # calculate DTW distance
    distance, path = fastdtw(
        mfcc_ref,
        mfcc_user,
        dist=euclidean
    )

    # 🔥 KEY FIX: Normalize by alignment path length
    normalized_distance = distance / len(path)

    return normalized_distance

def distance_to_score(distance):

    # Smooth exponential scaling
    score = 100 * np.exp(-distance / 50)

    # Clamp between 10 and 100 (no 0.00 anymore)
    score = max(10, min(100, score))

    return round(score, 2)