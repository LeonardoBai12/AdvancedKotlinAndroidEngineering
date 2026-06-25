---
layout: default
title: Data Network Security
parent: Android Security
nav_order: 2
---

## Secure Data Storage on Android

Where you store data determines its security. Android offers a hierarchy of options with very different characteristics. Never store sensitive data in plaintext, and never in external storage.

| Storage | Security | Use for |
| --- | --- | --- |
| Encrypted DataStore | Excellent | Auth tokens, sensitive preferences |
| Android Keystore | Excellent | Cryptographic keys only |
| Encrypted Room (SQLCipher) | Very good | Large sensitive datasets |
| Internal Storage | Good | App-private, non-sensitive files |
| SharedPreferences | Poor | Non-sensitive UI state only |
| External Storage | None | Public files — never secrets |

*Encrypted DataStore vs plain SharedPreferences*

```kotlin
// BAD -- a token in plain SharedPreferences is EXPOSED
prefs.edit().putString("auth_token", token).apply()

// GOOD -- encrypted at rest
// implementation("androidx.security:security-crypto:1.1.0-alpha06")
private val Context.encryptedDataStore by preferencesDataStore("secure_prefs")

suspend fun saveToken(token: String) {
    dataStore.edit { prefs ->
        prefs[stringPreferencesKey("auth_token")] = token
    }
}
```

*Android Keystore — keys never leave the secure container*

```kotlin
private fun generateKey(): SecretKey {
    val keyGenerator = KeyGenerator.getInstance(
        KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore"
    )
    keyGenerator.init(
        KeyGenParameterSpec.Builder(
            "my_key_alias",
            KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT
        )
            .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
            .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
            .setKeySize(256)
            .build()
    )
    return keyGenerator.generateKey()
}
```

> **Warning:**
>
> When you encrypt a Room database with SQLCipher, the passphrase must itself be stored in the Android Keystore — never hard-coded. A hard-coded passphrase defeats the entire encryption, since anyone who decompiles the APK reads it straight out.

## Cryptography Fundamentals

Before diving into TLS and certificates, two foundational concepts underpin everything in this section.

### Symmetric vs Asymmetric Encryption

| Property | Symmetric | Asymmetric |
| --- | --- | --- |
| **Keys** | One shared secret key | Public key + private key pair |
| **Speed** | Very fast (hardware-accelerated) | 100–1000× slower |
| **Key exchange problem** | How do two parties agree on the shared key securely? | Solved: encrypt with public key, only private key can decrypt |
| **Common algorithms** | AES-128, AES-256 | RSA-2048/4096, ECDSA (P-256), ECDH |
| **Use in practice** | Bulk data encryption (file, stream) | Key exchange, digital signatures |

In practice, you never encrypt large amounts of data with asymmetric crypto — it is too slow. Instead, you use asymmetric crypto to securely exchange a symmetric key, then use the symmetric key to encrypt the actual data. This hybrid approach is exactly what TLS does.

### Digital Signatures

A digital signature proves that a message came from a specific party and was not modified:

```
Signing:    hash(message) → encrypt with private key → signature
Verifying:  hash(message) → compare with decrypt(signature, public key)
```

If the hashes match, the message is authentic and unmodified. The sender's private key never leaves their possession — only the public key is shared.

---

## The TLS Handshake

TLS (Transport Layer Security) is what makes HTTPS secure. It solves three problems simultaneously: **confidentiality** (nobody can read the traffic), **integrity** (nobody can modify it undetected), and **authentication** (you are talking to who you think you are).

### TLS 1.3 Handshake (simplified)

```
Client                                          Server
  │                                               │
  ├─── ClientHello ──────────────────────────────►│
  │    (TLS version, cipher suites, client random,│
  │     key_share for ECDH)                       │
  │                                               │
  │◄─── ServerHello ──────────────────────────────┤
  │     (chosen cipher suite, server random,      │
  │      key_share for ECDH)                      │
  │                                               │
  │  [Both sides now compute the session key      │
  │   using ECDH: shared_secret = client_priv ×   │
  │   server_pub = server_priv × client_pub]      │
  │                                               │
  │◄─── Certificate ──────────────────────────────┤
  │     (server's cert chain)                     │
  │◄─── CertificateVerify ────────────────────────┤
  │     (signature proving server owns the cert)  │
  │◄─── Finished (encrypted) ─────────────────────┤
  │                                               │
  ├─── Finished (encrypted) ─────────────────────►│
  │                                               │
  ═══════ Encrypted application data ════════════
```

