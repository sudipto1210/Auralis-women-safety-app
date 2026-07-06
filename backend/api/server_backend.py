"""
Flask Backend – Women Safety Assistant
"""

import os
import time
import threading
import json
from datetime import datetime

import numpy as np
from flask import (
    Flask,
    render_template,
    Response,
    jsonify,
    request,
    session,
    redirect,
    url_for,
)
from dotenv import load_dotenv
from flask_cors import CORS

from api.mobile_auth import create_mobile_token, verify_mobile_token

# Import Google OAuth module (cloud-safe)
try:
    from api.google_oauth import (
        load_google_oauth_config,
        verify_google_id_token,
        create_or_update_user_google,
        register_oauth_routes,
    )
except ImportError as e:
    print(f"[WARN] Google OAuth import failed (cloud mode?): {e}")
    load_google_oauth_config = lambda: {}
    verify_google_id_token = lambda t: None
    create_or_update_user_google = lambda u, *args: ("demo", True)
    register_oauth_routes = lambda a: None

# Import Supabase database module
from database.database import (
    get_supabase,
    init_supabase,
    UserDB,
    EmergencyContactsDB,
    ActivityLogsDB,
    ConfigDB,
    ensure_admin_exists,
    check_database_connection,
)

# =========================================================
# ENV + BASIC CONFIG
# =========================================================

load_dotenv()

IS_CLOUD = os.environ.get("RENDER") == "true"
PRODUCTION = os.environ.get("PRODUCTION", "false").lower() == "true"

# Define paths (points to backend/ folder)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
INCIDENTS_FILE = os.path.join(DATA_DIR, "incident_timeline.json")
BASELINES_FILE = os.path.join(DATA_DIR, "baseline_profiles.json")

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static"),
)

# Production security settings
app.secret_key = os.environ.get("SECRET_KEY", "change-this-in-production")
app.config["SESSION_COOKIE_SECURE"] = PRODUCTION
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["DEBUG"] = False
app.config["TESTING"] = False

CORS(
    app,
    resources={r"/api/*": {"origins": "*"}},
    supports_credentials=False,
    allow_headers=["Content-Type", "Authorization"],
)

# Register Data Collection Blueprint
from collect_data import collect_bp
app.register_blueprint(collect_bp)

# CSRF protection disabled (no forms requiring CSRF in this app)


