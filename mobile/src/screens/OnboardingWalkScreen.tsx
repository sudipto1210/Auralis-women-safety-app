import React, { useEffect, useRef, useState } from "react";
import { Animated, StyleSheet, Text, View } from "react-native";
import { Haptics } from "../components/Haptics";
import { Ionicons } from "../components/Ionicons";
import { Screen } from "../components/Screen";
import { Button } from "../components/Button";
import { StepHeader } from "../components/StepHeader";
import { colors, spacing, radius } from "../theme";
import { api } from "../api/client";
import { useAuth } from "../store/AuthContext";
import { useMotionSampler } from "../hooks/useMotionSampler";
import type { SensorSample } from "../api/types";
import { useNavigation } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import type { RootStackParamList } from "../navigation/RootNavigator";

export function OnboardingWalkScreen() {
  const navigation =
    useNavigation<NativeStackNavigationProp<RootStackParamList>>();
  const { refreshOnboarding } = useAuth();
  const { collectFor } = useMotionSampler();
  const [step, setStep] = useState<1 | 2 | "done">(1);
  const [progress, setProgress] = useState(0);
  const [secondsLeft, setSecondsLeft] = useState(30);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [normalData, setNormalData] = useState<SensorSample[] | null>(null);

  const pulse = useRef(new Animated.Value(1)).current;

  const handleFinish = async () => {
    await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    if (navigation.canGoBack()) {
      navigation.goBack();
    } else {
      navigation.reset({
        index: 0,
        routes: [{ name: "Home" }],
      });
    }
  };
  const phaseFade = useRef(new Animated.Value(1)).current;
  const progressAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(pulse, {
          toValue: 1.12,
          duration: 900,
          useNativeDriver: true,
        }),
        Animated.timing(pulse, {
          toValue: 1,
          duration: 900,
          useNativeDriver: true,
        }),
      ]),
    );
    loop.start();
    return () => loop.stop();
  }, [pulse]);

  useEffect(() => {
    Animated.timing(progressAnim, {
      toValue: progress,
      duration: 260,
      useNativeDriver: false,
    }).start();
  }, [progress, progressAnim]);

  const switchPhase = async () => {
    await new Promise<void>((resolve) => {
      Animated.sequence([
        Animated.timing(phaseFade, {
          toValue: 0,
          duration: 180,
          useNativeDriver: true,
        }),
        Animated.timing(phaseFade, {
          toValue: 1,
          duration: 240,
          useNativeDriver: true,
        }),
      ]).start(() => resolve());
    });
  };

  const runStep = async (which: 1 | 2) => {
    setBusy(true);
    setError("");
    const duration = which === 1 ? 30000 : 15000;
    setSecondsLeft(duration / 1000);
    try {
      const data = await collectFor(duration, (pct) => {
        setProgress(pct);
        setSecondsLeft(Math.ceil(((100 - pct) / 100) * (duration / 1000)));
      });
      if (which === 1) {
        setNormalData(data);
        setStep(2);
        setProgress(0);
        setSecondsLeft(15);
        await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
        await switchPhase();
      } else {
        await api("/api/motion_baseline", {
          method: "POST",
          body: JSON.stringify({
            normal_readings: normalData,
            elevated_readings: data,
          }),
        });
        await api("/api/onboarding/finish", { method: "POST" });
        await Haptics.notificationAsync(
          Haptics.NotificationFeedbackType.Success,
        );
        setStep("done");
        await refreshOnboarding();
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Recording failed");
      await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
    } finally {
      setBusy(false);
      setProgress(0);
    }
  };

  if (step === "done") {
    return (
      <Screen>
        <StepHeader current={3} />
        <View style={styles.doneIcon}>
          <Ionicons name="checkmark-circle" size={56} color={colors.success} />
        </View>
        <Text style={styles.heading}>You're ready</Text>
        <Text style={styles.sub}>
          AURALIS now knows your walk rhythm and your emergency circle.
        </Text>
        <Button
          label="Enter dashboard"
          onPress={handleFinish}
          style={styles.doneButton}
        />
      </Screen>
    );
  }

  return (
    <Screen>
      <StepHeader current={2} />
      <Animated.View style={{ opacity: phaseFade }}>
        <View style={styles.phasePill}>
          <Text style={styles.phasePillText}>
            Phase {step === 1 ? "1 of 2" : "2 of 2"}
          </Text>
        </View>
        <Text style={styles.heading}>
          {step === 1
            ? "Walk at your usual pace"
            : "Walk briskly for a short stretch"}
        </Text>
        <Text style={styles.sub}>
          {step === 1
            ? "30 seconds. Keep the phone where you normally carry it."
            : "15 seconds. A natural, faster pace is enough."}
        </Text>
      </Animated.View>

      <View style={styles.visual}>
        <Animated.View
          style={[
            styles.ring,
            { transform: [{ scale: pulse }], opacity: 0.35 },
          ]}
        />
        <View style={styles.walkIcon}>
          <Ionicons
            name={step === 1 ? "walk-outline" : "fitness-outline"}
            size={48}
            color={colors.text}
          />
        </View>
      </View>

      <View style={styles.barTrack}>
        <Animated.View
          style={[
            styles.barFill,
            {
              width: progressAnim.interpolate({
                inputRange: [0, 100],
                outputRange: ["0%", "100%"],
              }),
            },
          ]}
        />
      </View>
      <Text style={styles.timer}>{secondsLeft}s</Text>
      <Text style={styles.timerHint}>
        {busy ? "Recording movement sample" : "Ready when you are"}
      </Text>

      {error ? <Text style={styles.error}>{error}</Text> : null}

      <Button
        label={
          busy
            ? "Recording…"
            : step === 1
              ? "Start comfortable walk"
              : "Start brisk walk"
        }
        onPress={() => runStep(step)}
        loading={busy}
        disabled={busy}
      />
    </Screen>
  );
}

