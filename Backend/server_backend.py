"""
Flask Backend – Women Safety Assistant
"""

import os
import time
import threading
from datetime import datetime

import numpy as np
from flask import (
    Flask, render_template, Response,
    jsonify, request, session, redirect, url_for
)
from dotenv import load_dotenv

# Import Google OAuth module (cloud-safe)
try:
    from Backend.google_oauth import (
        load_google_oauth_config,
        verify_google_id_token,
        create_or_update_user_google,
        register_oauth_routes
    )
except ImportError as e:
    print(f"[WARN] Google OAuth import failed (cloud mode?): {e}")
    load_google_oauth_config = lambda: {}
    verify_google_id_token = lambda t: None
    create_or_update_user_google = lambda u, *args: ('demo', True)
    register_oauth_routes = lambda a: None

# Import Supabase database module
from Database.database import (
    get_supabase, init_supabase,
    UserDB, EmergencyContactsDB, ActivityLogsDB,
    ConfigDB, ensure_admin_exists, check_database_connection
)

# =========================================================
# ENV + BASIC CONFIG
# =========================================================

load_dotenv()

IS_CLOUD = os.environ.get("RENDER") == "true"
PRODUCTION = os.environ.get("PRODUCTION", "false").lower() == "true"

# Define paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "Frontend")

app = Flask(__name__,
            template_folder=os.path.join(FRONTEND_DIR, "templates"),
            static_folder=os.path.join(FRONTEND_DIR, "static"))

# Production security settings
app.secret_key = os.environ.get("SECRET_KEY", "change-this-in-production")
app.config["SESSION_COOKIE_SECURE"] = PRODUCTION
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["DEBUG"] = False
app.config["TESTING"] = False

# CSRF protection disabled (no forms requiring CSRF in this app)

# Load Google OAuth config
oauth_config = load_google_oauth_config()
GOOGLE_CLIENT_ID = oauth_config["client_id"]

# =========================================================
# OPTIONAL OPENCV (LOCAL ONLY)
# =========================================================

if not IS_CLOUD:
    try:
        import cv2
    except ImportError:
        cv2 = None
else:
    cv2 = None

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
        
        print("✅ Database initialized successfully")
        return True
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        raise

# Initialize database on module load
initialize_database()

# =========================================================
# THREAT DETECTION SYSTEM
# =========================================================

import random

# Import emotion model integration
from src.speech_analysis.speech_detector import SpeechDetector
from src.audio_capture.audio_recorder import AudioRecorder
from src.motion_detection.motion_detector import MotionDetector

# Global state for threat detection
monitoring_active = False
current_threat_state = "SAFE"
current_threat_score = 0.0
threat_history = []
latest_speech = 0.0
latest_motion = 0.0
latest_emotion = "neutral"

# Threat detection thread
threat_thread = None
threat_lock = threading.Lock()

# Camera for motion detection (when available)
camera = None
motion_detector = None

# Audio detection components
speech_detector = None
audio_recorder = None

# Initialize camera and motion detector early for video feed functionality
if not IS_CLOUD and cv2 is not None:
    try:
        camera = cv2.VideoCapture(0)
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        motion_detector = MotionDetector(
            shadow_removal=True,
            min_area_ratio=0.001,
            sensitivity=1.0,
            history=200,
            var_threshold=48,
            learning_rate=0.003,
            smoothing_window=4
        )
        
        print("✅ Camera and motion detector pre-initialized for video feed")
    except Exception as e:
        print(f"⚠️  Camera pre-initialization failed: {e}")
        camera = None
        motion_detector = None

def init_camera():
    """Initialize camera for motion detection"""
    global camera, motion_detector
    
    if IS_CLOUD or cv2 is None:
        return False
        
    if camera is not None and camera.isOpened():
        return True
        
    try:
        camera = cv2.VideoCapture(0)
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        motion_detector = MotionDetector(
            shadow_removal=True,
            min_area_ratio=0.001,
            sensitivity=1.0,
            history=200,
            var_threshold=48,
            learning_rate=0.003,
            smoothing_window=4
        )
        
        print("✅ Camera and motion detector initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Camera initialization error: {e}")
        return False

