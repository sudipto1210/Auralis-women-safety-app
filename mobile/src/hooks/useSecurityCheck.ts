import { useEffect, useState } from 'react';
import { NativeModules } from 'react-native';

const { SecurityCheck } = NativeModules;

export type SecurityResult = {
  isRooted: boolean;
  isDebugging: boolean;
  isEmulator: boolean;
  signatureValid: boolean;
  isDebugBuild: boolean;
  passed: boolean;
};

type SecurityState =
  | { status: 'checking' }
  | { status: 'passed'; result: SecurityResult }
  | { status: 'failed'; result: SecurityResult }
  | { status: 'unavailable' }; // native module not linked (old RN, test env)

/**
 * useSecurityCheck
 * ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 * Runs the native SecurityCheckModule.checkIntegrity() once on mount.
 *
 * Returns a SecurityState describing the result:
 *   • 'checking'    — check is in progress (show loading)
 *   • 'passed'      — device is clean, app can start normally
 *   • 'failed'      — rooted/tampered/debugged device detected
 *   • 'unavailable' — native module not linked (pass through silently)
 *
 * In __DEV__ mode, failures are still reported but the app will not be
 * hard-blocked (the SecurityBlockScreen shows a dismissible warning).
 */
export function useSecurityCheck(): SecurityState {
  const [state, setState] = useState<SecurityState>({ status: 'checking' });

  useEffect(() => {
    if (!SecurityCheck || typeof SecurityCheck.checkIntegrity !== 'function') {
      // Native module not available (e.g. web/jest environment)
      setState({ status: 'unavailable' });
      return;
    }

    SecurityCheck.checkIntegrity()
      .then((result: SecurityResult) => {
        if (result.passed) {
          setState({ status: 'passed', result });
        } else {
          setState({ status: 'failed', result });
        }
      })
      .catch(() => {
        // If the native check itself throws, fail safe (treat as failed)
        setState({
          status: 'failed',
          result: {
            isRooted: true,
            isDebugging: false,
            isEmulator: false,
            signatureValid: false,
            isDebugBuild: __DEV__,
            passed: false,
          },
        });
      });
  }, []);

  return state;
}