Key points:
- **ECDH key exchange**: neither side ever transmits the shared secret — both sides derive the same key independently from their public values and each other's public key
- **Forward secrecy**: a new ephemeral ECDH key pair is generated for every session; compromising the server's long-term private key later does not decrypt past sessions
- **TLS 1.3 reduces to 1 round-trip** (vs 2 in TLS 1.2), making it both faster and more secure
- **TLS 1.0 and 1.1 are deprecated** and blocked by Android 10+ by default

### Enforcing Strong TLS in Android

*Network Security Config — block cleartext and weak TLS*

```xml
<!-- res/xml/network_security_config.xml -->
<network-security-config>
    <base-config cleartextTrafficPermitted="false">
        <trust-anchors>
            <certificates src="system"/>   <!-- system CAs only, no user-installed -->
        </trust-anchors>
    </base-config>
</network-security-config>
```

*OkHttp — enforce TLS 1.2/1.3 and strong cipher suites*

```kotlin
val tlsSpec = ConnectionSpec.Builder(ConnectionSpec.MODERN_TLS)
    .tlsVersions(TlsVersion.TLS_1_3, TlsVersion.TLS_1_2)  // block 1.0 / 1.1
    .cipherSuites(
        CipherSuite.TLS_AES_256_GCM_SHA384,         // TLS 1.3
        CipherSuite.TLS_CHACHA20_POLY1305_SHA256,   // TLS 1.3
        CipherSuite.TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384,  // TLS 1.2
        CipherSuite.TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384     // TLS 1.2
    )
    .build()

val client = OkHttpClient.Builder()
    .connectionSpecs(listOf(tlsSpec))
    .build()
```

---

## Certificate Chains & CA Hierarchy

A TLS certificate is not trusted in isolation — it is trusted because it is part of a **chain** that roots at a Certificate Authority (CA) your device trusts.

```
Root CA (self-signed, in device trust store)
    └── Intermediate CA (signed by Root CA)
            └── Server certificate (signed by Intermediate CA, contains your domain)
```

### How Trust Is Established

1. The server sends its certificate chain (its own cert + intermediate CA cert) during the TLS handshake
2. The client walks the chain: each certificate is verified against the signature of the one above it
3. The chain must terminate at a **Root CA** already in the device's trust store (`/system/etc/security/cacerts/`)
4. The server certificate's **Subject Alternative Name (SAN)** field must include the hostname being connected to

If any step fails — expired cert, unknown root CA, wrong hostname — the connection is rejected with an SSL error.

### Types of Certificates

| Type | Validation | Use for |
| --- | --- | --- |
| **DV (Domain Validated)** | Automated — just proves domain control | Most HTTPS sites; issued in minutes |
| **OV (Organisation Validated)** | Manual — CA checks org identity | Business sites |
| **EV (Extended Validation)** | Thorough — deep org verification | Financial institutions |
| **Wildcard** | Covers `*.domain.com` | All subdomains with one cert |
| **SAN (Multi-domain)** | Lists multiple hostnames in cert | Multiple domains on one cert |

### Certificate Transparency (CT)

Certificate Transparency is a public, append-only log of every certificate issued. Browsers and Android (since Android 7) enforce that certificates for publicly-trusted domains must appear in a CT log. This prevents a rogue CA from silently issuing a certificate for your domain without you knowing.

---

## Network Security — Certificate Pinning

Network communication is a primary attack vector. All transmitted data must be encrypted (HTTPS, never HTTP for sensitive data) and authenticated. Certificate pinning defends against man-in-the-middle attacks even when a certificate authority is compromised.

### What to Pin: Public Key Hash (SPKI) vs Certificate Hash

| Pin type | Survives cert renewal? | Survives key rotation? |
| --- | --- | --- |
| **Certificate hash** | No — cert changes on renewal | No |
| **Public key hash (SPKI)** | Yes — same key, new cert | No (intentionally) |

Pin the **SubjectPublicKeyInfo (SPKI) hash** — the SHA-256 of the public key. As long as the server renews its certificate with the same key pair, your pin remains valid.

```bash
# Extract the SPKI hash from a live server (openssl required)
openssl s_client -connect api.yourapp.com:443 -servername api.yourapp.com \
  < /dev/null 2>/dev/null \
  | openssl x509 -pubkey -noout \
  | openssl pkey -pubin -outform der \
  | openssl dgst -sha256 -binary \
  | base64
```

### Network Security Config — pinning

```xml
<!-- res/xml/network_security_config.xml -->
<network-security-config>
    <base-config cleartextTrafficPermitted="false">
        <trust-anchors>
            <certificates src="system"/>
            <!-- Do NOT include src="user" — blocks Charles/Fiddler MitM in production -->
        </trust-anchors>
    </base-config>
    <domain-config>
        <domain includeSubdomains="true">api.yourapp.com</domain>
        <pin-set expiration="2027-01-01">  <!-- expiration is mandatory -->
            <pin digest="SHA-256">primaryKeyHash==</pin>
            <pin digest="SHA-256">backupKeyHash==</pin>  <!-- ALWAYS include backup -->
        </pin-set>
    </domain-config>
</network-security-config>
```

