import React, { useEffect, useState } from "react";
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { LinearGradient } from "react-native-linear-gradient";
import {
  GoogleSignin,
  statusCodes,
} from "@react-native-google-signin/google-signin";
import ReactNativeHapticFeedback from "react-native-haptic-feedback";
import { Ionicons } from "../components/Ionicons"; // We'll create/update this to use react-native-vector-icons
import { Screen } from "../components/Screen";
import { Button } from "../components/Button";
import { colors, spacing, radius, shadow } from "../theme";
import { getGoogleClientIds } from "../config";
import { useAuth } from "../store/AuthContext";
import { getStoredApiUrl, setStoredApiUrl } from "../api/client";

export function LoginScreen() {
  const { signInWithGoogle } = useAuth();
  const [apiUrl, setApiUrl] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const googleClientIds = getGoogleClientIds();
  const clientId = googleClientIds.clientId || googleClientIds.androidClientId;

  useEffect(() => {
    getStoredApiUrl().then(setApiUrl);
  }, []);

  useEffect(() => {
    if (clientId) {
      GoogleSignin.configure({
        webClientId: googleClientIds.webClientId,
        offlineAccess: false,
      });
    }
  }, [clientId, googleClientIds.webClientId]);

  const signIn = async () => {
    setError("");
    setLoading(true);
    ReactNativeHapticFeedback.trigger("impactLight");
    try {
      await GoogleSignin.hasPlayServices();
      const userInfo = await GoogleSignin.signIn();
      const idToken =
        (userInfo as any).data?.idToken || (userInfo as any).idToken;
      if (!idToken) {
        throw new Error("Google Sign-In did not return an ID token.");
      }
      await signInWithGoogle(idToken);
    } catch (e: any) {
      if (e.code === statusCodes.SIGN_IN_CANCELLED) {
        setError("Sign-in cancelled.");
      } else if (e.code === statusCodes.IN_PROGRESS) {
        setError("Sign-in already in progress.");
      } else if (e.code === statusCodes.PLAY_SERVICES_NOT_AVAILABLE) {
        setError("Play Services not available.");
      } else {
        setError(e.message || "Google Sign-In failed.");
      }
    } finally {
      setLoading(false);
    }
  };

  const saveServer = async () => {
    if (apiUrl.trim()) await setStoredApiUrl(apiUrl.trim());
  };

  return (
    <Screen scroll>
      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        style={styles.flex}
      >
        <LinearGradient
          colors={["#312132", "#171018", colors.bg]}
          style={styles.hero}
        >
          <View style={styles.heroTop}>
            <View style={styles.iconWrap}>
              <Ionicons name="shield-checkmark" size={30} color={colors.text} />
            </View>
            <View style={styles.statusPill}>
              <View style={styles.statusDot} />
              <Text style={styles.statusText}>Private by design</Text>
            </View>
          </View>
          <Text style={styles.title}>AURALIS</Text>
          <Text style={styles.tagline}>
            A calm safety command center for walks, commutes, and late returns.
          </Text>
          <View style={styles.signalRow}>
            <View style={styles.signalItem}>
              <Ionicons name="walk-outline" size={18} color={colors.rose} />
              <Text style={styles.signalText}>Motion aware</Text>
            </View>
            <View style={styles.signalItem}>
              <Ionicons name="mic-outline" size={18} color={colors.success} />
              <Text style={styles.signalText}>Distress cues</Text>
            </View>
          </View>
        </LinearGradient>

        <View style={styles.panel}>
          <Text style={styles.sectionLabel}>Server URL</Text>
          <TextInput
            style={styles.input}
            value={apiUrl}
            onChangeText={(value) => {
              setApiUrl(value);
              if (error) setError("");
            }}
            onBlur={saveServer}
            placeholder="http://10.0.2.2:5001"
            placeholderTextColor={colors.textFaint}
            autoCapitalize="none"
            autoCorrect={false}
          />
          <Text style={styles.hint}>
            Use your laptop LAN address on a physical phone.
          </Text>

          {error ? (
            <View style={styles.errorBox}>
              <Ionicons
                name="alert-circle-outline"
                size={18}
                color={colors.danger}
              />
              <Text style={styles.error}>{error}</Text>
            </View>
          ) : null}

          {loading ? (
            <View style={styles.loadingRow}>
              <ActivityIndicator color={colors.rose} />
              <Text style={styles.loadingText}>
                Confirming your secure session...
              </Text>
            </View>
          ) : null}

          {clientId ? (
            <Button
              label="Continue with Google"
              onPress={async () => {
                await saveServer();
                signIn();
              }}
              loading={loading}
              style={styles.googleButton}
            />
          ) : (
            <View style={styles.warnBox}>
              <Ionicons name="key-outline" size={20} color={colors.warning} />
              <View style={styles.warnCopy}>
                <Text style={styles.warnTitle}>
                  Google Sign-In not configured
                </Text>
                <Text style={styles.warnText}>
                  Set EXPO_PUBLIC_GOOGLE_CLIENT_ID in mobile/.env or app.json
                  extra.googleClientId.
                </Text>
              </View>
            </View>
          )}
        </View>
      </KeyboardAvoidingView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1, justifyContent: "center" },
  hero: {
    borderRadius: radius.xl,
    padding: spacing.xl,
    marginBottom: spacing.lg,
    minHeight: 330,
    justifyContent: "space-between",
    overflow: "hidden",
    ...shadow.card,
  },
  heroTop: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  iconWrap: {
    width: 58,
    height: 58,
    borderRadius: 18,
    backgroundColor: colors.roseSoft,
    borderWidth: 1,
    borderColor: colors.roseBorder,
    alignItems: "center",
    justifyContent: "center",
  },
  statusPill: {
    flexDirection: "row",
    alignItems: "center",
    gap: 7,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.full,
    paddingHorizontal: 10,
    paddingVertical: 7,
    backgroundColor: "rgba(255,255,255,0.04)",
  },
  statusDot: {
    width: 7,
    height: 7,
    borderRadius: 4,
    backgroundColor: colors.success,
  },
  statusText: { color: colors.textSoft, fontSize: 12, fontWeight: "700" },
  title: { fontSize: 38, fontWeight: "900", color: colors.text },
  tagline: {
    fontSize: 17,
    color: colors.textSoft,
    lineHeight: 25,
    marginTop: spacing.sm,
  },
  signalRow: { flexDirection: "row", gap: spacing.sm, marginTop: spacing.lg },
  signalItem: {
    flex: 1,
    minHeight: 48,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: "rgba(255,255,255,0.04)",
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
  },
  signalText: { color: colors.textSoft, fontSize: 12, fontWeight: "700" },
  panel: {
    backgroundColor: colors.card,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.md,
    ...shadow.card,
  },
  sectionLabel: {
    fontSize: 13,
    fontWeight: "700",
    color: colors.textSoft,
    marginBottom: spacing.xs,
  },
  input: {
    backgroundColor: colors.bg,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    padding: 14,
    fontSize: 15,
    color: colors.text,
  },
  hint: { fontSize: 12, color: colors.textMuted, marginTop: spacing.xs },
  errorBox: {
    flexDirection: "row",
    gap: 8,
    alignItems: "center",
    backgroundColor: colors.dangerSoft,
    borderRadius: radius.md,
    padding: spacing.sm,
    marginTop: spacing.md,
  },
  error: { color: colors.text, flex: 1, fontSize: 13, lineHeight: 18 },
  loadingRow: {
    flexDirection: "row",
    gap: 10,
    alignItems: "center",
    marginTop: spacing.md,
  },
  loadingText: { color: colors.textSoft, fontSize: 13 },
  googleButton: { marginTop: spacing.lg },
  warnBox: {
    flexDirection: "row",
    gap: spacing.sm,
    backgroundColor: colors.warningSoft,
    padding: spacing.md,
    borderRadius: radius.md,
    marginTop: spacing.lg,
  },
  warnCopy: { flex: 1 },
  warnTitle: { fontWeight: "700", color: colors.text, marginBottom: 6 },
  warnText: { fontSize: 13, color: colors.textSoft, lineHeight: 20 },
});