const styles = StyleSheet.create({
  heading: { fontSize: 24, fontWeight: "800", color: colors.text },
  sub: {
    fontSize: 14,
    color: colors.textSoft,
    marginTop: 8,
    marginBottom: spacing.lg,
    lineHeight: 21,
  },
  phasePill: {
    alignSelf: "flex-start",
    backgroundColor: colors.roseSoft,
    borderColor: colors.roseBorder,
    borderWidth: 1,
    borderRadius: radius.full,
    paddingHorizontal: 12,
    paddingVertical: 7,
    marginBottom: spacing.md,
  },
  phasePillText: { color: colors.text, fontSize: 12, fontWeight: "800" },
  visual: {
    alignItems: "center",
    justifyContent: "center",
    height: 180,
    marginVertical: spacing.lg,
  },
  ring: {
    position: "absolute",
    width: 150,
    height: 150,
    borderRadius: 75,
    borderWidth: 2,
    borderColor: colors.rose,
  },
  walkIcon: {
    width: 108,
    height: 108,
    borderRadius: 54,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.cardElevated,
    borderWidth: 1,
    borderColor: colors.borderStrong,
  },
  barTrack: {
    height: 10,
    backgroundColor: colors.roseSoft,
    borderRadius: radius.full,
    overflow: "hidden",
    marginBottom: spacing.sm,
  },
  barFill: { height: "100%", backgroundColor: colors.rose },
  timer: {
    fontSize: 42,
    fontWeight: "900",
    color: colors.text,
    textAlign: "center",
    fontVariant: ["tabular-nums"],
  },
  timerHint: {
    color: colors.textMuted,
    textAlign: "center",
    marginBottom: spacing.lg,
    fontSize: 13,
  },
  error: {
    color: colors.danger,
    marginBottom: spacing.sm,
    textAlign: "center",
  },
  doneIcon: { alignItems: "center", marginVertical: spacing.xl },
  doneButton: { marginTop: spacing.xl },
});
