---
layout: default
title: "Chapter 21: Platform Constraints & Push — AlarmManager"
parent: "Chapter 21: Platform Constraints & Push"
nav_order: 2
---

## Section 2 · AlarmManager

*The full alarm API — clock types, exactness levels, Doze behaviour, and when to use which variant*

---

## What AlarmManager Is

`AlarmManager` is the Android system service for scheduling work at a specific point in time or after a specific interval. It operates at the system level: the alarm fires even if the app is not running and even if the device was restarted (provided the alarm is re-registered after boot via `BOOT_COMPLETED`).

AlarmManager is distinct from WorkManager and `JobScheduler`:

| | AlarmManager | WorkManager | JobScheduler |
| --- | --- | --- | --- |
| Timing precision | Exact (with permission) or approximate | Approximate (constraint-based) | Approximate |
| Survives app kill | Yes — system-level | Yes — persisted to disk | Yes — registered with system |
| Survives reboot | No — must re-register after BOOT_COMPLETED | Yes — automatic | No — must re-register |
| Battery impact | High when using exact alarms | Low — batched | Low — batched |
| Doze-aware | `setExactAndAllowWhileIdle` can fire during Doze | Deferred to maintenance window | Deferred to maintenance window |
| Use case | Calendar reminders, medication alarms, exact-time notifications | Deferrable background sync | Deferrable background work |

*Android Developers — Schedule alarms*

---

## Clock Types

Every alarm method takes a `type` parameter that controls two things: whether the time reference is real-world clock time or elapsed time since boot, and whether the alarm wakes the device from sleep.

| Type constant | Time reference | Wakes device? | Use when |
| --- | --- | --- | --- |
| `RTC` | Real-world time (UTC milliseconds) | No | Fire at wall-clock time, device must already be awake |
| `RTC_WAKEUP` | Real-world time (UTC milliseconds) | Yes | Fire at wall-clock time, must fire even if screen is off |
| `ELAPSED_REALTIME` | Milliseconds since boot | No | Fire after a duration, device must already be awake |
| `ELAPSED_REALTIME_WAKEUP` | Milliseconds since boot | Yes | Fire after a duration, must fire even if screen is off |

For user-facing alarms (reminders, medication timers): use `RTC_WAKEUP`.

For interval-based background work (poll every 15 minutes): use `ELAPSED_REALTIME_WAKEUP`.

```kotlin
val alarmManager = getSystemService(AlarmManager::class.java)

// Fire at a specific wall-clock time, waking the device if needed
val triggerAt = System.currentTimeMillis() + 30 * 60 * 1000L   // 30 minutes from now
alarmManager.set(AlarmManager.RTC_WAKEUP, triggerAt, pendingIntent)

// Fire after 1 hour of elapsed boot time, waking the device
val triggerElapsed = SystemClock.elapsedRealtime() + 60 * 60 * 1000L
alarmManager.set(AlarmManager.ELAPSED_REALTIME_WAKEUP, triggerElapsed, pendingIntent)
```

> `System.currentTimeMillis()` gives wall-clock UTC time. `SystemClock.elapsedRealtime()` gives monotonic time since boot. The monotonic clock is immune to user time changes and NTP adjustments, making it better for interval-based alarms.

---

## Exactness Levels

Android offers several alarm methods with different precision guarantees and Doze behaviour:

### `set()` — inexact, batch-aligned

The alarm fires at approximately the requested time. The system may defer it by up to 75% of the interval to batch alarms from multiple apps together. In Doze, it is deferred to the next maintenance window.

```kotlin
alarmManager.set(AlarmManager.RTC_WAKEUP, triggerAt, pendingIntent)
```

Use for work where approximate timing is acceptable (refresh a widget, pre-fetch content).

### `setInexactRepeating()` — repeating, batch-aligned

Repeating alarm with inexact timing. The system aligns repetitions from multiple apps together where possible to reduce wake-ups. The minimum interval is `AlarmManager.INTERVAL_FIFTEEN_MINUTES`.

```kotlin
alarmManager.setInexactRepeating(
    AlarmManager.ELAPSED_REALTIME_WAKEUP,
    SystemClock.elapsedRealtime() + AlarmManager.INTERVAL_FIFTEEN_MINUTES,
    AlarmManager.INTERVAL_HOUR,
    pendingIntent
)
```

**Predefined interval constants:**

| Constant | Value |
| --- | --- |
| `INTERVAL_FIFTEEN_MINUTES` | 15 minutes |
| `INTERVAL_HALF_HOUR` | 30 minutes |
| `INTERVAL_HOUR` | 1 hour |
| `INTERVAL_HALF_DAY` | 12 hours |
| `INTERVAL_DAY` | 24 hours |

> Prefer WorkManager over `setInexactRepeating` for any periodic work that does not need a notification at a specific time. WorkManager survives reboots automatically and respects constraints.

