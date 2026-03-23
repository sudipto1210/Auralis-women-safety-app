"""
Production WSGI Entry Point for Render Deployment
Optimized for Gunicorn with gthread workers for ML/audio workloads
"""

import os
import sys
import json
import logging
import threading
from datetime import datetime, timezone
from uuid import uuid4

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

# Ensure we use the virtual environment's site-packages
VENV_PATH = os.path.join(PROJECT_ROOT, "venv")
if os.path.exists(VENV_PATH):
    venv_site_packages = os.path.join(VENV_PATH, "lib")
    for item in os.listdir(venv_site_packages):
        if item.startswith("python"):
            site_packages = os.path.join(venv_site_packages, item, "site-packages")
            if os.path.exists(site_packages):
                sys.path.insert(0, site_packages)
                break

# =========================================================
# PRODUCTION LOGGING (JSON-like structured format)
# =========================================================

class ProductionLogger:
    """Production-safe structured logger using stdlib logging"""
    
    _initialized = False
    _lock = threading.Lock()
    
    @classmethod
    def setup(cls):
        with cls._lock:
            if cls._initialized:
                return
            cls._initialized = True
            
            cls.logger = logging.getLogger("auralis")
            cls.logger.setLevel(logging.INFO)
            cls.logger.handlers.clear()
            
            handler = logging.StreamHandler()
            handler.setLevel(logging.INFO)
            
            formatter = logging.Formatter(
                '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "name": "%(name)s", "message": "%(message)s"}'
            )
            handler.setFormatter(formatter)
            cls.logger.addHandler(handler)
    
    @classmethod
    def get_logger(cls, name=None):
        cls.setup()
        return cls.logger if name is None else cls.logger.getChild(name)

logger = ProductionLogger.get_logger("wsgi")

# =========================================================
# SUPABASE INITIALIZATION (runs once per worker)
# =========================================================

_supabase_initialized = False
_supabase_lock = threading.Lock()

def initialize_supabase_once():
    """Initialize Supabase only once per worker process"""
    global _supabase_initialized
    
    with _supabase_lock:
        if _supabase_initialized:
            logger.info("Supabase already initialized for this worker")
            return True
        
        try:
            from Database.database import init_supabase, check_database_connection, ensure_admin_exists
            init_supabase()
            if not check_database_connection():
                raise RuntimeError("Database connection failed")
            ensure_admin_exists()
            _supabase_initialized = True
            logger.info("Supabase initialized successfully (worker init)")
            return True
        except Exception as e:
            logger.error(f"Supabase initialization failed: {e}")
            # Don't raise - allow app to start, health check will catch issues
            return False

# =========================================================
# FLASK APPLICATION FACTORY
# =========================================================

def create_app():
    """Application factory with production settings"""
    
    from flask import Flask, g, request
    from dotenv import load_dotenv
    from Backend.server_backend import app as backend_app
    
    load_dotenv()
    
    FRONTEND_DIR = os.path.join(PROJECT_ROOT, "Frontend")
    
    app = Flask(
        __name__,
        template_folder=os.path.join(FRONTEND_DIR, "templates"),
        static_folder=os.path.join(FRONTEND_DIR, "static")
    )
    
    app.secret_key = os.environ.get("SECRET_KEY")
    app.config["SESSION_COOKIE_SECURE"] = True
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["DEBUG"] = False
    app.config["TESTING"] = False
    
    # Health check routes for Render (must not conflict with backend routes)
    @app.route("/health")
    @app.route("/healthz")
    def render_health():
        return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}
    
    # Request ID middleware
    @app.before_request
    def before_request():
        g.request_id = request.headers.get("X-Request-ID", str(uuid4()))
        g.start_time = datetime.now(timezone.utc)
    
    @app.after_request
    def after_request(response):
        response.headers["X-Request-ID"] = g.get("request_id", "N/A")
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        
        if hasattr(g, "start_time"):
            duration = (datetime.now(timezone.utc) - g.start_time).total_seconds()
        logger.info(
                f"request_completed method={request.method} path={request.path} "
                f"status={response.status_code} duration_ms={round(duration * 1000, 2)} "
                f"user={request.cookies.get('session', 'none')[:20]}..."
            )
        
        return response
    
    # Copy routes from backend app (skip static to avoid conflict)
    skipped = 0
    static_skipped = []
    for rule in backend_app.url_map.iter_rules():
        endpoint = rule.endpoint
        if endpoint == 'static':
            static_skipped.append(rule.rule)
            skipped += 1
            continue
        if endpoint in backend_app.view_functions:
            try:
                app.add_url_rule(rule.rule, endpoint, backend_app.view_functions[endpoint], methods=rule.methods)
            except AssertionError as e:
                print(f"[WSGI SKIPPED] {endpoint} {rule.rule}: {e}")
                skipped += 1
                continue
    print(f"[WSGI] Copied routes OK. Skipped static={static_skipped} other_conflicts={skipped-len(static_skipped)} Total backend rules={len(backend_app.url_map.rules)}")
    
    # Error handlers
    @app.errorhandler(400)
    def bad_request(error):
        return {"error": "Bad request", "request_id": g.get("request_id")}, 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        return {"error": "Unauthorized", "request_id": g.get("request_id")}, 401
    
    @app.errorhandler(403)
    def forbidden(error):
        return {"error": "Forbidden", "request_id": g.get("request_id")}, 403
    
    @app.errorhandler(404)
    def not_found(error):
        return {"error": "Not found", "request_id": g.get("request_id")}, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"internal_error request_id={g.get('request_id')} error={error}")
        return {"error": "Internal server error", "request_id": g.get("request_id")}, 500
    
    print(f"[WSGI DEBUG] Total routes: {len(app.url_map.rules)}")
    logger.info("flask_app_created production=true")
    logger.info(f"Routes loaded: {len(app.url_map.rules)}")
    
    return app

# Initialize Supabase on module load (per-worker)
initialize_supabase_once()

# Create application instance
app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, threaded=True)

