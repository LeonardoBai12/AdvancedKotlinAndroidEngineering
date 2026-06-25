---
layout: default
title: Doze Standby Battery
parent: "Platform Constraints & Push"
nav_order: 1
---

## Section 1 · Doze Mode, App Standby & Battery Optimisation

*How Android defends battery life — and how your background code must respond*

---

## Why These Systems Exist

Android's background execution model is fundamentally shaped by battery constraints. An app that runs indefinitely in the background is unacceptable on a mobile device. Starting with Android 6.0 (API 23), Google introduced a layered set of power management systems that progressively restrict what apps can do when the device is idle or the app is not being used. Understanding these systems is not optional — they directly determine whether your background code will run at all.

There are three interlocking systems:

1. **Doze Mode** — restricts network access and defers jobs/alarms when the device is idle
2. **App Standby** and **App Standby Buckets** — restricts apps the user has not recently used
3. **Battery Optimisation** — per-app exemptions managed by the user and enforced by the OS

*Android Developers — Optimize for battery life*

---

## Doze Mode (Android 6.0, API 23)

### What Doze Is

Doze Mode activates when the device is **unplugged, stationary, and has its screen off** for a significant period. In Doze, the system periodically allows apps into **maintenance windows** — brief intervals during which deferred network, jobs, alarms, and sync adapters are allowed to execute. Outside maintenance windows, the system blocks:

- Network access
- CPU wake locks
- `JobScheduler` jobs
- `AlarmManager` alarms (except `setAlarmClock`)
- Wi-Fi scans
- Sync adapters

```
Normal state
    │
Screen off + unplugged + stationary → [ Light Doze ]
    │                                  maintenance windows every few minutes
    │ (device stationary for longer)
    ▼
[ Deep Doze ]
   maintenance windows every few hours
   (no network access between windows)
```

### Light Doze vs Deep Doze (Android 7.0, API 24)

Android 7.0 extended Doze to two levels:

| | Light Doze | Deep Doze |
| --- | --- | --- |
| Trigger | Screen off + unplugged | Screen off + unplugged + stationary for an extended period |
| Network access | Blocked between maintenance windows | Blocked between maintenance windows |
| Maintenance window frequency | Every few minutes initially, then exponentially less frequent | Every few hours |
| `setAndAllowWhileIdle` alarms | Fires at next window | Fires at next window (but window is rare) |
| `setExactAndAllowWhileIdle` alarms | Fires, but deferred to window | Fires, but deferred to window |
| `setAlarmClock` alarms | Fires on time | Fires on time (exempt from Doze) |
| High-priority FCM | Wakes device from Doze | Wakes device from Doze |

### Maintenance Windows

During a maintenance window the OS lifts Doze restrictions briefly so that deferred operations can run. The windows start frequent and grow progressively less frequent as the device remains idle:

```
Hour 0: window at ~minute 5
Hour 0: window at ~minute 15
Hour 0: window at ~minute 30
Hour 1: window every ~hour
Hour 3+: window every few hours
```

WorkManager is designed around this: it queues work to execute at the next available maintenance window, transparently. `setExactAndAllowWhileIdle` fires once per window, not on the original schedule if the device is in deep Doze.

### What Is Exempt from Doze

| API / mechanism | Doze-exempt? |
| --- | --- |
| `AlarmManager.setAlarmClock()` | Yes — fires exactly on time |
| High-priority FCM messages | Yes — wakes device |
| Foreground Services | Yes — exempt while running |
| `setExactAndAllowWhileIdle()` | Partial — deferred to next maintenance window |
| Standard `JobScheduler` jobs | No — deferred |
| `WorkManager` periodic work | No — deferred (by design) |
| `AlarmManager.set()` / `setExact()` | No — deferred |
| Network access in general | No — blocked |

### Testing Doze Behaviour

```bash
# Force the device into Doze (adb)
adb shell dumpsys battery unplug
adb shell dumpsys deviceidle force-idle

# Check Doze state
adb shell dumpsys deviceidle

# Trigger a maintenance window
adb shell dumpsys deviceidle step

# Exit Doze
adb shell dumpsys deviceidle unforce
adb shell dumpsys battery reset
```

