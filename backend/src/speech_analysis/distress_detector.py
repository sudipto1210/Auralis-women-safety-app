"""
Distress Detection Module — Multi-layer Audio Pipeline

Replaces RAVDESS emotion classification with binary distress detection.
Pipeline: Environment Classification → VAD → Binary Distress Detection → Adaptive Threshold
"""

import numpy as np
import logging
import os
import time
from datetime import datetime

logger = logging.getLogger(__name__)


class EnvironmentClassifier:
    """
    Layer 1: Classify audio environment.
    Uses spectral features to classify: QUIET, STREET, CROWD, TRANSPORT
    """

    ENVIRONMENT_CLASSES = ["QUIET", "STREET", "CROWD", "TRANSPORT"]

    # Empirical thresholds for rule-based classification
    ENERGY_THRESHOLDS = {
        "QUIET": 0.01,
        "STREET": 0.05,
        "CROWD": 0.15,
        "TRANSPORT": 0.08,
    }

    def __init__(self):
        self._model = None
        self._use_model = False
        self._load_model()

    def _load_model(self):
        """Try to load trained UrbanSound8K classifier."""
        model_path = os.path.join(
            os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            ),
            "models",
            "environment_classifier.pkl",
        )
        try:
            if os.path.exists(model_path):
                import pickle

                with open(model_path, "rb") as f:
                    self._model = pickle.load(f)
                self._use_model = True
                logger.info("Loaded trained environment classifier")
        except Exception as e:
            logger.warning(f"Could not load environment model: {e}")
            self._use_model = False

    def classify(self, audio_features):
        """
        Classify environment from audio features.

        Args:
            audio_features: dict with 'mfccs', 'spectral_contrast', 'zcr', 'energy'

        Returns:
            str: one of QUIET, STREET, CROWD, TRANSPORT
        """
        if self._use_model and self._model is not None:
            try:
                feature_vec = self._build_feature_vector(audio_features)
                prediction = self._model.predict([feature_vec])[0]
                return self.ENVIRONMENT_CLASSES[int(prediction)]
            except Exception:
                pass

        # Rule-based fallback
        return self._rule_based_classify(audio_features)

    def _build_feature_vector(self, audio_features):
        """Build feature vector for model prediction."""
        features = []
        mfccs = audio_features.get("mfccs", [])
        if isinstance(mfccs, np.ndarray):
            features.extend(mfccs.flatten()[:26])  # 13 mean + 13 std
        else:
            features.extend([0.0] * 26)
        features.append(audio_features.get("spectral_contrast_mean", 0.0))
        features.append(audio_features.get("zcr_mean", 0.0))
        features.append(audio_features.get("energy", 0.0))
        return np.array(features, dtype=np.float64)

    def _rule_based_classify(self, audio_features):
        """Classify environment using energy, ZCR, and spectral contrast."""
        energy = audio_features.get("energy", 0.0)
        zcr = audio_features.get("zcr_mean", 0.0)
        spectral_contrast = audio_features.get("spectral_contrast_mean", 0.0)

        if energy < 0.01:
            return "QUIET"
        elif energy < 0.05 and zcr > 0.1:
            return "STREET"
        elif energy > 0.15 and zcr > 0.15:
            return "CROWD"
        elif energy > 0.05 and zcr < 0.08:
            return "TRANSPORT"
        elif energy > 0.1:
            return "CROWD"
        else:
            return "STREET"


class VoiceActivityDetector:
    """
    Layer 2: Detect human voice presence.
    Uses energy threshold + pitch range filter (85Hz-255Hz).
    """

    PITCH_MIN = 85.0  # Hz - lower bound of human voice
    PITCH_MAX = 255.0  # Hz - upper bound (female voice range)
    ENERGY_THRESHOLD = 0.005

    def detect(self, audio_features):
        """
        Detect if human voice is present.

        Args:
            audio_features: dict with 'energy', 'pitch', 'pitch_confidence'

        Returns:
            dict: {voice_detected: bool, reason: str}
        """
        energy = audio_features.get("energy", 0.0)
        pitch = audio_features.get("pitch", 0.0)
        pitch_confidence = audio_features.get("pitch_confidence", 0.0)

        if energy < self.ENERGY_THRESHOLD:
            return {"voice_detected": False, "reason": "energy_below_threshold"}

        if pitch_confidence < 0.3:
            return {"voice_detected": False, "reason": "no_pitch_detected"}

        if pitch < self.PITCH_MIN or pitch > self.PITCH_MAX:
            return {"voice_detected": False, "reason": "pitch_outside_voice_range"}

        return {"voice_detected": True, "reason": "voice_present"}


