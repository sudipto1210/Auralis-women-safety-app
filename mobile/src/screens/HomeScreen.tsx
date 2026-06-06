import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  Alert,
  Animated,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { useNavigation } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { Haptics } from "../components/Haptics";
import { Ionicons } from "../components/Ionicons";
import type { RootStackParamList } from "../navigation/RootNavigator";
import { Screen } from "../components/Screen";
import { Button } from "../components/Button";
import { Card } from "../components/Card";
import { colors, spacing, radius, shadow } from "../theme";
import { api } from "../api/client";
import { useAuth } from "../store/AuthContext";
import { useMonitoring, useThreatStatus } from "../hooks/useMonitoring";

const THREAT_COLORS: Record<string, string> = {
  SAFE: colors.success,
  LOW: colors.success,
  MEDIUM: colors.warning,
  HIGH: colors.danger,
  CRITICAL: colors.dangerDark,
};

const THREAT_COPY: Record<string, string> = {
  SAFE: "No elevated threat signals detected.",
  LOW: "Signals look steady. Monitoring stays ready in the background.",
  MEDIUM: "AURALIS is watching a few unusual cues. Stay aware.",
  HIGH: "Risk is elevated. Move toward light, people, or a known safe place.",
  CRITICAL:
    "Critical threat pattern detected. Use SOS if you need immediate help.",
};

const formatDuration = (seconds: number) => {
  const mins = Math.floor(seconds / 60)
    .toString()
    .padStart(2, "0");
  const secs = (seconds % 60).toString().padStart(2, "0");
  return `${mins}:${secs}`;
};

