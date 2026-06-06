"""
Supabase Database Module
Provides database operations for Women Safety App
Uses Supabase as the primary database (no fallback to JSON)
"""

import os
import json
from datetime import datetime
from uuid import uuid4
from supabase import create_client, Client
from werkzeug.security import generate_password_hash, check_password_hash

# =========================================================
# SUPABASE CLIENT INITIALIZATION
# =========================================================

_supabase_client: Client = None


def init_supabase() -> Client:
    """Initialize Supabase client from environment variables"""
    global _supabase_client
    
    if _supabase_client is not None:
        return _supabase_client
    
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    
    if not supabase_url or not supabase_service_key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in environment variables. "
            "Application cannot start without database connection."
        )
    
    _supabase_client = create_client(supabase_url, supabase_service_key)
    print("✅ Supabase client initialized successfully")
    return _supabase_client


def get_supabase() -> Client:
    """Get Supabase client, initializing if necessary"""
    global _supabase_client
    
    if _supabase_client is None:
        return init_supabase()
    
    return _supabase_client


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def datetime_to_iso(dt: datetime) -> str:
    """Convert datetime to ISO format string"""
    if dt is None:
        return None
    return dt.isoformat()


def json_dumps(data) -> str:
    """Safely dump data to JSON string"""
    if data is None:
        return None
    return json.dumps(data)


def json_loads(data: str):
    """Safely load data from JSON string"""
    if data is None:
        return None
    if isinstance(data, dict):
        return data
    try:
        return json.loads(data)
    except (json.JSONDecodeError, TypeError):
        return None


# =========================================================
# USER OPERATIONS
# =========================================================