class BinaryDistressDetector:
    """
    Layer 3: Binary distress vs non-distress classification.
    Uses spectral features for detection. Can use YAMNet or SVM.
    """

    def __init__(self):
        self._model = None
        self._scaler = None
        self._model_type = "rule_based"  # 'yamnet', 'svm', or 'rule_based'
        self._load_model()

    def _load_model(self):
        """Try to load trained distress model."""
        base_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )

        # Try YAMNet-based model first
        yamnet_path = os.path.join(base_dir, "models", "distress_yamnet.keras")
        svm_path = os.path.join(base_dir, "models", "distress_svm.pkl")
        scaler_path = os.path.join(base_dir, "models", "distress_scaler.pkl")

        try:
            if os.path.exists(svm_path):
                import pickle

                with open(svm_path, "rb") as f:
                    self._model = pickle.load(f)
                if os.path.exists(scaler_path):
                    with open(scaler_path, "rb") as f:
                        self._scaler = pickle.load(f)
                self._model_type = "svm"
                logger.info("Loaded SVM distress model")
            elif os.path.exists(yamnet_path):
                from tensorflow.keras.models import load_model as keras_load

                self._model = keras_load(yamnet_path)
                self._model_type = "yamnet"
                logger.info("Loaded YAMNet distress model")
        except Exception as e:
            logger.warning(
                f"Could not load distress model: {e}. Using rule-based fallback."
            )
            self._model_type = "rule_based"

    def predict(self, audio_features):
        """
        Predict distress probability.

        Args:
            audio_features: dict with MFCCs, spectral features, pitch, energy

        Returns:
            dict: {distress_score: 0.0-1.0, confidence: float, raw_label: str}
        """
        if self._model_type == "svm" and self._model is not None:
            return self._predict_svm(audio_features)
        elif self._model_type == "yamnet" and self._model is not None:
            return self._predict_yamnet(audio_features)
        else:
            return self._predict_rule_based(audio_features)

    def _predict_svm(self, audio_features):
        """SVM-based distress prediction."""
        try:
            feature_vec = self._build_feature_vector(audio_features)
            if self._scaler:
                feature_vec = self._scaler.transform([feature_vec])[0]

            proba = self._model.predict_proba([feature_vec])[0]
            distress_idx = 1  # assume class 1 = distress
            distress_score = (
                float(proba[distress_idx]) if len(proba) > 1 else float(proba[0])
            )

            return {
                "distress_score": round(distress_score, 4),
                "confidence": round(max(proba), 4),
                "raw_label": "distress" if distress_score > 0.5 else "non_distress",
            }
        except Exception as e:
            logger.error(f"SVM prediction error: {e}")
            return self._predict_rule_based(audio_features)

    def _predict_yamnet(self, audio_features):
        """YAMNet-based distress prediction."""
        try:
            feature_vec = self._build_feature_vector(audio_features)
            pred = self._model.predict(np.array([feature_vec]), verbose=0)
            distress_score = (
                float(pred[0][1]) if pred.shape[-1] > 1 else float(pred[0][0])
            )

            return {
                "distress_score": round(distress_score, 4),
                "confidence": round(float(max(pred[0])), 4),
                "raw_label": "distress" if distress_score > 0.5 else "non_distress",
            }
        except Exception as e:
            logger.error(f"YAMNet prediction error: {e}")
            return self._predict_rule_based(audio_features)

    def _predict_rule_based(self, audio_features):
        """
        Rule-based distress estimation using spectral features.
        High energy + high pitch + high spectral contrast = likely distress.
        """
        energy = audio_features.get("energy", 0.0)
        pitch = audio_features.get("pitch", 0.0)
        pitch_variance = audio_features.get("pitch_variance", 0.0)
        spectral_contrast = audio_features.get("spectral_contrast_mean", 0.0)
        zcr = audio_features.get("zcr_mean", 0.0)
        mfcc_delta_mean = audio_features.get("mfcc_delta_mean", 0.0)

        # Scoring heuristic based on distress acoustic signatures
        score = 0.0

        # High energy suggests shouting/screaming
        if energy > 0.3:
            score += 0.25
        elif energy > 0.15:
            score += 0.15

        # High pitch suggests distress vocalization
        if pitch > 200:
            score += 0.2
        elif pitch > 150:
            score += 0.1

        # High pitch variance suggests irregular/panicked speech
        if pitch_variance > 50:
            score += 0.15

        # High spectral contrast suggests sharp, sudden sounds
        if spectral_contrast > 30:
            score += 0.15
        elif spectral_contrast > 15:
            score += 0.08

        # High ZCR suggests noisy/harsh sounds
        if zcr > 0.15:
            score += 0.1

        # Rapid MFCC changes suggest sudden vocalizations
        if abs(mfcc_delta_mean) > 5:
            score += 0.15

        score = min(1.0, max(0.0, score))
        confidence = min(0.7, score + 0.2)  # rule-based has capped confidence

        return {
            "distress_score": round(score, 4),
            "confidence": round(confidence, 4),
            "raw_label": "distress" if score > 0.5 else "non_distress",
        }

    def _build_feature_vector(self, audio_features):
        """Build flat feature vector for model input."""
        features = []

        # MFCCs (13 coefficients)
        mfccs = audio_features.get("mfccs", np.zeros(13))
        if isinstance(mfccs, np.ndarray):
            features.extend(mfccs.flatten()[:13])
        elif isinstance(mfccs, list):
            features.extend(mfccs[:13])
        else:
            features.extend([0.0] * 13)

        # Pad to 13 if short
        while len(features) < 13:
            features.append(0.0)

        # Additional features
        features.append(audio_features.get("spectral_contrast_mean", 0.0))
        features.append(audio_features.get("pitch", 0.0))
        features.append(audio_features.get("pitch_variance", 0.0))
        features.append(audio_features.get("energy", 0.0))
        features.append(audio_features.get("zcr_mean", 0.0))

        return np.array(features, dtype=np.float64)


