---
layout: page
title: "Chapter 20: Background Work & Notifications — Notifications"
---

## Section 3 · Notifications

*Channels, styles, scheduling, permissions — the complete Android notification stack*

---

## Architecture Overview

Android's notification system has three layers:

1. **Notification Channel** — a category bucket that the user can configure independently (sound, vibration, importance). Required on Android 8.0+ (API 26). One app has one or more channels; the user controls each.
2. **Notification** — the individual alert built with `NotificationCompat.Builder`. It belongs to a channel.
3. **NotificationManager** — the system service that posts, updates, and cancels notifications.

```
App → NotificationManagerCompat → NotificationManager (system)
                                        │
                                  Channel (API 26+)
                                  importance / sound / vibration
                                        │
                                  Notification
                                  title / text / icon / actions / style
```

*Android Developers — Notifications overview*

---

## Notification Channels (API 26+)

Channels must be created before posting any notification. Creating a channel that already exists is a no-op, so it is safe to call at app startup.

```kotlin
object NotificationChannels {
    const val SYNC      = "sync_channel"
    const val ALERTS    = "alerts_channel"
    const val DOWNLOADS = "downloads_channel"
}

fun createChannels(context: Context) {
    val manager = context.getSystemService(NotificationManager::class.java)

    val syncChannel = NotificationChannel(
        NotificationChannels.SYNC,
        "Background Sync",
        NotificationManager.IMPORTANCE_LOW          // silent, no heads-up
    ).apply {
        description = "Periodic data synchronisation status"
        setShowBadge(false)
    }

    val alertsChannel = NotificationChannel(
        NotificationChannels.ALERTS,
        "Important Alerts",
        NotificationManager.IMPORTANCE_HIGH         // heads-up + sound
    ).apply {
        description = "Critical alerts that require your attention"
        enableLights(true)
        lightColor = Color.RED
        enableVibration(true)
    }

    val downloadsChannel = NotificationChannel(
        NotificationChannels.DOWNLOADS,
        "Downloads",
        NotificationManager.IMPORTANCE_DEFAULT
    )

    manager.createNotificationChannels(listOf(syncChannel, alertsChannel, downloadsChannel))
}
```

### Importance levels

| Importance constant | UI behaviour | Use when |
| --- | --- | --- |
| `IMPORTANCE_HIGH` | Heads-up banner + sound + vibration | Incoming call, urgent alert |
| `IMPORTANCE_DEFAULT` | Sound + status bar icon, no heads-up | New message, reminder |
| `IMPORTANCE_LOW` | Status bar icon only, no sound | Background sync progress |
| `IMPORTANCE_MIN` | No icon in status bar, no sound | Fully silent, informational |

> The user can override channel importance at any time in Settings → App Info → Notifications. You can set the initial importance, but you cannot force it back up after the user lowers it.

---

## Runtime Permission (Android 13+)

Android 13 (API 33) introduced `POST_NOTIFICATIONS`, a runtime permission. Without it, no notifications from your app appear.

```xml
<!-- AndroidManifest.xml -->
<uses-permission android:name="android.permission.POST_NOTIFICATIONS" />
```

```kotlin
// Request in an Activity or Fragment
private val requestPermissionLauncher =
    registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        if (!granted) {
            // show rationale or disable notification features
        }
    }

override fun onStart() {
    super.onStart()
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
        if (ContextCompat.checkSelfPermission(
                this, Manifest.permission.POST_NOTIFICATIONS
            ) != PackageManager.PERMISSION_GRANTED
        ) {
            requestPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
        }
    }
}
```

*Google — Notification runtime permission*

---

## Building a Notification

```kotlin
fun buildBasicNotification(context: Context): Notification {
    val tapIntent = Intent(context, MainActivity::class.java).apply {
        flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
    }
    val pendingIntent = PendingIntent.getActivity(
        context,
        0,
        tapIntent,
        PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
    )

    return NotificationCompat.Builder(context, NotificationChannels.ALERTS)
        .setSmallIcon(R.drawable.ic_notification)     // mandatory — 24×24 dp, alpha only
        .setContentTitle("Sync complete")
        .setContentText("42 items updated")
        .setSubText("Last sync")                      // third line of text (optional)
        .setContentIntent(pendingIntent)              // tap action
        .setAutoCancel(true)                          // dismiss on tap
        .setPriority(NotificationCompat.PRIORITY_DEFAULT)
        .build()
}

NotificationManagerCompat.from(context)
    .notify(NOTIFICATION_ID, notification)
```

