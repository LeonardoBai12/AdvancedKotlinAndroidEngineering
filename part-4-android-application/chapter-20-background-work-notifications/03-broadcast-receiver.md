---
layout: page
title: "Chapter 20: Background Work & Notifications — BroadcastReceiver"
---

## Section 2 · BroadcastReceiver — Deep Dive

*System signals, custom events, and the rules for surviving Android 8+ broadcast restrictions*

---

## What Is a BroadcastReceiver?

A `BroadcastReceiver` is an Android component that receives and reacts to `Intent`-based messages broadcast by the system or other apps. It is the listener side of Android's publish-subscribe messaging bus.

Typical system broadcasts:

| Action constant | When it fires |
| --- | --- |
| `Intent.ACTION_BOOT_COMPLETED` | After the device finishes booting |
| `Intent.ACTION_BATTERY_LOW` | Battery drops below the system threshold |
| `ConnectivityManager.CONNECTIVITY_ACTION` | Network connectivity changed (legacy) |
| `Intent.ACTION_AIRPLANE_MODE_CHANGED` | Airplane mode toggled |
| `Intent.ACTION_PACKAGE_ADDED` | A new app was installed |
| `Intent.ACTION_LOCALE_CHANGED` | System language changed |
| `Intent.ACTION_TIME_CHANGED` / `TIMEZONE_CHANGED` | Clock or timezone changed |

*Android Developers — Broadcasts overview*

---

## Static vs Dynamic Registration

### Static (Manifest-Declared)

Declared in `AndroidManifest.xml`. The system can deliver the broadcast even when the app has never been launched.

```xml
<receiver
    android:name=".BootReceiver"
    android:exported="false">
    <intent-filter>
        <action android:name="android.intent.action.BOOT_COMPLETED" />
    </intent-filter>
</receiver>

<uses-permission android:name="android.permission.RECEIVE_BOOT_COMPLETED" />
```

```kotlin
class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Intent.ACTION_BOOT_COMPLETED) return
        // Re-schedule WorkManager periodic jobs — they survive reboots
        // but their schedule entry does not; re-enqueue here
        WorkManager.getInstance(context).enqueueUniquePeriodicWork(
            "hourly-sync",
            ExistingPeriodicWorkPolicy.KEEP,
            PeriodicWorkRequestBuilder<SyncWorker>(1, TimeUnit.HOURS).build()
        )
    }
}
```

### Dynamic (Code-Registered)

Registered programmatically. Only receives broadcasts while registered; unregistering stops delivery.

```kotlin
class MainActivity : ComponentActivity() {

    private val downloadReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) {
            val id = intent.getLongExtra(DownloadManager.EXTRA_DOWNLOAD_ID, -1L)
            handleDownloadComplete(id)
        }
    }

    override fun onStart() {
        super.onStart()
        val filter = IntentFilter(DownloadManager.ACTION_DOWNLOAD_COMPLETE)
        registerReceiver(downloadReceiver, filter)
    }

    override fun onStop() {
        super.onStop()
        unregisterReceiver(downloadReceiver)
    }
}
```

> **Android 13+ (API 33):** `registerReceiver` requires an `RECEIVER_EXPORTED` or `RECEIVER_NOT_EXPORTED` flag for receivers that handle implicit broadcasts, to prevent third-party apps from sending unexpected intents.

```kotlin
// API 33+
registerReceiver(
    downloadReceiver,
    IntentFilter(DownloadManager.ACTION_DOWNLOAD_COMPLETE),
    Context.RECEIVER_NOT_EXPORTED   // only receive from our own app
)
```

---

## The Android 8+ Implicit Broadcast Restrictions

Android 8.0 (API 26) introduced a major restriction: **manifest-declared receivers can no longer receive most implicit broadcasts**. If a broadcast is implicit (no specific target component), and you declare the receiver in the manifest, the system will not deliver it.

*Android Developers — Background Execution Limits*

Exceptions that still work with manifest receivers (explicit list in official docs):

| Action | Why it's exempt |
| --- | --- |
| `ACTION_BOOT_COMPLETED` | Device startup — no app is running to register dynamically |
| `ACTION_LOCKED_BOOT_COMPLETED` | Direct Boot completion |
| `ACTION_MY_PACKAGE_REPLACED` | App update — app isn't running yet |
| `ACTION_LOCALE_CHANGED` | Language change — every app must update resources |
| `ACTION_TIMEZONE_CHANGED` / `TIME_CHANGED` | System time signals |
| `ACTION_NEW_OUTGOING_CALL` | Phone subsystem |

