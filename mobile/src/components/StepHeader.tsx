import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { Ionicons } from "./Ionicons";
import { colors, spacing, radius } from "../theme";

const STEPS = ["You", "People", "Your walk", "Ready"] as const;

type Props = { current: number };

export function StepHeader({ current }: Props) {
  return (
    <View style={styles.container}>
      {/* Background Track Line */}
      <View style={styles.trackLine} />

      {/* Active Progress Line */}
      <View
        style={[
          styles.progressLine,
          { width: `${Math.min(100, (current / (STEPS.length - 1)) * 100)}%` },
        ]}
      />

      <View style={styles.row}>
        {STEPS.map((label, i) => {
          const isCompleted = i < current;
          const isActive = i === current;

          return (
            <View key={label} style={styles.item}>
              <View
                style={[
                  styles.circle,
                  isCompleted && styles.circleCompleted,
                  isActive && styles.circleActive,
                ]}
              >
                {isCompleted ? (
                  <Ionicons name="checkmark" size={14} color="#FFF" />
                ) : (
                  <Text
                    style={[
                      styles.stepNumber,
                      isActive && styles.stepNumberActive,
                    ]}
                  >
                    {i + 1}
                  </Text>
                )}
              </View>
              <Text
                style={[
                  styles.label,
                  (isCompleted || isActive) && styles.labelActive,
                ]}
                numberOfLines={1}
              >
                {label}
              </Text>
            </View>
          );
        })}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    position: "relative",
    marginBottom: spacing.lg,
    paddingTop: spacing.xs,
  },
  trackLine: {
    position: "absolute",
    top: 19, // 5 (padding) + 14 (half of circle height 28)
    left: "12%",
    right: "12%",
    height: 3,
    backgroundColor: colors.border,
    borderRadius: radius.full,
  },
  progressLine: {
    position: "absolute",
    top: 19,
    left: "12%",
    height: 3,
    backgroundColor: colors.rose,
    borderRadius: radius.full,
  },
  row: {
    flexDirection: "row",
    justifyContent: "space-between",
    gap: 4,
  },
  item: {
    flex: 1,
    alignItems: "center",
    backgroundColor: "transparent",
  },
  circle: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: colors.bgDeep,
    borderWidth: 2,
    borderColor: colors.border,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 6,
    zIndex: 1,
  },
  circleCompleted: {
    backgroundColor: colors.rose,
    borderColor: colors.rose,
  },
  circleActive: {
    backgroundColor: colors.bg,
    borderColor: colors.rose,
    shadowColor: colors.rose,
    shadowOpacity: 0.4,
    shadowRadius: 6,
    elevation: 3,
  },
  stepNumber: {
    fontSize: 12,
    fontWeight: "800",
    color: colors.textMuted,
  },
  stepNumberActive: {
    color: colors.rose,
  },
  label: {
    fontSize: 11,
    color: colors.textMuted,
    fontWeight: "700",
    marginTop: 2,
  },
  labelActive: {
    color: colors.text,
  },
});