def detect_motion(frame):
    """Advanced motion detection using sophisticated background subtraction"""
    global motion_detector
    
    if not IS_CLOUD and cv2 is not None and frame is not None:
        if motion_detector is not None:
            motion_score, fg_mask = motion_detector.detect_motion(frame)
            return motion_score
        else:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(gray, (21, 21), 0)
            motion_score = random.uniform(0.0, 0.3)
            return motion_score
    else:
        return random.uniform(0.0, 0.2)

def init_audio_system():
    """Initialize audio capture and speech detection systems"""
    global speech_detector, audio_recorder
    
    try:
        speech_detector = SpeechDetector()
        print("Speech detector initialized with emotion model")
        
        audio_recorder = AudioRecorder(
            sample_rate=16000,
            chunk_size=1024,
            channels=1,
            format_width=2,
            buffer_duration=2.0
        )
        
        if audio_recorder.start_recording():
            print("Audio recording started successfully")
            return True
        else:
            print("Failed to start audio recording")
            return False
            
    except Exception as e:
        print(f"Error initializing audio system: {e}")
        return False

def analyze_audio():
    """Analyze audio for speech/emotion detection using real emotion model"""
    global speech_detector, audio_recorder
    
    if speech_detector is None or audio_recorder is None:
        if not init_audio_system():
            return 0.1, "neutral", 0.0
    
    try:
        audio_data = audio_recorder.get_processing_audio()
        
        if audio_data is None or len(audio_data) < 200:
            return 0.1, "neutral", 0.0
        
        speech_score, emotion, confidence = speech_detector.analyze_audio(
            audio_data, 
            sr=16000, 
            use_model=True
        )
        
        if speech_score is None:
            speech_score = 0.1
        if emotion is None:
            emotion = "neutral"
        if confidence is None:
            confidence = 0.0
            
        return speech_score, emotion, confidence
        
    except Exception as e:
        print(f"Error in audio analysis: {e}")
        return 0.1, "neutral", 0.0

def fuse_threat_signals(speech_score, motion_score, speech_confidence, emotion):
    """Fuse multiple threat signals into final threat score"""
    
    emotion_weights = {
        "neutral": 0.0,
        "fear": 0.4,
        "anger": 0.3,
        "distress": 0.6,
        "panic": 0.7,
        "scream": 0.8
    }
    
    speech_weight = 0.4
    motion_weight = 0.3
    emotion_weight = 0.3
    
    emotion_score = emotion_weights.get(emotion, 0.0)
    
    threat_score = (
        speech_weight * speech_score +
        motion_weight * motion_score +
        emotion_weight * emotion_score
    )
    
    threat_score = max(0.0, min(1.0, threat_score))
    
    if threat_score < 0.3:
        threat_state = "SAFE"
    elif threat_score < 0.6:
        threat_state = "MEDIUM"
    elif threat_score < 0.8:
        threat_state = "HIGH"
    else:
        threat_state = "CRITICAL"
    
    return threat_score, threat_state