---

## App Standby (Android 6.0, API 23)

### What App Standby Is

App Standby restricts apps that the user has not recently interacted with. Unlike Doze (which is device-level), App Standby is **per-app**. An app enters standby when:

- It has not been used recently (no foreground Activity, notification, or user interaction)
- The user has not explicitly launched it
- The device is not charging

While in standby, the app's network access and background jobs are deferred to a maintenance window — similar to Doze, but the window timing is per-app, not device-global.

---

## App Standby Buckets (Android 9.0, API 28)

Android 9.0 replaced the binary "standby / not standby" model with **five usage buckets**. The system places each app into a bucket based on its recent usage patterns and adjusts the bucket over time.

| Bucket | When app is in it | Job runs | Alarm runs | Network |
| --- | --- | --- | --- | --- |
| **Active** | User currently using the app or just launched it | Any time | Any time | Unrestricted |
| **Working Set** | Used frequently (daily) | Within a few minutes | Within 6 minutes | Unrestricted |
| **Frequent** | Used regularly but not daily | Within a few hours | Within 30 minutes | Unrestricted |
| **Rare** | Used infrequently (once a week or less) | Within a day | Within 2 hours | Restricted (can be deferred) |
| **Restricted** (Android 12+) | System detects abusive background behaviour | Within a day, limited count | Within 2 hours, limited count | Restricted |
| **Never** | Installed but never opened | Never | Never | Never |
| **Exempted** | User has whitelisted it, or critical app | Any time | Any time | Unrestricted |

*Android Developers — App Standby Buckets*

### Querying the Current Bucket

```kotlin
val usageStatsManager = getSystemService(UsageStatsManager::class.java)
val bucket = usageStatsManager.appStandbyBucket

when (bucket) {
    UsageStatsManager.STANDBY_BUCKET_ACTIVE     -> "Active"
    UsageStatsManager.STANDBY_BUCKET_WORKING_SET -> "Working Set"
    UsageStatsManager.STANDBY_BUCKET_FREQUENT   -> "Frequent"
    UsageStatsManager.STANDBY_BUCKET_RARE       -> "Rare"
    UsageStatsManager.STANDBY_BUCKET_RESTRICTED -> "Restricted"
    else                                         -> "Unknown"
}
```

Requires `PACKAGE_USAGE_STATS` permission (user-granted in Settings, not a normal runtime permission).

### How Buckets Affect WorkManager and AlarmManager

WorkManager works transparently with buckets: the platform defers jobs according to the app's current bucket. You do not need to check the bucket yourself — but you should understand that a `PeriodicWorkRequest` with a 1-hour interval may run every 6 minutes if the app is in `ACTIVE`, or only once per day if in `RARE`.

AlarmManager similarly defers non-exact alarms according to bucket constraints.

### Testing Standby Buckets

```bash
# Set your app to a specific bucket
adb shell am set-standby-bucket com.example.myapp rare

# Check which bucket the app is in
adb shell am get-standby-bucket com.example.myapp
```

---

## Battery Optimisation

### What Battery Optimisation Is

Battery Optimisation is a per-app system switch that controls whether an app's background behaviour is subject to Doze and App Standby restrictions. It is exposed to the user in **Settings → Battery → Battery Optimisation** and maps to a system whitelist.

An app that is **not optimised** (i.e., on the whitelist) behaves as if it is always in `ACTIVE` standby, can receive network at any time, and its alarms fire on schedule even in Doze. This is a significant privilege intended for system apps and a narrow set of use cases (calendar, alarm clock, accessibility services, VPN).

*Google Play policy limits which apps can request battery optimisation exemption.*

### Checking and Requesting Exemption

