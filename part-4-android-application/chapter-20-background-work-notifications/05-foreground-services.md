---
layout: page
title: "Chapter 20: Background Work & Notifications — Foreground Services"
---

## Section 4 · Foreground Services

*Long-running, user-visible background work — lifecycle, types, Android 14 enforcement, and when to use one*

---

## What Is a Foreground Service?

A **Foreground Service** is a `Service` that performs work the user is actively aware of and has agreed to keep running. The system signals this with a **persistent, non-dismissible notification** in the status bar. In exchange, the system treats the process with high priority — it is the last candidate for memory reclamation, and it is exempt from the background process limits introduced in Android 8.0.

The key contract: the user can always see that your app is doing something, and they can stop it. This is the philosophical and legal basis for the permission.

*Android Developers — Foreground services overview*

---

## When to Use a Foreground Service

| Scenario | Right tool |
| --- | --- |
| Playing music while the screen is off | Foreground Service (`mediaPlayback`) |
| Tracking GPS position for navigation | Foreground Service (`location`) |
| Uploading a large file the user triggered | Foreground Service (`dataSync`) |
| Recording a call or screen | Foreground Service (`phoneCall` / `camera`) |
| Syncing data on a schedule in background | WorkManager (not a Foreground Service) |
| Short burst of work when network arrives | WorkManager |
| Work triggered by a push notification | FCM handler + coroutine |

A Foreground Service is **not** a substitute for WorkManager. WorkManager is for deferrable, guaranteed work. A Foreground Service is for work that is happening **right now**, is user-initiated, and must be visible.

---

## Foreground Service Types (Android 10+ / enforced Android 14)

Every foreground service must declare a `foregroundServiceType` in the manifest. Android 10 (API 29) introduced types as optional metadata; Android 14 (API 34) **made them mandatory** — the system throws `MissingForegroundServiceTypeException` if a service calls `startForeground()` without a declared type.

```xml
<!-- AndroidManifest.xml -->
<service
    android:name=".MusicService"
    android:foregroundServiceType="mediaPlayback"
    android:exported="false" />
```

### All foreground service types

| Type | Manifest value | Required permission (API 34+) | Use case |
| --- | --- | --- | --- |
| Media playback | `mediaPlayback` | None extra | Music, podcast, audiobook players |
| Media projection | `mediaProjection` | `FOREGROUND_SERVICE_MEDIA_PROJECTION` | Screen recording, casting |
| Location | `location` | `ACCESS_FINE_LOCATION` or `ACCESS_COARSE_LOCATION` | Navigation, fitness tracking |
| Camera | `camera` | `CAMERA` | Video calling, scanning |
| Microphone | `microphone` | `RECORD_AUDIO` | Voice recording, voice calls |
| Phone call | `phoneCall` | `MANAGE_OWN_CALLS` or `CALL_PHONE` | VoIP, call management apps |
| Data sync | `dataSync` | None extra | Large file upload/download, data export |
| Remote messaging | `remoteMessaging` | None extra | Messaging apps receiving/processing messages |
| Health | `health` | `BODY_SENSORS` or activity permissions | Workout tracking, heart rate monitoring |
| Connected device | `connectedDevice` | Bluetooth / USB permissions | Wearable sync, car connectivity |
| Special use | `specialUse` | `FOREGROUND_SERVICE_SPECIAL_USE` | Niche use cases not covered by other types |
| Short service | `shortService` | None extra | Time-limited, brief work (≤ 3 minutes, Android 14+) |

*Android Developers — Foreground service types reference*

A service can combine multiple types with `|`:

```xml
<service
    android:name=".RecordingService"
    android:foregroundServiceType="camera|microphone"
    android:exported="false" />
```

And the call to `startForeground` on API 29+ must pass the type flag(s):

```kotlin
// API 29+
startForeground(
    NOTIFICATION_ID,
    buildNotification(),
    ServiceInfo.FOREGROUND_SERVICE_TYPE_CAMERA or
    ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE
)
```

---

## Required Permissions (Android 9+ / 14+)

Android 9 (API 28) introduced `FOREGROUND_SERVICE`, a normal (auto-granted) permission:

```xml
<uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
```

Android 14 (API 34) added **type-specific** foreground service permissions — declared as normal permissions but each tied to a type. Without them the system throws `SecurityException` before the service starts:

