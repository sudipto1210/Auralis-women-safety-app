# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# AURALIS — ProGuard / R8 Rules
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Applied by: android/app/build.gradle (proguard-android-optimize.txt +
# this file). R8 is the default minifier in modern AGP; ProGuard flags
# are compatible.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# ── 1. React Native core ─────────────────────────────────────────────
-keep class com.facebook.react.** { *; }
-keep class com.facebook.hermes.** { *; }
-keep class com.facebook.jni.** { *; }
-keep class com.facebook.soloader.** { *; }
-dontwarn com.facebook.react.**
-dontwarn com.facebook.hermes.**

# ── 2. React Native Reanimated ───────────────────────────────────────
-keep class com.swmansion.reanimated.** { *; }
-keep class com.swmansion.gesturehandler.** { *; }
-dontwarn com.swmansion.**

# ── 3. React Native Screens ─────────────────────────────────────────
-keep class com.swmansion.rnscreens.** { *; }

# ── 4. Keychain (react-native-keychain) ──────────────────────────────
-keep class com.oblador.keychain.** { *; }
-dontwarn com.oblador.keychain.**

# ── 5. Google Sign-In (@react-native-google-signin) ──────────────────
-keep class com.google.android.gms.auth.** { *; }
-keep class com.google.android.gms.common.** { *; }
-keep class com.google.android.gms.tasks.** { *; }
-keep class com.google.android.gms.signin.** { *; }
-dontwarn com.google.android.gms.**

# ── 6. Geolocation (react-native-geolocation-service) ────────────────
-keep class com.agontuk.RNFusedLocation.** { *; }
-dontwarn com.agontuk.**

# ── 7. Sensors (react-native-sensors) ───────────────────────────────
-keep class com.sensors.** { *; }

# ── 8. Sound Level (react-native-sound-level) ────────────────────────
-keep class com.lakeba.reactnative.soundlevel.** { *; }

# ── 9. Linear Gradient (react-native-linear-gradient) ────────────────
-keep class com.BV.LinearGradient.** { *; }

# ── 10. Vector Icons (react-native-vector-icons) ─────────────────────
-keep class com.oblador.vectoricons.** { *; }

# ── 11. Async Storage ────────────────────────────────────────────────
-keep class com.reactnativecommunity.asyncstorage.** { *; }

# ── 12. Haptic Feedback ──────────────────────────────────────────────
-keep class com.mkuczera.RNHapticFeedback.** { *; }

# ── 13. Security Check Module (AURALIS native) ────────────────────────
-keep class com.auralis.app.SecurityCheckModule { *; }
-keep class com.auralis.app.SecurityCheckPackage { *; }

# ── 14. TurboModules bridge ──────────────────────────────────────────
-keep class com.facebook.react.turbomodule.** { *; }
-keep interface com.facebook.react.turbomodule.** { *; }

# ── 15. Annotations & reflection ─────────────────────────────────────
-keepattributes *Annotation*
-keepattributes Signature
-keepattributes Exceptions
-keepattributes InnerClasses
-keepattributes EnclosingMethod

# ── 16. Kotlin metadata (required for Kotlin reflection) ─────────────
-keepattributes RuntimeVisibleAnnotations
-keep class kotlin.Metadata { *; }
-dontwarn kotlin.**

# ── 17. OkHttp (used internally by React Native) ─────────────────────
-keep class okhttp3.** { *; }
-keep interface okhttp3.** { *; }
-dontwarn okhttp3.**
-dontwarn okio.**

# ── 18. Strip logging in release ─────────────────────────────────────
# Remove android.util.Log calls entirely from release bytecode.
-assumenosideeffects class android.util.Log {
    public static int v(...);
    public static int d(...);
    public static int i(...);
    public static int w(...);
    public static int e(...);
    public static int wtf(...);
}