```kotlin
val powerManager = getSystemService(PowerManager::class.java)
val packageName = packageName

val isIgnoring = powerManager.isIgnoringBatteryOptimizations(packageName)

if (!isIgnoring) {
    // This opens the system dialog asking the user to exempt your app
    // Play Store policy: you may only request this for valid use cases
    val intent = Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS).apply {
        data = Uri.parse("package:$packageName")
    }
    startActivity(intent)
}
```

You can also send the user directly to the Battery Optimisation settings page:

```kotlin
startActivity(Intent(Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS))
```

### WakeLocks

A `WakeLock` is a lower-level mechanism that prevents the CPU or screen from sleeping. WorkManager and `JobScheduler` acquire a partial WakeLock automatically for the duration of a job. If you use a Service directly, you may need one.

```kotlin
val powerManager = getSystemService(PowerManager::class.java)

val wakeLock = powerManager.newWakeLock(
    PowerManager.PARTIAL_WAKE_LOCK,
    "MyApp::SyncTag"                // tag visible in battery usage reports
)

wakeLock.acquire(10 * 60 * 1000L)  // 10 minutes maximum — always pass a timeout

try {
    doBackgroundWork()
} finally {
    if (wakeLock.isHeld) wakeLock.release()   // ALWAYS release in finally
}
```

**WakeLock types:**

| Type | Keeps awake | Use case |
| --- | --- | --- |
| `PARTIAL_WAKE_LOCK` | CPU only | Background computation, network ops |
| `SCREEN_DIM_WAKE_LOCK` | Screen (dim) + CPU | Media playback, maps |
| `SCREEN_BRIGHT_WAKE_LOCK` | Screen (bright) + CPU | Video calls |
| `FULL_WAKE_LOCK` | Screen (bright) + keyboard + CPU | Deprecated |

> Never acquire a WakeLock without a timeout. An un-released WakeLock drains the battery completely and makes your app toxic to users. WorkManager handles WakeLocks for you — only use raw WakeLocks when you have no alternative.

### Detecting WakeLock Abuse

LeakCanary does not detect WakeLock leaks, but `Battery Historian` (Google tool) and Android Studio's Energy Profiler can show which component is holding the CPU awake. In adb:

```bash
adb shell dumpsys power | grep "Wake Locks"
```

---

## How the Three Systems Interact

```
App tries to run background work
        │
        ├─ Is device in Doze?
        │       YES → defer to next maintenance window
        │              (or wake via setExactAndAllowWhileIdle / high-priority FCM)
        │
        ├─ What is the app's Standby Bucket?
        │       RARE / RESTRICTED → jobs deferred up to 24 hours
        │       FREQUENT → jobs deferred up to a few hours
        │       ACTIVE / WORKING SET → runs soon
        │
        └─ Is app on Battery Optimisation whitelist?
                YES → effectively exempt from Doze and Standby
```

WorkManager transparently respects all three layers. If the device is in deep Doze, the job waits. If the app is in the `RARE` bucket, WorkManager's minimum period for a `PeriodicWorkRequest` may effectively be longer than the declared 1-hour interval.

---

## Practical Guidance for App Developers

- **Do not request battery optimisation exemption** unless your app has a legitimate, Play Store–approved reason (alarm clock, VPN, calendar sync that must fire at exact times). Abusing the exemption will get your app removed.
- **Design background work to be deferrable.** If your sync task can tolerate running an hour late, use WorkManager with appropriate constraints — the OS will batch it with other deferred work to minimise wake-ups.
- **Use high-priority FCM sparingly.** High-priority messages wake the device from Doze and consume battery. Reserve them for messages that genuinely need immediate delivery (incoming call, security alert).
- **Test in all standby states.** Use `adb shell am set-standby-bucket` to verify your app's behaviour in `FREQUENT`, `RARE`, and `RESTRICTED` buckets. A background sync that passes in `ACTIVE` may silently not run in `RARE`.
- **Do not hold WakeLocks manually.** Prefer WorkManager, which manages its own WakeLock internally. If you must use one, always set a timeout and release in `finally`.

---

← [↑ Chapter Index](../) · [Next: AlarmManager →](../02-alarm-manager/)
