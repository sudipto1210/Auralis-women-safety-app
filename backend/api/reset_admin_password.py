#!/usr/bin/env python3
"""
Reset Admin Password Script
Resets the admin password in Supabase database

Usage:
    python reset_admin_password.py --username admin --password "new-secure-password"
"""

import sys
import os
import getpass

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv

load_dotenv()

from database import init_supabase, UserDB, check_database_connection


def reset_admin_password(username: str, new_password: str):
    """Reset admin password in database"""
    print(f"🔐 Resetting admin password for: {username}")

    try:
        # Initialize database connection
        print("📦 Connecting to Supabase...")
        init_supabase()

        if not check_database_connection():
            print("❌ Failed to connect to database")
            return False

        # Check if user exists and is admin
        user = UserDB.get_by_username(username)

        if not user:
            print(f"❌ User '{username}' not found")
            return False

        if not user.get("is_admin", False):
            print(f"⚠️  User '{username}' is not an admin")
            return False

        # Update password
        print("💾 Updating password in database...")
        UserDB.update_admin_password(username, new_password)

        print(f"✅ Password reset successfully for admin: {username}")
        print(f"   Email: {user['email']}")
        print()
        print("⚠️  IMPORTANT: Remove ADMIN_USERNAME and ADMIN_PASSWORD from .env file")

        return True

    except Exception as e:
        print(f"❌ Error resetting password: {e}")
        return False


def interactive_reset():
    """Interactive password reset"""
    print("=" * 60)
    print("ADMIN PASSWORD RESET")
    print("=" * 60)
    print()

    default_username = "admin"
    username = input(f"Admin username [{default_username}]: ").strip()
    if not username:
        username = default_username

    while True:
        password = getpass.getpass("New password: ")
        if len(password) < 8:
            print("❌ Password must be at least 8 characters long")
            continue

        password_confirm = getpass.getpass("Confirm password: ")

        if password != password_confirm:
            print("❌ Passwords do not match")
            continue

        break

    print()
    return reset_admin_password(username, password)


def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description="Reset Admin Password")
    parser.add_argument("--username", "-u", type=str, help="Admin username")
    parser.add_argument("--password", "-p", type=str, help="New password")
    parser.add_argument(
        "--interactive", "-i", action="store_true", help="Interactive mode"
    )

    args = parser.parse_args()

    if args.interactive:
        success = interactive_reset()
        sys.exit(0 if success else 1)

    if args.username and args.password:
        success = reset_admin_password(args.username, args.password)
        sys.exit(0 if success else 1)

    if args.username or args.password:
        print("❌ Both --username and --password are required")
        parser.print_help()
        sys.exit(1)

    # Default to interactive mode
    success = interactive_reset()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
