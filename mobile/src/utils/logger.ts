/**
 * logger.ts
 * ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 * Production-safe logger that emits output ONLY in debug builds.
 *
 * Why not just remove console calls?
 *   In production, console.warn() still executes — it just sends output
 *   to the Android logcat buffer which is accessible via `adb logcat`.
 *   An attacker with USB access can read GPS coordinates, motion data,
 *   and auth info from logcat even without rooting the device.
 *
 * This module provides a zero-overhead alternative:
 *   • In __DEV__  → calls console.log/warn/error normally
 *   • In release  → all calls are no-ops (tree-shaken by Metro/Hermes)
 *
 * Usage:
 *   import { log, warn, error } from '../utils/logger';
 *   log('useMonitoring', 'GPS update', pos.coords);
 *   warn('client', 'Keychain error', e);
 */

const noop = (..._args: unknown[]) => {};

export const log: (...args: unknown[]) => void = __DEV__
  ? (...args) => console.log("[LOG]", ...args)
  : noop;

export const warn: (...args: unknown[]) => void = __DEV__
  ? (...args) => console.warn("[WARN]", ...args)
  : noop;

export const error: (...args: unknown[]) => void = __DEV__
  ? (...args) => console.error("[ERROR]", ...args)
  : noop;

/** Group-style logger for structured debug output */
export const logGroup = __DEV__
  ? (label: string, data: Record<string, unknown>) => {
      console.group(`[LOG] ${label}`);
      Object.entries(data).forEach(([k, v]) => console.log(` ${k}:`, v));
      console.groupEnd();
    }
  : noop;