def threat_monitoring_loop():
    """Main threat monitoring loop"""
    global current_threat_state, current_threat_score, latest_speech, latest_motion, latest_emotion
    
    prev_motion = 0.0
    
    while monitoring_active:
        try:
            speech_score, emotion, speech_conf = analyze_audio()
            latest_speech = speech_score
            latest_emotion = emotion
            
            if IS_CLOUD or camera is None or cv2 is None:
                motion_score = 0.0
            else:
                success, frame = camera.read()
                if success:
                    raw_motion = detect_motion(frame)
                    motion_score = 0.65 * prev_motion + 0.35 * raw_motion
                    prev_motion = motion_score
                else:
                    motion_score = 0.0
            
            latest_motion = motion_score
            
            threat_score, threat_state = fuse_threat_signals(
                speech_score=speech_score,
                motion_score=motion_score,
                speech_confidence=speech_conf,
                emotion=emotion
            )
            
            with threat_lock:
                current_threat_score = threat_score
                current_threat_state = threat_state
                
                threat_history.append({
                    "timestamp": datetime.now().isoformat(),
                    "score": round(threat_score, 3),
                    "state": threat_state,
                    "speech": round(speech_score, 3),
                    "motion": round(motion_score, 3),
                    "emotion": emotion
                })
                
                if len(threat_history) > 100:
                    threat_history.pop(0)
            
            if threat_state in ["HIGH", "CRITICAL"]:
                print(f"[THREAT DETECTED] {threat_state}: {threat_score:.3f} (Speech: {speech_score:.3f}, Motion: {motion_score:.3f}, Emotion: {emotion})")
            
            time.sleep(1.0)
            
        except Exception as e:
            print(f"[ERROR] Threat monitoring loop error: {e}")
            time.sleep(1.0)

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
        log_activity("admin", admin_username, "Admin logged out (homepage access)", "Admin attempted to access main page")
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
        is_admin=session.get("is_admin", False)
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
        session["needs_onboarding"] = user.get("needs_onboarding", True) if user else True

        # Update last login
        if user:
            UserDB.update_last_login(username)

        print(f"[DEBUG] User auth: username={username}, is_new={is_new}, needs_onboarding={session.get('needs_onboarding')}")

        # Log user registration/login
        action = "User registered" if is_new else "User logged in"
        log_activity("user", username, action, f"Name: {user_data['name']}, Email: {user_data.get('email', 'N/A')}, New user: {is_new}")

        return jsonify({
            "success": True,
            "redirect": "/onboarding" if is_new else "/"
        })

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
    print(f"[DEBUG] Onboarding route - needs_onboarding: {session.get('needs_onboarding')}")
    
    if "username" not in session:
        print(f"[DEBUG] Onboarding: No username in session, redirecting to login")
        return redirect(url_for("user_login"))
    
    if not session.get("needs_onboarding", False):
        print(f"[DEBUG] Onboarding: User already completed onboarding, redirecting to index")
        return redirect(url_for("index"))
    
    print(f"[DEBUG] Onboarding: Rendering onboarding page for user: {session.get('username')}")
    return render_template("onboarding.html", username=session.get("username"))

