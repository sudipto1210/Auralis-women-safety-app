"""
Push Notification Module
Simulates push notifications for SOS and alerts
"""

import json
from datetime import datetime


class PushNotifier:
    """Handles push notifications for safety alerts"""

    def __init__(self):
        self.notification_history = []
        self.max_history = 100

    # -------------------------------------------------------------------------
    # Internal Utility: Safely format contact
    # -------------------------------------------------------------------------
    def _format_contact(self, contact):
        return {
            "name": contact.get("name", "Unknown"),
            "phone": contact.get("phone", ""),
            "email": contact.get("email", ""),
        }

    # -------------------------------------------------------------------------
    # Internal Utility: Append to history safely
    # -------------------------------------------------------------------------
    def _store_notification(self, notification):
        self.notification_history.append(notification)
        if len(self.notification_history) > self.max_history:
            self.notification_history = self.notification_history[-self.max_history :]

    # -------------------------------------------------------------------------
    # SOS Notification
    # -------------------------------------------------------------------------
    def send_sos_notification(self, user_data, location=None):
        """
        Send SOS notification to emergency contacts
        """

        contacts = user_data.get("contacts", [])
        username = user_data.get("username", "User")

        if not isinstance(contacts, list):
            return {"success": False, "message": "Invalid contact list"}

        notifications_sent = []

        for contact in contacts:
            formatted_contact = self._format_contact(contact)

            notification = {
                "type": "SOS_ALERT",
                "timestamp": datetime.utcnow().isoformat(),
                "contact": formatted_contact,
                "message": f"URGENT: SOS activated by {username}",
                "location": location if isinstance(location, dict) else None,
                "status": "sent",
            }

            notifications_sent.append(notification)
            self._store_notification(notification)

        return {
            "success": True,
            "notifications_sent": len(notifications_sent),
            "details": notifications_sent,
        }

    # -------------------------------------------------------------------------
    # Threat-Level Notification
    # -------------------------------------------------------------------------
    def send_threat_alert(self, user_data, threat_level, location=None):
        """
        Send alert when user threat level is HIGH or CRITICAL
        """

        if threat_level not in ["HIGH", "CRITICAL"]:
            return {
                "success": False,
                "message": "Threat level not high enough for alert",
            }

        contacts = user_data.get("contacts", [])
        username = user_data.get("username", "User")

        if not isinstance(contacts, list):
            return {"success": False, "message": "Invalid contact list"}

        notifications_sent = []

        for contact in contacts:
            formatted_contact = self._format_contact(contact)

            notification = {
                "type": "THREAT_ALERT",
                "timestamp": datetime.utcnow().isoformat(),
                "contact": formatted_contact,
                "message": f"Alert: {username} threat level is {threat_level}",
                "threat_level": threat_level,
                "location": location if isinstance(location, dict) else None,
                "status": "sent",
            }

            notifications_sent.append(notification)
            self._store_notification(notification)

        return {
            "success": True,
            "notifications_sent": len(notifications_sent),
            "details": notifications_sent,
        }

    # -------------------------------------------------------------------------
    # Read History
    # -------------------------------------------------------------------------
    def get_notification_history(self, limit=20):
        """Retrieve last N notifications"""
        if limit <= 0:
            return []
        return self.notification_history[-limit:]
