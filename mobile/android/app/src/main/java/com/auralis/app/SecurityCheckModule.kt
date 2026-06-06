package com.auralis.app

import android.content.pm.PackageManager
import android.content.pm.Signature
import android.os.Build
import android.os.Debug
import com.facebook.react.bridge.Promise
import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.bridge.ReactContextBaseJavaModule
import com.facebook.react.bridge.ReactMethod
import com.facebook.react.bridge.WritableNativeMap
import java.io.File
import java.security.MessageDigest

/**
 * SecurityCheckModule
 * ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 * Native Kotlin module that performs integrity checks at runtime.
 * Exposes a single JS-callable method: `checkIntegrity()` which returns
 * a result map describing the security posture of the current device.
 *
 * Checks performed:
 *   1. Root detection   — looks for `su` binary and known root package names
 *   2. Debugger         — detects if a debugger is currently attached
 *   3. Emulator         — heuristic device fingerprint check
 *   4. APK signature    — verifies the APK signing cert matches expected hash
 *
 * In DEBUG builds (BuildConfig.DEBUG == true):
 *   • Emulator check is skipped (always passes)
 *   • Debugger check is skipped (always passes)
 *   • Root check still runs but result is advisory-only (JS side decides)
 */
class SecurityCheckModule(private val reactContext: ReactApplicationContext) :
    ReactContextBaseJavaModule(reactContext) {

    override fun getName(): String = "SecurityCheck"

    // ── Known root management app packages ────────────────────────────────
    private val ROOT_PACKAGES = listOf(
        "com.topjohnwu.magisk",
        "com.noshufou.android.su",
        "com.noshufou.android.su.elite",
        "eu.chainfire.supersu",
        "com.koushikdutta.superuser",
        "com.thirdparty.superuser",
        "com.yellowes.su",
        "com.koushikdutta.rommanager",
        "com.koushikdutta.rommanager.license",
        "com.dimonvideo.luckypatcher",
        "com.chelpus.lackypatch",
        "com.ramdroid.appquarantine",
        "com.ramdroid.appquarantine.pro",
        "com.devadvance.rootcloak",
        "com.devadvance.rootcloak.plus",
        "de.robv.android.xposed.installer",
        "com.saurik.substrate",
        "com.zachspong.temprootremovejb",
        "com.amphoras.hidemyroot",
        "com.formyhm.hiderootPremium",
        "com.amphoras.hidemyrootadfree",
        "com.formyhm.hideroot",
        "me.phh.superuser",
        "eu.chainfire.supersu.pro",
        "com.kingouser.com"
    )

    // ── Known `su` binary locations ───────────────────────────────────────
    private val SU_PATHS = listOf(
        "/system/app/Superuser.apk",
        "/sbin/su",
        "/system/bin/su",
        "/system/xbin/su",
        "/data/local/xbin/su",
        "/data/local/bin/su",
        "/data/local/su",
        "/system/bin/.ext/.su",
        "/system/usr/we-need-root/su-backup",
        "/system/xbin/mu"
    )

    // ── Emulator build fingerprint tokens ─────────────────────────────────
    private val EMULATOR_FINGERPRINTS = listOf(
        "generic", "unknown", "emulator", "sdk", "sdk_x86",
        "vbox86p", "goldfish", "ranchu"
    )

    // ──────────────────────────────────────────────────────────────────────
    // Public JS API
    // ──────────────────────────────────────────────────────────────────────

    @ReactMethod
    fun checkIntegrity(promise: Promise) {
        try {
            val result = WritableNativeMap()

            val isRooted = detectRoot()
            val isDebugging = detectDebugger()
            val isEmulator = detectEmulator()
            val signatureValid = verifySignature()

            result.putBoolean("isRooted", isRooted)
            result.putBoolean("isDebugging", isDebugging)
            result.putBoolean("isEmulator", isEmulator)
            result.putBoolean("signatureValid", signatureValid)
            result.putBoolean("isDebugBuild", BuildConfig.DEBUG)

            // Overall pass/fail:
            // In release: fail if rooted, debugging, or bad signature
            // In debug: only fail on bad signature (emulator/debug allowed)
            val passed = if (BuildConfig.DEBUG) {
                signatureValid
            } else {
                !isRooted && !isDebugging && signatureValid
            }
            result.putBoolean("passed", passed)

            promise.resolve(result)
        } catch (e: Exception) {
            // If the check itself crashes, treat as failed to be safe
            promise.reject("SECURITY_CHECK_ERROR", e.message ?: "Unknown error", e)
        }
    }

    // ──────────────────────────────────────────────────────────────────────
    // Root Detection
    // ──────────────────────────────────────────────────────────────────────

    private fun detectRoot(): Boolean {
        return checkSuBinaries() || checkRootPackages() || checkBuildTags()
    }

    private fun checkSuBinaries(): Boolean {
        return SU_PATHS.any { path -> File(path).exists() }
    }

    private fun checkRootPackages(): Boolean {
        val pm = reactContext.packageManager
        return ROOT_PACKAGES.any { pkg ->
            try {
                pm.getPackageInfo(pkg, 0)
                true
            } catch (e: PackageManager.NameNotFoundException) {
                false
            }
        }
    }

    private fun checkBuildTags(): Boolean {
        val tags = Build.TAGS
        return tags != null && tags.contains("test-keys")
    }

    // ──────────────────────────────────────────────────────────────────────
    // Debugger Detection
    // ──────────────────────────────────────────────────────────────────────

    private fun detectDebugger(): Boolean {
        if (BuildConfig.DEBUG) return false // Allowed in debug builds
        return Debug.isDebuggerConnected() || Debug.waitingForDebugger()
    }

    // ──────────────────────────────────────────────────────────────────────
    // Emulator Detection
    // ──────────────────────────────────────────────────────────────────────

    private fun detectEmulator(): Boolean {
        if (BuildConfig.DEBUG) return false // Always allowed in debug builds

        val fingerprint = Build.FINGERPRINT?.lowercase() ?: ""
        val hardware = Build.HARDWARE?.lowercase() ?: ""
        val product = Build.PRODUCT?.lowercase() ?: ""
        val model = Build.MODEL?.lowercase() ?: ""
        val manufacturer = Build.MANUFACTURER?.lowercase() ?: ""
        val brand = Build.BRAND?.lowercase() ?: ""

        return EMULATOR_FINGERPRINTS.any { token ->
            fingerprint.contains(token) ||
            hardware.contains(token) ||
            product.contains(token) ||
            model.contains(token)
        } || manufacturer == "genymotion"
          || (brand.startsWith("generic") && product.startsWith("sdk"))
    }

    // ──────────────────────────────────────────────────────────────────────
    // APK Signature Verification
    // ──────────────────────────────────────────────────────────────────────

    private fun verifySignature(): Boolean {
        // In DEBUG builds, skip signature check (debug key changes per machine)
        if (BuildConfig.DEBUG) return true

        return try {
            val pm = reactContext.packageManager
            val packageName = reactContext.packageName

            @Suppress("DEPRECATION")
            val signatures: Array<Signature> = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
                val signingInfo = pm.getPackageInfo(
                    packageName,
                    PackageManager.GET_SIGNING_CERTIFICATES
                ).signingInfo
                signingInfo?.apkContentsSigners ?: emptyArray()
            } else {
                @Suppress("DEPRECATION")
                pm.getPackageInfo(packageName, PackageManager.GET_SIGNATURES).signatures
                    ?: emptyArray()
            }

            if (signatures.isEmpty()) return false

            // Compute SHA-256 of the first signing certificate
            val cert = signatures[0].toByteArray()
            val md = MessageDigest.getInstance("SHA-256")
            val digest = md.digest(cert)
            val hexHash = digest.joinToString("") { "%02x".format(it) }

            // ── ACTION REQUIRED ────────────────────────────────────────────────
            // Replace EXPECTED_CERT_HASH with the SHA-256 of your production
            // signing certificate. Generate it with:
            //   keytool -printcert -jarfile app-release.apk
            // or check the walkthrough.md for instructions.
            //
            // Until this is set, signature verification is SKIPPED (returns true)
            // so you can build and test without a prod keystore.
            // ──────────────────────────────────────────────────────────────────
            val EXPECTED_CERT_HASH = "" // <-- fill in after generating prod keystore

            if (EXPECTED_CERT_HASH.isEmpty()) {
                // Hash not configured yet: pass but log a warning
                android.util.Log.w("SecurityCheck", "APK signature hash not configured. Skipping verification.")
                return true
            }

            hexHash == EXPECTED_CERT_HASH
        } catch (e: Exception) {
            false
        }
    }
}