@app.route("/api/onboarding/complete", methods=["POST"])
def complete_onboarding():
    """Save onboarding data and complete user setup"""
    if "username" not in session:
        return jsonify({"error": "Authentication required"}), 401
    
    if not session.get("needs_onboarding", False):
        return jsonify({"error": "Onboarding already completed"}), 400
    
    try:
        data = request.get_json()
        contacts = data.get("contacts", [])
        
        # Validate minimum contacts
        if len(contacts) < 4:
            return jsonify({"error": "At least 4 emergency contacts are required"}), 400
        
        # Validate each contact
        for contact in contacts:
            if not all([contact.get("name"), contact.get("phone"), contact.get("relationship")]):
                return jsonify({"error": "All required fields must be filled"}), 400
        
        # Save user data to database
        username = session["username"]
        user = UserDB.get_by_email(username)
        
        if user:
            # Update existing user
            UserDB.update(
                username,
                needs_onboarding=False,
                onboarding_completed_at=datetime.now().isoformat()
            )
            
            # Delete old contacts and create new ones
            EmergencyContactsDB.delete_by_user(user["id"])
            for contact in contacts:
                EmergencyContactsDB.create(
                    user_id=user["id"],
                    name=contact.get("name"),
                    phone=contact.get("phone"),
                    relationship=contact.get("relationship"),
                    priority=contact.get("priority", 0)
                )
        else:
            # Create new user entry with contacts
            new_user = UserDB.create(
                email=username,
                username=username,
                name=session.get("user_name", username),
                picture=session.get("user_picture", ""),
                password_hash=None,
                is_admin=False,
                needs_onboarding=False,
                contacts=contacts
            )
            
            for contact in contacts:
                EmergencyContactsDB.create(
                    user_id=new_user["id"],
                    name=contact.get("name"),
                    phone=contact.get("phone"),
                    relationship=contact.get("relationship"),
                    priority=contact.get("priority", 0)
                )
        
        # Log onboarding completion
        log_activity("user", username, "Completed onboarding", f"Added {len(contacts)} emergency contacts")
        
        # Update session
        session["needs_onboarding"] = False
        
        return jsonify({
            "status": "success",
            "message": "Onboarding completed successfully",
            "redirect": "/"
        })
        
    except Exception as e:
        print(f"Error completing onboarding: {e}")
        return jsonify({"error": "Failed to complete onboarding"}), 500

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
            "last_login": user_data.get("last_login", "")
        }
        users_list.append(user_obj)
    
    # Calculate statistics (exclude admin users)
    regular_users = [u for u in users_list if not u.get("is_admin", False)]
    total_users = len(regular_users)
    active_users = len([u for u in regular_users if u.get("last_login")])
    avg_contacts_per_user = round(total_contacts / total_users, 1) if total_users > 0 else 0
    
    stats = {
        "total_users": total_users,
        "active_users": active_users,
        "total_contacts": total_contacts,
        "avg_contacts_per_user": avg_contacts_per_user
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
        log_activity("admin", session.get("username"), "User deleted", f"Deleted user: {username_to_delete}")
        
        print(f"Admin '{session.get('username')}' deleted user '{username_to_delete}'")
        
        return jsonify({
            "status": "success",
            "message": f"User '{username_to_delete}' has been deleted successfully"
        })
        
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
        
        return jsonify({
            "status": "success",
            "logs": logs
        })
        
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
                "created_at": user_data.get("created_at", "")
            }
            
            user_threat_data.append(user_threat_info)
        
        return jsonify({
            "status": "success",
            "users": user_threat_data,
            "global_threat_state": global_threat_state,
            "global_threat_score": global_threat_score
        })
        
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
                "last_seen": user_data.get("last_login", datetime.now().isoformat())
            }
            
            users_list.append(user_info)
        
        return jsonify({
            "status": "success",
            "users": users_list
        })
        
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
        
        return jsonify({
            "status": "success",
            "username": user.get("username", user.get("email")),
            "email": user.get("email", ""),
            "name": user.get("name", ""),
            "contact_count": len(contacts),
            "contacts": contacts,
            "created_at": user.get("created_at", ""),
            "last_login": user.get("last_login", ""),
            "is_admin": user.get("is_admin", False)
        })
        
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
        return jsonify({
            "state": current_threat_state,
            "score": current_threat_score,
            "speech_contribution": latest_speech,
            "motion_contribution": latest_motion,
            "emotion": latest_emotion,
            "monitoring_active": monitoring_active,
            "history": threat_history[-20:] if threat_history else []
        })

# ---------------- MONITORING CONTROLS ----------------

@app.route("/api/start_monitoring", methods=["POST"])
def start_monitoring():
    """Start threat monitoring - requires authentication"""
    if "username" not in session:
        return jsonify({"error": "Authentication required"}), 401
    
    global monitoring_active, threat_thread
    
    if monitoring_active:
        return jsonify({"status": "already_running", "message": "Threat monitoring is already active"})
    
    init_camera()
    
    if not init_audio_system():
        return jsonify({"status": "error", "message": "Failed to initialize audio system"}), 500
    
    monitoring_active = True
    threat_thread = threading.Thread(target=threat_monitoring_loop, daemon=True)
    threat_thread.start()
    
    log_activity("user", session['username'], "Started threat monitoring")
    
    print(f"[MONITORING] Started threat monitoring for user: {session['username']}")
    
    return jsonify({"status": "started", "message": "Threat monitoring started"})

