# Chapter 15: Android Security — Data & Network Security

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

## Network Security

Network communication is a primary attack vector. All transmitted data must be encrypted (HTTPS, never HTTP for sensitive data) and authenticated. Certificate pinning defends against man-in-the-middle attacks even when a certificate authority is compromised.

*Network Security Config — no cleartext, pinned certs*

```kotlin
<!-- res/xml/network_security_config.xml -->
<network-security-config>
    <base-config cleartextTrafficPermitted="false">
        <trust-anchors><certificates src="system" /></trust-anchors>
    </base-config>
    <domain-config>
        <domain includeSubdomains="true">api.yourapp.com</domain>
        <pin-set expiration="2026-01-01">
            <pin digest="SHA-256">base64primaryHash==</pin>
            <pin digest="SHA-256">base64backupHash==</pin>  <!-- rotation -->
        </pin-set>
    </domain-config>
</network-security-config>
```

*OkHttp certificate pinning*

```kotlin
val certificatePinner = CertificatePinner.Builder()
    .add("api.yourapp.com", "sha256/AAAAAAAAAAAAAAAAAAAA==")
    .add("api.yourapp.com", "sha256/BBBBBBBBBBBBBBBBBBBB==")  // backup
    .build()

val client = OkHttpClient.Builder()
    .certificatePinner(certificatePinner)
    .build()
```

> **Avoid:**
>
> Never write a custom TrustManager that trusts all certificates. It is one of the most common and dangerous Android mistakes — typically added to silence a development error and then accidentally shipped, leaving every user open to interception.

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

← [Previous: Core Principles](./01-core-principles.md) · [↑ Chapter Index](./README.md) · [Next: Hardening & Checklist →](./03-hardening-checklist.md)
