"""Signed bearer tokens for React Native / mobile API clients."""

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Optional

TOKEN_TTL_SECONDS = 60 * 60 * 24 * 30  # 30 days


def _secret() -> bytes:
    return os.environ.get("SECRET_KEY", "change-this-in-production").encode("utf-8")


def create_mobile_token(email: str) -> str:
    payload = {
        "email": email,
        "exp": int(time.time()) + TOKEN_TTL_SECONDS,
    }
    body = (
        base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8"))
        .decode("ascii")
        .rstrip("=")
    )
    sig = hmac.new(_secret(), body.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{body}.{sig}"


def verify_mobile_token(token: str) -> Optional[str]:
    if not token or "." not in token:
        return None
    body, sig = token.rsplit(".", 1)
    expected = hmac.new(_secret(), body.encode("ascii"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        return None
    pad = "=" * (-len(body) % 4)
    try:
        payload = json.loads(base64.urlsafe_b64decode(body + pad))
    except (json.JSONDecodeError, ValueError):
        return None
    if payload.get("exp", 0) < int(time.time()):
        return None
    return payload.get("email")
