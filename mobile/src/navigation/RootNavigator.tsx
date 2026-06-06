import React, { useEffect, useRef } from "react";
import {
  ActivityIndicator,
  Animated,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { Ionicons } from "../components/Ionicons";
import { useAuth } from "../store/AuthContext";
import { LoginScreen } from "../screens/LoginScreen";
import { OnboardingContactsScreen } from "../screens/OnboardingContactsScreen";
import { OnboardingWalkScreen } from "../screens/OnboardingWalkScreen";
import { HomeScreen } from "../screens/HomeScreen";
import { SettingsScreen } from "../screens/SettingsScreen";
import { SafePlacesScreen } from "../screens/SafePlacesScreen";
import { ChatbotScreen } from "../screens/ChatbotScreen";
import { IncidentHistoryScreen } from "../screens/IncidentHistoryScreen";
import { colors, spacing } from "../theme";

export type RootStackParamList = {
  Login: undefined;
  OnboardingContacts: undefined;
  OnboardingWalk: undefined;
  Home: undefined;
  Settings: undefined;
  SafePlaces: undefined;
  Chatbot: undefined;
  IncidentHistory: undefined;
};

const Stack = createNativeStackNavigator<RootStackParamList>();

function BootstrapScreen() {
  const pulseAnim = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    const animation = Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, {
          toValue: 1.12,
          duration: 1000,
          useNativeDriver: true,
        }),
        Animated.timing(pulseAnim, {
          toValue: 1.0,
          duration: 1000,
          useNativeDriver: true,
        }),
      ]),
    );
    animation.start();
    return () => animation.stop();
  }, [pulseAnim]);

  return (
    <View style={styles.bootstrapContainer}>
      <View style={styles.bootstrapContent}>
        <Animated.View
          style={[styles.iconWrapper, { transform: [{ scale: pulseAnim }] }]}
        >
          <Ionicons name="shield-half-outline" size={60} color={colors.rose} />
        </Animated.View>
        <Text style={styles.bootstrapTitle}>AURALIS</Text>
        <Text style={styles.bootstrapSubtitle}>PERSONAL SAFETY SYSTEM</Text>

        <View style={styles.loaderWrapper}>
          <ActivityIndicator size="small" color={colors.rose} />
          <Text style={styles.loaderText}>Establishing secure session...</Text>
        </View>
      </View>
      <Text style={styles.bootstrapFooter}>End-to-End Encrypted & Secure</Text>
    </View>
  );
}

export function RootNavigator() {
  const { ready, user, onboardingStep } = useAuth();

  if (!ready) {
    return <BootstrapScreen />;
  }

  return (
    <NavigationContainer>
      <Stack.Navigator
        screenOptions={{ headerShown: false, animation: "slide_from_right" }}
      >
        {!user ? (
          <Stack.Screen name="Login" component={LoginScreen} />
        ) : onboardingStep === "contacts" ? (
          <Stack.Screen
            name="OnboardingContacts"
            component={OnboardingContactsScreen}
          />
        ) : onboardingStep === "calibration" ? (
          <Stack.Screen
            name="OnboardingWalk"
            component={OnboardingWalkScreen}
          />
        ) : (
          <>
            <Stack.Screen name="Home" component={HomeScreen} />
            <Stack.Screen
              name="Settings"
              component={SettingsScreen}
              options={{ animation: "slide_from_bottom" }}
            />
            <Stack.Screen
              name="OnboardingContacts"
              component={OnboardingContactsScreen}
            />
            <Stack.Screen
              name="OnboardingWalk"
              component={OnboardingWalkScreen}
            />
            <Stack.Screen name="SafePlaces" component={SafePlacesScreen} />
            <Stack.Screen name="Chatbot" component={ChatbotScreen} />
            <Stack.Screen
              name="IncidentHistory"
              component={IncidentHistoryScreen}
            />
          </>
        )}
      </Stack.Navigator>
    </NavigationContainer>
  );
}

const styles = StyleSheet.create({
  bootstrapContainer: {
    flex: 1,
    backgroundColor: colors.bg,
    alignItems: "center",
    justifyContent: "space-between",
    paddingVertical: spacing.xl * 1.5,
  },
  bootstrapContent: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    width: "100%",
  },
  iconWrapper: {
    width: 108,
    height: 108,
    borderRadius: 54,
    backgroundColor: colors.surface,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 1.5,
    borderColor: colors.border,
    shadowColor: colors.rose,
    shadowOpacity: 0.15,
    shadowRadius: 10,
    elevation: 4,
    marginBottom: spacing.lg,
  },
  bootstrapTitle: {
    color: colors.text,
    fontSize: 28,
    fontWeight: "900",
    letterSpacing: 6,
    textTransform: "uppercase",
  },
  bootstrapSubtitle: {
    color: colors.textMuted,
    fontSize: 11,
    fontWeight: "800",
    letterSpacing: 2,
    marginTop: 6,
    marginBottom: spacing.xl * 1.5,
  },
  loaderWrapper: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    backgroundColor: colors.surface,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderRadius: 30,
    borderWidth: 1,
    borderColor: colors.border,
  },
  loaderText: {
    color: colors.textSoft,
    fontSize: 13,
    fontWeight: "600",
  },
  bootstrapFooter: {
    color: colors.textFaint,
    fontSize: 11,
    fontWeight: "700",
    letterSpacing: 1,
  },
});