> `PendingIntent.FLAG_IMMUTABLE` is required on Android 12+ (API 31). The `MUTABLE` flag is only needed when the system needs to fill in intent extras (e.g., inline reply actions).

---

## Notification Styles

Styles expand the notification to show richer content when the user swipes down.

### BigTextStyle

```kotlin
NotificationCompat.Builder(context, NotificationChannels.ALERTS)
    .setSmallIcon(R.drawable.ic_notification)
    .setContentTitle("Server error")
    .setContentText("An error occurred. Tap to see details.")
    .setStyle(
        NotificationCompat.BigTextStyle()
            .bigText("HTTP 503 Service Unavailable on /api/v2/sync. " +
                     "Retry scheduled in 15 minutes. Check server logs for details.")
            .setBigContentTitle("Server Error")
            .setSummaryText("api.example.com")
    )
    .build()
```

### BigPictureStyle

```kotlin
NotificationCompat.Builder(context, NotificationChannels.ALERTS)
    .setSmallIcon(R.drawable.ic_photo)
    .setContentTitle("Photo uploaded")
    .setStyle(
        NotificationCompat.BigPictureStyle()
            .bigPicture(bitmap)
            .bigLargeIcon(null as Bitmap?)   // hide the large icon when expanded
    )
    .build()
```

### InboxStyle — multiple lines

```kotlin
NotificationCompat.Builder(context, NotificationChannels.ALERTS)
    .setSmallIcon(R.drawable.ic_email)
    .setContentTitle("3 new messages")
    .setStyle(
        NotificationCompat.InboxStyle()
            .addLine("Alice: See you tomorrow")
            .addLine("Bob: The meeting is at 3pm")
            .addLine("Carol: Did you get my email?")
            .setSummaryText("+3 more")
    )
    .build()
```

### MessagingStyle — chat threads

```kotlin
val person = Person.Builder()
    .setName("Alice")
    .setIcon(IconCompat.createWithBitmap(avatarBitmap))
    .build()

NotificationCompat.Builder(context, NotificationChannels.ALERTS)
    .setSmallIcon(R.drawable.ic_message)
    .setStyle(
        NotificationCompat.MessagingStyle(person)
            .setConversationTitle("Team Chat")
            .addMessage("Deploy is done!", System.currentTimeMillis(), person)
            .addMessage("Tests passed!", System.currentTimeMillis() + 1000, person)
    )
    .build()
```

---

## Actions

Add up to three tappable action buttons.

```kotlin
val replyIntent = Intent(context, ReplyReceiver::class.java)
val replyPendingIntent = PendingIntent.getBroadcast(
    context, 0, replyIntent,
    PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_MUTABLE   // MUTABLE for inline reply
)

val remoteInput = RemoteInput.Builder("reply_key")
    .setLabel("Reply")
    .build()

val replyAction = NotificationCompat.Action.Builder(
    R.drawable.ic_reply, "Reply", replyPendingIntent
)
    .addRemoteInput(remoteInput)   // enables inline reply on API 24+
    .build()

NotificationCompat.Builder(context, NotificationChannels.ALERTS)
    .setSmallIcon(R.drawable.ic_message)
    .setContentTitle("New message from Alice")
    .setContentText("Are you free tomorrow?")
    .addAction(replyAction)
    .addAction(R.drawable.ic_mark_read, "Mark as read", markReadPendingIntent)
    .build()
```

---

## Notification Groups

Group related notifications under a summary so the status bar stays clean.