```xml
<!-- For mediaProjection type -->
<uses-permission android:name="android.permission.FOREGROUND_SERVICE_MEDIA_PROJECTION" />
<!-- For camera type -->
<uses-permission android:name="android.permission.FOREGROUND_SERVICE_CAMERA" />
<!-- For microphone type -->
<uses-permission android:name="android.permission.FOREGROUND_SERVICE_MICROPHONE" />
<!-- For location type -->
<uses-permission android:name="android.permission.FOREGROUND_SERVICE_LOCATION" />
<!-- For health type -->
<uses-permission android:name="android.permission.FOREGROUND_SERVICE_HEALTH" />
<!-- For remoteMessaging type -->
<uses-permission android:name="android.permission.FOREGROUND_SERVICE_REMOTE_MESSAGING" />
<!-- For connectedDevice type -->
<uses-permission android:name="android.permission.FOREGROUND_SERVICE_CONNECTED_DEVICE" />
<!-- For dataSync type -->
<uses-permission android:name="android.permission.FOREGROUND_SERVICE_DATA_SYNC" />
<!-- For specialUse type -->
<uses-permission android:name="android.permission.FOREGROUND_SERVICE_SPECIAL_USE" />
```

---

## Lifecycle

A Foreground Service goes through the same lifecycle as a Started Service, plus the foreground state transitions:

```
startForegroundService(intent)
        │
        ▼
   onCreate()          ← called once when the service is first created
        │
        ▼
   onStartCommand()    ← called each time startForegroundService() is called
        │              ← must call startForeground() within 5 seconds (ANR if not)
        │
   [ running ]
        │
        ▼
   stopSelf() / stopService()
        │
        ▼
   onDestroy()         ← clean up: stop media player, release location, cancel jobs
```

```kotlin
class MusicService : Service() {

    private var mediaPlayer: MediaPlayer? = null

    override fun onCreate() {
        super.onCreate()
        mediaPlayer = MediaPlayer()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val track = intent?.getStringExtra("track_url") ?: return START_NOT_STICKY

        val notification = buildPlaybackNotification(track)
        // Must be called within 5 seconds of onStartCommand on most versions;
        // on Android 12+ the system enforces this strictly
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(
                NOTIFICATION_ID,
                notification,
                ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK
            )
        } else {
            startForeground(NOTIFICATION_ID, notification)
        }

        mediaPlayer?.apply {
            setDataSource(track)
            prepareAsync()
            setOnPreparedListener { start() }
        }

        return START_STICKY   // restart with the last intent if killed
    }

    override fun onBind(intent: Intent?): IBinder? = null   // not a bound service

    override fun onDestroy() {
        mediaPlayer?.release()
        mediaPlayer = null
        super.onDestroy()
    }
}
```

### START_ return values

| Return value | Behaviour after system kill |
| --- | --- |
| `START_STICKY` | Service is recreated; `onStartCommand` receives a null Intent — used for ongoing services that manage their own state (media player, location) |
| `START_NOT_STICKY` | Service is **not** recreated — used for services that handle discrete requests and do not need to resume (file upload, one-shot sync) |
| `START_REDELIVER_INTENT` | Service is recreated **and** `onStartCommand` receives the original Intent redelivered — used when the Intent contains critical data for the operation (e.g., a file URI) |

---

## Starting a Foreground Service

Since Android 8.0 (API 26), you **cannot** call `startService()` for a service that will become a foreground service while the app is in the background — the system throws `IllegalStateException`. Use `startForegroundService()` instead:

```kotlin
// Caller (Activity, Fragment, ViewModel)
val intent = Intent(context, MusicService::class.java).apply {
    putExtra("track_url", url)
}

if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
    context.startForegroundService(intent)
} else {
    context.startService(intent)
}
```

The service then **must** call `startForeground()` within 5 seconds, or the system raises an `ANR` crash.

---

## Stopping a Foreground Service

Call `stopForeground()` to demote the service to a background service (remove the notification) without stopping it, or `stopSelf()` / `stopService()` to stop it entirely.

```kotlin
// Demote to background — notification disappears, service keeps running
// Useful when the long-running work just finished but you need the service alive briefly
stopForeground(STOP_FOREGROUND_REMOVE)   // API 33+ flag; removes the notification
// or on older APIs:
// stopForeground(true)                 // true = remove notification (deprecated on API 33)

// Stop completely
stopSelf()
// or from outside:
// context.stopService(Intent(context, MusicService::class.java))
```

`STOP_FOREGROUND_DETACH` (API 33+) removes the service's ownership of the notification but lets the notification remain visible — useful for showing a "download complete" notification after stopping a download service.