### `setExact()` — exact, no Doze exemption

Fires at exactly the requested time when the device is awake. In Doze, it is deferred to the next maintenance window — so it may fire late if the device is idle.

```kotlin
alarmManager.setExact(AlarmManager.RTC_WAKEUP, triggerAt, pendingIntent)
```

Use for alarms that are exact when the device is active, but where firing slightly late during idle periods is acceptable.

### `setWindow()` — exact window, batch-optimised

Fires within a time window you define. This allows the system to align the alarm within the window with other alarms, reducing the number of wake-ups, while still guaranteeing delivery before the window ends.

```kotlin
alarmManager.setWindow(
    AlarmManager.RTC_WAKEUP,
    triggerAt,                      // window start
    15 * 60 * 1000L,                // window length (15 minutes)
    pendingIntent
)
```

This is the right trade-off for alarms that should be "approximately on time" without batching unpredictably.

### `setExactAndAllowWhileIdle()` — exact, fires during Doze

The most powerful commonly available alarm. Fires exactly on time even if the device is in Doze — it wakes the device from idle state. However, the system limits how often an app can use this: one alarm per app per 9-minute window in deep Doze.

```kotlin
alarmManager.setExactAndAllowWhileIdle(
    AlarmManager.RTC_WAKEUP,
    triggerAt,
    pendingIntent
)
```

Use for alarms that must fire at a specific time regardless of Doze — medication reminders, time-sensitive alerts.

### `setAlarmClock()` — calendar alarm, highest priority

The strongest alarm available without special permissions. It fires exactly on time, wakes the device from Doze, and is **fully exempt from all Doze restrictions**. The system also shows the user an alarm indicator in the status bar. Designed specifically for clock/calendar apps.

```kotlin
val alarmClockInfo = AlarmManager.AlarmClockInfo(
    triggerAt,         // exact fire time in wall-clock milliseconds
    pendingIntent      // PendingIntent shown when user taps the status bar alarm icon
)

alarmManager.setAlarmClock(alarmClockInfo, pendingIntent)
```

**Summary of all alarm methods:**

| Method | Exact? | Fires in Doze? | Survives Doze? | Requires permission? |
| --- | --- | --- | --- | --- |
| `set()` | No | No | No | No |
| `setInexactRepeating()` | No | No | No | No |
| `setExact()` | Yes | No | Deferred | No |
| `setWindow()` | Window | No | Deferred | No |
| `setExactAndAllowWhileIdle()` | Yes | Partial (one per 9 min) | Yes, rate-limited | No |
| `setAlarmClock()` | Yes | Yes | Yes | No |
| `setExact()` + `SCHEDULE_EXACT_ALARM` | Yes | No | No | Yes (API 31+) |

---

## Exact Alarm Permissions (Android 12+, API 31)

Before Android 12, `setExact()` was unrestricted. From API 31 onwards, apps that target API 31+ must hold a permission to use `setExact()` without Doze deferral:

```xml
<!-- AndroidManifest.xml -->
<!-- Request the permission — user must grant it in Special App Access settings -->
<uses-permission android:name="android.permission.SCHEDULE_EXACT_ALARM" />
```

Or, for apps where exact alarms are a core use case (clock apps, calendar apps):

```xml
<!-- Automatically granted on install for pre-approved categories -->
<uses-permission android:name="android.permission.USE_EXACT_ALARM" />
```

| Permission | Who gets it | User can revoke? |
| --- | --- | --- |
| `SCHEDULE_EXACT_ALARM` | Any app — user must grant in Settings | Yes |
| `USE_EXACT_ALARM` | Clock, calendar, alarm apps (Play policy-gated) | No |

**Always check before scheduling an exact alarm:**

```kotlin
val alarmManager = getSystemService(AlarmManager::class.java)

if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
    if (alarmManager.canScheduleExactAlarms()) {
        alarmManager.setExactAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, triggerAt, pi)
    } else {
        // Fall back to inexact, or direct the user to grant the permission
        val intent = Intent(Settings.ACTION_REQUEST_SCHEDULE_EXACT_ALARM)
        startActivity(intent)
    }
} else {
    alarmManager.setExactAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, triggerAt, pi)
}
```

The system broadcasts `ACTION_SCHEDULE_EXACT_ALARM_PERMISSION_STATE_CHANGED` when the user grants or revokes the permission — register a `BroadcastReceiver` for it if you need to re-schedule alarms reactively.

---

## PendingIntent for Alarms

AlarmManager delivers alarms by firing a `PendingIntent`. The three common targets:

