---
layout: page
title: "Chapter 15: Android Security — Hardening & Checklist"
---

## Code Obfuscation & R8

APK files can be decompiled with tools like JADX or Apktool, exposing your class structure, business logic, and string constants in minutes. Obfuscation will not stop a determined attacker, but it significantly raises the reverse-engineering cost. Enable R8 for release builds.

### What R8 Does to Your Code

R8 is not just a name renamer. It runs four operations in a single pass:

| Operation | Effect |
| --- | --- |
| **Shrinking** | Removes unused classes, methods, and fields |
| **Minification** | Renames identifiers to short names (`a`, `b`, `aa`, `ab`…) |
| **Optimisation** | Inlines short methods, eliminates dead branches, merges classes |
| **Desugaring** | Rewrites Java 8+ constructs for older API levels |

A typical release build with R8 enabled is 30–60% smaller than the debug build and contains far less readable code when decompiled.

### Obfuscating Classes That Implement Interfaces

This is where most R8 configurations break. R8 renames a class implementing an interface only if it can prove the interface's methods will never be looked up by their original names. Any of the following bypass that proof and require an explicit `keep` rule:

**Reflection**: `Class.forName("com.example.MyRepo")` uses the original name — R8 cannot know about this at compile time.

**Retrofit / Gson / Moshi**: these libraries use reflection to find method names and field names on interface and data class types at runtime.

**Parcelable**: `CREATOR` field and constructor are accessed by name by the Android framework.

**Enums**: `values()` and `valueOf()` are called by name by serialisation frameworks.

```proguard
# Keep all interface implementations found via service locator / DI
-keep class * implements com.example.repo.Repository { *; }

# Keep data models (field names used by JSON serialization)
-keepclassmembers class com.example.model.** {
    <fields>;
}

# Keep Retrofit service interfaces (methods called by name via reflection)
-keep interface com.example.api.** { *; }

# Keep Parcelable CREATOR (accessed by Android framework by name)
-keep class * implements android.os.Parcelable {
    public static final android.os.Parcelable$Creator *;
}

# Keep enum members (valueOf / values called by serialization)
-keepclassmembers enum * {
    public static **[] values();
    public static ** valueOf(java.lang.String);
}

# Keep JNI methods (method name must match C side exactly)
-keepclasseswithmembernames class * {
    native <methods>;
}

# Strip debug logs from release (no functionality loss, reduces attack surface)
-assumenosideeffects class android.util.Log {
    public static *** d(...);
    public static *** v(...);
    public static *** i(...);
}
```

### Custom Obfuscation Dictionaries

By default R8 uses `a`, `b`, `c`… for renamed identifiers. You can replace these with visually confusing lookalikes that are valid Java identifiers but hard for a human to read:

```proguard
# dict.txt — confusing but legal identifiers
ll
lI
Il
II
lIl
IlI
```

```proguard
# proguard-rules.pro
-obfuscationdictionary       dict.txt   # method and field names
-classobfuscationdictionary  dict.txt   # class names
-packageobfuscationdictionary dict.txt  # package names
```

The result: decompiled code looks like `ll.lI(Il.II())` instead of `a.b(c.d())` — marginally harder to read, but it defeats simple grep searches for identifiable symbols.

### Enabling R8

```kotlin
android {
    buildTypes {
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }
}
```

### Release Build Testing Checklist

Obfuscation introduces a new class of bugs that only appear in release builds. Always test the release APK — not just debug.

| What to verify | How |
| --- | --- |
| **Decompile with JADX** | Confirm class/method names are obfuscated as expected; check no secrets are in string literals |
| **Mapping file** | `build/outputs/mapping/release/mapping.txt` maps obfuscated → original names. Keep this file; you need it to de-obfuscate crash stack traces |
| **Crash reporting** | Upload mapping to Firebase Crashlytics / Play Console so stack traces are readable in production |
| **All API calls work** | Retrofit interfaces, JSON serialization — these break silently if keep rules are missing |
| **Parcelable / Serializable** | Pass objects between screens and across process death; test with `adb shell am kill <package>` |
| **Reflection calls** | Any `Class.forName()` or `getDeclaredMethod()` by string — run every code path that uses them |
| **JNI method names** | Native methods called from C must match exactly; test all NDK-dependent features |
| **Deep links** | Activity/scheme classes must be kept if referenced in manifest by name |

---

## App Signing