The `expiration` date on `<pin-set>` is a deliberate forcing function: when the date passes, pinning is disabled and the app falls back to normal CA validation. This prevents users being permanently locked out if you lose your keys and can't ship an update. Set it 6–12 months out and rotate before it expires.

> **Never** include `<certificates src="user"/>` in your base-config in a production build. That is what allows testing tools like Charles to intercept traffic; shipping it means any user who installs a certificate into their device's user store can MITM your app.

*OkHttp certificate pinning*

```kotlin
val certificatePinner = CertificatePinner.Builder()
    .add("api.yourapp.com", "sha256/primaryKeyHash==")
    .add("api.yourapp.com", "sha256/backupKeyHash==")  // backup — never skip this
    .build()

val client = OkHttpClient.Builder()
    .certificatePinner(certificatePinner)
    .build()
```

> **Avoid:**
>
> Never write a custom TrustManager that trusts all certificates. It is one of the most common and dangerous Android mistakes — typically added to silence a development error and then accidentally shipped, leaving every user open to interception.

---

## Device Identification

Device IDs are used for analytics, fraud detection, and personalisation. Android has progressively restricted access to stable hardware identifiers to protect user privacy.

| Identifier | Stability | Access since Android 10 |
| --- | --- | --- |
| **IMEI** | Permanent (hardware) | Requires `READ_PRIVILEGED_PHONE_STATE` — system apps only |
| **Serial number** | Permanent (hardware) | Same — unavailable to third-party apps |
| **MAC address** | Randomised per network since Android 10 | Not a reliable identifier |
| **`ANDROID_ID`** | Scoped per app + signing key + user | Available; resets on factory reset |
| **Advertising ID (AAID)** | Resettable by user | Via Google Play Services; user can opt out |

The recommended identifier for most apps is `ANDROID_ID`:

```kotlin
val androidId = Settings.Secure.getString(
    contentResolver,
    Settings.Secure.ANDROID_ID
)
```

Since Android 8.0, `ANDROID_ID` is scoped per **app signing certificate + user + device** — two apps signed with different keys see different values for the same device. This prevents cross-app tracking while still giving a stable per-app identifier.

For apps that must identify the device regardless of reinstall (e.g., fraud detection), the **Play Integrity API** provides a cryptographically-attested device verdict that is verified server-side.

## Input Validation & SQL Injection Prevention

This is Practice 1 made concrete. Never trust user input; validate, sanitise, and escape it before processing or storing. The Android equivalent of the Bobby Tables example is a raw Room query built by string concatenation.

*Room parameterized queries auto-escape input*

```kotlin
// BAD -- string concatenation is a SQL injection hole
val sql = "SELECT * FROM users WHERE name = '$query'"
// Attack: query = "'; DROP TABLE users; --"

// GOOD -- Room parameterizes and escapes automatically
@Dao
interface UserDao {
    @Query("SELECT * FROM users WHERE name = :query")
    suspend fun searchUsers(query: String): List<User>
}
```

*WebView — disable what you don't need*

```kotlin
webView.settings.apply {
    javaScriptEnabled = false           // enable ONLY if truly needed
    allowFileAccess = false
    allowContentAccess = false
    allowFileAccessFromFileURLs = false
    allowUniversalAccessFromFileURLs = false
}
// If JavaScript is required, whitelist trusted domains in a WebViewClient.
```

## Cryptography Best Practices

Use well-tested cryptographic libraries; never implement your own algorithm. The recommended approach is AES-GCM with a 256-bit key managed by the Android Keystore. AES-GCM provides both confidentiality and integrity in a single operation.

*AES-GCM encryption with the Android Keystore*

```kotlin
object CryptoManager {
    private const val TRANSFORMATION = "AES/GCM/NoPadding"

    fun encrypt(data: String): EncryptedData {
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.ENCRYPT_MODE, getKey())
        val encrypted = cipher.doFinal(data.toByteArray(Charsets.UTF_8))
        return EncryptedData(
            ciphertext = Base64.encodeToString(encrypted, Base64.NO_WRAP),
            iv = Base64.encodeToString(cipher.iv, Base64.NO_WRAP)
        )
    }
}
data class EncryptedData(val ciphertext: String, val iv: String)
```

---

← [Previous: Core Principles](../01-core-principles/) · [↑ Chapter Index](../) · [Next: Hardening & Checklist →](../03-hardening-checklist/)
