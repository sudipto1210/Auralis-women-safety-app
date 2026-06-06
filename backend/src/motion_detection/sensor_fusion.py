"""
Sensor Fusion Module — IMU-based Motion Anomaly Detection

Replaces CV2 camera-based motion detection with accelerometer/gyroscope
sensor data from client-side DeviceMotion API.
"""

import numpy as np
import time
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class BaselineProfiler:
    """Builds per-user motion baseline from 30s of walking data."""

    @staticmethod
    def extract_features(readings):
        """
        Extract motion features from a window of sensor readings.

        Args:
            readings: list of dicts with keys {ax, ay, az, gx, gy, gz, timestamp}

        Returns:
            dict of extracted features
        """
        if not readings or len(readings) < 2:
            return None

        ax = np.array([r["ax"] for r in readings], dtype=np.float64)
        ay = np.array([r["ay"] for r in readings], dtype=np.float64)
        az = np.array([r["az"] for r in readings], dtype=np.float64)
        gx = np.array([r.get("gx", 0) for r in readings], dtype=np.float64)
        gy = np.array([r.get("gy", 0) for r in readings], dtype=np.float64)
        gz = np.array([r.get("gz", 0) for r in readings], dtype=np.float64)
        timestamps = np.array([r["timestamp"] for r in readings], dtype=np.float64)

        # Total acceleration magnitude
        accel_mag = np.sqrt(ax**2 + ay**2 + az**2)

        # Step cadence estimation via zero-crossing of filtered accel
        accel_detrended = accel_mag - np.mean(accel_mag)
        zero_crossings = np.sum(np.diff(np.sign(accel_detrended)) != 0)
        duration = max(timestamps[-1] - timestamps[0], 0.001)
        cadence = zero_crossings / (2.0 * duration)  # steps per second

        # Jerk (rate of acceleration change)
        dt = np.diff(timestamps)
        dt = np.where(dt < 1e-6, 1e-6, dt)  # avoid division by zero
        jerk_x = np.diff(ax) / dt
        jerk_y = np.diff(ay) / dt
        jerk_z = np.diff(az) / dt
        jerk_mag = np.sqrt(jerk_x**2 + jerk_y**2 + jerk_z**2)

        # Peak magnitude distribution
        peak_95th = float(np.percentile(accel_mag, 95)) if len(accel_mag) > 0 else 0.0

        features = {
            "cadence_mean": float(cadence),
            "cadence_std": float(np.std(accel_detrended)),
            "accel_variance_x": float(np.var(ax)),
            "accel_variance_y": float(np.var(ay)),
            "accel_variance_z": float(np.var(az)),
            "accel_variance": float(np.var(accel_mag)),
            "peak_magnitude_95th": peak_95th,
            "jerk_mean": float(np.mean(jerk_mag)) if len(jerk_mag) > 0 else 0.0,
            "jerk_std": float(np.std(jerk_mag)) if len(jerk_mag) > 0 else 0.0,
            "gyro_variance": float(np.var(np.sqrt(gx**2 + gy**2 + gz**2))),
            "duration": float(duration),
            "sample_count": len(readings),
        }
        return features

    @staticmethod
    def build_baseline(normal_readings, elevated_readings=None):
        """
        Build a user motion baseline from normal (30s) and optional elevated (15s) walking data.

        Returns:
            dict suitable for storing in Supabase user_motion_profiles
        """
        normal_features = BaselineProfiler.extract_features(normal_readings)
        if normal_features is None:
            return None

        baseline = {
            "cadence_mean": normal_features["cadence_mean"],
            "cadence_std": max(normal_features["cadence_std"], 0.05),
            "accel_variance": normal_features["accel_variance"],
            "peak_magnitude_95th": normal_features["peak_magnitude_95th"],
            "jerk_mean": normal_features["jerk_mean"],
            "jerk_std": max(normal_features["jerk_std"], 0.1),
            "gyro_variance": normal_features["gyro_variance"],
            "created_at": datetime.now().isoformat(),
        }

        # If elevated readings provided, compute elevated thresholds
        if elevated_readings:
            elevated_features = BaselineProfiler.extract_features(elevated_readings)
            if elevated_features:
                baseline["elevated_jerk_mean"] = elevated_features["jerk_mean"]
                baseline["elevated_accel_variance"] = elevated_features[
                    "accel_variance"
                ]

        return baseline


