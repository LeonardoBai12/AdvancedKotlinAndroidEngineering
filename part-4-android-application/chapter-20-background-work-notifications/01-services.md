---
layout: default
title: "Chapter 20: Background Work & Notifications — Services"
parent: "Chapter 20: Background Work & Notifications"
nav_order: 1
---

## Section 1 · Services

*Android's long-running work primitive — types, lifecycle, IPC patterns, and when a coroutine is enough*

---

## What Is a Service?

A `Service` is an Android application component designed to perform operations in the background without a user interface. It runs in the main thread of its hosting process by default — it does not automatically create its own thread — and it can outlive any individual Activity.

There are three distinct kinds of Service in Android, each with a different lifecycle and purpose:

| Type | How started | Visible to user? | Survives app background? | Primary use |
| --- | --- | --- | --- | --- |
| **Started (background)** | `startService()` / `startForegroundService()` | No | Until stopped or system kills it | Fire-and-forget work initiated by the app |
| **Bound** | `bindService()` | No | Only while clients are bound | Client–server API within or across processes |
| **Foreground** | `startForegroundService()` + `startForeground()` | Yes — persistent notification | Until explicitly stopped | User-visible long-running work: music, navigation, upload |

A Service can be both Started and Bound simultaneously — the Started state keeps it alive; the Bound state gives clients a direct interface to control it.

*Android Developers — Services overview*

---

## The Service Lifecycle

### Started Service

```
Context.startService(intent)
        │
        ▼
   onCreate()           ← called once; set up resources here
        │
        ▼
   onStartCommand()     ← called every time startService() is called
        │               ← do NOT do long work here; it runs on the main thread
        │
   [ running ]
        │
   stopSelf()  or  Context.stopService()
        │
        ▼
   onDestroy()          ← release all resources
```

Every call to `startService()` delivers another Intent to `onStartCommand()`. The Service keeps running until `stopSelf()` or `stopService()` is called — not just until `onStartCommand()` returns.

### Bound Service

```
Context.bindService(intent, connection, BIND_AUTO_CREATE)
        │
        ▼
   onCreate()
        │
        ▼
   onBind()             ← return the IBinder that clients will receive
        │
   [ client holds IBinder ]
        │
   All clients unbind
        │
        ▼
   onUnbind()
        │
        ▼
   onDestroy()
```

A pure Bound Service (never started) is destroyed as soon as all clients unbind. If no client has bound and `BIND_AUTO_CREATE` was used, the service is never even created.

### Hybrid: Started + Bound

When a service is both started and bound, it lives until it is both stopped *and* all clients have unbound. This is the pattern used by media players — the service is started to keep music playing; the UI binds to control playback.

```
onCreate()
   ├─ onStartCommand()    ← keeps it alive
   └─ onBind()            ← gives UI a control interface

stopSelf()               ← transitions to "stopping"
last client unbinds      ← triggers onDestroy()
```

---

## `onStartCommand()` Return Values

The return value of `onStartCommand()` tells the system what to do if it kills the service due to memory pressure and then wants to restart it.

| Return value | Restart behaviour | Use case |
| --- | --- | --- |
| `START_STICKY` | Restarted; `onStartCommand` receives **null** Intent | Ongoing services that manage their own state (music player, location tracker) |
| `START_NOT_STICKY` | **Not** restarted automatically | Services handling discrete, re-triggerable requests — a missed restart is acceptable |
| `START_REDELIVER_INTENT` | Restarted; `onStartCommand` receives the **original** Intent re-delivered | Services where the Intent carries critical data (e.g., a file URI to process) |

```kotlin
override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
    val action = intent?.action

    when (action) {
        ACTION_START -> startWork()
        ACTION_STOP  -> { stopWork(); stopSelf(startId) }  // stopSelf(startId) only stops
    }                                                       // if no newer startId is pending

    return START_STICKY
}
```

---

## Started Service — Full Example

A started service that performs background work using a coroutine. Because `onStartCommand` runs on the main thread, the actual work is always dispatched to a background dispatcher.

