import React, { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { useNavigation } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { Haptics } from "../components/Haptics";
import { Ionicons } from "../components/Ionicons";
import { Screen } from "../components/Screen";
import { Button } from "../components/Button";
import { Card } from "../components/Card";
import type { RootStackParamList } from "../navigation/RootNavigator";
import { colors, radius, shadow, spacing } from "../theme";
import { api } from "../api/client";
import { useMotionSampler } from "../hooks/useMotionSampler";

type LabelType = "normal_walk" | "grab" | "fall" | "panic_run";

type LabelConfig = {
  id: LabelType;
  emoji: string;
  title: string;
  color: string;
  bgColor: string;
  description: string;
};

const LABELS: LabelConfig[] = [
  {
    id: "normal_walk",
    emoji: "🚶‍♂️",
    title: "Normal Walk",
    color: "#4ade80",
    bgColor: "rgba(74, 222, 128, 0.1)",
    description: "Walk at your normal speed and cadence (Normal).",
  },
  {
    id: "grab",
    emoji: "🤚",
    title: "Grab",
    color: "#f87171",
    bgColor: "rgba(248, 113, 113, 0.1)",
    description: "Simulate a sudden grabbing or pulling action.",
  },
  {
    id: "fall",
    emoji: "⚠️",
    title: "Fall",
    color: "#fb923c",
    bgColor: "rgba(251, 146, 60, 0.1)",
    description: "Simulate a sudden trip, fall, or collapse.",
  },
  {
    id: "panic_run",
    emoji: "🏃‍♀️",
    title: "Panic Run",
    color: "#60a5fa",
    bgColor: "rgba(96, 165, 250, 0.1)",
    description: "Simulate running away quickly in fear or panic.",
  },
];

const TARGET_SAMPLES = 100;

export function DataCollectionScreen() {
  const navigation =
    useNavigation<NativeStackNavigationProp<RootStackParamList>>();
  const { collectFor } = useMotionSampler();

  const [selectedLabel, setSelectedLabel] = useState<LabelType>("normal_walk");
  const [stats, setStats] = useState<Record<LabelType, number>>({
    normal_walk: 0,
    grab: 0,
    fall: 0,
    panic_run: 0,
  });
  const [loadingStats, setLoadingStats] = useState(true);
  const [recording, setRecording] = useState(false);
  const [countdown, setCountdown] = useState(5);
  const [statusMsg, setStatusMsg] = useState("");
  const [statusType, setStatusType] = useState<"success" | "error" | "">("");

  const fetchStats = async () => {
    try {
      const data = await api<Record<string, number>>("/api/collect_data/stats");
      // Map response string keys safely to LabelType
      const updatedStats: Record<LabelType, number> = {
        normal_walk: data.normal_walk || 0,
        grab: data.grab || 0,
        fall: data.fall || 0,
        panic_run: data.panic_run || 0,
      };
      setStats(updatedStats);
    } catch (e) {
      console.warn("Failed to fetch data collection stats:", e);
    } finally {
      setLoadingStats(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  const handleRecord = async () => {
    setRecording(true);
    setStatusMsg("");
    setStatusType("");
    setCountdown(5);
    await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Warning);

    try {
      const window = await collectFor(5000, (pct) => {
        const remaining = Math.ceil(5 - (pct / 100) * 5);
        setCountdown(remaining);
      });

      setStatusMsg("Uploading data to server...");
      const res = await api<{
        status: string;
        message?: string;
        dataset_counts?: Record<string, number>;
      }>("/api/collect_data", {
        method: "POST",
        body: JSON.stringify({
          label: selectedLabel,
          sensor_window: window,
        }),
      });

      if (res.status === "success") {
        await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
        setStatusType("success");
        setStatusMsg(`Successfully uploaded! Count: ${res.dataset_counts?.[selectedLabel] || 0}`);
        if (res.dataset_counts) {
          const updatedStats: Record<LabelType, number> = {
            normal_walk: res.dataset_counts.normal_walk || 0,
            grab: res.dataset_counts.grab || 0,
            fall: res.dataset_counts.fall || 0,
            panic_run: res.dataset_counts.panic_run || 0,
          };
          setStats(updatedStats);
        }
      } else {
        throw new Error(res.message || "Unknown server error");
      }
    } catch (e: any) {
      await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
      setStatusType("error");
      setStatusMsg(e.message || "Failed to record or upload telemetry.");
    } finally {
      setRecording(false);
    }
  };

  return (
    <Screen scroll>
      <View style={styles.header}>
        <Pressable style={styles.back} onPress={() => navigation.goBack()}>
          <Ionicons name="chevron-back" size={24} color={colors.text} />
        </Pressable>
        <Text style={styles.title}>ML Telemetry</Text>
        <Pressable style={styles.back} onPress={fetchStats}>
          <Ionicons name="refresh" size={21} color={colors.textSoft} />
        </Pressable>
      </View>

      <Text style={styles.description}>
        Select a motion pattern to record. Perform the action continuously for
        the 5-second duration of the recording. We aim for 100 samples per class.
      </Text>

      {loadingStats ? (
        <View style={styles.loadingContainer}>
          <ActivityIndicator color={colors.rose} />
          <Text style={styles.loadingText}>Fetching server statistics...</Text>
        </View>
      ) : (
        <ScrollView style={styles.cardsContainer} scrollEnabled={false}>
          {LABELS.map((item) => {
            const count = stats[item.id] || 0;
            const progress = Math.min(100, (count / TARGET_SAMPLES) * 100);
            const isSelected = selectedLabel === item.id;

            return (
              <Pressable
                key={item.id}
                onPress={() => {
                  Haptics.selectionAsync();
                  setSelectedLabel(item.id);
                }}
              >
                <View
                  style={[
                    styles.card,
                    isSelected && { borderColor: item.color },
                    isSelected && styles.cardSelected,
                  ]}
                >
                  <View style={styles.cardHeader}>
                    <View
                      style={[styles.emojiWrap, { backgroundColor: item.bgColor }]}
                    >
                      <Text style={styles.emoji}>{item.emoji}</Text>
                    </View>
                    <View style={styles.cardInfo}>
                      <Text style={styles.cardTitle}>{item.title}</Text>
                      <Text style={styles.cardCount}>
                        {count} / {TARGET_SAMPLES} samples
                      </Text>
                    </View>
                  </View>
                  <Text style={styles.cardDescription}>{item.description}</Text>

                  <View style={styles.progressTrack}>
                    <View
                      style={[
                        styles.progressFill,
                        {
                          backgroundColor: item.color,
                          width: `${progress}%`,
                        },
                      ]}
                    />
                  </View>
                </View>
              </Pressable>
            );
          })}
        </ScrollView>
      )}

      {statusMsg ? (
        <View
          style={[
            styles.statusBox,
            statusType === "success" ? styles.statusSuccess : styles.statusError,
          ]}
        >
          <Ionicons
            name={
              statusType === "success"
                ? "checkmark-circle-outline"
                : "alert-circle-outline"
            }
            size={18}
            color={statusType === "success" ? colors.success : colors.danger}
          />
          <Text style={styles.statusText}>{statusMsg}</Text>
        </View>
      ) : null}

      {recording ? (
        <View style={styles.recordingOverlay}>
          <View style={styles.recordingContent}>
            <Text style={styles.recordingTitle}>Recording in progress</Text>
            <Text style={styles.recordingCountdown}>{countdown}s</Text>
            <ActivityIndicator size="large" color={colors.rose} style={{ marginTop: 20 }} />
            <Text style={styles.recordingSubtitle}>
              Perform "{LABELS.find((l) => l.id === selectedLabel)?.title}" action now
            </Text>
          </View>
        </View>
      ) : (
        <Button
          label="Start Recording"
          onPress={handleRecord}
          disabled={loadingStats}
          style={styles.recordButton}
        />
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: spacing.lg,
  },
  back: {
    width: 42,
    height: 42,
    borderRadius: 21,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.border,
  },
  title: { fontSize: 24, fontWeight: "800", color: colors.text },
  description: {
    fontSize: 14,
    color: colors.textSoft,
    lineHeight: 21,
    marginBottom: spacing.md,
  },
  loadingContainer: {
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: spacing.xl,
    gap: spacing.sm,
  },
  loadingText: { color: colors.textSoft, fontSize: 14 },
  cardsContainer: { gap: spacing.md, marginBottom: spacing.lg },
  card: {
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.lg,
    padding: spacing.md,
    marginBottom: spacing.md,
    ...shadow.card,
  },
  cardSelected: {
    backgroundColor: "rgba(255, 255, 255, 0.02)",
    ...shadow.card,
  },
  cardHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    marginBottom: spacing.sm,
  },
  emojiWrap: {
    width: 44,
    height: 44,
    borderRadius: 14,
    alignItems: "center",
    justifyContent: "center",
  },
  emoji: { fontSize: 22 },
  cardInfo: { flex: 1 },
  cardTitle: { color: colors.text, fontSize: 16, fontWeight: "800" },
  cardCount: { color: colors.textSoft, fontSize: 12, marginTop: 2 },
  cardDescription: {
    color: colors.textMuted,
    fontSize: 13,
    lineHeight: 18,
    marginBottom: spacing.md,
  },
  progressTrack: {
    height: 6,
    backgroundColor: colors.bgDeep,
    borderRadius: radius.full,
    overflow: "hidden",
  },
  progressFill: { height: "100%", borderRadius: radius.full },
  statusBox: {
    flexDirection: "row",
    gap: 8,
    alignItems: "center",
    borderRadius: radius.md,
    padding: spacing.sm,
    marginBottom: spacing.lg,
  },
  statusSuccess: {
    backgroundColor: colors.successSoft,
  },
  statusError: {
    backgroundColor: colors.dangerSoft,
  },
  statusText: { color: colors.text, flex: 1, fontSize: 13, lineHeight: 18 },
  recordButton: { marginVertical: spacing.lg },
  recordingOverlay: {
    position: "absolute",
    top: -spacing.xl * 2,
    bottom: -spacing.xl * 2,
    left: -spacing.xl,
    right: -spacing.xl,
    backgroundColor: "rgba(13, 10, 14, 0.95)",
    zIndex: 9999,
    alignItems: "center",
    justifyContent: "center",
  },
  recordingContent: {
    alignItems: "center",
    paddingHorizontal: spacing.xl,
  },
  recordingTitle: {
    color: colors.text,
    fontSize: 20,
    fontWeight: "800",
    textTransform: "uppercase",
    letterSpacing: 1,
    marginBottom: spacing.md,
  },
  recordingCountdown: {
    color: colors.rose,
    fontSize: 64,
    fontWeight: "900",
  },
  recordingSubtitle: {
    color: colors.textSoft,
    fontSize: 15,
    textAlign: "center",
    marginTop: spacing.xl,
  },
});
