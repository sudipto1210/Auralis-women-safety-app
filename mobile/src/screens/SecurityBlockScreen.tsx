import React from 'react';
import {
  StyleSheet,
  Text,
  View,
  ScrollView,
} from 'react-native';
import { colors, radius, spacing } from '../theme';
import type { SecurityResult } from '../hooks/useSecurityCheck';

type Props = {
  result: SecurityResult;
};

/**
 * SecurityBlockScreen
 * ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 * Shown when the integrity check fails in production (rooted device,
 * attached debugger, or invalid APK signature).
 *
 * In __DEV__ mode this screen is still rendered but includes extra
 * debug detail so developers can diagnose what triggered it.
 *
 * The screen is intentionally non-dismissible — the user cannot
 * bypass it by pressing back or navigating away. The only recovery
 * is to run the app on a clean device.
 */
export function SecurityBlockScreen({ result }: Props) {
  const reasons: string[] = [];
  if (result.isRooted) reasons.push('Root access detected on this device');
  if (result.isDebugging) reasons.push('Debugger is attached');
  if (result.isEmulator && !result.isDebugBuild) reasons.push('Emulator environment detected');
  if (!result.signatureValid) reasons.push('APK signature verification failed');

  return (
    <View style={styles.container}>
      <ScrollView contentContainerStyle={styles.content} bounces={false}>
        {/* Shield icon placeholder — uses text glyph for zero dependency */}
        <View style={styles.iconWrap}>
          <Text style={styles.iconText}>🛡️</Text>
        </View>

        <Text style={styles.title}>Device Security Check Failed</Text>

        <Text style={styles.body}>
          AURALIS is a safety-critical application. For your protection,
          it cannot run on devices with detected security risks.
        </Text>

        {reasons.length > 0 && (
          <View style={styles.reasonsBox}>
            <Text style={styles.reasonsTitle}>Detected Issues</Text>
            {reasons.map((reason, i) => (
              <View key={i} style={styles.reasonRow}>
                <Text style={styles.bullet}>•</Text>
                <Text style={styles.reasonText}>{reason}</Text>
              </View>
            ))}
          </View>
        )}

        <View style={styles.adviceBox}>
          <Text style={styles.adviceTitle}>What can I do?</Text>
          <Text style={styles.adviceText}>
            Use a non-rooted Android device with the official AURALIS app
            installed from a trusted source. If you believe this is an error,
            please contact support.
          </Text>
        </View>

        {__DEV__ && (
          <View style={styles.debugBox}>
            <Text style={styles.debugTitle}>DEV — Raw Security Result</Text>
            <Text style={styles.debugText}>{JSON.stringify(result, null, 2)}</Text>
          </View>
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0d0a0e',
  },
  content: {
    flexGrow: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.xl,
  },
  iconWrap: {
    width: 96,
    height: 96,
    borderRadius: 28,
    backgroundColor: 'rgba(220, 38, 38, 0.12)',
    borderWidth: 1,
    borderColor: 'rgba(220, 38, 38, 0.3)',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.lg,
  },
  iconText: {
    fontSize: 42,
  },
  title: {
    fontSize: 22,
    fontWeight: '900',
    color: '#fff',
    textAlign: 'center',
    marginBottom: spacing.md,
  },
  body: {
    fontSize: 15,
    color: 'rgba(255,255,255,0.65)',
    textAlign: 'center',
    lineHeight: 23,
    marginBottom: spacing.lg,
  },
  reasonsBox: {
    width: '100%',
    backgroundColor: 'rgba(220, 38, 38, 0.08)',
    borderWidth: 1,
    borderColor: 'rgba(220, 38, 38, 0.25)',
    borderRadius: radius.lg,
    padding: spacing.md,
    marginBottom: spacing.lg,
  },
  reasonsTitle: {
    fontSize: 13,
    fontWeight: '700',
    color: 'rgba(220, 38, 38, 0.9)',
    marginBottom: spacing.sm,
    textTransform: 'uppercase',
    letterSpacing: 0.8,
  },
  reasonRow: {
    flexDirection: 'row',
    gap: 8,
    marginBottom: 6,
  },
  bullet: {
    color: 'rgba(220, 38, 38, 0.7)',
    fontSize: 15,
    lineHeight: 22,
  },
  reasonText: {
    flex: 1,
    color: 'rgba(255,255,255,0.75)',
    fontSize: 14,
    lineHeight: 22,
  },
  adviceBox: {
    width: '100%',
    backgroundColor: 'rgba(255,255,255,0.04)',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.08)',
    borderRadius: radius.lg,
    padding: spacing.md,
  },
  adviceTitle: {
    fontSize: 13,
    fontWeight: '700',
    color: 'rgba(255,255,255,0.5)',
    marginBottom: spacing.sm,
    textTransform: 'uppercase',
    letterSpacing: 0.8,
  },
  adviceText: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.55)',
    lineHeight: 22,
  },
  debugBox: {
    width: '100%',
    marginTop: spacing.lg,
    backgroundColor: 'rgba(251, 191, 36, 0.06)',
    borderWidth: 1,
    borderColor: 'rgba(251, 191, 36, 0.2)',
    borderRadius: radius.md,
    padding: spacing.md,
  },
  debugTitle: {
    fontSize: 11,
    fontWeight: '700',
    color: 'rgba(251, 191, 36, 0.8)',
    marginBottom: spacing.xs,
    textTransform: 'uppercase',
    letterSpacing: 0.8,
  },
  debugText: {
    fontFamily: 'monospace',
    fontSize: 11,
    color: 'rgba(251, 191, 36, 0.6)',
    lineHeight: 18,
  },
});