```kotlin
class DataExportService : Service() {

    private val serviceScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    override fun onCreate() {
        super.onCreate()
        // one-time initialisation
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val exportId = intent?.getStringExtra("export_id")
            ?: return START_NOT_STICKY

        serviceScope.launch {
            try {
                exportRepository.export(exportId)
            } finally {
                stopSelf(startId)   // stop after this specific request completes
            }
        }

        return START_NOT_STICKY   // don't restart if killed; caller can re-trigger
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        serviceScope.cancel()     // cancel all in-flight coroutines
        super.onDestroy()
    }
}
```

```xml
<service
    android:name=".DataExportService"
    android:exported="false" />
```

> **Important:** Always cancel the `CoroutineScope` in `onDestroy()`. If the Service is killed before the coroutine finishes and the scope is not cancelled, the coroutine may continue running in a zombie state.

---

## Bound Service — Local Binder

The most common pattern for binding within the same process. The `Binder` subclass holds a reference to the Service, giving bound clients full access to its public API.

```kotlin
class MusicService : Service() {

    private val binder = MusicBinder()

    inner class MusicBinder : Binder() {
        fun getService(): MusicService = this@MusicService
    }

    // Public API for bound clients
    fun play(trackUrl: String) { /* ... */ }
    fun pause()                { /* ... */ }
    fun seekTo(positionMs: Int){ /* ... */ }
    fun getCurrentPosition(): Int = /* ... */ 0

    override fun onBind(intent: Intent?): IBinder = binder

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        // Also started so it survives when the Activity unbinds
        return START_STICKY
    }
}
```

```kotlin
// In Activity / Fragment
class PlayerActivity : ComponentActivity() {

    private var musicService: MusicService? = null
    private var isBound = false

    private val connection = object : ServiceConnection {
        override fun onServiceConnected(name: ComponentName, binder: IBinder) {
            musicService = (binder as MusicService.MusicBinder).getService()
            isBound = true
            updateUI()
        }

        override fun onServiceDisconnected(name: ComponentName) {
            // Called when the service crashes or is killed unexpectedly
            musicService = null
            isBound = false
        }
    }

    override fun onStart() {
        super.onStart()
        Intent(this, MusicService::class.java).also { intent ->
            bindService(intent, connection, Context.BIND_AUTO_CREATE)
        }
    }

    override fun onStop() {
        super.onStop()
        if (isBound) {
            unbindService(connection)
            isBound = false
        }
    }

    fun onPlayClicked() {
        musicService?.play(currentTrackUrl)
    }
}
```

---

## Bound Service — Messenger (Cross-Process, Simple)

`Messenger` wraps a `Handler` and allows passing `Message` objects across process boundaries using Binder IPC under the hood. It is simpler than AIDL but processes messages serially (one at a time), so it is appropriate for low-throughput IPC.

```kotlin
// In the Service process
class RemoteService : Service() {

    companion object {
        const val MSG_DO_WORK = 1
        const val MSG_GET_STATUS = 2
    }

    private val handler = object : Handler(Looper.getMainLooper()) {
        override fun handleMessage(msg: Message) {
            when (msg.what) {
                MSG_DO_WORK -> {
                    val data = msg.data.getString("payload")
                    doWork(data)
                    // Reply to the caller using the replyTo Messenger
                    val reply = Message.obtain(null, MSG_DO_WORK)
                    reply.data = bundleOf("result" to "done")
                    msg.replyTo?.send(reply)
                }
                MSG_GET_STATUS -> {
                    val reply = Message.obtain(null, MSG_GET_STATUS)
                    reply.arg1 = getCurrentStatus()
                    msg.replyTo?.send(reply)
                }
            }
        }
    }

    private val messenger = Messenger(handler)

    override fun onBind(intent: Intent?): IBinder = messenger.binder
}
```

```kotlin
// In the client process
class ClientActivity : ComponentActivity() {

    private var remoteMessenger: Messenger? = null

    private val replyHandler = object : Handler(Looper.getMainLooper()) {
        override fun handleMessage(msg: Message) {
            when (msg.what) {
                RemoteService.MSG_DO_WORK -> {
                    val result = msg.data.getString("result")
                    showResult(result)
                }
            }
        }
    }

    private val replyMessenger = Messenger(replyHandler)

    private val connection = object : ServiceConnection {
        override fun onServiceConnected(name: ComponentName, binder: IBinder) {
            remoteMessenger = Messenger(binder)
        }
        override fun onServiceDisconnected(name: ComponentName) {
            remoteMessenger = null
        }
    }

    fun sendWork(payload: String) {
        val msg = Message.obtain(null, RemoteService.MSG_DO_WORK).apply {
            data = bundleOf("payload" to payload)
            replyTo = replyMessenger   // where the service should send the reply
        }
        remoteMessenger?.send(msg)
    }
}
```

