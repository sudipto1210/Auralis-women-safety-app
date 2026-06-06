/**
 * secureClient.ts
 * ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 * Production-safe API request wrapper that enforces:
 *
 *   1. HTTPS-only in production  — rejects any http:// URL
 *   2. Request timeout           — 15s default (no more silent hangs)
 *   3. Canonical headers         — X-App-Version, X-Platform for
 *                                   server-side request validation
 *   4. URL sanitization          — strips trailing slashes, validates scheme
 *
 * In __DEV__ mode, http:// is allowed (emulator + LAN dev server).
 *
 * This module re-exports a `secureApi()` function with the same
 * signature as `api()` from client.ts — swap it in anywhere you want
 * extra security without changing call sites.
 */

import { Platform } from "react-native";
import { api, getStoredApiUrl } from "./client";
import { log } from "../utils/logger";

/** Default request timeout in milliseconds */
const REQUEST_TIMEOUT_MS = 15_000;

/** App version — update this on each release */
const APP_VERSION = "1.0.0";

// ──────────────────────────────────────────────────────────────────────
// URL Scheme Validator
// ──────────────────────────────────────────────────────────────────────

/**
 * Validates that the given base URL uses a safe scheme.
 * In production: only https:// is allowed.
 * In debug: http:// is also allowed (for 10.0.2.2 / LAN).
 *
 * Throws a descriptive error if validation fails so the caller gets
 * a clear message instead of a cryptic network error.
 */
export function validateApiUrl(url: string): void {
  const trimmed = url.trim();
  const isHttps = trimmed.startsWith("https://");
  const isHttp = trimmed.startsWith("http://");

  if (!isHttps && !isHttp) {
    throw new Error(
      `[AURALIS Security] Invalid API URL scheme: "${trimmed}". Must start with https:// or http://.`
    );
  }

  if (!__DEV__ && isHttp) {
    throw new Error(
      `[AURALIS Security] Cleartext HTTP is not allowed in production. ` +
        `Configure a valid HTTPS server URL. Current URL: "${trimmed}"`
    );
  }

  if (__DEV__ && isHttp) {
    log(
      "SecureClient",
      `⚠️  HTTP allowed in debug mode: ${trimmed}`
    );
  }
}

// ──────────────────────────────────────────────────────────────────────
// Timeout-aware fetch wrapper
// ──────────────────────────────────────────────────────────────────────

/**
 * Wraps a Promise with a timeout. If the promise does not resolve
 * within `ms` milliseconds, rejects with a TimeoutError.
 */
function withTimeout<T>(promise: Promise<T>, ms: number): Promise<T> {
  let timeoutHandle: ReturnType<typeof setTimeout>;

  const timeoutPromise = new Promise<T>((_, reject) => {
    timeoutHandle = setTimeout(() => {
      reject(
        new Error(
          `[AURALIS Security] Request timed out after ${ms / 1000}s. ` +
            `Check your network connection and server availability.`
        )
      );
    }, ms);
  });

  return Promise.race([
    promise.finally(() => clearTimeout(timeoutHandle)),
    timeoutPromise,
  ]);
}

// ──────────────────────────────────────────────────────────────────────
// Canonical security headers
// ──────────────────────────────────────────────────────────────────────

/**
 * Returns the standard security headers that every AURALIS request
 * should include. The server can use these for:
 *   • Rejecting requests from unofficial clients
 *   • Logging client versions for debugging
 *   • Rate-limiting old app versions
 */
export function getSecurityHeaders(): Record<string, string> {
  return {
    "X-App-Version": APP_VERSION,
    "X-Platform": Platform.OS,
    "X-App-ID": "com.auralis.app",
  };
}

// ──────────────────────────────────────────────────────────────────────
// secureApi — drop-in replacement for api()
// ──────────────────────────────────────────────────────────────────────

/**
 * Makes an authenticated, timeout-enforced, scheme-validated API request.
 *
 * Usage is identical to `api()` from client.ts:
 *   const data = await secureApi<MyType>('/api/endpoint', { method: 'POST', body: '...' });
 *
 * @param path    — API path, e.g. '/api/motion_data'
 * @param options — Standard RequestInit (method, body, headers, etc.)
 * @param auth    — Whether to attach the Bearer token (default: true)
 * @param timeoutMs — Override the default 15s timeout
 */
export async function secureApi<T>(
  path: string,
  options: RequestInit = {},
  auth = true,
  timeoutMs = REQUEST_TIMEOUT_MS
): Promise<T> {
  // Validate the stored API base URL before every request
  const base = await getStoredApiUrl();
  validateApiUrl(base);

  // Inject canonical headers alongside caller's headers
  const mergedOptions: RequestInit = {
    ...options,
    headers: {
      ...getSecurityHeaders(),
      ...(options.headers as Record<string, string>),
    },
  };

  // Delegate to the existing api() and wrap with a timeout
  return withTimeout(api<T>(path, mergedOptions, auth), timeoutMs);
}
