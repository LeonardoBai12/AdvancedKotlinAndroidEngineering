---
layout: default
title: "Chapter 21: Platform Constraints & Push — Background Execution Limits History"
parent: "Chapter 21: Platform Constraints & Push"
nav_order: 4
---

## Section 4 · Background Execution Limits — A Version-by-Version History

*How Android has progressively restricted background work from Android 6 through Android 14, and what each change means for your code*

---

## Why This History Matters

Understanding why the current background execution model looks the way it does requires tracing the history. Each Android release introduced new restrictions in response to real problems — battery drain, memory pressure, performance issues — and each restriction invalidated previously acceptable engineering patterns. Code that worked perfectly on Android 5 may be silently broken on Android 8 and crash on Android 14.

This section is a chronological reference. Use it to understand why the APIs exist in their current form and what migration path each restriction required.

*Android Developers — Background optimizations*

---

## Android 5.0 — Lollipop (API 21) — The Baseline

Before API 21, background work was largely unconstrained. Apps could:

- Start background `Service`s freely from any state
- Register any number of manifest-declared `BroadcastReceiver`s for any implicit broadcast
- Use `AlarmManager.setRepeating()` for frequent repeating alarms
- Start `IntentService` workers freely

`JobScheduler` was introduced in API 21 as the first system-managed background work scheduler, but adoption was low and it was not yet required.

**Status:** No meaningful restrictions. Anything goes.

---

## Android 6.0 — Marshmallow (API 23) — Doze and App Standby

### What Changed

Two major systems introduced:

**1. Doze Mode**

When the device is unplugged, stationary, and has its screen off for a period, the system enters Doze. In Doze:

- Network access is blocked
- Wake locks are ignored
- `AlarmManager` alarms (except `setAlarmClock`) are deferred to maintenance windows
- `JobScheduler` jobs are deferred

Apps can use `setAlarmClock()` to guarantee exact alarm delivery, or `setExactAndAllowWhileIdle()` which fires but is rate-limited to one alarm per 9 minutes in deep Doze.

**2. App Standby**

If the user has not interacted with an app recently and has not pinned it, the app enters standby and its background jobs and network access are deferred.

### Impact

- Repeating `AlarmManager` alarms break in Doze unless they use `setExactAndAllowWhileIdle`.
- Background network calls in a `Service` may fail silently when the device is idle.
- FCM high-priority messages become the standard way to wake apps from Doze.

### Migration

Switch from `AlarmManager.setRepeating()` to `JobScheduler` for periodic work, or use `setExactAndAllowWhileIdle()` for time-critical alarms. Add Doze awareness to any service that performs network operations.

---

## Android 7.0 — Nougat (API 24) — Light Doze and Broadcast Reduction

### What Changed

**1. Light Doze**

Doze was split into two levels: Light Doze activates as soon as the screen turns off and the device is unplugged (even if it is not stationary). Deep Doze activates later when the device has been stationary for an extended period. Light Doze has more frequent maintenance windows; Deep Doze has windows every few hours.

**2. Three implicit broadcasts removed from manifest receivers**

The following broadcasts could no longer be received by manifest-declared receivers (apps had to register dynamically):

- `CONNECTIVITY_ACTION` (`android.net.conn.CONNECTIVITY_CHANGE`)
- `ACTION_NEW_PICTURE`
- `ACTION_NEW_VIDEO`

This was the first explicit restriction on implicit broadcasts, foreshadowing the much larger restriction in API 26.

### Migration

- Remove manifest receivers for `CONNECTIVITY_ACTION`; register dynamically in foreground components
- Use `ConnectivityManager.NetworkCallback` for network state monitoring
- Use `JobScheduler` with `setRequiredNetworkType()` for deferred network-dependent work

---

## Android 8.0 — Oreo (API 26) — The Background Revolution

### What Changed

Android 8.0 introduced the most significant background execution restrictions in Android's history. Two sweeping changes:

**1. Background Service Limits**

An app that is **not in the foreground** cannot start a background `Service` with `startService()`. Calling `startService()` from the background throws `IllegalStateException`. The system allows a grace period immediately after the app moves to the background, but this window is short (~1 minute) and unreliable.