---

## Bound Service — AIDL (Cross-Process, Full IPC)

`AIDL` (Android Interface Definition Language) is for high-performance, concurrent cross-process communication. Unlike Messenger (serial), AIDL calls run concurrently — each call arrives on a thread from the Binder thread pool. The service must be thread-safe.

Define the interface in an `.aidl` file:

```aidl
// IDataService.aidl
package com.example.service;

interface IDataService {
    String processData(String input);
    int getQueueSize();
}
```

Android generates a `IDataService.Stub` class. Implement it in the Service:

```kotlin
class DataService : Service() {

    private val binder = object : IDataService.Stub() {
        // Runs on a Binder thread — must be thread-safe
        override fun processData(input: String): String {
            return dataProcessor.process(input)   // thread-safe operation
        }

        override fun getQueueSize(): Int = workQueue.size
    }

    override fun onBind(intent: Intent?): IBinder = binder
}
```

```kotlin
// In the client
private var dataService: IDataService? = null

private val connection = object : ServiceConnection {
    override fun onServiceConnected(name: ComponentName, binder: IBinder) {
        dataService = IDataService.Stub.asInterface(binder)
        // asInterface() returns a local proxy if same process, a remote proxy if cross-process
    }
    override fun onServiceDisconnected(name: ComponentName) {
        dataService = null
    }
}

fun doRemoteWork(input: String): String? {
    return dataService?.processData(input)   // blocks the calling thread until the remote returns
}
```

> AIDL calls from the client **block the calling thread**. Never call them on the main thread. Wrap them in a `withContext(Dispatchers.IO)` coroutine.

---

## `IntentService` — Deprecated, Historical Context

`IntentService` was the pre-coroutine solution for sequential background work in a started service. It automatically created a worker thread, processed Intents one at a time via `onHandleIntent()`, and stopped itself when the queue was empty.

```kotlin
// IntentService — deprecated in API 30
class OldSyncService : IntentService("OldSyncService") {
    override fun onHandleIntent(intent: Intent?) {
        // Ran on a background thread automatically
        syncRepository.sync()
    }
}
```

It is deprecated because `CoroutineWorker` in WorkManager does everything `IntentService` did, plus:

- Survives process death
- Supports retry and backoff
- Respects constraints (network, charging, idle)
- Has observable state
- Survives device reboot

The replacement for simple sequential background work is:

```kotlin
// Modern replacement
class SyncWorker(ctx: Context, params: WorkerParameters) : CoroutineWorker(ctx, params) {
    override suspend fun doWork(): Result {
        syncRepository.sync()
        return Result.success()
    }
}
```

---

## When to Use a Service vs Alternatives

| Scenario | Right choice | Why |
| --- | --- | --- |
| Short async work triggered by a user action | `viewModelScope.launch { }` | No overhead; tied to ViewModel lifecycle |
| Background work that must survive app death | WorkManager | Persistent, constraint-aware, retryable |
| Work visible to the user (music, download, navigation) | Foreground Service | Persistent notification; high-priority process |
| IPC interface to another process | Bound Service + AIDL | Binder IPC; the only way to call methods cross-process |
| IPC to another app module in the same process | Bound Service (local Binder) or Hilt-injected interface | Direct method call; no IPC overhead |
| React to a system event and do background work | BroadcastReceiver → WorkManager | Receiver wakes the app; WorkManager does the durable work |

> **Interview Tip:**
>
> A very common interview question is "when would you use a Service vs a coroutine?" The answer: use a coroutine when the work is tied to a UI component (ViewModel scope) or when the app is guaranteed to be in the foreground. Use a Service when the work must outlive any individual UI component and survive the app moving to the background — and then ask whether WorkManager or a Foreground Service is the right variant.

---

← [↑ Chapter Index](../) · [Next: WorkManager →](../02-workmanager/)
