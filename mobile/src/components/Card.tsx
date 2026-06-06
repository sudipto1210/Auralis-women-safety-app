import React from "react";
import { StyleSheet, Text, View, ViewStyle } from "react-native";
import { colors, radius, shadow, spacing } from "../theme";

type Props = {
  title?: string;
  children: React.ReactNode;
  style?: ViewStyle;
};

export function Card({ title, children, style }: Props) {
  return (
    <View style={[styles.card, style]}>
      {title ? <Text style={styles.title}>{title}</Text> : null}
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.card,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.md,
    marginBottom: spacing.md,
    ...shadow.card,
  },
  title: {
    fontSize: 15,
    fontWeight: "700",
    color: colors.text,
    marginBottom: spacing.sm,
  },
});