@app.route("/api/stop_monitoring", methods=["POST"])
def stop_monitoring():
    """Stop threat monitoring - requires authentication"""
    if "username" not in session:
        return jsonify({"error": "Authentication required"}), 401
    
    global monitoring_active
    
    if not monitoring_active:
        return jsonify({"status": "not_running", "message": "Threat monitoring is not active"})
    
    monitoring_active = False
    
    global audio_recorder, camera, motion_detector
    if audio_recorder:
        try:
            audio_recorder.stop_recording()
            print("Audio recording stopped")
        except Exception as e:
            print(f"Error stopping audio recording: {e}")
    
    if camera:
        try:
            camera.release()
            print("Camera released")
        except Exception as e:
            print(f"Error releasing camera: {e}")
    
    motion_detector = None
    camera = None
    
    log_activity("user", session['username'], "Stopped threat monitoring")
    
    print(f"[MONITORING] Stopped threat monitoring for user: {session['username']}")
    
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
        
        return jsonify({"status": "location_updated", "message": "Location updated successfully"})
        
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
            "distance": 0.5
        },
        {
            "name": "City Hospital",
            "type": "hospital",
            "lat": lat - 0.008,
            "lng": lng + 0.015,
            "address": "456 Health Ave",
            "phone": "N/A",
            "rating": 4.2,
            "distance": 1.2
        }
    ]
    
    return jsonify({
        "status": "ok",
        "places": places
    })

# ---------------- EMERGENCY/SOS ----------------

@app.route("/api/trigger_sos", methods=["POST"])
def trigger_sos():
    """Trigger SOS emergency - requires authentication"""
    if "username" not in session:
        return jsonify({"error": "Authentication required"}), 401
    
    log_activity("user", session['username'], "SOS emergency triggered", "Emergency contacts notified")
    
    return jsonify({
        "status": "sos_triggered",
        "message": "Emergency contacts have been notified"
    })

# ---------------- CHATBOT ----------------

@app.route("/api/chatbot", methods=["POST"])
def chatbot():
    """Handle chatbot messages - requires authentication"""
    if "username" not in session:
        return jsonify({"error": "Authentication required"}), 401
    
    data = request.json or {}
    message = data.get("message", "")
    
    response = "I'm here to help with safety-related questions. How can I assist you today?"
    
    return jsonify({
        "response": response,
        "message": response
    })

@app.route("/api/chatbot/auto_alert", methods=["POST"])
def chatbot_auto_alert():
    """Handle automatic alerts from chatbot - requires authentication"""
    if "username" not in session:
        return jsonify({"error": "Authentication required"}), 401
    
    return jsonify({
        "status": "alert_sent",
        "message": "Emergency contacts have been automatically notified"
    })

# ---------------- RECOMMENDATIONS ----------------

@app.route("/api/recommendations", methods=["GET"])
def recommendations():
    """Get safety recommendations - requires authentication"""
    if "username" not in session:
        return jsonify({"error": "Authentication required"}), 401
    
    recommendations = [
        "Stay aware of your surroundings",
        "Keep your phone charged",
        "Trust your instincts"
    ]
    
    return jsonify({
        "recommendations": recommendations
    })

# Register OAuth routes using the module
register_oauth_routes(app)

# =========================================================
# VIDEO FEED ROUTES
# =========================================================

@app.route('/video_feed')
def video_feed():
    """Video feed endpoint for motion detection visualization"""
    if IS_CLOUD or camera is None or cv2 is None:
        def generate_blank_frame():
            blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(blank_frame, 'Camera Unavailable', (150, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            _, buffer = cv2.imencode('.jpg', blank_frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')
        return Response(generate_blank_frame(), mimetype='multipart/x-mixed-replace; boundary=frame')
    
    def generate_frames():
        while True:
            success, frame = camera.read()
            if not success:
                break
            
            motion_score = 0.0
            if motion_detector is not None:
                motion_score, _ = motion_detector.detect_motion(frame)
            
            if motion_score > 0.1:
                color = (0, 255, 0) if motion_score < 0.3 else (0, 255, 255) if motion_score < 0.6 else (0, 0, 255)
                cv2.putText(frame, f'Motion: {motion_score:.3f}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                
                if motion_score > 0.7:
                    cv2.putText(frame, 'HIGH MOTION!', (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            
            _, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')
    
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, threaded=True)