For **everything else** (including `CONNECTIVITY_ACTION`), register dynamically while the app is running, or use `WorkManager` with a network constraint.

| Approach | Works on API 26+? |
| --- | --- |
| Static manifest receiver for implicit broadcast | No — silently ignored |
| Dynamic receiver for implicit broadcast | Yes |
| WorkManager with `NetworkType.CONNECTED` constraint | Yes — preferred |

---

## `onReceive()` Threading Rules

`onReceive()` runs on the **main thread** with a **10-second deadline**. Any ANR risk, I/O, or network call must be handed off immediately.

```kotlin
// WRONG — blocks the main thread
class BadReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val data = api.fetchSync()   // ANR risk
        db.insert(data)              // ANR risk
    }
}
```

### Option 1: Delegate to WorkManager (preferred)

```kotlin
class ConnectivityReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        WorkManager.getInstance(context)
            .enqueueUniqueWork(
                "sync-on-connect",
                ExistingWorkPolicy.KEEP,
                OneTimeWorkRequestBuilder<SyncWorker>().build()
            )
    }
}
```

### Option 2: `goAsync()` for short coroutine work

`goAsync()` extends the 10-second deadline by returning a `PendingResult`. You must call `pendingResult.finish()` when the work completes, or the system assumes you abandoned the broadcast.

```kotlin
class DataReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val pendingResult = goAsync()

        CoroutineScope(Dispatchers.IO).launch {
            try {
                processIntentData(intent)
            } finally {
                pendingResult.finish()   // MANDATORY — or the process may be killed
            }
        }
    }
}
```

> `goAsync()` is appropriate for short bursts of work (a few seconds). For anything that could take more than a few seconds, use WorkManager.

---

## Sending Custom Broadcasts

### App-internal broadcasts (preferred)

For events within your own process, use explicit intents or — far better — a `MutableSharedFlow` / `EventBus`. They are fast, type-safe, and do not cross process boundaries.

### App-internal broadcasts via `sendBroadcast`

```kotlin
// Sender
val intent = Intent("com.example.ACTION_SYNC_COMPLETE").apply {
    setPackage(packageName)   // make it explicit to your app only
    putExtra("count", 42)
}
context.sendBroadcast(intent)

// Receiver
class SyncCompleteReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val count = intent.getIntExtra("count", 0)
        // update UI or trigger next step
    }
}
```

### Ordered broadcasts

`sendOrderedBroadcast` delivers the intent to receivers one at a time in priority order. Each receiver can pass a result to the next, or abort the chain entirely.

```kotlin
context.sendOrderedBroadcast(intent, null)

class PriorityReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        setResult(Activity.RESULT_OK, "processed", null)   // pass result to next
        // abortBroadcast()   // stop delivery to lower-priority receivers
    }
}
```

---

## Security Considerations

**Always set `android:exported="false"`** for receivers that should only be triggered by your own app. If a receiver must accept intents from the system (e.g., `BOOT_COMPLETED`), it must be exported, but use permissions to gate it:

```xml
<receiver
    android:name=".SensitiveReceiver"
    android:exported="true"
    android:permission="com.example.CUSTOM_PERMISSION">
    <intent-filter>
        <action android:name="com.example.SECURE_ACTION" />
    </intent-filter>
</receiver>
```

Only senders who hold `com.example.CUSTOM_PERMISSION` can deliver intents to this receiver.

For dynamically registered receivers on Android 13+, always use `RECEIVER_NOT_EXPORTED` unless you deliberately want to accept broadcasts from other apps.

---

## BroadcastReceiver vs Alternatives

| Need | Preferred tool |
| --- | --- |
| React to system event, trigger background work | BroadcastReceiver → WorkManager |
| React to system event while app is foreground | BroadcastReceiver (dynamic) or `ConnectivityManager.NetworkCallback` |
| App-internal events across components | `SharedFlow` or `StateFlow` via ViewModel |
| Work that must complete even if app dies | WorkManager (not BroadcastReceiver alone) |
| Immediate reaction within the same process | Coroutines / callbacks — skip BroadcastReceiver entirely |