class AdaptiveThresholdEngine:
    """
    Layer 4: Adjust distress threshold based on environment.
    """

    ENVIRONMENT_THRESHOLDS = {
        "QUIET": 0.45,
        "STREET": 0.60,
        "CROWD": 0.72,
        "TRANSPORT": 0.78,
    }

    def apply(self, distress_result, environment):
        """
        Apply adaptive threshold to distress score.

        Args:
            distress_result: dict from BinaryDistressDetector
            environment: str from EnvironmentClassifier

        Returns:
            dict: {alert: bool, adjusted_score: float, environment: str,
                   threshold_used: float, event_type: str}
        """
        threshold = self.ENVIRONMENT_THRESHOLDS.get(environment, 0.60)
        distress_score = distress_result.get("distress_score", 0.0)
        confidence = distress_result.get("confidence", 0.0)

        # Adjust score: weight by confidence
        adjusted_score = distress_score * (0.6 + 0.4 * confidence)
        alert = adjusted_score > threshold

        event_type = "NONE"
        if alert:
            if adjusted_score > 0.85:
                event_type = "SCREAM"
            elif adjusted_score > 0.70:
                event_type = "SHOUT"
            else:
                event_type = "DISTRESS_VOCAL"

        return {
            "alert": alert,
            "adjusted_score": round(float(adjusted_score), 4),
            "environment": environment,
            "threshold_used": threshold,
            "event_type": event_type,
            "raw_distress_score": distress_result.get("distress_score", 0.0),
            "raw_confidence": confidence,
        }