```kotlin
val GROUP_KEY = "com.example.EMAIL_GROUP"

// Individual notifications — same group key
val msg1 = NotificationCompat.Builder(context, NotificationChannels.ALERTS)
    .setSmallIcon(R.drawable.ic_email)
    .setContentTitle("Alice")
    .setContentText("See you tomorrow")
    .setGroup(GROUP_KEY)
    .build()

val msg2 = NotificationCompat.Builder(context, NotificationChannels.ALERTS)
    .setSmallIcon(R.drawable.ic_email)
    .setContentTitle("Bob")
    .setContentText("Meeting at 3pm")
    .setGroup(GROUP_KEY)
    .build()

// Summary notification — required on API 24+
val summary = NotificationCompat.Builder(context, NotificationChannels.ALERTS)
    .setSmallIcon(R.drawable.ic_email)
    .setContentTitle("2 new messages")
    .setGroup(GROUP_KEY)
    .setGroupSummary(true)                   // this is the stack header
    .setStyle(
        NotificationCompat.InboxStyle()
            .addLine("Alice: See you tomorrow")
            .addLine("Bob: Meeting at 3pm")
            .setSummaryText("your@email.com")
    )
    .build()

val nm = NotificationManagerCompat.from(context)
nm.notify(1, msg1)
nm.notify(2, msg2)
nm.notify(0, summary)    // summary must be posted
```

---

## Updating and Cancelling

```kotlin
val nm = NotificationManagerCompat.from(context)

// Update — use the same notification ID
nm.notify(NOTIFICATION_ID, updatedNotification)

// Cancel one
nm.cancel(NOTIFICATION_ID)

// Cancel all from this app
nm.cancelAll()
```

For progress bars, update the same ID with a new notification:

```kotlin
fun showProgress(context: Context, progress: Int, max: Int) {
    val notification = NotificationCompat.Builder(context, NotificationChannels.DOWNLOADS)
        .setSmallIcon(R.drawable.ic_download)
        .setContentTitle("Downloading…")
        .setProgress(max, progress, false)   // false = determinate
        .setOngoing(true)                    // user cannot swipe away
        .build()
    NotificationManagerCompat.from(context).notify(DOWNLOAD_NOTIFICATION_ID, notification)
}

fun completeDownload(context: Context) {
    val notification = NotificationCompat.Builder(context, NotificationChannels.DOWNLOADS)
        .setSmallIcon(R.drawable.ic_download_done)
        .setContentTitle("Download complete")
        .setProgress(0, 0, false)
        .setAutoCancel(true)
        .build()
    NotificationManagerCompat.from(context).notify(DOWNLOAD_NOTIFICATION_ID, notification)
}
```

---

## Scheduling Notifications

Android provides no dedicated "schedule a notification at time T" API. You choose between two approaches depending on timing precision and survivability requirements.

### Option 1: AlarmManager (exact, system-level)

For notifications that must fire at an exact time even when the app is not running. Requires the `SCHEDULE_EXACT_ALARM` (API 31+) or `USE_EXACT_ALARM` (API 33+) permission.

```kotlin
// Manifest
// <uses-permission android:name="android.permission.SCHEDULE_EXACT_ALARM" />
// or for API 33+:
// <uses-permission android:name="android.permission.USE_EXACT_ALARM" />

fun scheduleNotification(context: Context, triggerAtMillis: Long, notificationId: Int) {
    val intent = Intent(context, NotificationReceiver::class.java).apply {
        putExtra("notification_id", notificationId)
    }
    val pendingIntent = PendingIntent.getBroadcast(
        context,
        notificationId,
        intent,
        PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
    )

    val alarmManager = context.getSystemService(AlarmManager::class.java)
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S && alarmManager.canScheduleExactAlarms()) {
        alarmManager.setExactAndAllowWhileIdle(
            AlarmManager.RTC_WAKEUP,
            triggerAtMillis,
            pendingIntent
        )
    } else {
        alarmManager.setAndAllowWhileIdle(   // inexact but still fires in Doze
            AlarmManager.RTC_WAKEUP,
            triggerAtMillis,
            pendingIntent
        )
    }
}

// Receiver that posts the notification
class NotificationReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val id = intent.getIntExtra("notification_id", 0)
        val notification = buildReminderNotification(context)
        NotificationManagerCompat.from(context).notify(id, notification)
    }
}
```