> **Interview Tip:**
>
> When asked "how would you restart your background sync after a reboot?", the answer is: static `BroadcastReceiver` listening for `BOOT_COMPLETED` → re-enqueue `WorkManager` periodic work. The receiver wakes the app; WorkManager persists and executes the actual work with its full constraint and retry machinery.

---

## ConnectivityManager.NetworkCallback — the Modern Replacement

`CONNECTIVITY_ACTION` is deprecated since Android 7 (API 24) and cannot be received by manifest receivers since Android 8 (API 26). The modern alternative is `ConnectivityManager.NetworkCallback`, a callback-based API that delivers fine-grained, real-time network events without any Intent overhead.

### Registering a NetworkCallback

```kotlin
class NetworkMonitor(private val context: Context) {

    private val connectivityManager =
        context.getSystemService(ConnectivityManager::class.java)

    private val networkCallback = object : ConnectivityManager.NetworkCallback() {
        override fun onAvailable(network: Network) {
            // A network satisfying our request became available
            // Runs on a background thread — post to Main if you need to update UI
        }

        override fun onLost(network: Network) {
            // The network we were using was lost
        }

        override fun onCapabilitiesChanged(
            network: Network,
            networkCapabilities: NetworkCapabilities
        ) {
            val hasInternet = networkCapabilities
                .hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
            val isValidated = networkCapabilities
                .hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED)
            val isUnmetered = networkCapabilities
                .hasCapability(NetworkCapabilities.NET_CAPABILITY_NOT_METERED)
        }

        override fun onLinkPropertiesChanged(network: Network, linkProperties: LinkProperties) {
            // DNS servers, routes, proxy changed
        }
    }

    fun startMonitoring() {
        val request = NetworkRequest.Builder()
            .addCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
            .addTransportType(NetworkCapabilities.TRANSPORT_WIFI)
            .addTransportType(NetworkCapabilities.TRANSPORT_CELLULAR)
            .build()

        connectivityManager.registerNetworkCallback(request, networkCallback)
    }

    fun stopMonitoring() {
        connectivityManager.unregisterNetworkCallback(networkCallback)   // must call to avoid leaks
    }
}
```

### Checking current connectivity synchronously

```kotlin
fun isConnected(context: Context): Boolean {
    val cm = context.getSystemService(ConnectivityManager::class.java)
    val network = cm.activeNetwork ?: return false
    val caps = cm.getNetworkCapabilities(network) ?: return false
    return caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET) &&
           caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED)
}
```

> `NET_CAPABILITY_VALIDATED` means the system actually verified internet reachability (probed Google's connectivity check). A network can have `INTERNET` capability but still be a captive portal or an offline Wi-Fi with no real connectivity — `VALIDATED` catches that.

### Wrapping as a Flow (Kotlin-idiomatic)

```kotlin
fun Context.networkStatusFlow(): Flow<Boolean> = callbackFlow {
    val cm = getSystemService(ConnectivityManager::class.java)

    val callback = object : ConnectivityManager.NetworkCallback() {
        override fun onAvailable(network: Network) { trySend(true) }
        override fun onLost(network: Network)      { trySend(false) }
    }

    val request = NetworkRequest.Builder()
        .addCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
        .build()

    cm.registerNetworkCallback(request, callback)

    // emit the current state immediately on collection
    val current = cm.activeNetwork?.let {
        cm.getNetworkCapabilities(it)
            ?.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
    } ?: false
    trySend(current)

    awaitClose { cm.unregisterNetworkCallback(callback) }
}

// Collect in ViewModel
viewModelScope.launch {
    context.networkStatusFlow()
        .distinctUntilChanged()
        .collect { online -> if (online) syncRepository.sync() }
}
```

### NetworkCallback vs CONNECTIVITY_ACTION vs WorkManager

| Approach | Scope | Precision | Background (app killed)? |
| --- | --- | --- | --- |
| `CONNECTIVITY_ACTION` broadcast | Legacy (deprecated API 28) | Coarse | No (blocked on API 26+) |
| `NetworkCallback` | App is running | Fine-grained (per network, per capability) | No — callback dies with process |
| WorkManager `NetworkType` constraint | Background + foreground | Coarse (connected / unmetered) | Yes — survives process death |

The pattern for full coverage: `NetworkCallback` for real-time UI reactions while the app is running, WorkManager constraint for deferred background work that must succeed even when the app is killed.

---

← [Previous: WorkManager](../02-workmanager/) · [↑ Chapter Index](../) · [Next: Notifications →](../04-notifications/)
