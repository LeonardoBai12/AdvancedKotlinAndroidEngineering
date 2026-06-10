---
layout: page
title: "Chapter 15: Android Security — Hardening & Checklist"
---

## Code Obfuscation & R8

APK files can be decompiled to reveal source code. Obfuscation will not stop a determined attacker, but it significantly raises the bar and protects intellectual property. Enable R8 for release builds to shrink, optimise, and rename your code, and to strip debug logging.

*Enable R8 for release*

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

# proguard-rules.pro -- strip logging from release builds
-assumenosideeffects class android.util.Log {
    public static *** d(...);
    public static *** v(...);
}
```

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