*Android Developers — Schedule exact alarms*

### Option 2: WorkManager (deferrable, battery-friendly)

For notifications that do not need to fire at an exact millisecond — reminders, digest notifications, or daily summaries. WorkManager respects Doze and battery optimisation, so the actual trigger time may be slightly later than requested.

```kotlin
class DailyDigestWorker(ctx: Context, params: WorkerParameters)
    : CoroutineWorker(ctx, params) {

    override suspend fun doWork(): Result {
        val digest = repository.buildDailyDigest()
        val notification = buildDigestNotification(applicationContext, digest)
        NotificationManagerCompat.from(applicationContext)
            .notify(DIGEST_NOTIFICATION_ID, notification)
        return Result.success()
    }
}

// Schedule to run approximately every day
WorkManager.getInstance(context).enqueueUniquePeriodicWork(
    "daily-digest",
    ExistingPeriodicWorkPolicy.KEEP,
    PeriodicWorkRequestBuilder<DailyDigestWorker>(1, TimeUnit.DAYS)
        .setInitialDelay(hoursUntilMorning(), TimeUnit.HOURS)
        .build()
)
```

### Choosing between them

| Requirement | AlarmManager | WorkManager |
| --- | --- | --- |
| Must fire at exact time | Yes | No — may be deferred |
| Survives device reboot | Only if re-registered after `BOOT_COMPLETED` | Yes — automatic |
| Respects Doze mode | `setExactAndAllowWhileIdle` wakes from Doze | Yes — WorkManager is Doze-aware |
| Battery impact | High if used frequently | Low — batched by OS |
| Requires extra permission | Yes (API 31+) | No |
| Best for | Calendar alarms, medication reminders | Daily digests, periodic reminders, deferrable alerts |

---

## Foreground Service Notifications

A Foreground Service requires a persistent, non-dismissible notification to keep running while the app is in the background. This is covered in detail in the Services section, but the notification pattern is:

```kotlin
class DownloadService : Service() {

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val notification = NotificationCompat.Builder(this, NotificationChannels.DOWNLOADS)
            .setSmallIcon(R.drawable.ic_download)
            .setContentTitle("Downloading file…")
            .setProgress(100, 0, true)     // indeterminate progress initially
            .setOngoing(true)
            .build()

        startForeground(FOREGROUND_NOTIFICATION_ID, notification)
        return START_NOT_STICKY
    }

    override fun onBind(intent: Intent?): IBinder? = null
}
```

The foreground notification must be posted before `startForeground()` times out (5 seconds on most versions).

---

## NotificationCompat vs Notification

Always use `NotificationCompat.Builder` from `androidx.core`, not `android.app.Notification.Builder` directly. NotificationCompat:

- Back-fills modern features (MessagingStyle, inline reply) on older API levels gracefully
- Normalises priority/importance differences between pre-26 and post-26 APIs
- Is the only way to use `Person`, `BubbleMetadata`, and other Jetpack-defined types

---

## Common Pitfalls

- **No channel on API 26+**: the notification silently disappears — `NotificationManager.IMPORTANCE_NONE` if the channel isn't created.
- **MUTABLE PendingIntent not used for RemoteInput**: inline reply will not work if the `PendingIntent` is immutable.
- **Reusing IDs unintentionally**: posting to the same ID updates the existing notification — intended, but easy to do by mistake if IDs are hardcoded.
- **Ongoing foreground service notification dismissible**: use `setOngoing(true)` to prevent the user from swiping it away while the service is running.
- **Missing POST_NOTIFICATIONS permission on API 33+**: the permission check returns granted on older APIs, so guard with a version check before posting or requesting.
- **Exact alarm permission removed by user (API 31+)**: always check `alarmManager.canScheduleExactAlarms()` before calling `setExactAndAllowWhileIdle`.

---

← [Previous: BroadcastReceiver](../02-broadcast-receiver/) · [↑ Chapter Index](../) · [Next: Foreground Services →](../04-foreground-services/)
