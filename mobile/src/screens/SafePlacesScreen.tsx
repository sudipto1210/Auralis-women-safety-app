import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Linking,
  PermissionsAndroid,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";
import Geolocation from "react-native-geolocation-service";
import { Haptics } from "../components/Haptics";
import { Ionicons } from "../components/Ionicons";
import { useNavigation } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { Screen } from "../components/Screen";
import { Button } from "../components/Button";
import type { RootStackParamList } from "../navigation/RootNavigator";
import { api } from "../api/client";
import { colors, radius, shadow, spacing } from "../theme";

type SafePlace = {
  id: string;
  name: string;
  type: string;
  distance: number | string;
  rating?: number | string;
  lat?: number;
  lng?: number;
  latitude?: number;
  longitude?: number;
  address?: string;
};

const toPlaces = (data: unknown): SafePlace[] => {
  if (Array.isArray(data)) return data as SafePlace[];
  if (
    data &&
    typeof data === "object" &&
    Array.isArray((data as { places?: unknown }).places)
  ) {
    return (data as { places: SafePlace[] }).places;
  }
  if (
    data &&
    typeof data === "object" &&
    Array.isArray((data as { safe_places?: unknown }).safe_places)
  ) {
    return (data as { safe_places: SafePlace[] }).safe_places;
  }
  return [];
};

export function SafePlacesScreen() {
  const navigation =
    useNavigation<NativeStackNavigationProp<RootStackParamList>>();
  const [places, setPlaces] = useState<SafePlace[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const granted =
        (await PermissionsAndroid.request(
          PermissionsAndroid.PERMISSIONS.ACCESS_FINE_LOCATION,
        )) === PermissionsAndroid.RESULTS.GRANTED;
      if (!granted) {
        setError("Location permission is needed to find nearby safe places.");
        setPlaces([]);
        return;
      }
      const position = await new Promise<any>((resolve, reject) => {
        Geolocation.getCurrentPosition(
          (pos) => resolve(pos),
          (err) => reject(err),
          { enableHighAccuracy: true, timeout: 15000, maximumAge: 10000 },
        );
      });
      const query = `?lat=${position.coords.latitude}&lng=${position.coords.longitude}`;
      const data = await api<unknown>(`/api/safe_places${query}`);
      setPlaces(toPlaces(data));
      await Haptics.selectionAsync();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load safe places.");
      setPlaces([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const openMap = async (place: SafePlace) => {
    await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    const lat = place.lat ?? place.latitude;
    const lng = place.lng ?? place.longitude;
    const query =
      lat !== undefined && lng !== undefined
        ? `${lat},${lng}`
        : encodeURIComponent(place.name);
    await Linking.openURL(
      `https://www.google.com/maps/search/?api=1&query=${query}`,
    );
  };

  return (
    <Screen scroll>
      <View style={styles.header}>
        <Pressable style={styles.back} onPress={() => navigation.goBack()}>
          <Ionicons name="chevron-back" size={24} color={colors.text} />
        </Pressable>
        <Text style={styles.title}>Safe Places</Text>
        <Pressable style={styles.back} onPress={load}>
          <Ionicons name="refresh" size={21} color={colors.textSoft} />
        </Pressable>
      </View>

      {loading ? (
        <View style={styles.state}>
          <ActivityIndicator color={colors.rose} />
          <Text style={styles.stateText}>Finding nearby help points...</Text>
        </View>
      ) : error ? (
        <View style={styles.state}>
          <Ionicons name="location-outline" size={32} color={colors.warning} />
          <Text style={styles.stateText}>{error}</Text>
          <Button label="Try again" onPress={load} style={styles.stateButton} />
        </View>
      ) : places.length === 0 ? (
        <View style={styles.state}>
          <Ionicons name="map-outline" size={32} color={colors.textMuted} />
          <Text style={styles.stateText}>
            No safe places were returned for this location.
          </Text>
          <Button label="Refresh" onPress={load} style={styles.stateButton} />
        </View>
      ) : (
        places.map((place, index) => (
          <Pressable
            key={place.id || `${place.name}-${index}`}
            style={styles.placeCard}
            onPress={() => openMap(place)}
          >
            <View style={styles.placeIcon}>
              <Ionicons
                name="business-outline"
                size={22}
                color={colors.success}
              />
            </View>
            <View style={styles.placeBody}>
              <Text style={styles.placeName}>{place.name}</Text>
              <Text style={styles.placeMeta}>
                {place.type || "Safe location"}
              </Text>
              {place.address ? (
                <Text style={styles.address}>{place.address}</Text>
              ) : null}
            </View>
            <View style={styles.placeSide}>
              <Text style={styles.distance}>
                {String(place.distance || "Nearby")}
              </Text>
              <Text style={styles.rating}>
                {place.rating ? `${place.rating} stars` : "Open map"}
              </Text>
            </View>
          </Pressable>
        ))
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
  title: { color: colors.text, fontSize: 24, fontWeight: "900" },
  state: {
    minHeight: 320,
    alignItems: "center",
    justifyContent: "center",
    gap: spacing.md,
  },
  stateText: { color: colors.textSoft, textAlign: "center", lineHeight: 21 },
  stateButton: { width: 180 },
  placeCard: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.lg,
    padding: spacing.md,
    marginBottom: spacing.md,
    ...shadow.card,
  },
  placeIcon: {
    width: 46,
    height: 46,
    borderRadius: 23,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.successSoft,
  },
  placeBody: { flex: 1 },
  placeName: { color: colors.text, fontSize: 16, fontWeight: "800" },
  placeMeta: { color: colors.textSoft, fontSize: 13, marginTop: 3 },
  address: { color: colors.textMuted, fontSize: 12, marginTop: 5 },
  placeSide: { alignItems: "flex-end", maxWidth: 92 },
  distance: { color: colors.text, fontSize: 13, fontWeight: "800" },
  rating: {
    color: colors.textMuted,
    fontSize: 11,
    marginTop: 5,
    textAlign: "right",
  },
});
