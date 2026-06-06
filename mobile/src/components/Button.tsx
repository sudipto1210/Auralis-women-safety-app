import React from "react";
import {
  ActivityIndicator,
  GestureResponderEvent,
  Pressable,
  StyleSheet,
  Text,
  ViewStyle,
} from "react-native";
import { colors, radius, spacing } from "../theme";

type Props = {
  label: string;
  onPress: (event: GestureResponderEvent) => void;
  variant?: "primary" | "secondary" | "ghost" | "danger";
  disabled?: boolean;
  loading?: boolean;
  style?: ViewStyle;
};

export function Button({
  label,
  onPress,
  variant = "primary",
  disabled,
  loading,
  style,
}: Props) {
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled || loading}
      style={({ pressed }) => [
        styles.base,
        styles[variant],
        pressed && styles.pressed,
        (disabled || loading) && styles.disabled,
        style,
      ]}
    >
      {loading ? (
        <ActivityIndicator color={variant === "ghost" ? colors.rose : "#fff"} />
      ) : (
        <Text style={[styles.label, variant === "ghost" && styles.labelGhost]}>
          {label}
        </Text>
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: {
    minHeight: 52,
    borderRadius: radius.md,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: spacing.lg,
  },
  primary: { backgroundColor: colors.rose },
  secondary: {
    backgroundColor: colors.cardElevated,
    borderWidth: 1,
    borderColor: colors.borderStrong,
  },
  ghost: { backgroundColor: "transparent" },
  danger: { backgroundColor: colors.danger },
  pressed: { opacity: 0.88, transform: [{ scale: 0.98 }] },
  disabled: { opacity: 0.45 },
  label: { color: "#fff", fontSize: 16, fontWeight: "700" },
  labelGhost: { color: colors.rose },
});