Exceptions — the following can still start services from background:
- Apps receiving a high-priority FCM message
- Apps receiving a broadcast in a manifest-declared receiver (for the brief duration of `onReceive`)
- Apps visible to the user (foreground)
- `startForegroundService()` — which must then call `startForeground()` within 5 seconds

**2. Implicit Broadcast Restrictions**

Nearly all implicit broadcasts can no longer be received by manifest-declared receivers. The system silently drops them. Only a short list of explicit exceptions (statutory broadcasts) still works with manifest receivers:

- `ACTION_BOOT_COMPLETED`
- `ACTION_LOCKED_BOOT_COMPLETED`
- `ACTION_MY_PACKAGE_REPLACED`
- `ACTION_LOCALE_CHANGED`
- `ACTION_TIMEZONE_CHANGED` / `ACTION_TIME_CHANGED`
- `ACTION_NEW_OUTGOING_CALL`
- (and ~20 others listed in the official docs)

**3. Notification Channels**

All notifications must now be assigned to a `NotificationChannel`. Notifications posted without a channel are silently dropped on API 26+.

### Impact

This release broke a large fraction of background service patterns that had worked for years:

- `IntentService` started from background → `IllegalStateException`
- Manifest receivers for connectivity, power, storage → silently never fire
- Notifications without channels → silently dropped

### Migration

- Replace background `Service` with `WorkManager` or use `startForegroundService()` + `startForeground()`
- Replace manifest broadcast receivers with dynamic receivers or `WorkManager` constraints
- Add `NotificationChannel` creation to app startup

---

## Android 9.0 — Pie (API 28) — App Standby Buckets and Foreground Service Permission

### What Changed

**1. App Standby Buckets**

The binary App Standby system from API 23 was replaced with five usage buckets: Active, Working Set, Frequent, Rare, and Never. The system automatically moves apps between buckets based on usage patterns and applies different job and alarm deferral policies to each.

Apps in the `RARE` bucket may see their `PeriodicWorkRequest` only execute once per day, regardless of the declared interval.

**2. `FOREGROUND_SERVICE` Permission**

Starting a Foreground Service now requires declaring:

```xml
<uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
```

This is a normal permission (auto-granted at install) but the manifest declaration is required. Apps that omit it and call `startForeground()` receive a `SecurityException`.

**3. Power-Saving Mode Enhancements**

Manufacturers gained more official hooks for their own power-saving modes. Background work in Battery Saver mode became even more restricted — no background jobs, no location, no network.

### Migration

- Add `FOREGROUND_SERVICE` permission to manifest
- Test WorkManager in all five standby buckets using `adb shell am set-standby-bucket`

---

## Android 10.0 — Q (API 29) — Background Activity Launch Restrictions and Location

### What Changed

**1. Background Activity Launches Blocked**

Apps can no longer start an `Activity` from the background. Starting an Activity requires the app to be in the foreground or to have been granted a specific exemption (e.g., the app received a high-priority FCM message, the app has a `PendingIntent` from the system, the activity being started is a `Notification` full-screen intent).

This broke the common pattern of launching an Activity from a background service or `BroadcastReceiver`.

**2. Foreground Service Type Introduced (Location)**

Apps that access location from a Foreground Service must declare `foregroundServiceType="location"` in the manifest. Without it, accessing fine or coarse location from a foreground service triggers a `SecurityException`.

**3. Background Location Access Restricted**

Apps must now request `ACCESS_BACKGROUND_LOCATION` (a runtime permission) to access location in the background. Users see a separate permission prompt. Background location is categorized as a sensitive permission and Play Store policy governs when apps can request it.

**4. `READ_CALL_LOG` and `PROCESS_OUTGOING_CALLS` moved**

Access to call metadata is further restricted.

### Migration

- Replace Activity-from-background patterns with high-priority notifications with `fullScreenIntent`
- Declare `foregroundServiceType="location"` for services that use location
- Add `ACCESS_BACKGROUND_LOCATION` permission requests where necessary

---

## Android 11.0 — R (API 30) — Package Visibility and One-Time Permissions

### What Changed

**1. Package Visibility (query filter)**

Apps can no longer query arbitrary installed packages. The `PackageManager.getInstalledApplications()` method returns a limited set by default. To query specific packages, the app must declare them in `<queries>` in the manifest.

