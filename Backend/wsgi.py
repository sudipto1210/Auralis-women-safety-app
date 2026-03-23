#!/usr/bin/env python3
"""Production WSGI Entry Point for Render - Simplified"""

import sys
import os
from datetime import datetime, timezone
import logging
import threading

# Add project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

# Production logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('auralis')

# Supabase worker init
_supabase_initialized = False
_supabase_lock = threading.Lock()

def initialize_supabase_once():
    global _supabase_initialized
    with _supabase_lock:
        if _supabase_initialized:
            return
        try:
            from Database.database import init_supabase, check_database_connection, ensure_admin_exists
            init_supabase()
            if check_database_connection():
                ensure_admin_exists()
                logger.info("Supabase initialized")
            _supabase_initialized = True
        except Exception as e:
            logger.error(f"Supabase init failed: {e}")

# Initialize before import
initialize_supabase_once()

# Import production Flask app
from Backend.server_backend import app

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