---

## Updating the Foreground Notification

The notification is a live view into the service's state. Update it by posting to the same ID without restarting the service:

```kotlin
fun updateProgress(progress: Int, total: Int) {
    val updatedNotification = NotificationCompat.Builder(this, CHANNEL_ID)
        .setSmallIcon(R.drawable.ic_upload)
        .setContentTitle("Uploading…")
        .setProgress(total, progress, false)
        .setOngoing(true)
        .build()

    val nm = getSystemService(NotificationManager::class.java)
    nm.notify(NOTIFICATION_ID, updatedNotification)
    // No need to call startForeground() again — same ID, system updates in place
}
```

---

## Bound + Started Hybrid

A service can be both started (foreground) and bound simultaneously. This is the standard pattern for media players: the foreground service keeps playback alive, while the Activity binds to control it (play, pause, skip).

```kotlin
class MusicService : Service() {
    private val binder = MusicBinder()

    inner class MusicBinder : Binder() {
        fun getService(): MusicService = this@MusicService
    }

    // expose control interface to bound clients
    override fun onBind(intent: Intent?): IBinder = binder

    fun pause()  { mediaPlayer?.pause() }
    fun resume() { mediaPlayer?.start() }
    fun seekTo(ms: Int) { mediaPlayer?.seekTo(ms) }
}

// In Activity
private val connection = object : ServiceConnection {
    override fun onServiceConnected(name: ComponentName, service: IBinder) {
        musicService = (service as MusicService.MusicBinder).getService()
    }
    override fun onServiceDisconnected(name: ComponentName) {
        musicService = null
    }
}

override fun onStart() {
    super.onStart()
    bindService(Intent(this, MusicService::class.java), connection, BIND_AUTO_CREATE)
}

override fun onStop() {
    super.onStop()
    unbindService(connection)
}
```

The service lifecycle here: started via `startForegroundService` (keeps it alive even when no clients are bound), bound by the Activity (gives the Activity a control interface). The service only dies when `stopSelf()` is called — not when the Activity unbinds.

---

## Android 12: Background Activity Launch Restrictions

Android 12 (API 31) introduced stricter rules around which apps can start Foreground Services from the background. Apps that are fully background-restricted must use `WorkManager` with `setExpedited()` instead. Exceptions that are still allowed to start from background:

- App receives a high-priority FCM notification
- App is in the exact alarm allowlist
- App has `SYSTEM_ALERT_WINDOW` (special permission, Play policy governs this)
- The service is started by the system on behalf of the app (e.g., binding started by another foreground app)

*Android 12 — behavior changes: apps targeting API 31*

---

## Short Service (Android 14+)

`shortService` is a new type introduced in Android 14 for brief, urgent work that does not fit neatly into the other types. It runs for a maximum of **3 minutes** before the system stops it automatically. Unlike other foreground service types, it does not require type-specific permissions and does not need an associated notification.

```xml
<service
    android:name=".QuickExportService"
    android:foregroundServiceType="shortService"
    android:exported="false" />
```

```kotlin
class QuickExportService : Service() {
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        startForeground(
            NOTIFICATION_ID,
            buildQuickNotification(),
            ServiceInfo.FOREGROUND_SERVICE_TYPE_SHORT_SERVICE
        )
        // do quick work — max 3 minutes
        stopSelf()
        return START_NOT_STICKY
    }

    override fun onBind(intent: Intent?): IBinder? = null
}
```

---

## Common Pitfalls

- **Not calling `startForeground()` within 5 seconds** — the system throws a `ForegroundServiceDidNotStartInTimeException` (Android 12+) or causes an ANR.
- **Calling `startService()` instead of `startForegroundService()` from background** — `IllegalStateException` on API 26+.
- **Forgetting to declare `foregroundServiceType` on API 34** — `MissingForegroundServiceTypeException` at runtime.
- **Missing type-specific permission on API 34** — `SecurityException` before the service starts.
- **Not releasing resources in `onDestroy()`** — media player, location client, camera handle — if the service is killed without calling `onDestroy()`, resources leak at the process level.
- **Using a Foreground Service for deferrable work** — wastes battery, annoys users with persistent notifications; use WorkManager with `setExpedited()` instead.
- **Not stopping the service when work completes** — the persistent notification stays forever; always call `stopSelf()` when done.

---

← [Previous: Notifications](../04-notifications/) · [↑ Chapter Index](../) · [Next: Chapter 21 →](../../chapter-21-platform-constraints-push/)
