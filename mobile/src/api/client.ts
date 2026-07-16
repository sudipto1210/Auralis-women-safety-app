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
  return getApiUrl();
}

export async function setStoredApiUrl(url: string) {
  // Locked to built-in EXPO_PUBLIC_API_URL
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

/**
 * clearAuthTokens
 * ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 * Wipes only the JWT access token and its timestamp from the Keychain.
 * This is used for logout and token-expired signouts, preserving
 * the custom API server URL so the user doesn't have to re-enter it.
 */
export async function clearAuthTokens() {
  const keys = [TOKEN_SERVICE, TOKEN_TIMESTAMP_SERVICE];
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