class DistressPipeline:
    """
    Full audio distress pipeline combining all 4 layers.
    """

    def __init__(self):
        self.environment_classifier = EnvironmentClassifier()
        self.vad = VoiceActivityDetector()
        self.distress_detector = BinaryDistressDetector()
        self.adaptive_threshold = AdaptiveThresholdEngine()
        logger.info("Distress pipeline initialized")

    def analyze(self, audio_features):
        """
        Run full audio distress pipeline.

        Args:
            audio_features: dict with all audio features
                Required keys: mfccs, spectral_contrast_mean, zcr_mean, energy,
                               pitch, pitch_confidence, pitch_variance

        Returns:
            dict: complete analysis result
        """
        start_time = time.time()

        # Layer 1: Environment classification
        environment = self.environment_classifier.classify(audio_features)

        # Layer 2: Voice Activity Detection
        vad_result = self.vad.detect(audio_features)
        if not vad_result["voice_detected"]:
            return {
                "distress_score": 0.0,
                "confidence": 0.0,
                "alert": False,
                "environment": environment,
                "vad": vad_result,
                "event_type": "NONE",
                "reason": "no_voice",
                "latency_ms": round((time.time() - start_time) * 1000, 2),
            }

        # Layer 3: Binary distress detection
        distress_result = self.distress_detector.predict(audio_features)

        # Layer 4: Adaptive thresholding
        threshold_result = self.adaptive_threshold.apply(distress_result, environment)

        latency_ms = round((time.time() - start_time) * 1000, 2)

        return {
            "distress_score": threshold_result["adjusted_score"],
            "confidence": distress_result["confidence"],
            "alert": threshold_result["alert"],
            "environment": environment,
            "vad": vad_result,
            "event_type": threshold_result["event_type"],
            "threshold_used": threshold_result["threshold_used"],
            "raw_distress_score": distress_result["distress_score"],
            "raw_label": distress_result["raw_label"],
            "reason": "distress_analysis_complete",
            "latency_ms": latency_ms,
        }


def extract_audio_features(audio_data, sr=16000):
    """
    Extract audio features from raw audio data for the distress pipeline.
    Pure numpy implementation — no librosa dependency at runtime.

    Args:
        audio_data: numpy array of audio samples
        sr: sample rate

    Returns:
        dict of audio features
    """
    if audio_data is None or len(audio_data) < 200:
        return _empty_features()

    audio = np.array(audio_data, dtype=np.float64)

    # Normalize
    max_val = np.max(np.abs(audio))
    if max_val > 0:
        audio = audio / max_val

    # Energy (RMS)
    energy = float(np.sqrt(np.mean(audio**2)))

    # Zero Crossing Rate
    zcr = np.mean(np.abs(np.diff(np.sign(audio)))) / 2.0

    # MFCCs (simplified numpy implementation)
    mfccs = _compute_mfccs(audio, sr, n_mfcc=13)
    mfcc_delta = np.diff(mfccs) if len(mfccs) > 1 else np.zeros(1)

    # Pitch estimation (autocorrelation method)
    pitch, pitch_confidence = _estimate_pitch(audio, sr)

    # Spectral contrast
    spectral_contrast = _compute_spectral_contrast(audio, sr)

    # Pitch variance over frames
    pitch_variance = _compute_pitch_variance(audio, sr)

    return {
        "mfccs": mfccs,
        "mfcc_delta_mean": float(np.mean(np.abs(mfcc_delta))),
        "spectral_contrast_mean": float(spectral_contrast),
        "zcr_mean": float(zcr),
        "energy": float(energy),
        "pitch": float(pitch),
        "pitch_confidence": float(pitch_confidence),
        "pitch_variance": float(pitch_variance),
    }


def _empty_features():
    return {
        "mfccs": np.zeros(13),
        "mfcc_delta_mean": 0.0,
        "spectral_contrast_mean": 0.0,
        "zcr_mean": 0.0,
        "energy": 0.0,
        "pitch": 0.0,
        "pitch_confidence": 0.0,
        "pitch_variance": 0.0,
    }