class UserDB:
    """Database operations for users"""
    
    @staticmethod
    def get_by_email(email: str) -> dict:
        """Get user by email"""
        supabase = get_supabase()
        result = supabase.table("users").select("*").eq("email", email).execute()
        
        if result.data and len(result.data) > 0:
            return result.data[0]
        return None
    
    @staticmethod
    def get_by_username(username: str) -> dict:
        """Get user by username"""
        supabase = get_supabase()
        result = supabase.table("users").select("*").eq("username", username).execute()
        
        if result.data and len(result.data) > 0:
            return result.data[0]
        return None
    
    @staticmethod
    def get_by_google_id(google_id: str) -> dict:
        """Get user by Google ID"""
        supabase = get_supabase()
        result = supabase.table("users").select("*").eq("google_id", google_id).execute()
        
        if result.data and len(result.data) > 0:
            return result.data[0]
        return None
    
    @staticmethod
    def get_admin_users() -> list:
        """Get all admin users"""
        supabase = get_supabase()
        result = supabase.table("users").select("*").eq("is_admin", True).execute()
        return result.data or []
    
    @staticmethod
    def get_all_users() -> list:
        """Get all users (admin use only)"""
        supabase = get_supabase()
        result = supabase.table("users").select("*").order("created_at", desc=True).execute()
        return result.data or []
    
    @staticmethod
    def create(
        email: str,
        username: str,
        name: str = None,
        picture: str = None,
        google_id: str = None,
        password_hash: str = None,
        is_admin: bool = False,
        needs_onboarding: bool = True,
        contacts: list = None
    ) -> dict:
        """Create a new user"""
        supabase = get_supabase()
        
        user_data = {
            "email": email,
            "username": username,
            "name": name,
            "picture": picture,
            "google_id": google_id,
            "password_hash": password_hash,  # NULL for OAuth users
            "is_admin": is_admin,
            "needs_onboarding": needs_onboarding,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # Remove None values
        user_data = {k: v for k, v in user_data.items() if v is not None}
        
        result = supabase.table("users").insert(user_data).execute()
        
        if result.data and len(result.data) > 0:
            # Create emergency contacts if provided
            if contacts:
                for contact in contacts:
                    EmergencyContactsDB.create(
                        user_id=result.data[0]["id"],
                        name=contact.get("name"),
                        phone=contact.get("phone"),
                        relationship=contact.get("relationship"),
                        priority=contact.get("priority", 0)
                    )
            
            return result.data[0]
        
        raise Exception("Failed to create user")
    
    @staticmethod
    def update(email: str, **kwargs) -> dict:
        """Update user data"""
        supabase = get_supabase()
        
        kwargs["updated_at"] = datetime.now().isoformat()
        
        result = supabase.table("users").update(kwargs).eq("email", email).execute()
        
        if result.data and len(result.data) > 0:
            return result.data[0]
        
        raise Exception("Failed to update user")
    
    @staticmethod
    def update_by_id(user_id: str, **kwargs) -> dict:
        """Update user by ID"""
        supabase = get_supabase()
        
        kwargs["updated_at"] = datetime.now().isoformat()
        
        result = supabase.table("users").update(kwargs).eq("id", user_id).execute()
        
        if result.data and len(result.data) > 0:
            return result.data[0]
        
        raise Exception("Failed to update user")
    
    @staticmethod
    def update_last_login(email: str):
        """Update user's last login timestamp"""
        supabase = get_supabase()
        
        supabase.table("users").update({
            "last_login": datetime.now().isoformat()
        }).eq("email", email).execute()
    
    @staticmethod
    def delete(email: str):
        """Delete user by email"""
        supabase = get_supabase()
        supabase.table("users").delete().eq("email", email).execute()
    
    @staticmethod
    def delete_by_id(user_id: str):
        """Delete user by ID"""
        supabase = get_supabase()
        supabase.table("users").delete().eq("id", user_id).execute()
    
    @staticmethod
    def verify_password(email: str, password: str) -> bool:
        """
        Verify user password - returns False for OAuth users
        Can accept either email or username (for admin login)
        """
        # Try to find user by email first
        user = UserDB.get_by_email(email)
        
        # If not found by email, try username
        if not user:
            user = UserDB.get_by_username(email)
        
        if not user:
            return False
        
        # OAuth users have NULL password_hash
        if user.get("password_hash") is None:
            return False
        
        # Must be admin to login with password
        if not user.get("is_admin", False):
            return False
        
        return check_password_hash(user["password_hash"], password)
    
    @staticmethod
    def is_admin(email: str) -> bool:
        """Check if user is admin"""
        user = UserDB.get_by_email(email)
        
        if not user:
            return False
        
        return user.get("is_admin", False)
    
    @staticmethod
    def create_admin(username: str, password: str) -> dict:
        """Create or update admin user with hashed password"""
        supabase = get_supabase()
        
        # Hash the password using Werkzeug's bcrypt
        hashed_password = generate_password_hash(password)
        
        # Check if admin already exists
        existing = UserDB.get_by_username(username)
        
        user_data = {
            "username": username,
            "email": f"{username}@admin.local",
            "name": "Administrator",
            "password_hash": hashed_password,
            "is_admin": True,
            "needs_onboarding": False,
            "updated_at": datetime.now().isoformat()
        }
        
        if existing:
            # Update existing admin
            result = supabase.table("users").update(user_data).eq("id", existing["id"]).execute()
        else:
            # Create new admin
            user_data["created_at"] = datetime.now().isoformat()
            result = supabase.table("users").insert(user_data).execute()
        
        if result.data and len(result.data) > 0:
            return result.data[0]
        
        raise Exception("Failed to create/update admin user")
    
    @staticmethod
    def update_admin_password(username: str, new_password: str) -> dict:
        """Update admin password with new hashed password"""
        supabase = get_supabase()
        
        hashed_password = generate_password_hash(new_password)
        
        result = supabase.table("users").update({
            "password_hash": hashed_password,
            "updated_at": datetime.now().isoformat()
        }).eq("username", username).eq("is_admin", True).execute()
        
        if result.data and len(result.data) > 0:
            return result.data[0]
        
        raise Exception("Failed to update admin password")
    
    @staticmethod
    def get_or_create_oauth_user(user_data: dict) -> tuple:
        """
        Get or create OAuth user
        Returns (user_dict, is_new)
        
        OAuth users will have:
        - password_hash = NULL
        - is_admin = FALSE
        """
        email = user_data["email"]
        
        # Check if user exists
        existing = UserDB.get_by_email(email)
        
        if existing:
            # Update existing user with latest OAuth data
            # IMPORTANT: Never overwrite is_admin or password_hash for OAuth users
            update_data = {
                "name": user_data["name"],
                "picture": user_data["picture"],
                "google_id": user_data["google_id"],
                "last_login": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            # Preserve admin status and password_hash
            update_data["is_admin"] = existing.get("is_admin", False)
            update_data["password_hash"] = existing.get("password_hash")
            
            result = UserDB.update_by_id(existing["id"], **update_data)
            return result, False
        else:
            # Create new OAuth user
            # IMPORTANT: OAuth users cannot be admins and have NULL password_hash
            # Generate unique username from email prefix + random suffix
            email_prefix = email.split('@')[0]
            unique_username = f"{email_prefix}_{uuid4().hex[:6]}"
            
            user = UserDB.create(
                email=email,
                username=unique_username,
                name=user_data["name"],
                picture=user_data["picture"],
                google_id=user_data["google_id"],
                password_hash=None,  # NULL for OAuth users
                is_admin=False,  # OAuth users cannot be admins
                needs_onboarding=True
            )
            return user, True


# =========================================================
# EMERGENCY CONTACTS OPERATIONS
# =========================================================

class EmergencyContactsDB:
    """Database operations for emergency contacts"""
    
    @staticmethod
    def get_by_user(user_id: str) -> list:
        """Get all emergency contacts for a user"""
        supabase = get_supabase()
        result = supabase.table("emergency_contacts").select("*").eq("user_id", user_id).order("priority").execute()
        return result.data or []
    
    @staticmethod
    def create(user_id: str, name: str, phone: str, relationship: str = None, priority: int = 0) -> dict:
        """Create emergency contact"""
        supabase = get_supabase()
        
        contact_data = {
            "user_id": user_id,
            "name": name,
            "phone": phone,
            "relationship": relationship,
            "priority": priority,
            "created_at": datetime.now().isoformat()
        }
        
        result = supabase.table("emergency_contacts").insert(contact_data).execute()
        
        if result.data and len(result.data) > 0:
            return result.data[0]
        
        raise Exception("Failed to create emergency contact")
    
    @staticmethod
    def update(contact_id: str, **kwargs) -> dict:
        """Update emergency contact"""
        supabase = get_supabase()
        result = supabase.table("emergency_contacts").update(kwargs).eq("id", contact_id).execute()
        
        if result.data and len(result.data) > 0:
            return result.data[0]
        
        raise Exception("Failed to update emergency contact")
    
    @staticmethod
    def delete(contact_id: str):
        """Delete emergency contact"""
        supabase = get_supabase()
        supabase.table("emergency_contacts").delete().eq("id", contact_id).execute()
    
    @staticmethod
    def delete_by_user(user_id: str):
        """Delete all emergency contacts for a user"""
        supabase = get_supabase()
        supabase.table("emergency_contacts").delete().eq("user_id", user_id).execute()


# =========================================================
# ACTIVITY LOG OPERATIONS
# =========================================================

class ActivityLogsDB:
    """Database operations for activity logs"""
    
    @staticmethod
    def log(user_type: str, username: str, action: str, details: str = None):
        """Log an activity"""
        supabase = get_supabase()
        
        log_entry = {
            "user_type": user_type,
            "username": username,
            "action": action,
            "details": details,
            "created_at": datetime.now().isoformat()
        }
        
        supabase.table("activity_logs").insert(log_entry).execute()
    
    @staticmethod
    def get_recent(limit: int = 20) -> list:
        """Get recent activity logs"""
        supabase = get_supabase()
        result = supabase.table("activity_logs").select("*").order("created_at", desc=True).limit(limit).execute()
        return result.data or []
    
    @staticmethod
    def get_by_username(username: str, limit: int = 50) -> list:
        """Get activity logs for a specific user"""
        supabase = get_supabase()
        result = supabase.table("activity_logs").select("*").eq("username", username).order("created_at", desc=True).limit(limit).execute()
        return result.data or []
    
    @staticmethod
    def get_by_user_type(user_type: str, limit: int = 50) -> list:
        """Get activity logs by user type (admin/user)"""
        supabase = get_supabase()
        result = supabase.table("activity_logs").select("*").eq("user_type", user_type).order("created_at", desc=True).limit(limit).execute()
        return result.data or []


# =========================================================
# CONFIG OPERATIONS
# =========================================================

class ConfigDB:
    """Database operations for configuration"""
    
    # Emergency Config
    @staticmethod
    def get_emergency_config(config_key: str = "default_emergency_services") -> dict:
        """Get emergency configuration"""
        supabase = get_supabase()
        result = supabase.table("emergency_config").select("*").eq("config_key", config_key).execute()
        
        if result.data and len(result.data) > 0:
            return json_loads(result.data[0].get("config_value"))
        
        # Return default if not found
        defaults = {
            "default_emergency_services": {
                "police": "100",
                "ambulance": "102",
                "fire": "101",
                "women_helpline": "1091"
            },
            "default_sos_settings": {
                "auto_call": False,
                "auto_sms": True,
                "location_sharing": True
            },
            "default_threat_thresholds": {
                "safe": 0.2,
                "low": 0.4,
                "medium": 0.6,
                "high": 0.8,
                "critical": 1.0
            }
        }
        return defaults.get(config_key, {})
    
    @staticmethod
    def set_emergency_config(config_key: str, config_value: dict, config_type: str = "json"):
        """Set emergency configuration"""
        supabase = get_supabase()
        
        data = {
            "config_key": config_key,
            "config_value": json_dumps(config_value),
            "config_type": config_type,
            "updated_at": datetime.now().isoformat()
        }
        
        supabase.table("emergency_config").upsert(data).execute()
    
    # Chatbot Training Config
    @staticmethod
    def get_chatbot_config(config_key: str = "intents") -> dict:
        """Get chatbot training configuration"""
        supabase = get_supabase()
        result = supabase.table("chatbot_training").select("*").eq("config_key", config_key).execute()
        
        if result.data and len(result.data) > 0:
            return json_loads(result.data[0].get("config_value"))
        
        return {}
    
    @staticmethod
    def set_chatbot_config(config_key: str, config_value: dict, config_type: str = "json"):
        """Set chatbot training configuration"""
        supabase = get_supabase()
        
        data = {
            "config_key": config_key,
            "config_value": json_dumps(config_value),
            "config_type": config_type,
            "updated_at": datetime.now().isoformat()
        }
        
        supabase.table("chatbot_training").upsert(data).execute()
    
    # Safe Places Config
    @staticmethod
    def get_safe_places_config(config_key: str = "default_settings") -> dict:
        """Get safe places configuration"""
        supabase = get_supabase()
        result = supabase.table("safe_places_config").select("*").eq("config_key", config_key).execute()
        
        if result.data and len(result.data) > 0:
            return json_loads(result.data[0].get("config_value"))
        
        return {
            "search_radius_km": 5,
            "place_types": ["police_station", "hospital", "safe_zone", "community_center", "women_shelter"]
        }
    
    @staticmethod
    def set_safe_places_config(config_key: str, config_value: dict, config_type: str = "json"):
        """Set safe places configuration"""
        supabase = get_supabase()
        
        data = {
            "config_key": config_key,
            "config_value": json_dumps(config_value),
            "config_type": config_type,
            "updated_at": datetime.now().isoformat()
        }
        
        supabase.table("safe_places_config").upsert(data).execute()


# =========================================================
# THREAT HISTORY OPERATIONS
# =========================================================

class ThreatHistoryDB:
    """Database operations for threat history"""
    
    @staticmethod
    def log(
        user_id: str = None,
        threat_state: str = "SAFE",
        threat_score: float = 0.0,
        speech_contribution: float = 0.0,
        motion_contribution: float = 0.0,
        emotion: str = "neutral"
    ):
        """Log a threat event"""
        supabase = get_supabase()
        
        entry = {
            "user_id": user_id,
            "threat_state": threat_state,
            "threat_score": float(threat_score),
            "speech_contribution": float(speech_contribution) if speech_contribution else None,
            "motion_contribution": float(motion_contribution) if motion_contribution else None,
            "emotion": emotion,
            "created_at": datetime.now().isoformat()
        }
        
        supabase.table("threat_history").insert(entry).execute()
    
    @staticmethod
    def get_recent(user_id: str = None, limit: int = 100) -> list:
        """Get recent threat history"""
        supabase = get_supabase()
        query = supabase.table("threat_history").select("*").order("created_at", desc=True).limit(limit)
        
        if user_id:
            query = query.eq("user_id", user_id)
        
        result = query.execute()
        return result.data or []
    
    @staticmethod
    def get_by_time_range(start_time: str, end_time: str = None, user_id: str = None) -> list:
        """Get threat history by time range"""
        supabase = get_supabase()
        query = supabase.table("threat_history").select("*").gte("created_at", start_time)
        
        if end_time:
            query = query.lte("created_at", end_time)
        
        if user_id:
            query = query.eq("user_id", user_id)
        
        result = query.order("created_at", desc=True).execute()
        return result.data or []
    
    @staticmethod
    def cleanup_older_than(days: int = 30):
        """Delete threat history older than specified days"""
        supabase = get_supabase()
        
        from datetime import timedelta
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        supabase.table("threat_history").delete().lt("created_at", cutoff_date).execute()


# =========================================================
# MIGRATION HELPERS (Optional - for one-time data migration)
# =========================================================

class MigrationHelper:
    """Helper class for migrating data from JSON to Supabase"""
    
    @staticmethod
    def migrate_users_from_json(json_file: str):
        """Migrate users from JSON file to database"""
        import json
        
        with open(json_file, "r") as f:
            users = json.load(f)
        
        for email, user_data in users.items():
            try:
                # Create user in database
                user = UserDB.create(
                    email=email,
                    username=user_data.get("name", email).replace(" ", "_").lower(),
                    name=user_data.get("name"),
                    picture=user_data.get("picture"),
                    google_id=user_data.get("google_id"),
                    password_hash=user_data.get("password_hash"),
                    is_admin=user_data.get("is_admin", False),
                    needs_onboarding=user_data.get("needs_onboarding", True)
                )
                
                # Migrate contacts
                contacts = user_data.get("contacts", [])
                for contact in contacts:
                    EmergencyContactsDB.create(
                        user_id=user["id"],
                        name=contact.get("name"),
                        phone=contact.get("phone"),
                        relationship=contact.get("relationship"),
                        priority=contact.get("priority", 0)
                    )
                
                print(f"✅ Migrated user: {email}")
                
            except Exception as e:
                print(f"❌ Failed to migrate user {email}: {e}")
    
    @staticmethod
    def migrate_activity_logs_from_json(json_file: str):
        """Migrate activity logs from JSON file to database"""
        import json
        
        with open(json_file, "r") as f:
            logs = json.load(f)
        
        for log in logs:
            try:
                ActivityLogsDB.log(
                    user_type=log.get("user_type", "unknown"),
                    username=log.get("username", "unknown"),
                    action=log.get("action", "unknown"),
                    details=log.get("details", "")
                )
            except Exception as e:
                print(f"❌ Failed to migrate log: {e}")
        
        print(f"✅ Migrated {len(logs)} activity logs")
    
    @staticmethod
    def migrate_config_from_json(json_file: str, config_type: str, config_key: str):
        """Migrate config from JSON file to database"""
        import json
        
        with open(json_file, "r") as f:
            config_data = json.load(f)
        
        if config_type == "emergency":
            ConfigDB.set_emergency_config(config_key, config_data)
        elif config_type == "chatbot":
            ConfigDB.set_chatbot_config(config_key, config_data)
        elif config_type == "safe_places":
            ConfigDB.set_safe_places_config(config_key, config_data)
        
        print(f"✅ Migrated {config_type} config: {config_key}")


# =========================================================
# RESEARCH AND ANOMALY DETECTION DATA TABLES
# =========================================================

class UserMotionProfilesDB:
    """Database operations for user motion baseline profiles"""
    
    @staticmethod
    def get_by_user(user_id: str) -> dict:
        """Get motion profile for a user"""
        try:
            supabase = get_supabase()
            result = supabase.table("user_motion_profiles").select("*").eq("user_id", user_id).execute()
            if result.data and len(result.data) > 0:
                return result.data[0]
        except Exception as e:
            print(f"Error getting motion profile: {e}")
        return None
        
    @staticmethod
    def upsert(user_id: str, profile: dict) -> dict:
        """Upsert motion profile for a user"""
        try:
            supabase = get_supabase()
            data = {
                "user_id": user_id,
                "cadence_mean": float(profile.get("cadence_mean", 0.0)),
                "cadence_std": float(profile.get("cadence_std", 0.05)),
                "accel_variance": float(profile.get("accel_variance", 0.0)),
                "peak_magnitude_95th": float(profile.get("peak_magnitude_95th", 0.0)),
                "jerk_mean": float(profile.get("jerk_mean", 0.0)),
                "jerk_std": float(profile.get("jerk_std", 0.1)),
                "gyro_variance": float(profile.get("gyro_variance", 0.0)),
                "created_at": datetime.now().isoformat()
            }
            if "elevated_jerk_mean" in profile:
                data["elevated_jerk_mean"] = float(profile["elevated_jerk_mean"])
            if "elevated_accel_variance" in profile:
                data["elevated_accel_variance"] = float(profile["elevated_accel_variance"])
                
            result = supabase.table("user_motion_profiles").upsert(data).execute()
            if result.data and len(result.data) > 0:
                return result.data[0]
        except Exception as e:
            print(f"Error upserting motion profile: {e}")
        return None


class IncidentsDB:
    """Database operations for research incidents logging"""
    
    @staticmethod
    def create(
        user_id: str,
        motion_score: float,
        audio_score: float,
        fused_score: float,
        threat_level: str,
        event_type: str,
        environment_class: str,
        alert_triggered: bool,
        details: dict = None
    ) -> dict:
        """Create a new incident log"""
        try:
            supabase = get_supabase()
            data = {
                "user_id": user_id,
                "timestamp": datetime.now().isoformat(),
                "motion_score": float(motion_score),
                "audio_score": float(audio_score),
                "fused_score": float(fused_score),
                "threat_level": threat_level,
                "event_type": event_type,
                "environment_class": environment_class,
                "alert_triggered": bool(alert_triggered),
                "details": json_dumps(details)
            }
            result = supabase.table("incidents").insert(data).execute()
            if result.data and len(result.data) > 0:
                return result.data[0]
        except Exception as e:
            print(f"Error creating incident: {e}")
        return None
        
    @staticmethod
    def get_recent(user_id: str = None, limit: int = 50) -> list:
        """Get recent incident logs"""
        try:
            supabase = get_supabase()
            query = supabase.table("incidents").select("*").order("timestamp", desc=True).limit(limit)
            if user_id:
                query = query.eq("user_id", user_id)
            result = query.execute()
            return result.data or []
        except Exception as e:
            print(f"Error getting recent incidents: {e}")
        return []
        
    @staticmethod
    def submit_feedback(incident_id: str, label: str) -> bool:
        """Submit manual feedback for research evaluation"""
        try:
            supabase = get_supabase()
            # If the user marks it as false alarm, we also log it to false_alerts table
            result = supabase.table("incidents").update({
                "feedback": {"label": label, "reviewed_at": datetime.now().isoformat()}
            }).eq("id", incident_id).execute()
            
            if label == "false_alarm" and result.data and len(result.data) > 0:
                user_id = result.data[0].get("user_id")
                FalseAlertsDB.log(incident_id, user_id)
                
            return True
        except Exception as e:
            print(f"Error submitting incident feedback: {e}")
        return False


class FalseAlertsDB:
    """Database operations for false alert tracking"""
    
    @staticmethod
    def log(incident_id: str, user_id: str = None) -> dict:
        """Log a false positive alert for evaluation"""
        try:
            supabase = get_supabase()
            data = {
                "incident_id": incident_id,
                "user_id": user_id,
                "timestamp": datetime.now().isoformat()
            }
            result = supabase.table("false_alerts").insert(data).execute()
            if result.data and len(result.data) > 0:
                return result.data[0]
        except Exception as e:
            print(f"Error logging false alert: {e}")
        return None


# =========================================================
# DATABASE INITIALIZATION CHECK
# =========================================================

def check_database_connection() -> bool:
    """Check if database connection is working"""
    try:
        supabase = get_supabase()
        # Try a simple query
        result = supabase.table("users").select("count", count="exact").limit(1).execute()
        print(f"✅ Database connection successful")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


def ensure_admin_exists(default_username: str = "admin", default_password: str = None):
    """
    Ensure admin user exists in database
    This replaces the old bootstrap_admin() function
    """
    try:
        admins = UserDB.get_admin_users()
        
        if len(admins) == 0:
            # No admin exists, create one
            if default_password is None:
                print("⚠️  No admin user found and no default password provided")
                print("   Please create admin user manually using:")
                print("   python -c 'from database import UserDB; UserDB.create_admin(\"admin\", \"your-password\")'")
                return False
            
            print(f"🔐 Creating default admin user: {default_username}")
            UserDB.create_admin(default_username, default_password)
            print(f"✅ Admin user '{default_username}' created successfully")
        else:
            print(f"✅ Admin user(s) found: {[a['username'] for a in admins]}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error ensuring admin exists: {e}")
        return False

