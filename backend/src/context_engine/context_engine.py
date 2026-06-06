"""
Dynamic Context Engine Module
-----------------------------
Provides adaptive, environment-oriented context awareness
to enhance behavioral threat detection.

Key properties:
- Dynamic weighting (situation-aware)
- Environment-driven risk modulation
- Temporal smoothing (context memory)
- Privacy-preserving (no object detection)

Output:
- Normalized context risk score (0.0 – 1.0)
"""

from datetime import datetime
import numpy as np
from collections import deque


class ContextEngine:
    def __init__(
        self,
        night_start=22,
        night_end=5,
        dark_threshold=70,
        history_size=10,
        ema_alpha=0.4,
    ):
        self.night_start = night_start
        self.night_end = night_end
        self.dark_threshold = dark_threshold

        # Context memory (for temporal awareness)
        self.context_history = deque(maxlen=history_size)
        self.ema_alpha = ema_alpha
        self.context_ema = 0.0

    # ==========================================================
    # TIME CONTEXT (DYNAMIC)
    # ==========================================================
    def compute_time_risk(self):
        hour = datetime.now().hour

        if hour >= self.night_start or hour <= self.night_end:
            return 0.8
        elif 18 <= hour < self.night_start:
            return 0.5
        else:
            return 0.3

    # ==========================================================
    # LOCATION CONTEXT
    # ==========================================================
    def compute_location_risk(self, near_police, near_hospital, public_place):
        if near_police:
            return 0.2
        if near_hospital:
            return 0.3
        if public_place:
            return 0.45
        return 0.75

    # ==========================================================
    # ENVIRONMENT CONTEXT (MULTI-SIGNAL)
    # ==========================================================
    def compute_environment_risk(self, frame, motion_intensity):
        """
        Uses brightness + motion energy to infer environment quality.
        """
        if frame is None:
            return 0.5

        brightness = np.mean(frame)
        brightness_risk = 0.7 if brightness < self.dark_threshold else 0.3

        # Motion instability → chaotic surroundings
        if motion_intensity > 0.6:
            motion_risk = 0.7
        elif motion_intensity > 0.3:
            motion_risk = 0.5
        else:
            motion_risk = 0.3

        return round(0.6 * brightness_risk + 0.4 * motion_risk, 3)

    # ==========================================================
    # SOCIAL CONTEXT (DYNAMIC ISOLATION)
    # ==========================================================
    def compute_isolation_risk(self, motion_blob_count):
        if motion_blob_count == 0:
            return 0.85
        if motion_blob_count <= 2:
            return 0.65
        if motion_blob_count <= 5:
            return 0.4
        return 0.25

    # ==========================================================
    # DYNAMIC WEIGHT ADAPTATION
    # ==========================================================
    def compute_dynamic_weights(self, time_risk, environment_risk):
        """
        Environment dictates which context matters more.
        """
        if time_risk > 0.6 and environment_risk > 0.6:
            # Dangerous situation → isolation & environment matter more
            return {
                "time": 0.15,
                "location": 0.25,
                "environment": 0.30,
                "isolation": 0.30,
            }

        # Normal conditions
        return {"time": 0.20, "location": 0.30, "environment": 0.20, "isolation": 0.30}

    # ==========================================================
    # CONTEXT SCORE (FULLY DYNAMIC)
    # ==========================================================
    def compute_context_score(
        self,
        *,
        frame=None,
        motion_blob_count=0,
        motion_intensity=0.0,
        near_police=False,
        near_hospital=False,
        public_place=True
    ):
        time_risk = self.compute_time_risk()
        location_risk = self.compute_location_risk(
            near_police, near_hospital, public_place
        )
        environment_risk = self.compute_environment_risk(frame, motion_intensity)
        isolation_risk = self.compute_isolation_risk(motion_blob_count)

        weights = self.compute_dynamic_weights(time_risk, environment_risk)

        raw_context_score = (
            time_risk * weights["time"]
            + location_risk * weights["location"]
            + environment_risk * weights["environment"]
            + isolation_risk * weights["isolation"]
        )

        # ======================================================
        # TEMPORAL SMOOTHING (EMA)
        # ======================================================
        self.context_ema = (
            self.ema_alpha * raw_context_score + (1 - self.ema_alpha) * self.context_ema
        )

        self.context_history.append(self.context_ema)

        return round(min(1.0, max(0.0, self.context_ema)), 3)

    # ==========================================================
    # CONTEXT SNAPSHOT (FOR LOGS / UI / ADMIN)
    # ==========================================================
    def get_context_snapshot(
        self,
        *,
        frame=None,
        motion_blob_count=0,
        motion_intensity=0.0,
        near_police=False,
        near_hospital=False,
        public_place=True
    ):
        score = self.compute_context_score(
            frame=frame,
            motion_blob_count=motion_blob_count,
            motion_intensity=motion_intensity,
            near_police=near_police,
            near_hospital=near_hospital,
            public_place=public_place,
        )

        return {
            "time_risk": self.compute_time_risk(),
            "location_risk": self.compute_location_risk(
                near_police, near_hospital, public_place
            ),
            "environment_risk": self.compute_environment_risk(frame, motion_intensity),
            "isolation_risk": self.compute_isolation_risk(motion_blob_count),
            "context_score": score,
        }
