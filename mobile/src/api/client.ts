/**
 * client.ts
 * ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 * Core API client with secure credential management.
 *
 * Security decisions:
 *   • JWT tokens     → Keychain (AES-256 encrypted, hardware-backed on
 *                       supported devices)
 *   • API URL        → Keychain (prevents preference poisoning via ADB
 *                       or backup restore on an insecure device)
 *   • No secrets     → AsyncStorage (AsyncStorage is plaintext SQLite)
 *
 * Token lifecycle:
 *   • Tokens are stored with an issue timestamp
 *   • Tokens older than TOKEN_TTL_MS are treated as expired
 *   • 401 responses trigger auto-signout (via exported onUnauthorized hook)
 *
 * clearAllSecureStorage() wipes ALL Keychain entries on signout —
 * call this instead of just resetting the token key.
 */

import * as Keychain from "react-native-keychain";
import { getApiUrl } from "../config";
import { ApiError } from "./apiError";
import { warn } from "../utils/logger";

// ── Re-export ApiError so callers can import from one place ──────────
export { ApiError };

// ── Keychain service keys ─────────────────────────────────────────────
const TOKEN_SERVICE = "auralis_access_token";
const API_URL_SERVICE = "auralis_api_url";
const TOKEN_TIMESTAMP_SERVICE = "auralis_token_ts";

// Token time-to-live: 7 days (in ms). Adjust to match your backend JWT expiry.
const TOKEN_TTL_MS = 7 * 24 * 60 * 60 * 1000;

// ── In-memory cache (avoids redundant Keychain reads in same session) ─
let _apiUrlCache: string | null = null;

// ── Global 401 hook ───────────────────────────────────────────────────
// Set by AuthContext so that any 401 from any API call triggers signout.
let _onUnauthorized: (() => void) | null = null;

export function registerUnauthorizedHandler(handler: () => void) {
  _onUnauthorized = handler;
}

// ──────────────────────────────────────────────────────────────────────
// API URL — stored in Keychain (not AsyncStorage)
// ──────────────────────────────────────────────────────────────────────

export async function getStoredApiUrl(): Promise<string> {
  if (_apiUrlCache) return _apiUrlCache;

  try {
    const creds = await Keychain.getGenericPassword({ service: API_URL_SERVICE });
    if (creds && creds.password) {
      _apiUrlCache = creds.password;
      return _apiUrlCache;
    }
  } catch (e) {
    warn("SecureStorage", "Keychain URL read failed", e);
  }

  return getApiUrl();
}

export async function setStoredApiUrl(url: string) {
  const sanitized = url.replace(/\/$/, "").trim();
  _apiUrlCache = sanitized;

  try {
    await Keychain.setGenericPassword("url", sanitized, {
      service: API_URL_SERVICE,
      // Do not require user authentication for the URL (just confidentiality)
      accessible: Keychain.ACCESSIBLE.AFTER_FIRST_UNLOCK,
    });
  } catch (e) {
    // On Keychain write failure, keep the in-memory cache so the session works
    warn("SecureStorage", "Could not persist API URL to Keychain", e);
  }
}

// ──────────────────────────────────────────────────────────────────────
// Token management — Keychain with TTL enforcement
// ──────────────────────────────────────────────────────────────────────

export async function getToken(): Promise<string | null> {
  try {
    // Check token age first
    const tsCreds = await Keychain.getGenericPassword({ service: TOKEN_TIMESTAMP_SERVICE });
    if (tsCreds && tsCreds.password) {
      const issuedAt = parseInt(tsCreds.password, 10);
      if (Date.now() - issuedAt > TOKEN_TTL_MS) {
        // Token is expired — clear it and return null
        await clearAllSecureStorage();
        return null;
      }
    }

    const credentials = await Keychain.getGenericPassword({ service: TOKEN_SERVICE });
    return credentials ? credentials.password : null;
  } catch {
    return null;
  }
}

export async function setToken(token: string | null) {
  try {
    if (token) {
      await Keychain.setGenericPassword("token", token, {
        service: TOKEN_SERVICE,
        accessible: Keychain.ACCESSIBLE.AFTER_FIRST_UNLOCK,
      });
      // Store issue timestamp alongside the token
      await Keychain.setGenericPassword("ts", String(Date.now()), {
        service: TOKEN_TIMESTAMP_SERVICE,
        accessible: Keychain.ACCESSIBLE.AFTER_FIRST_UNLOCK,
      });
    } else {
      await Keychain.resetGenericPassword({ service: TOKEN_SERVICE });
      await Keychain.resetGenericPassword({ service: TOKEN_TIMESTAMP_SERVICE });
    }
  } catch (e) {
    warn("SecureStorage", "Keychain token write error", e);
  }
}

/**
 * clearAllSecureStorage
 * ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 * Wipes ALL Keychain entries stored by AURALIS.
 * Call this on signout or when a 401 is received.
 * Also resets the in-memory URL cache.
 */
export async function clearAllSecureStorage() {
  _apiUrlCache = null;

  const keys = [TOKEN_SERVICE, TOKEN_TIMESTAMP_SERVICE, API_URL_SERVICE];
  await Promise.allSettled(
    keys.map((service) => Keychain.resetGenericPassword({ service }))
  );
}

// ──────────────────────────────────────────────────────────────────────
// Core api() function
// ──────────────────────────────────────────────────────────────────────

export async function api<T>(
  path: string,
  options: RequestInit = {},
  auth = true,
): Promise<T> {
  const base = await getStoredApiUrl();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (auth) {
    const token = await getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  const res = await fetch(`${base}${path}`, { ...options, headers });
  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    // Auto-signout on 401 Unauthorized
    if (res.status === 401 && _onUnauthorized) {
      _onUnauthorized();
    }

    throw new ApiError(
      (data as { error?: string }).error || res.statusText,
      res.status,
    );
  }

  return data as T;
}