class MotionAnomalyDetector:
    """Real-time anomaly detection against stored user baseline."""

    # Event detection constants
    FREEFALL_THRESHOLD = 0.1  # ~0.1g indicates freefall
    IMPACT_THRESHOLD = 3.0  # >3g indicates impact
    FREEFALL_IMPACT_WINDOW = 0.5  # 500ms window for fall detection
    STRUGGLE_JERK_MULTIPLIER = 3.0
    STRUGGLE_DURATION = 3.0  # seconds of sustained erratic motion
    GRAB_THRESHOLD = 4.0  # single spike >4g

    DEFAULT_BASELINE = {
        "cadence_mean": 1.8,
        "cadence_std": 0.3,
        "accel_variance": 0.15,
        "peak_magnitude_95th": 2.5,
        "jerk_mean": 0.8,
        "jerk_std": 0.4,
        "gyro_variance": 0.1,
    }

    def __init__(self, baseline=None):
        self.baseline = baseline or self.DEFAULT_BASELINE.copy()
        self._struggle_start = None

    def update_baseline(self, baseline):
        if baseline:
            self.baseline = baseline

    def analyze_window(self, sensor_window):
        """
        Analyze a 5-second rolling window of sensor readings.

        Args:
            sensor_window: list of dicts {ax, ay, az, gx, gy, gz, timestamp}

        Returns:
            dict: {anomaly_score, event_type, confidence, timestamp}
        """
        if not sensor_window or len(sensor_window) < 5:
            return {
                "anomaly_score": 0.0,
                "event_type": "NONE",
                "confidence": 0.0,
                "timestamp": datetime.now().isoformat(),
            }

        features = BaselineProfiler.extract_features(sensor_window)
        if features is None:
            return {
                "anomaly_score": 0.0,
                "event_type": "NONE",
                "confidence": 0.0,
                "timestamp": datetime.now().isoformat(),
            }

        # Compute z-scores against baseline
        z_scores = {}
        for key in [
            "cadence_mean",
            "accel_variance",
            "peak_magnitude_95th",
            "jerk_mean",
            "gyro_variance",
        ]:
            baseline_val = self.baseline.get(key, 0.0)
            baseline_std = self.baseline.get(
                f"{key}_std", self.baseline.get("cadence_std", 0.3)
            )
            baseline_std = max(baseline_std, 0.01)  # avoid div by zero
            current_val = features.get(key, 0.0)
            z_scores[key] = abs(current_val - baseline_val) / baseline_std

        # Aggregate anomaly score (max z-score, normalized to 0-1)
        max_z = max(z_scores.values()) if z_scores else 0.0
        anomaly_score = min(1.0, max_z / 5.0)  # z=5 maps to score 1.0

        # Event detection
        event_type, event_confidence = self._detect_events(sensor_window, features)

        # If specific event detected, boost anomaly score
        if event_type != "NONE":
            anomaly_score = max(anomaly_score, event_confidence)

        return {
            "anomaly_score": round(float(anomaly_score), 4),
            "event_type": event_type,
            "confidence": round(
                float(event_confidence if event_type != "NONE" else anomaly_score), 4
            ),
            "timestamp": datetime.now().isoformat(),
            "z_scores": {k: round(v, 3) for k, v in z_scores.items()},
            "features": {
                k: round(v, 4) for k, v in features.items() if isinstance(v, float)
            },
        }

    def _detect_events(self, sensor_window, features):
        """
        Detect specific event types: FALL, STRUGGLE, GRABBED

        Returns:
            (event_type, confidence)
        """
        ax = np.array([r["ax"] for r in sensor_window], dtype=np.float64)
        ay = np.array([r["ay"] for r in sensor_window], dtype=np.float64)
        az = np.array([r["az"] for r in sensor_window], dtype=np.float64)
        timestamps = np.array([r["timestamp"] for r in sensor_window], dtype=np.float64)
        accel_mag = np.sqrt(ax**2 + ay**2 + az**2)

        # FALL DETECTION: freefall (~0g) followed by impact (>3g) within 500ms
        fall_detected, fall_conf = self._detect_fall(accel_mag, timestamps)
        if fall_detected:
            return "FALL", fall_conf

        # GRABBED DETECTION: sudden spike >4g without fall pattern
        grab_detected, grab_conf = self._detect_grab(accel_mag, timestamps)
        if grab_detected:
            return "GRABBED", grab_conf

        # STRUGGLE DETECTION: sustained erratic high-variance motion
        struggle_detected, struggle_conf = self._detect_struggle(features)
        if struggle_detected:
            return "STRUGGLE", struggle_conf

        return "NONE", 0.0

    def _detect_fall(self, accel_mag, timestamps):
        """Detect freefall signature followed by impact spike."""
        freefall_indices = np.where(accel_mag < self.FREEFALL_THRESHOLD)[0]
        if len(freefall_indices) == 0:
            return False, 0.0

        for ff_idx in freefall_indices:
            ff_time = timestamps[ff_idx]
            # Look for impact spike within 500ms after freefall
            window_mask = (timestamps > ff_time) & (
                timestamps <= ff_time + self.FREEFALL_IMPACT_WINDOW
            )
            if np.any(window_mask):
                window_accel = accel_mag[window_mask]
                max_impact = np.max(window_accel)
                if max_impact > self.IMPACT_THRESHOLD:
                    confidence = min(1.0, max_impact / (self.IMPACT_THRESHOLD * 2))
                    return True, max(0.7, confidence)

        return False, 0.0

    def _detect_grab(self, accel_mag, timestamps):
        """Detect sudden single acceleration spike >4g."""
        spikes = np.where(accel_mag > self.GRAB_THRESHOLD)[0]
        if len(spikes) == 0:
            return False, 0.0

        # Check it's a sudden spike, not sustained (which would be struggle)
        max_spike = np.max(accel_mag[spikes])
        for idx in spikes:
            if idx > 0 and idx < len(accel_mag) - 1:
                if accel_mag[idx - 1] < self.GRAB_THRESHOLD * 0.5:
                    confidence = min(1.0, max_spike / (self.GRAB_THRESHOLD * 2))
                    return True, max(0.65, confidence)

        return False, 0.0

    def _detect_struggle(self, features):
        """Detect sustained erratic high-variance motion."""
        baseline_jerk = self.baseline.get("jerk_mean", 0.8)
        current_jerk = features.get("jerk_mean", 0.0)

        if current_jerk > baseline_jerk * self.STRUGGLE_JERK_MULTIPLIER:
            now = time.time()
            if self._struggle_start is None:
                self._struggle_start = now

            duration = now - self._struggle_start
            if duration >= self.STRUGGLE_DURATION:
                confidence = min(
                    1.0,
                    current_jerk / (baseline_jerk * self.STRUGGLE_JERK_MULTIPLIER * 2),
                )
                return True, max(0.6, confidence)
        else:
            self._struggle_start = None

        return False, 0.0