export function HomeScreen() {
  const navigation =
    useNavigation<NativeStackNavigationProp<RootStackParamList>>();
  const { user } = useAuth();
  const threat = useThreatStatus();
  const [monitoring, setMonitoring] = useState(false);
  const [sosBusy, setSosBusy] = useState(false);
  const [duration, setDuration] = useState(0);
  const riskAnim = useRef(new Animated.Value(0)).current;
  const sosPulse = useRef(new Animated.Value(1)).current;
  const threatPulse = useRef(new Animated.Value(1)).current;

  useMonitoring(monitoring);

  useEffect(() => {
    if (threat && threat.monitoring_active !== monitoring) {
      setMonitoring(threat.monitoring_active);
    }
  }, [monitoring, threat]);

  useEffect(() => {
    if (!monitoring) {
      setDuration(0);
      return undefined;
    }
    const id = setInterval(() => setDuration((value) => value + 1), 1000);
    return () => clearInterval(id);
  }, [monitoring]);

  const level = (threat?.state || "SAFE").toUpperCase();
  const levelColor = THREAT_COLORS[level] || colors.success;
  const riskScore = Math.max(0, Math.min(1, threat?.score ?? 0));

  useEffect(() => {
    Animated.timing(riskAnim, {
      toValue: riskScore,
      duration: 450,
      useNativeDriver: false,
    }).start();
  }, [riskAnim, riskScore]);

  useEffect(() => {
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(sosPulse, {
          toValue: 1.08,
          duration: 1100,
          useNativeDriver: true,
        }),
        Animated.timing(sosPulse, {
          toValue: 1,
          duration: 1100,
          useNativeDriver: true,
        }),
      ]),
    );
    loop.start();
    return () => loop.stop();
  }, [sosPulse]);

  useEffect(() => {
    const urgent = level === "HIGH" || level === "CRITICAL";
    if (!urgent) {
      threatPulse.setValue(1);
      return undefined;
    }
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(threatPulse, {
          toValue: 1.02,
          duration: 700,
          useNativeDriver: true,
        }),
        Animated.timing(threatPulse, {
          toValue: 1,
          duration: 700,
          useNativeDriver: true,
        }),
      ]),
    );
    loop.start();
    return () => loop.stop();
  }, [level, threatPulse]);

  const sensors = useMemo(
    () => [
      { label: "Sensors", icon: "pulse-outline" as const, active: monitoring },
      { label: "GPS", icon: "location-outline" as const, active: monitoring },
      { label: "Mic", icon: "mic-outline" as const, active: monitoring },
    ],
    [monitoring],
  );

  const triggerSos = async () => {
    setSosBusy(true);
    await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Warning);
    try {
      await api("/api/trigger_sos", {
        method: "POST",
        body: JSON.stringify({}),
      });
      await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
    } catch (e) {
      console.warn(e);
    } finally {
      setSosBusy(false);
    }
  };

  const confirmSos = async () => {
    await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Warning);
    Alert.alert(
      "Send emergency SOS?",
      "AURALIS will alert your emergency contacts using your latest safety context.",
      [
        { text: "Cancel", style: "cancel" },
        { text: "Send SOS", style: "destructive", onPress: triggerSos },
      ],
    );
  };

  const toggleMonitoring = async () => {
    await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    setMonitoring((active) => !active);
  };

  return (
    <Screen scroll>
      <View style={styles.topRow}>
        <View>
          <Text style={styles.hello}>
            Hello, {user?.name?.split(" ")[0] || "friend"}
          </Text>
          <Text style={styles.subtitle}>
            Your protection is active on this device
          </Text>
        </View>
        <Pressable onPress={() => navigation.navigate("Settings")} hitSlop={12}>
          <View style={styles.settingsButton}>
            <Ionicons
              name="settings-outline"
              size={22}
              color={colors.textSoft}
            />
          </View>
        </Pressable>
      </View>

      <Animated.View
        style={[styles.threatCard, { transform: [{ scale: threatPulse }] }]}
      >
        <View style={styles.threatTop}>
          <View>
            <Text style={styles.cardKicker}>Threat level</Text>
            <Text style={styles.summary}>
              {threat?.summary || THREAT_COPY[level] || THREAT_COPY.SAFE}
            </Text>
          </View>
          <View style={[styles.threatBadge, { backgroundColor: levelColor }]}>
            <Text style={styles.threatLabel}>{level}</Text>
          </View>
        </View>
        <View style={styles.riskHeader}>
          <Text style={styles.riskLabel}>Risk score</Text>
          <Text style={styles.riskValue}>
            {threat ? `${Math.round(riskScore * 100)}%` : "Waiting"}
          </Text>
        </View>
        <View style={styles.riskTrack}>
          <Animated.View
            style={[
              styles.riskFill,
              {
                backgroundColor: levelColor,
                width: riskAnim.interpolate({
                  inputRange: [0, 1],
                  outputRange: ["0%", "100%"],
                }),
              },
            ]}
          />
        </View>
      </Animated.View>

      <Animated.View style={{ transform: [{ scale: sosPulse }] }}>
        <Pressable
          style={({ pressed }) => [styles.sos, pressed && styles.sosPressed]}
          onPress={confirmSos}
          disabled={sosBusy}
        >
          <View style={styles.sosRipple} />
          <Text style={styles.sosText}>{sosBusy ? "SENDING" : "SOS"}</Text>
          <Text style={styles.sosHint}>Confirm before alerting contacts</Text>
        </Pressable>
      </Animated.View>

      <Card title="Live monitoring">
        <View style={styles.monitorTop}>
          <View>
            <Text style={styles.monitorStatus}>
              {monitoring ? "Active protection" : "Monitoring paused"}
            </Text>
            <Text style={styles.monitorTime}>{formatDuration(duration)}</Text>
          </View>
          <Button
            label={monitoring ? "Stop" : "Start"}
            variant={monitoring ? "secondary" : "primary"}
            onPress={toggleMonitoring}
            style={styles.monitorButton}
          />
        </View>
        <View style={styles.sensorRow}>
          {sensors.map((sensor) => (
            <View key={sensor.label} style={styles.sensorItem}>
              <View
                style={[styles.sensorDot, sensor.active && styles.sensorDotOn]}
              >
                <Ionicons
                  name={sensor.icon}
                  size={18}
                  color={sensor.active ? colors.success : colors.textMuted}
                />
              </View>
              <Text style={styles.sensorLabel}>{sensor.label}</Text>
            </View>
          ))}
        </View>
      </Card>

      <View style={styles.quickGrid}>
        <Pressable
          style={styles.quickAction}
          onPress={() => navigation.navigate("SafePlaces")}
        >
          <Ionicons name="map-outline" size={24} color={colors.success} />
          <Text style={styles.quickTitle}>Safe Places</Text>
        </Pressable>
        <Pressable
          style={styles.quickAction}
          onPress={() => navigation.navigate("Chatbot")}
        >
          <Ionicons name="chatbubbles-outline" size={24} color={colors.rose} />
          <Text style={styles.quickTitle}>Chatbot</Text>
        </Pressable>
        <Pressable
          style={styles.quickAction}
          onPress={() => navigation.navigate("IncidentHistory")}
        >
          <Ionicons name="time-outline" size={24} color={colors.warning} />
          <Text style={styles.quickTitle}>History</Text>
        </Pressable>
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  topRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
    marginBottom: spacing.lg,
  },
  hello: { fontSize: 26, fontWeight: "800", color: colors.text },
  subtitle: { fontSize: 14, color: colors.textSoft, marginTop: 4 },
  settingsButton: {
    width: 44,
    height: 44,
    borderRadius: 22,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.border,
  },
  threatCard: {
    backgroundColor: colors.card,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.md,
    marginBottom: spacing.md,
    ...shadow.card,
  },
  threatTop: {
    flexDirection: "row",
    gap: spacing.md,
    justifyContent: "space-between",
    alignItems: "flex-start",
  },
  cardKicker: {
    color: colors.textMuted,
    fontSize: 12,
    fontWeight: "800",
    textTransform: "uppercase",
    marginBottom: 8,
  },
  threatBadge: {
    borderRadius: radius.full,
    paddingHorizontal: 12,
    paddingVertical: 8,
    minWidth: 82,
    alignItems: "center",
  },
  threatLabel: { color: "#fff", fontSize: 12, fontWeight: "900" },
  summary: {
    fontSize: 15,
    color: colors.textSoft,
    lineHeight: 21,
    maxWidth: 220,
  },
  riskHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginTop: spacing.lg,
    marginBottom: spacing.xs,
  },
  riskLabel: { color: colors.textMuted, fontSize: 12, fontWeight: "700" },
  riskValue: { color: colors.text, fontSize: 12, fontWeight: "900" },
  riskTrack: {
    height: 10,
    backgroundColor: colors.bgDeep,
    borderRadius: radius.full,
    overflow: "hidden",
  },
  riskFill: { height: "100%", borderRadius: radius.full },
  sos: {
    backgroundColor: colors.danger,
    borderRadius: radius.xl,
    paddingVertical: spacing.xl,
    alignItems: "center",
    marginBottom: spacing.lg,
    overflow: "hidden",
    shadowColor: colors.danger,
    shadowOpacity: 0.35,
    shadowRadius: 16,
    shadowOffset: { width: 0, height: 8 },
    elevation: 6,
  },
  sosPressed: { opacity: 0.92, transform: [{ scale: 0.98 }] },
  sosRipple: {
    position: "absolute",
    width: 190,
    height: 190,
    borderRadius: 95,
    backgroundColor: "rgba(255,255,255,0.12)",
    top: -44,
  },
  sosText: { color: "#fff", fontSize: 38, fontWeight: "900" },
  sosHint: { color: "rgba(255,255,255,0.85)", fontSize: 12, marginTop: 6 },
  monitorTop: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: spacing.md,
  },
  monitorStatus: { color: colors.text, fontSize: 16, fontWeight: "800" },
  monitorTime: {
    color: colors.textSoft,
    fontSize: 28,
    fontWeight: "900",
    marginTop: 4,
    fontVariant: ["tabular-nums"],
  },
  monitorButton: { width: 96, minHeight: 44 },
  sensorRow: { flexDirection: "row", gap: spacing.sm, marginTop: spacing.md },
  sensorItem: { flex: 1, alignItems: "center", gap: 8 },
  sensorDot: {
    width: 46,
    height: 46,
    borderRadius: 23,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.bg,
    borderWidth: 1,
    borderColor: colors.border,
  },
  sensorDotOn: {
    backgroundColor: colors.successSoft,
    borderColor: colors.success,
  },
  sensorLabel: { color: colors.textMuted, fontSize: 12, fontWeight: "700" },
  quickGrid: {
    flexDirection: "row",
    gap: spacing.sm,
    marginBottom: spacing.md,
  },
  quickAction: {
    flex: 1,
    minHeight: 98,
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.lg,
    alignItems: "center",
    justifyContent: "center",
    gap: 10,
  },
  quickTitle: {
    color: colors.text,
    fontSize: 12,
    fontWeight: "800",
    textAlign: "center",
  },
});
