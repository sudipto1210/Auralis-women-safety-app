"""
Threat Assessment — Sensor Fusion Engine

Combines motion anomaly scores and audio distress scores
with event-type override logic for research-grade threat assessment.
"""

import time
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Threat level definitions
THREAT_LEVELS = {
    "SAFE": (0.0, 0.2),
    "LOW": (0.2, 0.4),
    "MEDIUM": (0.4, 0.6),
    "HIGH": (0.6, 0.8),
    "CRITICAL": (0.8, 1.0),
}


def get_threat_level(score):
    """Map a 0-1 score to a threat level label."""
    score = max(0.0, min(1.0, float(score)))
    if score >= 0.8:
        return "CRITICAL"
    elif score >= 0.6:
        return "HIGH"
    elif score >= 0.4:
        return "MEDIUM"
    elif score >= 0.2:
        return "LOW"
    return "SAFE"


def fuse_threat_signals(
    motion_result=None, audio_result=None, context_score=0.0, username=None
):
    """
    Fuse motion anomaly and audio distress signals into a unified threat assessment.

    Args:
        motion_result: dict from MotionAnomalyDetector.analyze_window()
            Expected keys: anomaly_score, event_type, confidence
        audio_result: dict from DistressPipeline.analyze()
            Expected keys: distress_score, confidence, alert, environment, event_type
        context_score: float 0-1 from ContextEngine (time-of-day, location risk)
        username: str for logging

    Returns:
        dict: complete threat assessment
    """
    motion_result = motion_result or {
        "anomaly_score": 0.0,
        "event_type": "NONE",
        "confidence": 0.0,
    }
    audio_result = audio_result or {
        "distress_score": 0.0,
        "confidence": 0.0,
        "alert": False,
        "environment": "QUIET",
        "event_type": "NONE",
    }

    motion_score = float(motion_result.get("anomaly_score", 0.0))
    audio_score = float(audio_result.get("distress_score", 0.0))
    motion_event = motion_result.get("event_type", "NONE")
    audio_event = audio_result.get("event_type", "NONE")
    environment = audio_result.get("environment", "QUIET")

    # Base fusion: weighted combination
    # Motion weighted higher — can detect silent attacks
    fused_score = (0.4 * audio_score) + (0.6 * motion_score)

    # Override logic for critical combinations
    override_reason = None

    # GRAB + distress → CRITICAL
    if motion_event == "GRAB" and audio_score > 0.5:
        fused_score = max(fused_score, 0.9)
        override_reason = "GRAB detected with audio distress"

    # FALL + distress → CRITICAL
    if motion_event == "FALL" and audio_score > 0.65:
        fused_score = max(fused_score, 0.85)
        override_reason = "FALL detected with audio distress"

    # Motion alone at very high → HIGH (silent attack scenario)
    if motion_score > 0.85 and audio_score < 0.3:
        fused_score = max(fused_score, 0.65)
        override_reason = "High motion anomaly (possible silent attack)"

    # Audio alone at very high → HIGH (stationary victim scenario)
    if audio_score > 0.88 and motion_score < 0.2:
        fused_score = max(fused_score, 0.65)
        override_reason = "High audio distress (possible stationary victim)"



    # PANIC_RUN event
    if motion_event == "PANIC_RUN":
        fused_score = max(fused_score, 0.6)
        override_reason = "PANIC_RUN event detected"

    # Clamp
    fused_score = max(0.0, min(1.0, fused_score))
    threat_level = get_threat_level(fused_score)
    alert_triggered = threat_level in ("HIGH", "CRITICAL")

    # Determine primary event type
    if motion_event != "NONE":
        primary_event = motion_event
    elif audio_event != "NONE":
        primary_event = audio_event
    else:
        primary_event = "NONE"

    assessment = {
        "fused_score": round(fused_score, 4),
        "threat_level": threat_level,
        "motion_score": round(motion_score, 4),
        "audio_score": round(audio_score, 4),
        "motion_event": motion_event,
        "audio_event": audio_event,
        "event_type": primary_event,
        "environment": environment,
        "alert_triggered": alert_triggered,
        "override_reason": override_reason,
        "context_score": round(float(context_score), 4),
        "timestamp": datetime.now().isoformat(),
        "username": username,
    }

    if alert_triggered:
        logger.warning(
            f"[THREAT] {threat_level}: score={fused_score:.3f} "
            f"motion={motion_score:.3f}({motion_event}) "
            f"audio={audio_score:.3f}({audio_event}) "
            f"user={username}"
        )

    return assessment


def build_incident_record(assessment, user_id=None):
    """
    Build an incident record suitable for Supabase logging.

    Args:
        assessment: dict from fuse_threat_signals()
        user_id: Supabase user ID

    Returns:
        dict: incident record for Supabase incidents table
    """
    return {
        "user_id": user_id,
        "timestamp": assessment.get("timestamp", datetime.now().isoformat()),
        "motion_score": assessment.get("motion_score", 0.0),
        "audio_score": assessment.get("audio_score", 0.0),
        "fused_score": assessment.get("fused_score", 0.0),
        "threat_level": assessment.get("threat_level", "SAFE"),
        "event_type": assessment.get("event_type", "NONE"),
        "environment_class": assessment.get("environment", "QUIET"),
        "alert_triggered": assessment.get("alert_triggered", False),
    }
