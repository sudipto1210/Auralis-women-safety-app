#!/usr/bin/env python3
"""
Clear user data to test onboarding flow with fresh account
Uses Supabase database
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv

load_dotenv()

from database.database import UserDB, EmergencyContactsDB, ActivityLogsDB


def backup_and_clear_users():
    """Backup current users and clear all except admin"""

    try:
        # Get all users
        users = UserDB.get_all_users()

        print("=== Current Users in System ===")
        for user in users:
            email = user.get("email", "Unknown")
            username = user.get("username", "Unknown")
            onboarding = user.get("needs_onboarding", "Unknown")
            is_admin = user.get("is_admin", False)
            print(f"  {email} (@{username})")
            print(f"    - is_admin: {is_admin}")
            print(f"    - needs_onboarding: {onboarding}")
            print(f"    - created_at: {user.get('created_at', 'Unknown')}")
            print()

        # Count non-admin users
        non_admin = [u for u in users if not u.get("is_admin", False)]
        admin = [u for u in users if u.get("is_admin", False)]

        print(f"Total users: {len(users)}")
        print(f"Admin users: {len(admin)}")
        print(f"Regular users: {len(non_admin)}")

        return True

    except Exception as e:
        print(f"Error: {e}")
        return False


def clear_regular_users():
    """Clear all regular users (keep admins)"""

    try:
        users = UserDB.get_all_users()
        cleared = 0

        for user in users:
            if not user.get("is_admin", False):
                UserDB.delete_by_id(user["id"])
                print(f"Deleted user: {user.get('email', user.get('username'))}")
                cleared += 1

        print(f"\nCleared {cleared} regular users")
        print("\n=== Instructions ===")
        print("1. Clear your browser cache or use incognito mode")
        print("2. Restart the server if needed")
        print("3. Try logging in with your Google account again")

        return True

    except Exception as e:
        print(f"Error: {e}")
        return False


def show_users():
    """Show current users"""

    try:
        users = UserDB.get_all_users()

        print("\n=== Current Users ===")
        for user in users:
            email = user.get("email", "Unknown")
            username = user.get("username", "Unknown")
            onboarding = user.get("needs_onboarding", "Unknown")
            is_admin = user.get("is_admin", False)
            created = user.get("created_at", "Unknown")
            last_login = user.get("last_login", "Never")

            print(f"  {email} (@{username})")
            print(f"    - is_admin: {is_admin}")
            print(f"    - needs_onboarding: {onboarding}")
            print(f"    - created: {created}")
            print(f"    - last_login: {last_login}")
            print()

        return True

    except Exception as e:
        print(f"Error reading users: {e}")
        return False


def show_activity_logs():
    """Show recent activity logs"""

    try:
        logs = ActivityLogsDB.get_recent(10)

        print("\n=== Recent Activity Logs ===")
        for log in logs:
            print(
                f"  [{log.get('user_type', 'unknown')}] {log.get('username')}: {log.get('action')}"
            )
            if log.get("details"):
                print(f"    Details: {log.get('details')}")

        return True

    except Exception as e:
        print(f"Error reading activity logs: {e}")
        return False


def main():
    print("=== User Data Management Tool (Supabase) ===")
    print("This tool helps manage user data for testing")
    print()

    while True:
        print("Options:")
        print("1. Show all users")
        print("2. Clear all regular users (keep admins)")
        print("3. Show activity logs")
        print("4. Exit")

        choice = input("\nSelect option (1-4): ").strip()

        if choice == "1":
            show_users()

        elif choice == "2":
            confirm = input("This will delete all regular user data. Continue? (y/N): ")
            if confirm.lower() == "y":
                clear_regular_users()
            else:
                print("Cancelled")

        elif choice == "3":
            show_activity_logs()

        elif choice == "4":
            print("Goodbye!")
            break

        else:
            print("Invalid choice")

        print("\n" + "=" * 50 + "\n")


if __name__ == "__main__":
    main()