def _compute_mfccs(audio, sr, n_mfcc=13, n_fft=2048, hop_length=512, n_mels=40):
    """Compute MFCCs using numpy."""
    # Frame the signal
    n_frames = 1 + (len(audio) - n_fft) // hop_length
    if n_frames < 1:
        return np.zeros(n_mfcc)

    frames = np.stack(
        [audio[i * hop_length : i * hop_length + n_fft] for i in range(n_frames)]
    )

    # Apply Hamming window
    window = np.hamming(n_fft)
    frames = frames * window

    # FFT
    fft_result = np.fft.rfft(frames, n=n_fft)
    power_spectrum = np.abs(fft_result) ** 2 / n_fft

    # Mel filterbank
    mel_filters = _mel_filterbank(sr, n_fft, n_mels)
    mel_spectrum = np.dot(power_spectrum, mel_filters.T)
    mel_spectrum = np.maximum(mel_spectrum, 1e-10)
    log_mel = np.log(mel_spectrum)

    # DCT to get MFCCs
    n_coeff = log_mel.shape[1]
    dct_matrix = np.zeros((n_mfcc, n_coeff))
    for i in range(n_mfcc):
        for j in range(n_coeff):
            dct_matrix[i, j] = np.cos(np.pi * i * (2 * j + 1) / (2 * n_coeff))

    mfccs = np.dot(log_mel, dct_matrix.T)
    return np.mean(mfccs, axis=0)  # Average across frames


def _mel_filterbank(sr, n_fft, n_mels):
    """Create mel filterbank."""
    f_min = 0
    f_max = sr / 2
    mel_min = 2595 * np.log10(1 + f_min / 700)
    mel_max = 2595 * np.log10(1 + f_max / 700)
    mel_points = np.linspace(mel_min, mel_max, n_mels + 2)
    freq_points = 700 * (10 ** (mel_points / 2595) - 1)
    bin_points = np.floor((n_fft + 1) * freq_points / sr).astype(int)

    n_freq_bins = n_fft // 2 + 1
    filters = np.zeros((n_mels, n_freq_bins))

    for i in range(n_mels):
        left = bin_points[i]
        center = bin_points[i + 1]
        right = bin_points[i + 2]

        for j in range(left, center):
            if j < n_freq_bins and center > left:
                filters[i, j] = (j - left) / (center - left)
        for j in range(center, right):
            if j < n_freq_bins and right > center:
                filters[i, j] = (right - j) / (right - center)

    return filters


def _estimate_pitch(audio, sr, frame_size=2048):
    """Estimate pitch via autocorrelation."""
    if len(audio) < frame_size:
        return 0.0, 0.0

    frame = audio[:frame_size]
    # Autocorrelation
    corr = np.correlate(frame, frame, mode="full")
    corr = corr[len(corr) // 2 :]

    # Find first peak after initial decline
    min_lag = int(sr / 255)  # Max freq 255Hz
    max_lag = int(sr / 85)  # Min freq 85Hz

    if max_lag >= len(corr):
        max_lag = len(corr) - 1
    if min_lag >= max_lag:
        return 0.0, 0.0

    segment = corr[min_lag:max_lag]
    if len(segment) == 0:
        return 0.0, 0.0

    peak_idx = np.argmax(segment) + min_lag
    pitch = sr / peak_idx if peak_idx > 0 else 0.0
    confidence = corr[peak_idx] / (corr[0] + 1e-10)

    return float(pitch), float(max(0, min(1, confidence)))


def _compute_spectral_contrast(audio, sr, n_fft=2048):
    """Compute mean spectral contrast."""
    if len(audio) < n_fft:
        return 0.0

    fft_result = np.fft.rfft(audio[:n_fft])
    magnitude = np.abs(fft_result)

    if len(magnitude) < 2:
        return 0.0

    # Split into bands and compute contrast
    n_bands = 6
    band_size = len(magnitude) // n_bands
    contrasts = []

    for i in range(n_bands):
        band = magnitude[i * band_size : (i + 1) * band_size]
        if len(band) > 0:
            peak = np.max(band)
            valley = np.min(band)
            contrast = peak - valley
            contrasts.append(contrast)

    return float(np.mean(contrasts)) if contrasts else 0.0


def _compute_pitch_variance(audio, sr, frame_size=2048, hop=1024):
    """Compute pitch variance across frames."""
    pitches = []
    for i in range(0, len(audio) - frame_size, hop):
        frame = audio[i : i + frame_size]
        p, c = _estimate_pitch(frame, sr)
        if c > 0.3 and p > 0:
            pitches.append(p)

    if len(pitches) < 2:
        return 0.0
    return float(np.var(pitches))
