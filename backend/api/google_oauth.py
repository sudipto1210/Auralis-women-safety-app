"""
Google OAuth Authentication Module
Handles Google Identity Services integration and OAuth debugging
"""

import os
import json
from datetime import datetime
from flask import jsonify, request, session
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from dotenv import load_dotenv

# =========================================================
# GOOGLE OAUTH CONFIGURATION
# =========================================================


def load_google_oauth_config():
    """Load and validate Google OAuth configuration"""
    load_dotenv()

    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
    if not GOOGLE_CLIENT_ID:
        raise RuntimeError("GOOGLE_CLIENT_ID not set")

    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
    GOOGLE_REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI")
    GOOGLE_JAVASCRIPT_ORIGINS = os.environ.get("GOOGLE_JAVASCRIPT_ORIGINS", "").split(
        ","
    )

    return {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "javascript_origins": GOOGLE_JAVASCRIPT_ORIGINS,
    }


# =========================================================
# GOOGLE ID TOKEN VERIFICATION
# =========================================================


def verify_google_id_token(token: str):
    """Verify Google ID token using Google Identity Services"""
    config = load_google_oauth_config()

    try:
        idinfo = id_token.verify_oauth2_token(
            token, google_requests.Request(), config["client_id"]
        )

        if not idinfo.get("email_verified"):
            raise ValueError("Email not verified")

        email = idinfo.get("email", "")
        if not email.endswith("@gmail.com"):
            raise ValueError("Only Gmail accounts allowed")

        return {
            "email": email,
            "name": idinfo.get("name"),
            "picture": idinfo.get("picture"),
            "google_id": idinfo.get("sub"),
        }

    except Exception as e:
        print(f"[OAuth] Token verification failed: {e}")
        return None


# =========================================================
# OAUTH DEBUGGING & TESTING UTILITIES
# =========================================================


def log_oauth_state(action, details=None):
    """Log OAuth state for debugging"""
    timestamp = datetime.now().isoformat()
    log_entry = {
        "timestamp": timestamp,
        "action": action,
        "details": details or {},
        "session_keys": list(session.keys()),
    }
    print(f"[OAUTH DEBUG] {json.dumps(log_entry, indent=2)}")


def validate_oauth_config():
    """Validate OAuth configuration"""
    issues = []

    # Check required environment variables
    required_vars = ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"]
    for var in required_vars:
        if not os.environ.get(var):
            issues.append(f"Missing environment variable: {var}")

    # Validate redirect URI
    redirect_uri = os.environ.get("GOOGLE_REDIRECT_URI")
    if not redirect_uri:
        issues.append("No redirect URI configured")
    elif not redirect_uri.startswith(("http://", "https://")):
        issues.append(f"Invalid redirect URI format: {redirect_uri}")

    # Check JavaScript origins
    origins = os.environ.get("GOOGLE_JAVASCRIPT_ORIGINS", "")
    if origins:
        origin_list = origins.split(",")
        for origin in origin_list:
            origin = origin.strip()
            if not origin.startswith(("http://", "https://")):
                issues.append(f"Invalid JavaScript origin: {origin}")

    return issues


def test_oauth_flow():
    """Test OAuth flow creation"""
    try:
        # Check if we can create a basic flow
        client_id = os.environ.get("GOOGLE_CLIENT_ID")
        client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
        redirect_uri = os.environ.get("GOOGLE_REDIRECT_URI")

        if not all([client_id, client_secret, redirect_uri]):
            return {
                "success": False,
                "error": "Missing required OAuth configuration",
                "missing": {
                    "client_id": not client_id,
                    "client_secret": not client_secret,
                    "redirect_uri": not redirect_uri,
                },
            }

        client_config = {
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [redirect_uri],
            }
        }

        flow = Flow.from_client_config(
            client_config,
            scopes=["openid", "https://www.googleapis.com/auth/userinfo.email"],
        )

        return {
            "success": True,
            "message": "OAuth flow created successfully",
            "flow_details": {
                "client_id": flow.client_config.get("web", {}).get(
                    "client_id", "Not available"
                ),
                "redirect_uri": flow.redirect_uri,
                "scopes": flow.client_config.get("web", {}).get("scopes", []),
            },
        }

    except Exception as e:
        return {"success": False, "error": str(e), "error_type": type(e).__name__}


def analyze_oauth_session():
    """Analyze current OAuth session state"""
    oauth_data = {
        "session_exists": bool(session),
        "oauth_credentials": session.get("oauth_credentials"),
        "state": session.get("state"),
        "oauth_flow": session.get("oauth_flow"),
        "user_info": {
            "username": session.get("username"),
            "user_type": session.get("user_type"),
        },
    }

    # Check if credentials need refreshing
    if oauth_data["oauth_credentials"]:
        creds = oauth_data["oauth_credentials"]
        oauth_data["credentials_valid"] = bool(creds.get("token"))
        oauth_data["has_refresh_token"] = bool(creds.get("refresh_token"))

        # Check token age
        token_received = creds.get("token_received_at")
        if token_received:
            try:
                received_time = datetime.fromisoformat(token_received)
                token_age = (datetime.now() - received_time).total_seconds()
                oauth_data["token_age_seconds"] = token_age
            except:
                oauth_data["token_age_seconds"] = None

    return oauth_data


def get_oauth_debug_info():
    """Get comprehensive OAuth debug information"""
    config_issues = validate_oauth_config()
    flow_test = test_oauth_flow()
    session_analysis = analyze_oauth_session()

    return {
        "timestamp": datetime.now().isoformat(),
        "configuration": {"issues": config_issues, "valid": len(config_issues) == 0},
        "flow_test": flow_test,
        "session": session_analysis,
        "environment": {
            "client_id": os.environ.get("GOOGLE_CLIENT_ID", "NOT_SET")[:20] + "...",
            "redirect_uri": os.environ.get("GOOGLE_REDIRECT_URI", "NOT_SET"),
            "render_mode": os.environ.get("RENDER", "NOT_SET"),
            "flask_env": os.environ.get("FLASK_ENV", "NOT_SET"),
        },
    }


# =========================================================
# OAUTH ROUTES (FLASK ROUTES)
# =========================================================


def register_oauth_routes(app):
    """Register OAuth-related routes with Flask app"""

    @app.route("/api/oauth/debug")
    def oauth_debug():
        """OAuth debugging endpoint"""
        debug_info = get_oauth_debug_info()
        return jsonify(debug_info)

    @app.route("/api/oauth/test_flow")
    def oauth_test_flow():
        """Test OAuth flow creation"""
        result = test_oauth_flow()
        return jsonify(result)

    @app.route("/api/oauth/session")
    def oauth_session():
        """Analyze current OAuth session"""
        analysis = analyze_oauth_session()
        return jsonify(analysis)

    return app


# =========================================================
# USER HELPER FUNCTIONS
# =========================================================


def create_or_update_user_google(user_data, load_users_func=None, save_users_func=None):
    """
    Create or update user with Google ID token data

    IMPORTANT SECURITY RULES:
    - OAuth users must have password_hash = NULL
    - OAuth users must have is_admin = FALSE
    - Never allow OAuth to grant admin privileges
    - Preserve existing user data during OAuth login

    This function now uses Supabase database by default.
    The load_users_func and save_users_func parameters are deprecated.
    """
    # Import here to avoid circular imports
    from database.database import UserDB

    email = user_data["email"]

    # Use database operations
    user, is_new = UserDB.get_or_create_oauth_user(user_data)

    return user["email"], is_new