**2. One-Time Permissions**

Location, microphone, and camera permissions can now be granted as one-time grants — they are revoked automatically when the app leaves the foreground.

**3. Background location permission on separate screen**

Play Store now strictly enforces the policy that apps requesting `ACCESS_BACKGROUND_LOCATION` must have a core feature that requires it. The permission is moved to a separate settings page — users cannot grant it from a dialog.

### Migration

- Declare required `<queries>` in manifest for inter-app communication
- Handle one-time permission grants gracefully — re-request when the feature is used

---

## Android 12.0 — S (API 31) — Exact Alarms and Foreground Service Restrictions

### What Changed

**1. Exact Alarm Permission Required**

`AlarmManager.setExact()` and `setExactAndAllowWhileIdle()` now require apps targeting API 31+ to hold `SCHEDULE_EXACT_ALARM`. Without it, the alarm is silently made inexact. The permission must be granted by the user in Special App Access settings.

Exception: `setAlarmClock()` remains unrestricted (it is the designated API for clock apps).

**2. Background Activity Launch Restrictions Tightened**

Additional restrictions on when background apps can launch Activities or start Foreground Services. Apps in full-background state need explicit exemptions from specific system events (high-priority FCM, recent app usage, `PendingIntent` from a notification).

**3. Custom Notifications Must Use System-Provided Templates**

Custom `RemoteViews` for standard notifications are deprecated. Apps must use `NotificationCompat.DecoratedCustomViewStyle` or the system standard templates. This prevents abuse of notification space for ads and misleading content.

**4. Pending Intent Mutability**

All `PendingIntent` objects must explicitly declare `FLAG_MUTABLE` or `FLAG_IMMUTABLE`. Omitting both throws `IllegalArgumentException`. Use `FLAG_IMMUTABLE` unless the system must modify the intent (inline reply, direct share).

**5. Splash Screen API**

Mandatory splash screen for all apps — `SplashScreen` API. Unrelated to background execution but widely noticed.

### Migration

- Declare `SCHEDULE_EXACT_ALARM` permission; add `canScheduleExactAlarms()` guard
- Add explicit mutability flags to all `PendingIntent` calls
- Replace content-wide custom notifications with `DecoratedCustomViewStyle`

---

## Android 13.0 — Tiramisu (API 33) — Notification Permission and Receiver Flags

### What Changed

**1. `POST_NOTIFICATIONS` Runtime Permission**

Posting any notification now requires the user to grant `POST_NOTIFICATIONS` — a runtime permission. On upgrade from older APIs, the system automatically grants the permission to existing installs during a transition period, but new installs must request it.

```xml
<uses-permission android:name="android.permission.POST_NOTIFICATIONS" />
```

**2. Dynamic Receiver Flags Required**

`Context.registerReceiver()` now requires either `RECEIVER_EXPORTED` or `RECEIVER_NOT_EXPORTED` for receivers that handle implicit intents. Omitting the flag on API 34+ (enforced starting 34, introduced at 33) causes a crash.

**3. `USE_EXACT_ALARM` Permission**

A new permission for apps where exact alarms are a core feature (clock, calendar, timer apps) — auto-granted at install without user interaction:

```xml
<uses-permission android:name="android.permission.USE_EXACT_ALARM" />
```

Regular apps continue to use `SCHEDULE_EXACT_ALARM` with user approval.

**4. Media Permission Split**

`READ_EXTERNAL_STORAGE` is replaced with granular permissions: `READ_MEDIA_IMAGES`, `READ_MEDIA_VIDEO`, `READ_MEDIA_AUDIO`.

### Migration

- Add `POST_NOTIFICATIONS` permission and request flow
- Add `RECEIVER_EXPORTED` / `RECEIVER_NOT_EXPORTED` flags to all `registerReceiver` calls
- Replace `READ_EXTERNAL_STORAGE` with granular media permissions

---

## Android 14.0 — Upside Down Cake (API 34) — Foreground Service Enforcement

### What Changed

**1. Foreground Service Types Mandatory**

Every Foreground Service must now declare `android:foregroundServiceType` in the manifest AND pass the type flag to `startForeground()`. Omitting either throws:

- `MissingForegroundServiceTypeException` if no type is declared in manifest
- `InvalidForegroundServiceTypeException` if the type does not match a valid constant