Every APK must be signed before it can be installed. The signature proves the APK has not been tampered with and identifies the developer. Android's signing schemes have evolved across four versions.

| Scheme | Android version | What is signed | Notes |
| --- | --- | --- | --- |
| **v1 (JAR signing)** | All | Individual files inside the ZIP | Vulnerable to ZIP manipulation — attacker can add files without invalidating signatures |
| **v2 (APK Signature Scheme v2)** | 7.0+ | Entire APK byte stream | Any modification breaks the signature; requires v1 as fallback for older devices |
| **v3 (Rotation)** | 9.0+ | Entire APK + key rotation proof | Allows signing key rotation with a proof-of-rotation chain |
| **v4 (Incremental)** | 11+ | Hash tree over the APK | Enables streaming install — Play Store can install while downloading |

Modern apps should use **v1 + v2 + v3**. AGP does this by default.

```kotlin
android {
    signingConfigs {
        create("release") {
            storeFile = file(System.getenv("KEYSTORE_PATH") ?: "debug.jks")
            storePassword = System.getenv("KEYSTORE_PASSWORD")
            keyAlias = System.getenv("KEY_ALIAS")
            keyPassword = System.getenv("KEY_PASSWORD")
            enableV1Signing = true
            enableV2Signing = true
            enableV3Signing = true
        }
    }
    buildTypes {
        release {
            signingConfig = signingConfigs.getByName("release")
        }
    }
}
```

```bash
# Verify which schemes are present in an APK
apksigner verify --verbose app-release.apk

# Check the certificate details
apksigner verify --print-certs app-release.apk
```

### Signature Verification at Runtime

An app can verify its own signature to detect repackaging (an attacker strips your signing certificate and re-signs with their own):

```kotlin
fun isSignatureValid(context: Context): Boolean {
    val expectedSha256 = "your:cert:sha256:fingerprint:here"
    return try {
        val info = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            context.packageManager.getPackageInfo(
                context.packageName,
                PackageManager.GET_SIGNING_CERTIFICATES
            )
        } else {
            @Suppress("DEPRECATION")
            context.packageManager.getPackageInfo(
                context.packageName,
                PackageManager.GET_SIGNATURES
            )
        }
        val signatures = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            info.signingInfo.apkContentsSigners
        } else {
            @Suppress("DEPRECATION")
            info.signatures
        }
        signatures.any { sig ->
            val digest = MessageDigest.getInstance("SHA-256").digest(sig.toByteArray())
            Base64.encodeToString(digest, Base64.NO_WRAP) == expectedSha256
        }
    } catch (e: Exception) {
        false
    }
}
```

> **Note:** This check is bypassable by Frida hooks at runtime. For stronger guarantees, perform signature verification in native code (NDK) and cross-check server-side using the Play Integrity API verdict.

---

## Emulator & Tamper Detection

Running your app in an emulator is the first step for most reverse engineering and automation attacks. A layered detection strategy raises the cost significantly.

### Layer 1 — Build Properties

```kotlin
fun isEmulator(): Boolean = (
    Build.FINGERPRINT.startsWith("generic") ||
    Build.FINGERPRINT.startsWith("unknown") ||
    Build.MODEL.contains("google_sdk") ||
    Build.MODEL.contains("Emulator") ||
    Build.MODEL.contains("Android SDK built for x86") ||
    Build.MANUFACTURER.contains("Genymotion") ||
    (Build.BRAND.startsWith("generic") && Build.DEVICE.startsWith("generic")) ||
    Build.PRODUCT == "google_sdk"
)
```

`Build.*` values are the quickest check but also the easiest to spoof with Magisk modules or custom QEMU flags. Never rely on this alone.

### Layer 2 — Hardware Sensors

Real devices have accelerometers and gyroscopes. Most emulators don't, or emulate them unrealistically.

```kotlin
fun hasSensors(context: Context): Boolean {
    val sm = context.getSystemService(SENSOR_SERVICE) as SensorManager
    return sm.getDefaultSensor(Sensor.TYPE_ACCELEROMETER) != null &&
           sm.getDefaultSensor(Sensor.TYPE_GYROSCOPE) != null
}
```

### Layer 3 — Radio / Telephony

```kotlin
fun hasRealTelephony(context: Context): Boolean {
    val tm = context.getSystemService(TELEPHONY_SERVICE) as TelephonyManager
    val operator = tm.networkOperatorName
    return operator.isNotEmpty() && operator != "Android"
}
```