@app.before_request
def bind_mobile_bearer_session():
    """Let React Native clients authenticate with Authorization: Bearer tokens."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return
    email = verify_mobile_token(auth[7:].strip())
    if not email:
        return
    session["username"] = email
    user = UserDB.get_by_email(email)
    if user:
        session["needs_onboarding"] = user.get("needs_onboarding", True)
        session["user_name"] = user.get("name", email)
        session["user_picture"] = user.get("picture", "")
        session["is_admin"] = user.get("is_admin", False)


# Load Google OAuth config
oauth_config = load_google_oauth_config()
GOOGLE_CLIENT_ID = oauth_config["client_id"]

# =========================================================
# SENSOR FUSION MODULES (replaces CV2 camera system)
# =========================================================

from src.motion_detection.sensor_fusion import BaselineProfiler
from motion_anomaly_detector import MotionAnomalyDetector
from src.speech_analysis.distress_detector import (
    DistressPipeline,
    extract_audio_features,
)
from src.threat_assessment.threat_fusion import (
    fuse_threat_signals as fuse_new_threat,
    get_threat_level,
    build_incident_record,
)

# =========================================================
# UTILITIES
# =========================================================


def rotate_session():
    session.clear()
    session.modified = True


def log_activity(user_type, username, action, details=""):
    """Log user/admin activity to database"""
    try:
        ActivityLogsDB.log(user_type, username, action, details)
        print(f"[ACTIVITY LOG] {user_type.upper()} {username}: {action} - {details}")
    except Exception as e:
        print(f"Error logging activity to database: {e}")


def load_json_file(path, default):
    try:
        if not os.path.exists(path):
            return default
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {path}: {e}")
        return default


def save_json_file(path, data):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp_path = f"{path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, path)
    except Exception as e:
        print(f"Error saving {path}: {e}")


# =========================================================
# DATABASE INITIALIZATION
# =========================================================


def initialize_database():
    """Initialize database connection and ensure admin exists"""
    try:
        # Initialize Supabase client
        init_supabase()

        # Check connection
        if not check_database_connection():
            raise RuntimeError("Database connection failed")

        # Ensure admin user exists (database is single source of truth)
        ensure_admin_exists()

        print("Database initialized successfully")
        return True

    except Exception as e:
        print(f"Database initialization failed: {e}")
        raise


# Initialize database on module load
initialize_database()

# =========================================================
# THREAT DETECTION SYSTEM
# =========================================================

import random

# Import notification system (kept from original)
from src.notifications.push_notifier import PushNotifier

# Global state for threat detection
monitoring_active = False
monitoring_username = None
current_threat_state = "SAFE"
current_threat_score = 0.0
threat_history = []
incident_timeline = load_json_file(INCIDENTS_FILE, [])
baseline_profiles = load_json_file(BASELINES_FILE, {})
latest_speech = 0.0
latest_motion = 0.0
latest_emotion = "neutral"
latest_explanation = {
    "summary": "Monitoring has not produced a threat assessment yet.",
    "signals": [],
    "recommendations": [],
}
last_threat_incident_at = 0.0
user_locations = {}

# Threat detection thread
threat_thread = None
threat_lock = threading.Lock()

# New sensor fusion components
motion_anomaly_detectors = {}  # per-user MotionAnomalyDetector instances
distress_pipeline = DistressPipeline()
push_notifier = PushNotifier()

# Legacy mode flag for A/B comparison
LEGACY_MODE = os.environ.get("LEGACY_MODE", "false").lower() == "true"


def get_motion_detector(user_id):
    """Get or create a MotionAnomalyDetector for a user."""
    if user_id not in motion_anomaly_detectors:
        motion_anomaly_detectors[user_id] = MotionAnomalyDetector()
    return motion_anomaly_detectors[user_id]


def analyze_audio_features(audio_features):
    """Analyze audio features through the new distress pipeline."""
    try:
        result = distress_pipeline.analyze(audio_features)
        return result
    except Exception as e:
        print(f"Error in audio analysis: {e}")
        return {
            "distress_score": 0.0,
            "confidence": 0.0,
            "alert": False,
            "environment": "QUIET",
            "event_type": "NONE",
        }


def build_signal_explanation(name, score, weight, reason):
    contribution = max(0.0, min(1.0, score)) * weight
    return {
        "name": name,
        "score": round(float(score), 3),
        "weight": round(float(weight), 2),
        "contribution": round(float(contribution), 3),
        "reason": reason,
    }


def get_state_recommendations(threat_state):
    if threat_state == "CRITICAL":
        return [
            "Trigger SOS if you have not already.",
            "Move toward a public or well-lit safe place.",
            "Keep the phone reachable for trusted contacts.",
        ]
    if threat_state == "HIGH":
        return [
            "Stay alert and prepare to trigger SOS.",
            "Move toward nearby safe places.",
            "Share location with trusted contacts if risk continues.",
        ]
    if threat_state == "MEDIUM":
        return [
            "Keep monitoring active.",
            "Check surroundings and avoid isolated routes.",
        ]
    return ["Environment appears stable.", "Keep monitoring active when travelling."]


def get_baseline_profile(username):
    username = username or "anonymous"
    profile = baseline_profiles.setdefault(
        username,
        {
            "count": 0,
            "speech_mean": 0.0,
            "speech_m2": 0.0,
            "motion_mean": 0.0,
            "motion_m2": 0.0,
            "updated_at": None,
        },
    )
    return profile


def get_baseline_snapshot(username):
    profile = get_baseline_profile(username)
    count = int(profile.get("count", 0))
    speech_var = profile.get("speech_m2", 0.0) / max(count - 1, 1)
    motion_var = profile.get("motion_m2", 0.0) / max(count - 1, 1)
    return {
        "samples": count,
        "ready": count >= 8,
        "speech_mean": round(float(profile.get("speech_mean", 0.0)), 3),
        "speech_std": round(float(speech_var**0.5), 3),
        "motion_mean": round(float(profile.get("motion_mean", 0.0)), 3),
        "motion_std": round(float(motion_var**0.5), 3),
        "updated_at": profile.get("updated_at"),
    }


def update_baseline_profile(username, speech_score, motion_score):
    """Update per-user normal behavior profile using Welford statistics."""
    profile = get_baseline_profile(username)
    count = int(profile.get("count", 0)) + 1
    profile["count"] = count

    for key, value in (("speech", speech_score), ("motion", motion_score)):
        value = float(value or 0.0)
        mean_key = f"{key}_mean"
        m2_key = f"{key}_m2"
        old_mean = float(profile.get(mean_key, 0.0))
        delta = value - old_mean
        new_mean = old_mean + delta / count
        delta_2 = value - new_mean
        profile[mean_key] = new_mean
        profile[m2_key] = float(profile.get(m2_key, 0.0)) + delta * delta_2

    profile["updated_at"] = datetime.now().isoformat()
    if count % 5 == 0:
        save_json_file(BASELINES_FILE, baseline_profiles)


def compute_baseline_anomaly(username, speech_score, motion_score):
    snapshot = get_baseline_snapshot(username)
    if not snapshot["ready"]:
        return {
            "score": 0.0,
            "reason": f"Learning personal baseline ({snapshot['samples']}/8 safe samples collected)",
            "snapshot": snapshot,
        }

    speech_std = max(snapshot["speech_std"], 0.03)
    motion_std = max(snapshot["motion_std"], 0.03)
    speech_z = abs(float(speech_score or 0.0) - snapshot["speech_mean"]) / speech_std
    motion_z = abs(float(motion_score or 0.0) - snapshot["motion_mean"]) / motion_std
    anomaly_score = min(1.0, max(speech_z, motion_z) / 4.0)

    return {
        "score": round(anomaly_score, 3),
        "reason": f"Personal baseline deviation: speech z={speech_z:.1f}, motion z={motion_z:.1f}",
        "snapshot": snapshot,
    }


# fuse_threat_signals is now imported from src.threat_assessment.threat_fusion
# The function signature is: fuse_new_threat(motion_result, audio_result, context_score, username)


def record_incident(event_type, username, threat_state, threat_score, details=None):
    """Store a compact incident timeline entry for research/evaluation views."""
    details = details or {}
    incident = {
        "id": f"incident-{int(time.time() * 1000)}",
        "timestamp": datetime.now().isoformat(),
        "event_type": event_type,
        "username": username,
        "threat_state": threat_state,
        "threat_score": round(float(threat_score or 0.0), 3),
        "details": details,
    }
    incident_timeline.append(incident)
    if len(incident_timeline) > 100:
        incident_timeline.pop(0)
    save_json_file(INCIDENTS_FILE, incident_timeline)
    print(
        f"[INCIDENT] {event_type} user={username} state={threat_state} score={incident['threat_score']}"
    )
    return incident


def build_research_metrics(username=None):
    history = threat_history[-100:]
    incidents = incident_timeline[-100:]
    state_counts = {}
    for item in history:
        state = item.get("state", "UNKNOWN")
        state_counts[state] = state_counts.get(state, 0) + 1

    scores = [float(item.get("score", 0.0)) for item in history]
    high_events = len(
        [i for i in incidents if i.get("threat_state") in ["HIGH", "CRITICAL"]]
    )
    sos_events = len([i for i in incidents if i.get("event_type") == "SOS_TRIGGERED"])
    labeled = [i for i in incidents if i.get("feedback", {}).get("label")]
    confirmed = len(
        [i for i in labeled if i.get("feedback", {}).get("label") == "confirmed_threat"]
    )
    false_alarms = len(
        [i for i in labeled if i.get("feedback", {}).get("label") == "false_alarm"]
    )

    # Per-environment false positive breakdown
    env_fp = {}
    for i in incidents:
        env = i.get("details", {}).get("environment", "UNKNOWN")
        fb = i.get("feedback", {}).get("label", "")
        if env not in env_fp:
            env_fp[env] = {"total": 0, "false_alarms": 0}
        env_fp[env]["total"] += 1
        if fb == "false_alarm":
            env_fp[env]["false_alarms"] += 1

    # Signal type breakdown
    motion_only = len(
        [
            i
            for i in incidents
            if i.get("details", {}).get("motion_event", "NONE") != "NONE"
            and i.get("details", {}).get("audio_event", "NONE") == "NONE"
        ]
    )
    audio_only = len(
        [
            i
            for i in incidents
            if i.get("details", {}).get("audio_event", "NONE") != "NONE"
            and i.get("details", {}).get("motion_event", "NONE") == "NONE"
        ]
    )
    fused_alerts = len(
        [
            i
            for i in incidents
            if i.get("details", {}).get("motion_event", "NONE") != "NONE"
            and i.get("details", {}).get("audio_event", "NONE") != "NONE"
        ]
    )

    return {
        "history_samples": len(history),
        "incident_count": len(incidents),
        "high_or_critical_events": high_events,
        "sos_events": sos_events,
        "labeled_incidents": len(labeled),
        "confirmed_threats": confirmed,
        "false_alarms": false_alarms,
        "false_positive_rate": (
            round(false_alarms / len(labeled), 3) if labeled else None
        ),
        "estimated_precision": round(confirmed / len(labeled), 3) if labeled else None,
        "average_score": round(sum(scores) / len(scores), 3) if scores else 0.0,
        "max_score": round(max(scores), 3) if scores else 0.0,
        "state_distribution": state_counts,
        "per_environment_fp": env_fp,
        "motion_only_alerts": motion_only,
        "audio_only_alerts": audio_only,
        "fused_alerts": fused_alerts,
        "baseline": get_baseline_snapshot(
            username or monitoring_username or "anonymous"
        ),
    }


def get_current_user_profile():
    """Fetch the current user and contacts for emergency workflows."""
    username = session.get("username")
    if not username:
        return None, []

    user = UserDB.get_by_email(username) or UserDB.get_by_username(username)
    if not user:
        return None, []

    contacts = EmergencyContactsDB.get_by_user(user["id"])
    return user, contacts


def threat_monitoring_loop():
    """Main threat monitoring loop — uses sensor fusion pipeline."""
    global current_threat_state, current_threat_score, latest_speech, latest_motion, latest_explanation, last_threat_incident_at

    while monitoring_active:
        try:
            # Motion data comes from client-side POSTs to /api/motion_data
            # Audio data comes from client-side POSTs to /api/audio_data
            # This loop now just maintains state and checks for alerts

            with threat_lock:
                threat_history.append(
                    {
                        "timestamp": datetime.now().isoformat(),
                        "score": round(current_threat_score, 3),
                        "state": current_threat_state,
                        "speech": round(latest_speech, 3),
                        "motion": round(latest_motion, 3),
                        "explanation": latest_explanation.get("summary", ""),
                    }
                )

                if len(threat_history) > 100:
                    threat_history.pop(0)

            time.sleep(2.0)

        except Exception as e:
            print(f"[ERROR] Threat monitoring loop error: {e}")
            time.sleep(2.0)


# =========================================================
# ROUTES
# =========================================================


@app.route("/")
def index():
    print(f"[DEBUG] Index route - username: {session.get('username')}")
    print(f"[DEBUG] Index route - needs_onboarding: {session.get('needs_onboarding')}")
    print(f"[DEBUG] Index route - is_admin: {session.get('is_admin')}")

    # Log out admin users if they try to access the main page
    if session.get("is_admin"):
        admin_username = session.get("username")
        log_activity(
            "admin",
            admin_username,
            "Admin logged out (homepage access)",
            "Admin attempted to access main page",
        )
        rotate_session()
        return redirect(url_for("admin_login"))

    # Redirect users who haven't completed onboarding
    if session.get("username") and session.get("needs_onboarding"):
        print(f"[DEBUG] Redirecting user {session.get('username')} to onboarding")
        return redirect(url_for("onboarding"))

    print(f"[DEBUG] Rendering index page for user: {session.get('username')}")
    return render_template(
        "index.html",
        logged_in="username" in session,
        username=session.get("username"),
        is_admin=session.get("is_admin", False),
    )


# ---------------- GOOGLE LOGIN ----------------


@app.route("/user-login")
def user_login():
    return render_template("user_login.html", GOOGLE_CLIENT_ID=GOOGLE_CLIENT_ID)


@app.route("/api/google-auth", methods=["POST"])
def google_auth():
    """Handle Google ID token authentication"""
    try:
        data = request.get_json()
        token = data.get("credential") if data else None

        if not token:
            return jsonify({"error": "Missing credential"}), 400

        user_data = verify_google_id_token(token)
        if not user_data:
            return jsonify({"error": "Invalid Google token"}), 401

        # Create or update user in database
        username, is_new = create_or_update_user_google(user_data)

        rotate_session()
        session["username"] = username
        session["user_name"] = user_data["name"]
        session["user_picture"] = user_data["picture"]
        session["is_admin"] = False

        # Get user from database to get onboarding state
        user = UserDB.get_by_email(username)
        session["needs_onboarding"] = (
            user.get("needs_onboarding", True) if user else True
        )

        # Update last login
        if user:
            UserDB.update_last_login(username)

        print(
            f"[DEBUG] User auth: username={username}, is_new={is_new}, needs_onboarding={session.get('needs_onboarding')}"
        )

        # Log user registration/login
        action = "User registered" if is_new else "User logged in"
        log_activity(
            "user",
            username,
            action,
            f"Name: {user_data['name']}, Email: {user_data.get('email', 'N/A')}, New user: {is_new}",
        )

        needs = session.get("needs_onboarding", True)
        redirect = "/onboarding" if needs else "/"

        return jsonify(
            {
                "success": True,
                "access_token": create_mobile_token(username),
                "needs_onboarding": needs,
                "user": {
                    "email": username,
                    "name": user_data.get("name") or session.get("user_name"),
                    "picture": user_data.get("picture") or session.get("user_picture"),
                },
                "redirect": redirect,
            }
        )

    except Exception as e:
        print(f"Google auth error: {e}")
        return jsonify({"error": "Authentication failed"}), 500


# ---------------- LOGOUT ----------------


@app.route("/logout")
def logout():
    username = session.get("username")
    is_admin = session.get("is_admin", False)

    if is_admin:
        log_activity("admin", username, "Admin logged out")
    else:
        log_activity("user", username, "User logged out")

    rotate_session()
    return redirect(url_for("index"))


# ---------------- ABOUT ----------------


@app.route("/about")
def about():
    """About page - accessible to all users"""
    return render_template("about.html")


# ---------------- ONBOARDING ----------------


@app.route("/onboarding")
def onboarding():
    """Onboarding page for new users"""
    print(f"[DEBUG] Onboarding route - username: {session.get('username')}")
    print(
        f"[DEBUG] Onboarding route - needs_onboarding: {session.get('needs_onboarding')}"
    )

    if "username" not in session:
        print(f"[DEBUG] Onboarding: No username in session, redirecting to login")
        return redirect(url_for("user_login"))

    if not session.get("needs_onboarding", False):
        print(
            f"[DEBUG] Onboarding: User already completed onboarding, redirecting to index"
        )
        return redirect(url_for("index"))

    print(
        f"[DEBUG] Onboarding: Rendering onboarding page for user: {session.get('username')}"
    )
    return render_template("onboarding.html", username=session.get("username"))


def _save_onboarding_contacts(contacts):
    """Persist emergency contacts during onboarding (does not finish onboarding)."""
    username = session["username"]
    user = UserDB.get_by_email(username)

    if user:
        EmergencyContactsDB.delete_by_user(user["id"])
        for contact in contacts:
            EmergencyContactsDB.create(
                user_id=user["id"],
                name=contact.get("name"),
                phone=contact.get("phone"),
                relationship=contact.get("relationship"),
                priority=contact.get("order", contact.get("priority", 0)),
            )
    else:
        new_user = UserDB.create(
            email=username,
            username=username,
            name=session.get("user_name", username),
            picture=session.get("user_picture", ""),
            password_hash=None,
            is_admin=False,
            needs_onboarding=True,
            contacts=contacts,
        )
        for contact in contacts:
            EmergencyContactsDB.create(
                user_id=new_user["id"],
                name=contact.get("name"),
                phone=contact.get("phone"),
                relationship=contact.get("relationship"),
                priority=contact.get("order", contact.get("priority", 0)),
            )

    session["onboarding_contacts_saved"] = True
    log_activity(
        "user",
        username,
        "Onboarding contacts saved",
        f"Added {len(contacts)} emergency contacts",
    )


@app.route("/api/mobile/me", methods=["GET"])
def mobile_me():
    """Profile for React Native clients."""
    if "username" not in session:
        return jsonify({"error": "Authentication required"}), 401
    user = UserDB.get_by_email(session["username"])
    return jsonify(
        {
            "email": session["username"],
            "name": session.get("user_name")
            or (user.get("name") if user else session["username"]),
            "picture": session.get("user_picture")
            or (user.get("picture") if user else ""),
            "needs_onboarding": session.get("needs_onboarding", False),
        }
    )


@app.route("/api/onboarding/status", methods=["GET"])
def onboarding_status():
    """Return onboarding progress for contacts + motion calibration."""
    if "username" not in session:
        return jsonify({"error": "Authentication required"}), 401

    username = session["username"]
    user = UserDB.get_by_email(username)
    contact_count = 0
    if user:
        contact_count = len(EmergencyContactsDB.get_by_user(user["id"]) or [])

    has_baseline = username in baseline_profiles
    contacts_saved = contact_count >= 4 or session.get(
        "onboarding_contacts_saved", False
    )
    needs_onboarding = session.get("needs_onboarding", True)

    if contacts_saved and has_baseline:
        step = "complete"
    elif contacts_saved:
        step = "calibration"
    else:
        step = "contacts"

    return jsonify(
        {
            "needs_onboarding": needs_onboarding,
            "contacts_saved": contacts_saved,
            "contact_count": contact_count,
            "has_baseline": has_baseline,
            "step": step,
            "user_name": session.get("user_name")
            or (user.get("name") if user else username),
        }
    )


@app.route("/api/onboarding/contacts", methods=["POST"])
def save_onboarding_contacts():
    """Save emergency contacts; user must still complete motion calibration."""
    if "username" not in session:
        return jsonify({"error": "Authentication required"}), 401

    if not session.get("needs_onboarding", False):
        return jsonify({"error": "Onboarding already completed"}), 400

    try:
        data = request.get_json() or {}
        contacts = data.get("contacts", [])

        if len(contacts) < 4:
            return jsonify({"error": "At least 4 emergency contacts are required"}), 400

        for contact in contacts:
            if not all(
                [contact.get("name"), contact.get("phone"), contact.get("relationship")]
            ):
                return jsonify({"error": "All required fields must be filled"}), 400

        _save_onboarding_contacts(contacts)

        return jsonify(
            {
                "status": "success",
                "message": "Contacts saved. Continue to walk calibration.",
                "step": "calibration",
            }
        )
    except Exception as e:
        print(f"Error saving onboarding contacts: {e}")
        return jsonify({"error": "Failed to save contacts"}), 500


@app.route("/api/onboarding/complete", methods=["POST"])
def complete_onboarding():
    """Legacy alias — saves contacts only (calibration required separately)."""
    return save_onboarding_contacts()


@app.route("/api/onboarding/finish", methods=["POST"])
def finish_onboarding():
    """Mark onboarding complete after motion profile calibration."""
    if "username" not in session:
        return jsonify({"error": "Authentication required"}), 401

    username = session["username"]
    user = UserDB.get_by_email(username)
    contact_count = (
        len(EmergencyContactsDB.get_by_user(user["id"]) or []) if user else 0
    )
    has_baseline = username in baseline_profiles

    if contact_count < 4 and not session.get("onboarding_contacts_saved"):
        return jsonify({"error": "Emergency contacts required before finishing"}), 400
    if not has_baseline:
        return jsonify({"error": "Motion calibration required before finishing"}), 400

    UserDB.update(username, needs_onboarding=False)
    session["needs_onboarding"] = False
    session.pop("onboarding_contacts_saved", None)

    log_activity(
        "user", username, "Completed onboarding", "Contacts + motion profile ready"
    )

    return jsonify(
        {
            "status": "success",
            "message": "Welcome to AURALIS",
            "redirect": "/",
        }
    )


# ---------------- ADMIN LOGIN ----------------


@app.route("/login", methods=["GET", "POST"])
def admin_login():
    """Admin login - validates against database with hashed password"""
    if request.method == "POST":
        u = request.form.get("username")
        p = request.form.get("password")

        # Verify credentials against database
        if UserDB.verify_password(u, p):
            rotate_session()
            session["username"] = u
            session["is_admin"] = True

            # Update last login
            UserDB.update_last_login(u)

            # Log admin login
            log_activity("admin", u, "Admin logged in")

            return redirect(url_for("admin_dashboard"))

        return render_template("login.html", error="Invalid credentials")

    return render_template("login.html")


# ---------------- ADMIN DASHBOARD ----------------


@app.route("/admin")
def admin_dashboard():
    """Admin dashboard - shows all users from database"""
    if not session.get("is_admin"):
        return redirect(url_for("admin_login"))

    # Get all users from database
    users_data = UserDB.get_all_users()

    # Process users data for template
    users_list = []
    total_contacts = 0

    for user_data in users_data:
        # Get contacts count from database
        contacts = EmergencyContactsDB.get_by_user(user_data["id"])
        contact_count = len(contacts)
        total_contacts += contact_count

        # Create user object for template
        user_obj = {
            "username": user_data.get("username", user_data.get("email")),
            "contact_count": contact_count,
            "created_at": user_data.get("created_at", ""),
            "is_admin": user_data.get("is_admin", False),
            "email": user_data.get("email", user_data.get("username")),
            "name": user_data.get("name", ""),
            "last_login": user_data.get("last_login", ""),
        }
        users_list.append(user_obj)

    # Calculate statistics (exclude admin users)
    regular_users = [u for u in users_list if not u.get("is_admin", False)]
    total_users = len(regular_users)
    active_users = len([u for u in regular_users if u.get("last_login")])
    avg_contacts_per_user = (
        round(total_contacts / total_users, 1) if total_users > 0 else 0
    )

    stats = {
        "total_users": total_users,
        "active_users": active_users,
        "total_contacts": total_contacts,
        "avg_contacts_per_user": avg_contacts_per_user,
    }

    return render_template("admin.html", users=users_list, stats=stats)


# ---------------- USER DELETION ----------------


@app.route("/api/admin/delete_user", methods=["POST"])
def admin_delete_user():
    """Delete a user - admin only"""
    if not session.get("is_admin"):
        return jsonify({"error": "Admin authentication required"}), 403

    try:
        data = request.get_json()
        username_to_delete = data.get("username")

        if not username_to_delete:
            return jsonify({"error": "Username is required"}), 400

        # Prevent admin from deleting themselves
        if username_to_delete == session.get("username"):
            return jsonify({"error": "Cannot delete your own admin account"}), 400

        # Get user from database - try email first, then username
        user = UserDB.get_by_email(username_to_delete)

        if not user:
            user = UserDB.get_by_username(username_to_delete)

        if not user:
            return jsonify({"error": "User not found"}), 404

        # Prevent deleting admin users
        if user.get("is_admin"):
            return jsonify({"error": "Cannot delete admin users"}), 400

        # Delete user from database (contacts will be deleted via CASCADE)
        UserDB.delete_by_id(user["id"])

        # Log admin action
        log_activity(
            "admin",
            session.get("username"),
            "User deleted",
            f"Deleted user: {username_to_delete}",
        )

        print(f"Admin '{session.get('username')}' deleted user '{username_to_delete}'")

        return jsonify(
            {
                "status": "success",
                "message": f"User '{username_to_delete}' has been deleted successfully",
            }
        )

    except Exception as e:
        print(f"Error deleting user: {e}")
        return jsonify({"error": "Failed to delete user"}), 500


# ---------------- ACTIVITY LOGS ----------------


@app.route("/api/admin/activity_logs")
def get_activity_logs():
    """Get recent activity logs - admin only"""
    if not session.get("is_admin"):
        return jsonify({"error": "Admin authentication required"}), 403

    try:
        logs = ActivityLogsDB.get_recent(20)

        return jsonify({"status": "success", "logs": logs})

    except Exception as e:
        print(f"Error loading activity logs: {e}")
        return jsonify({"error": "Failed to load activity logs"}), 500


# ---------------- USER THREAT STATUS ----------------


@app.route("/api/admin/user_threat_status")
def get_user_threat_status():
    """Get threat status for all users - admin only"""
    if not session.get("is_admin"):
        return jsonify({"error": "Admin authentication required"}), 403

    try:
        users_data = UserDB.get_all_users()
        user_threat_data = []

        global_threat_state = current_threat_state
        global_threat_score = current_threat_score

        for user_data in users_data:
            # Skip admin users
            if user_data.get("is_admin"):
                continue

            user_threat_info = {
                "username": user_data.get("username", user_data.get("email")),
                "threat_state": global_threat_state,
                "threat_score": global_threat_score,
                "last_updated": datetime.now().isoformat(),
                "monitoring_active": monitoring_active,
                "email": user_data.get("email", ""),
                "created_at": user_data.get("created_at", ""),
            }

            user_threat_data.append(user_threat_info)

        return jsonify(
            {
                "status": "success",
                "users": user_threat_data,
                "global_threat_state": global_threat_state,
                "global_threat_score": global_threat_score,
            }
        )

    except Exception as e:
        print(f"Error loading user threat status: {e}")
        return jsonify({"error": "Failed to load user threat status"}), 500


# ---------------- DETECTABILITY ----------------


@app.route("/api/admin/detectability")
def get_detectability():
    """Get user detectability data for admin map - admin only"""
    if not session.get("is_admin"):
        return jsonify({"error": "Admin authentication required"}), 403

    try:
        users_data = UserDB.get_all_users()
        users_list = []

        for user_data in users_data:
            # Skip admin users
            if user_data.get("is_admin"):
                continue

            user_info = {
                "username": user_data.get("username", user_data.get("email")),
                "email": user_data.get("email", ""),
                "status": "OFFLINE",
                "threat_level": "SAFE",
                "location": None,
                "last_seen": user_data.get("last_login", datetime.now().isoformat()),
            }

            users_list.append(user_info)

        return jsonify({"status": "success", "users": users_list})

    except Exception as e:
        print(f"Error loading detectability data: {e}")
        return jsonify({"error": "Failed to load detectability data"}), 500


# ---------------- USER DETAILS ----------------


@app.route("/api/admin/user_details/<username>")
def get_user_details(username):
    """Get detailed user information - admin only"""
    if not session.get("is_admin"):
        return jsonify({"error": "Admin authentication required"}), 403

    try:
        # Try to find user by email first, then username
        user = UserDB.get_by_email(username)
        if not user:
            user = UserDB.get_by_username(username)

        if not user:
            return jsonify({"error": "User not found"}), 404

        # Get user's emergency contacts
        contacts = EmergencyContactsDB.get_by_user(user["id"])

        return jsonify(
            {
                "status": "success",
                "username": user.get("username", user.get("email")),
                "email": user.get("email", ""),
                "name": user.get("name", ""),
                "contact_count": len(contacts),
                "contacts": contacts,
                "created_at": user.get("created_at", ""),
                "last_login": user.get("last_login", ""),
                "is_admin": user.get("is_admin", False),
            }
        )

    except Exception as e:
        print(f"Error loading user details: {e}")
        return jsonify({"error": "Failed to load user details"}), 500


# ---------------- THREAT STATUS ----------------


@app.route("/api/threat_status")
def threat_status():
    """Get current threat status - requires authentication"""
    if "username" not in session:
        return jsonify({"error": "Authentication required"}), 401

    with threat_lock:
        return jsonify(
            {
                "state": current_threat_state,
                "score": current_threat_score,
                "speech_contribution": latest_speech,
                "motion_contribution": latest_motion,
                "emotion": "n/a",
                "explanation": latest_explanation,
                "research_metrics": build_research_metrics(session.get("username")),
                "monitoring_active": monitoring_active,
                "history": threat_history[-20:] if threat_history else [],
                "incidents": incident_timeline[-10:] if incident_timeline else [],
            }
        )


@app.route("/api/incidents")
def get_incidents():
    """Get recent research/evaluation incident timeline entries."""
    if "username" not in session:
        return jsonify({"error": "Authentication required"}), 401

    return jsonify({"status": "success", "incidents": incident_timeline[-30:]})


@app.route("/api/incidents/<incident_id>/feedback", methods=["POST"])
def incident_feedback(incident_id):
    """Attach user/admin evaluation feedback to an incident."""
    if "username" not in session:
        return jsonify({"error": "Authentication required"}), 401

    data = request.json or {}
    label = data.get("label")
    note = data.get("note", "")
    allowed = {"confirmed_threat", "false_alarm", "needs_review"}

    if label not in allowed:
        return jsonify({"error": "Invalid feedback label"}), 400

    for incident in incident_timeline:
        if incident.get("id") == incident_id:
            incident["feedback"] = {
                "label": label,
                "note": note,
                "reviewed_by": session.get("username"),
                "reviewed_at": datetime.now().isoformat(),
            }
            save_json_file(INCIDENTS_FILE, incident_timeline)
            log_activity(
                "user",
                session.get("username"),
                "Incident feedback submitted",
                f"{incident_id}: {label}",
            )
            return jsonify(
                {
                    "status": "success",
                    "incident": incident,
                    "metrics": build_research_metrics(session.get("username")),
                }
            )

    return jsonify({"error": "Incident not found"}), 404


@app.route("/api/research_metrics")
def research_metrics():
    """Get research metrics for evaluation and prototype reporting."""
    if "username" not in session:
        return jsonify({"error": "Authentication required"}), 401

    return jsonify(
        {
            "status": "success",
            "metrics": build_research_metrics(session.get("username")),
        }
    )


@app.route("/api/research_report")
def research_report():
    """Export a compact research report as JSON."""
    if "username" not in session:
        return jsonify({"error": "Authentication required"}), 401

    username = session.get("username")
    report = {
        "generated_at": datetime.now().isoformat(),
        "generated_for": username,
        "app": "AURALIS Women Safety Assistant",
        "metrics": build_research_metrics(username),
        "baseline": get_baseline_snapshot(username),
        "recent_threat_history": threat_history[-50:],
        "recent_incidents": incident_timeline[-50:],
        "notes": [
            "Scores are normalized between 0 and 1.",
            "Estimated precision is computed only from manually labeled incidents.",
            "Baseline anomaly becomes active after 8 SAFE samples for the current user.",
        ],
    }

    return jsonify({"status": "success", "report": report})


# ---------------- MONITORING CONTROLS ----------------


@app.route("/api/start_monitoring", methods=["POST"])
def start_monitoring():
    """Start threat monitoring - requires authentication"""
    if "username" not in session:
        return jsonify({"error": "Authentication required"}), 401

    global monitoring_active, monitoring_username, threat_thread

    if monitoring_active:
        return jsonify(
            {
                "status": "already_running",
                "message": "Threat monitoring is already active",
            }
        )

    monitoring_active = True
    monitoring_username = session["username"]
    threat_thread = threading.Thread(target=threat_monitoring_loop, daemon=True)
    threat_thread.start()

    log_activity("user", session["username"], "Started threat monitoring")

    print(
        f"[MONITORING] Started sensor fusion monitoring for user: {session['username']}"
    )

    return jsonify({"status": "started", "message": "Sensor fusion monitoring started"})


@app.route("/api/stop_monitoring", methods=["POST"])
def stop_monitoring():
    """Stop threat monitoring - requires authentication"""
    if "username" not in session:
        return jsonify({"error": "Authentication required"}), 401

    global monitoring_active, monitoring_username

    if not monitoring_active:
        return jsonify(
            {"status": "not_running", "message": "Threat monitoring is not active"}
        )

    monitoring_active = False
    monitoring_username = None

    log_activity("user", session["username"], "Stopped threat monitoring")

    print(
        f"[MONITORING] Stopped sensor fusion monitoring for user: {session['username']}"
    )

    return jsonify({"status": "stopped", "message": "Threat monitoring stopped"})


# ---------------- LOCATION UPDATE ----------------


@app.route("/api/update_location", methods=["POST"])
def update_location():
    """Update user location - requires authentication"""
    if "username" not in session:
        return jsonify({"error": "Authentication required"}), 401

    try:
        data = request.json
        lat = data.get("lat")
        lng = data.get("lng")

        if lat is None or lng is None:
            return jsonify({"error": "Invalid location data"}), 400

        user_locations[session["username"]] = {
            "lat": float(lat),
            "lng": float(lng),
            "updated_at": datetime.now().isoformat(),
        }

        return jsonify(
            {"status": "location_updated", "message": "Location updated successfully"}
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------- SAFE PLACES ----------------


@app.route("/api/safe_places", methods=["GET"])
def safe_places():
    """Get safe places near user location - requires authentication"""
    if "username" not in session:
        return jsonify({"error": "Authentication required"}), 401

    try:
        lat = float(request.args.get("lat"))
        lng = float(request.args.get("lng"))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid coordinates"}), 400

    places = [
        {
            "name": "Local Police Station",
            "type": "police",
            "lat": lat + 0.01,
            "lng": lng + 0.01,
            "address": "123 Main St",
            "phone": "N/A",
            "rating": 4.5,
            "distance": 0.5,
        },
        {
            "name": "City Hospital",
            "type": "hospital",
            "lat": lat - 0.008,
            "lng": lng + 0.015,
            "address": "456 Health Ave",
            "phone": "N/A",
            "rating": 4.2,
            "distance": 1.2,
        },
    ]

    return jsonify({"status": "ok", "places": places})


# ---------------- EMERGENCY/SOS ----------------


@app.route("/api/trigger_sos", methods=["POST"])
def trigger_sos():
    """Trigger SOS emergency - requires authentication"""
    if "username" not in session:
        return jsonify({"error": "Authentication required"}), 401

    data = request.json or {}
    username = session["username"]
    user, contacts = get_current_user_profile()
    location = None

    if data.get("lat") is not None and data.get("lng") is not None:
        location = {"lat": data.get("lat"), "lng": data.get("lng")}
    elif username in user_locations:
        location = user_locations[username]

    user_data = {"username": username, "contacts": contacts}
    notification_result = push_notifier.send_sos_notification(
        user_data, location=location
    )
    incident = record_incident(
        "SOS_TRIGGERED",
        username,
        "CRITICAL",
        1.0,
        {
            "contacts_notified": notification_result.get("notifications_sent", 0),
            "location": location,
            "notification_success": notification_result.get("success", False),
        },
    )

    log_activity(
        "user",
        username,
        "SOS emergency triggered",
        f"Contacts notified: {notification_result.get('notifications_sent', 0)}",
    )

    return jsonify(
        {
            "status": "sos_triggered",
            "message": "Emergency contacts have been notified",
            "contacts_notified": notification_result.get("notifications_sent", 0),
            "notification_result": notification_result,
            "incident": incident,
        }
    )


# ---------------- CHATBOT ----------------


@app.route("/api/chatbot", methods=["POST"])
def chatbot():
    """Handle chatbot messages - requires authentication"""
    if "username" not in session:
        return jsonify({"error": "Authentication required"}), 401

    data = request.json or {}
    message = data.get("message", "")

    response = (
        "I'm here to help with safety-related questions. How can I assist you today?"
    )

    return jsonify({"response": response, "message": response})


@app.route("/api/chatbot/auto_alert", methods=["POST"])
def chatbot_auto_alert():
    """Handle automatic alerts from chatbot - requires authentication"""
    if "username" not in session:
        return jsonify({"error": "Authentication required"}), 401

    data = request.json or {}
    username = session["username"]
    user, contacts = get_current_user_profile()
    location = None
    if data.get("lat") is not None and data.get("lng") is not None:
        location = {"lat": data.get("lat"), "lng": data.get("lng")}
    elif username in user_locations:
        location = user_locations[username]

    threat_level = data.get("threat_level", current_threat_state)
    notification_result = push_notifier.send_threat_alert(
        {"username": username, "contacts": contacts}, threat_level, location=location
    )
    record_incident(
        "AUTO_ALERT",
        username,
        threat_level,
        current_threat_score,
        {
            "contacts_notified": notification_result.get("notifications_sent", 0),
            "location": location,
            "notification_success": notification_result.get("success", False),
        },
    )

    return jsonify(
        {
            "status": "alert_sent",
            "message": "Emergency contacts have been automatically notified",
            "contacts_notified": notification_result.get("notifications_sent", 0),
            "notification_result": notification_result,
        }
    )


# ---------------- RECOMMENDATIONS ----------------


@app.route("/api/recommendations", methods=["GET"])
def recommendations():
    """Get safety recommendations - requires authentication"""
    if "username" not in session:
        return jsonify({"error": "Authentication required"}), 401

    recommendations = [
        *latest_explanation.get("recommendations", []),
        "Keep your phone charged",
        "Trust your instincts",
    ]

    return jsonify({"recommendations": recommendations})


# Register OAuth routes using the module
register_oauth_routes(app)

# =========================================================
# SENSOR FUSION API ENDPOINTS
# =========================================================


@app.route("/api/motion_data", methods=["POST"])
def motion_data():
    """Accept motion sensor data and return anomaly assessment."""
    if "username" not in session:
        return jsonify({"error": "Authentication required"}), 401

    try:
        data = request.get_json()
        user_id = data.get("user_id", session.get("username"))
        sensor_window = data.get("sensor_window", [])

        if not sensor_window:
            return jsonify({"error": "No sensor data provided"}), 400

        detector = get_motion_detector(user_id)
        result = detector.analyze_window(sensor_window)

        global latest_motion, current_threat_score, current_threat_state, latest_explanation
        latest_motion = result["anomaly_score"]

        # Fuse with latest audio score
        assessment = fuse_new_threat(
            motion_result=result,
            audio_result={
                "distress_score": latest_speech,
                "environment": "QUIET",
                "event_type": "NONE",
                "confidence": 0.0,
            },
            username=user_id,
        )

        with threat_lock:
            current_threat_score = assessment["fused_score"]
            current_threat_state = assessment["threat_level"]
            latest_explanation = {
                "summary": f"{assessment['threat_level']}: motion={result['anomaly_score']:.3f} event={result['event_type']}",
                "signals": [
                    {
                        "name": "Motion",
                        "score": result["anomaly_score"],
                        "event": result["event_type"],
                    }
                ],
                "recommendations": get_state_recommendations(
                    assessment["threat_level"]
                ),
            }

        # Record incident if threat detected
        if assessment["alert_triggered"]:
            record_incident(
                "THREAT_DETECTED",
                user_id,
                assessment["threat_level"],
                assessment["fused_score"],
                {
                    "motion_score": result["anomaly_score"],
                    "motion_event": result["event_type"],
                    "audio_score": latest_speech,
                    "environment": assessment.get("environment", "QUIET"),
                },
            )

        return jsonify(
            {"status": "success", "motion": result, "assessment": assessment}
        )
    except Exception as e:
        print(f"Error processing motion data: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/audio_data", methods=["POST"])
def audio_data():
    """Accept audio features or raw audio and return distress assessment."""
    if "username" not in session:
        return jsonify({"error": "Authentication required"}), 401

    try:
        data = request.get_json()
        user_id = data.get("user_id", session.get("username"))
        audio_features = data.get("audio_features", {})

        if not audio_features:
            return jsonify({"error": "No audio features provided"}), 400

        result = analyze_audio_features(audio_features)

        global latest_speech
        latest_speech = result.get("distress_score", 0.0)

        # Fuse with latest motion score
        assessment = fuse_new_threat(
            motion_result={
                "anomaly_score": latest_motion,
                "event_type": "NONE",
                "confidence": 0.0,
            },
            audio_result=result,
            username=user_id,
        )

        with threat_lock:
            current_threat_score = assessment["fused_score"]
            current_threat_state = assessment["threat_level"]

        # Record incident if threat detected
        if assessment["alert_triggered"]:
            record_incident(
                "THREAT_DETECTED",
                user_id,
                assessment["threat_level"],
                assessment["fused_score"],
                {
                    "audio_score": result.get("distress_score", 0.0),
                    "audio_event": result.get("event_type", "NONE"),
                    "motion_score": latest_motion,
                    "environment": result.get("environment", "QUIET"),
                },
            )

        return jsonify({"status": "success", "audio": result, "assessment": assessment})
    except Exception as e:
        print(f"Error processing audio data: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/motion_baseline", methods=["POST"])
def motion_baseline():
    """Accept baseline motion data and create user motion profile."""
    if "username" not in session:
        return jsonify({"error": "Authentication required"}), 401

    try:
        data = request.get_json()
        user_id = data.get("user_id", session.get("username"))
        normal_readings = data.get("normal_readings", [])
        elevated_readings = data.get("elevated_readings", [])

        if not normal_readings or len(normal_readings) < 50:
            return (
                jsonify(
                    {"error": "Insufficient baseline data. Need at least 50 readings."}
                ),
                400,
            )

        baseline = BaselineProfiler.build_baseline(
            normal_readings, elevated_readings or None
        )

        if baseline is None:
            return (
                jsonify({"error": "Could not build baseline from provided data"}),
                400,
            )

        # Store baseline in local profiles
        baseline_profiles[user_id] = baseline
        save_json_file(BASELINES_FILE, baseline_profiles)

        # Update the user's motion detector with new baseline
        detector = get_motion_detector(user_id)
        detector.update_baseline(baseline)

        log_activity(
            "user",
            user_id,
            "Motion baseline created",
            f"Samples: {len(normal_readings)}",
        )

        finish_payload = {}
        if session.get("needs_onboarding"):
            finish_payload["onboarding_ready_to_finish"] = True

        return jsonify(
            {
                "status": "success",
                "message": "Motion baseline saved successfully",
                "baseline": baseline,
                **finish_payload,
            }
        )
    except Exception as e:
        print(f"Error creating motion baseline: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/false_alert", methods=["POST"])
def false_alert():
    """Mark the last alert as a false positive for research metrics."""
    if "username" not in session:
        return jsonify({"error": "Authentication required"}), 401

    try:
        data = request.get_json() or {}
        username = session.get("username")

        # Find the most recent incident for this user
        user_incidents = [
            i for i in reversed(incident_timeline) if i.get("username") == username
        ]

        if not user_incidents:
            return jsonify({"error": "No recent incidents found"}), 404

        latest_incident = user_incidents[0]
        latest_incident["feedback"] = {
            "label": "false_alarm",
            "note": data.get("note", "Marked as false positive by user"),
            "reviewed_by": username,
            "reviewed_at": datetime.now().isoformat(),
        }
        save_json_file(INCIDENTS_FILE, incident_timeline)

        log_activity(
            "user",
            username,
            "False alert reported",
            f"Incident: {latest_incident.get('id')}",
        )

        return jsonify(
            {
                "status": "success",
                "message": "Alert marked as false positive",
                "incident_id": latest_incident.get("id"),
                "metrics": build_research_metrics(username),
            }
        )
    except Exception as e:
        print(f"Error marking false alert: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/user_baseline_status", methods=["GET"])
def user_baseline_status():
    """Check if user has a motion baseline profile."""
    if "username" not in session:
        return jsonify({"error": "Authentication required"}), 401

    username = session.get("username")
    has_baseline = (
        username in baseline_profiles
        and baseline_profiles[username].get("cadence_mean") is not None
    )

    return jsonify(
        {
            "status": "success",
            "has_baseline": has_baseline,
            "baseline": baseline_profiles.get(username) if has_baseline else None,
        }
    )


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    host = os.environ.get("HOST", "0.0.0.0")
    app.run(host=host, port=port, threaded=True)