Apps that had `foregroundServiceType` declared before API 34 remain compatible — the enforcement applies to apps targeting API 34+.

**2. Type-Specific Foreground Service Permissions**

Each foreground service type now has a corresponding normal permission that must be declared in the manifest:

```xml
<uses-permission android:name="android.permission.FOREGROUND_SERVICE_CAMERA" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE_MICROPHONE" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE_LOCATION" />
<!-- etc. -->
```

**3. Short Service Type**

New `shortService` foreground service type — runs for a maximum of 3 minutes, requires no additional permissions, and stops automatically when the time limit is reached.

**4. Minimum Exact Alarm Interval**

The minimum interval between exact alarms is now enforced more strictly in some scenarios to prevent battery abuse.

**5. Implicit Intent Restrictions**

Implicit intents can no longer start components that are declared with `android:exported="false"`. Previously this had inconsistent enforcement; API 34 makes it strict.

**6. `SCHEDULE_EXACT_ALARM` Revoked on Update**

Apps that upgrade their target SDK to 34 lose the `SCHEDULE_EXACT_ALARM` grant by default and must re-request it.

### Migration

- Add `foregroundServiceType` to every `<service>` in the manifest
- Add type-specific `FOREGROUND_SERVICE_*` permissions
- Add `startForeground(ID, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_*)` call
- Re-handle `SCHEDULE_EXACT_ALARM` grants on update

---

## Complete Restriction Timeline

| Android Version | API | Key restriction |
| --- | --- | --- |
| 6.0 Marshmallow | 23 | Doze Mode; App Standby |
| 7.0 Nougat | 24 | Light Doze; `CONNECTIVITY_ACTION` blocked from manifest receivers |
| 8.0 Oreo | 26 | Background Service limits; implicit broadcast restrictions; Notification Channels required |
| 9.0 Pie | 28 | App Standby Buckets; `FOREGROUND_SERVICE` permission required |
| 10.0 Q | 29 | Background Activity Launch blocked; `foregroundServiceType` for location; background location permission |
| 11.0 R | 30 | Package Visibility; one-time permissions |
| 12.0 S | 31 | Exact Alarm permission; `PendingIntent` mutability flags required |
| 13.0 Tiramisu | 33 | `POST_NOTIFICATIONS` runtime permission; receiver flags required; `USE_EXACT_ALARM` |
| 14.0 UpsideDownCake | 34 | Foreground Service type mandatory; type-specific FOREGROUND_SERVICE permissions; Short Service |

---

## The Migration Pattern Each Restriction Follows

Every Android background restriction follows the same general shape: Google observed a class of battery or performance abuse, introduced a new API that is exempt from the restriction, and deprecated or blocked the old approach. The canonical migrations are:

| Old pattern (broken by restriction) | New pattern |
| --- | --- |
| Background `Service` via `startService()` | WorkManager, or `startForegroundService()` + Foreground Service |
| Manifest receiver for `CONNECTIVITY_ACTION` | `ConnectivityManager.NetworkCallback` (foreground) or WorkManager constraint (background) |
| `AlarmManager.setRepeating()` | WorkManager `PeriodicWorkRequest` |
| Untyped Foreground Service | Typed Foreground Service with `foregroundServiceType` |
| Notification without channel | `NotificationChannel` + `NotificationCompat.Builder` |
| Any `PendingIntent` without mutability | `FLAG_IMMUTABLE` or `FLAG_MUTABLE` explicit flag |
| `startActivity()` from background | `fullScreenIntent` in notification, or high-priority FCM handler |
| `AlarmManager.setExact()` without permission | `canScheduleExactAlarms()` + `SCHEDULE_EXACT_ALARM` permission request |

---

> **Interview Tip:**
>
> A common interview question is "How has Android restricted background work over the years?" The expected answer traces: Doze in API 23 → broadcast restrictions in API 26 + background service ban → Standby Buckets in API 28 → Activity launch ban in API 29 → exact alarm permission in API 31 → notification permission in API 33 → foreground service type enforcement in API 34. Each restriction pairs with the correct modern API that replaced it.

---

← [Previous: Firebase Cloud Messaging](../03-fcm/) · [↑ Chapter Index](../)
