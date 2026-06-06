#!/usr/bin/env python3
"""
Admin Password Setup Script
Creates or updates admin user in Supabase database with securely hashed password

Usage:
    python setup_admin.py --username admin --password "your-secure-password"
    
Or interactive mode:
    python setup_admin.py
"""

import sys
import os
import getpass

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file

from database import init_supabase, UserDB, check_database_connection

def setup_admin(username: str, password: str):
    """Create or update admin user with hashed password"""
    print(f"🔐 Setting up admin user: {username}")
    
    try:
        # Initialize database connection
        print("📦 Connecting to Supabase...")
        init_supabase()
        
        if not check_database_connection():
            print("❌ Failed to connect to database")
            return False
        
        # Create/update admin user
        print("💾 Creating admin user in database...")
        admin = UserDB.create_admin(username, password)
        
        print(f"✅ Admin user '{username}' created/updated successfully!")
        print(f"   User ID: {admin['id']}")
        print(f"   Email: {admin['email']}")
        print(f"   Is Admin: {admin['is_admin']}")
        print()
        print("⚠️  IMPORTANT: Remove ADMIN_USERNAME and ADMIN_PASSWORD from .env file")
        print("   The database is now the single source of truth for admin authentication.")
        
        return True
        
    except Exception as e:
        print(f"❌ Error setting up admin: {e}")
        return False

def interactive_setup():
    """Interactive admin setup"""
    print("=" * 60)
    print("ADMIN PASSWORD SETUP - Supabase Database")
    print("=" * 60)
    print()
    
    # Get username
    default_username = "admin"
    username = input(f"Admin username [{default_username}]: ").strip()
    if not username:
        username = default_username
    
    # Get password (with confirmation)
    while True:
        password = getpass.getpass("Password: ")
        if len(password) < 8:
            print("❌ Password must be at least 8 characters long")
            continue
            
        password_confirm = getpass.getpass("Confirm password: ")
        
        if password != password_confirm:
            print("❌ Passwords do not match")
            continue
            
        break
    
    print()
    return setup_admin(username, password)

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Admin Password Setup for Supabase")
    parser.add_argument("--username", "-u", type=str, help="Admin username")
    parser.add_argument("--password", "-p", type=str, help="Admin password")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")
    
    args = parser.parse_args()
    
    if args.interactive:
        success = interactive_setup()
        sys.exit(0 if success else 1)
    
    if args.username and args.password:
        success = setup_admin(args.username, args.password)
        sys.exit(0 if success else 1)
    
    if args.username or args.password:
        print("❌ Both --username and --password are required")
        parser.print_help()
        sys.exit(1)
    
    # Default to interactive mode
    success = interactive_setup()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()