### Layer 4 — Emulator-Specific Files

```kotlin
fun hasEmulatorFiles(): Boolean {
    val paths = listOf(
        "/dev/socket/qemud",
        "/dev/qemu_pipe",
        "/system/lib/libc_malloc_debug_qemu.so",
        "/sys/qemu_trace",
        "/system/bin/qemu-props"
    )
    return paths.any { java.io.File(it).exists() }
}
```

### Layer 5 — Google Play Integrity API (strongest)

The Play Integrity API replaces the deprecated SafetyNet. It returns a **verdict token** that your server validates with Google. The verdict includes a device integrity level:

| Verdict | Meaning |
| --- | --- |
| `MEETS_DEVICE_INTEGRITY` | Real Android device with Google Play, passes hardware attestation |
| `MEETS_BASIC_INTEGRITY` | Passes basic software checks, but may be rooted or modified |
| `MEETS_STRONG_INTEGRITY` | Hardware-backed attestation, unmodified OS |

```kotlin
val integrityManager = IntegrityManagerFactory.create(context)
val requestHash = computeHash(requestNonce)  // tie verdict to this specific request

integrityManager.requestIntegrityToken(
    IntegrityTokenRequest.builder()
        .setNonce(requestHash)
        .build()
).addOnSuccessListener { response ->
    val token = response.token()
    // Send token to YOUR backend — backend calls Google to decode it
    // Never decode client-side: attacker can intercept and replay a valid token
}
```

The key difference from the local checks: the verdict is **server-validated** by Google, not by your app. An attacker cannot forge it.

### Combining the Layers

```kotlin
fun riskScore(context: Context): Int {
    var score = 0
    if (isEmulator()) score += 30
    if (!hasSensors(context)) score += 20
    if (!hasRealTelephony(context)) score += 15
    if (hasEmulatorFiles()) score += 35
    return score  // 0 = likely real; 100 = almost certainly emulator
}
```

Use the score to decide on a graduated response: log, show a warning, or silently restrict functionality — rather than hard-blocking (which is easily detected and bypassed by attackers who then know exactly what check failed).

---

## OWASP Mobile Top 10

**OWASP** — the Open Worldwide Application Security Project — is a non-profit foundation that publishes free, community-driven security standards and tooling. Its best-known output is the periodically updated 'Top 10' lists of the most critical security risks for a given platform. The **OWASP Mobile Top 10** is the mobile-specific list; the entries are labelled M1 through M10 (M for Mobile). It is the industry's common reference point for what to defend against, so it is worth knowing by name in interviews. The table below pairs each risk with its concrete Android mitigation — most of which were covered in the sections above.

| # | Vulnerability | Android mitigation |
| --- | --- | --- |
| M1 | Improper Platform Usage | Follow Android best practices |
| M2 | Insecure Data Storage | Encrypted DataStore, Keystore |
| M3 | Insecure Communication | HTTPS + certificate pinning |
| M4 | Insecure Authentication | BiometricPrompt, OAuth 2.0 |
| M5 | Insufficient Cryptography | Android Keystore, AES-GCM 256-bit |
| M6 | Insecure Authorization | Validate permissions server-side |
| M7 | Client Code Quality | Enable R8, fix lint warnings |
| M8 | Code Tampering | Play Integrity API |
| M9 | Reverse Engineering | R8 obfuscation, NDK for secrets |
| M10 | Extraneous Functionality | Remove debug code and verbose logs |

## Security Checklist

- **Storage**: encrypted DataStore for prefs, Keystore for keys, SQLCipher for sensitive DBs; nothing sensitive in SharedPreferences, external storage, or logs.
- **Network**: HTTPS everywhere, certificate pinning, a Network Security Config, no custom trust-all TrustManager.
- **Code**: R8 enabled, no hard-coded secrets, debug logging stripped from release.
- **Auth**: BiometricPrompt, OAuth 2.0, short-lived access tokens with refresh, tokens in encrypted storage.
- **Input**: validate everything, parameterized Room queries, locked-down WebView, validated deep-link data.
- **Testing**: scan the APK (MobSF/JADX) for hard-coded secrets; confirm pinning holds against a MITM proxy.

---

← [Previous: Data & Network Security](../02-data-network-security/) · [↑ Chapter Index](../)