```kotlin
// 1. BroadcastReceiver — most common, lowest overhead
val pi = PendingIntent.getBroadcast(
    context,
    requestCode,
    Intent(context, AlarmReceiver::class.java),
    PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
)

// 2. Service — if you need to start a service immediately on alarm fire
val pi = PendingIntent.getService(
    context,
    requestCode,
    Intent(context, UploadService::class.java),
    PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
)

// 3. Activity — brings an Activity to the foreground (user-visible alarms)
val pi = PendingIntent.getActivity(
    context,
    requestCode,
    Intent(context, ReminderActivity::class.java),
    PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
)
```

`FLAG_IMMUTABLE` is required on Android 12+ for alarms that do not need the system to fill in extras. Use `FLAG_MUTABLE` only when the system must modify the intent (e.g., `setAlarmClock`'s show intent).

---

## Cancelling Alarms

Cancelling requires an identical `PendingIntent` — same action, same extras, same request code:

```kotlin
val cancelIntent = PendingIntent.getBroadcast(
    context,
    requestCode,                // must match the ID used when scheduling
    Intent(context, AlarmReceiver::class.java),
    PendingIntent.FLAG_NO_CREATE or PendingIntent.FLAG_IMMUTABLE
)

if (cancelIntent != null) {
    alarmManager.cancel(cancelIntent)
    cancelIntent.cancel()       // also cancel the PendingIntent itself
}
```

`FLAG_NO_CREATE` returns null if no matching PendingIntent exists — safe to check before cancelling.

---

## Surviving Reboots

AlarmManager alarms are stored in RAM and lost on device reboot. To restore them, listen for `BOOT_COMPLETED`:

```kotlin
class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Intent.ACTION_BOOT_COMPLETED) return
        // Re-read all pending alarms from your local database and re-schedule them
        val pending = AlarmRepository(context).getPendingAlarms()
        pending.forEach { alarm ->
            AlarmScheduler(context).schedule(alarm)
        }
    }
}
```

```xml
<receiver android:name=".BootReceiver" android:exported="true">
    <intent-filter>
        <action android:name="android.intent.action.BOOT_COMPLETED" />
    </intent-filter>
</receiver>
<uses-permission android:name="android.permission.RECEIVE_BOOT_COMPLETED" />
```

The canonical pattern: store alarm data in a local database (Room), read it on boot, re-register each alarm with AlarmManager.

---

## Full Example: Medication Reminder

```kotlin
class MedicationAlarmScheduler(private val context: Context) {

    private val alarmManager = context.getSystemService(AlarmManager::class.java)

    fun schedule(medicationId: Long, timeMillis: Long) {
        val intent = Intent(context, MedicationAlarmReceiver::class.java).apply {
            putExtra("medication_id", medicationId)
        }
        val pendingIntent = PendingIntent.getBroadcast(
            context,
            medicationId.toInt(),
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S &&
            !alarmManager.canScheduleExactAlarms()
        ) {
            // Request permission then try again
            context.startActivity(
                Intent(Settings.ACTION_REQUEST_SCHEDULE_EXACT_ALARM)
            )
            return
        }

        alarmManager.setExactAndAllowWhileIdle(
            AlarmManager.RTC_WAKEUP,
            timeMillis,
            pendingIntent
        )
    }

    fun cancel(medicationId: Long) {
        val intent = Intent(context, MedicationAlarmReceiver::class.java)
        val pendingIntent = PendingIntent.getBroadcast(
            context,
            medicationId.toInt(),
            intent,
            PendingIntent.FLAG_NO_CREATE or PendingIntent.FLAG_IMMUTABLE
        ) ?: return
        alarmManager.cancel(pendingIntent)
        pendingIntent.cancel()
    }
}

class MedicationAlarmReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val id = intent.getLongExtra("medication_id", -1L)
        if (id == -1L) return

        val notification = NotificationCompat.Builder(context, MEDICATION_CHANNEL)
            .setSmallIcon(R.drawable.ic_pill)
            .setContentTitle("Time to take your medication")
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setAutoCancel(true)
            .build()

        NotificationManagerCompat.from(context)
            .notify(id.toInt(), notification)
    }
}
```

---

## AlarmManager vs WorkManager — Decision Guide

| Use this | When |
| --- | --- |
| `setAlarmClock()` | Clock app, calendar alarm — must fire at exact time, Doze-exempt, visible status bar indicator |
| `setExactAndAllowWhileIdle()` | Medication reminder, time-critical notification — exact, fires during Doze |
| `setExact()` | Alarm that must be exact when device is awake, tolerate Doze deferral |
| `setWindow()` | Alarm that should be within a time window, OK if OS picks the best moment |
| `set()` | Approximate alarm, OK to batch with other apps |
| WorkManager | Background work that must survive reboots, complex constraint logic, retry, chaining |

---

← [Previous: Doze, App Standby & Battery](../01-doze-standby-battery/) · [↑ Chapter Index](../) · [Next: Firebase Cloud Messaging →](../03-fcm/)
