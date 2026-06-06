import {
  EXPO_PUBLIC_API_URL,
  EXPO_PUBLIC_GOOGLE_CLIENT_ID,
  EXPO_PUBLIC_GOOGLE_ANDROID_CLIENT_ID,
} from "@env";

let localApiUrlOverride: string | null = null;

export function getApiUrl(): string {
  return localApiUrlOverride || EXPO_PUBLIC_API_URL || "http://10.0.2.2:5001";
}

export function getGoogleClientId(): string {
  return EXPO_PUBLIC_GOOGLE_CLIENT_ID || "";
}

export function getGoogleClientIds() {
  const webClientId = EXPO_PUBLIC_GOOGLE_CLIENT_ID || "";
  return {
    webClientId,
    androidClientId: EXPO_PUBLIC_GOOGLE_ANDROID_CLIENT_ID || "",
    iosClientId: "",
    clientId: webClientId,
  };
}

export function setApiUrlOverride(url: string) {
  localApiUrlOverride = url;
}
