---
layout: page
title: "Chapter 20: Background Work & Notifications — WorkManager"
---

## Section 1 · WorkManager

*Guaranteed, deferrable background work that survives process death and respects system constraints*

---

## What WorkManager Is (and Is Not)

WorkManager is Jetpack's recommended solution for **deferrable, guaranteed background work** — work that must eventually run even if the app is killed or the device restarts. It is not a general coroutine scheduler or a replacement for threads; it is a persistent job scheduler backed by the platform.

*Google Android Developers — WorkManager overview*

Under the hood, WorkManager chooses the best available platform API automatically:

| API level | Backing implementation |
| --- | --- |
| API 23+ | `JobScheduler` |
| API < 23 with Google Play Services | `GCMNetworkManager` |
| API < 23 without Play Services | `AlarmManager` + `BroadcastReceiver` |

Your code never changes — WorkManager abstracts all of this.

### When to use WorkManager

| Scenario | Right tool |
| --- | --- |
| Sync data to server when network is available | WorkManager |
| Upload logs or analytics on charging + unmetered network | WorkManager |
| Compress images on idle + sufficient storage | WorkManager |
| Re-schedule background work after device reboot | WorkManager |
| Play music while the screen is off | Foreground Service |
| React to a push notification right now | FCM + immediate coroutine |
| Execute code every 100ms | Timer / coroutine, not WorkManager |

> WorkManager is for *deferrable* work. If the task must run within a few seconds of the user action, launch a coroutine instead. WorkManager is free to run the work up to 15 minutes late to satisfy constraints and battery optimisation.

---

## Dependency

```kotlin
// build.gradle.kts (app)
dependencies {
    implementation("androidx.work:work-runtime-ktx:2.9.1")
}
```

---

## The Worker

All work is defined by extending `CoroutineWorker` (preferred for coroutine-based code) or `ListenableWorker`.

```kotlin
class SyncWorker(
    context: Context,
    params: WorkerParameters
) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result {
        return try {
            val count = repository.syncWithServer()
            Result.success(
                workDataOf("synced_count" to count)   // optional output data
            )
        } catch (e: IOException) {
            if (runAttemptCount < 3) Result.retry()   // ask WorkManager to retry
            else Result.failure(workDataOf("error" to e.message))
        }
    }
}
```

`doWork()` runs on a background dispatcher automatically. Return one of:

| Result | Meaning |
| --- | --- |
| `Result.success()` | Work completed; do not re-run |
| `Result.failure()` | Work failed permanently |
| `Result.retry()` | Ask WorkManager to retry according to backoff policy |

---

## OneTimeWorkRequest

For work that should run once.

```kotlin
val syncRequest = OneTimeWorkRequestBuilder<SyncWorker>()
    .setConstraints(
        Constraints.Builder()
            .setRequiredNetworkType(NetworkType.CONNECTED)
            .setRequiresBatteryNotLow(true)
            .build()
    )
    .setInputData(workDataOf("user_id" to userId))
    .setBackoffCriteria(
        BackoffPolicy.EXPONENTIAL,
        WorkRequest.MIN_BACKOFF_MILLIS,
        TimeUnit.MILLISECONDS
    )
    .addTag("sync")
    .build()

WorkManager.getInstance(context).enqueue(syncRequest)
```

---

## PeriodicWorkRequest

For work that repeats on a schedule. Minimum interval is **15 minutes** (platform constraint from `JobScheduler`).

```kotlin
val periodicSync = PeriodicWorkRequestBuilder<SyncWorker>(
    repeatInterval = 1,
    repeatIntervalTimeUnit = TimeUnit.HOURS,
    flexTimeInterval = 15,
    flexTimeIntervalUnit = TimeUnit.MINUTES   // run in last 15 min of each hour
)
    .setConstraints(
        Constraints.Builder()
            .setRequiredNetworkType(NetworkType.UNMETERED)
            .setRequiresCharging(true)
            .build()
    )
    .build()
```

The `flexTimeInterval` defines a window at the end of each period during which WorkManager will try to run the work.

---

## Constraints

```kotlin
Constraints.Builder()
    .setRequiredNetworkType(NetworkType.CONNECTED)      // any network
    .setRequiredNetworkType(NetworkType.UNMETERED)      // Wi-Fi only
    .setRequiresCharging(true)                          // plugged in
    .setRequiresBatteryNotLow(true)                     // battery above threshold
    .setRequiresDeviceIdle(true)                        // Doze-idle (API 23+)
    .setRequiresStorageNotLow(true)                     // sufficient free space
    .build()
```

| Constraint | Android docs threshold |
| --- | --- |
| Battery not low | Below ~15% triggers the condition |
| Storage not low | Below ~1 GB (device-specific) triggers the condition |
| Device idle | Device in Doze mode with screen off and stationary |

---

## Unique Work

`enqueueUniqueWork` / `enqueueUniquePeriodicWork` ensures only one instance of a named job exists at a time.

```kotlin
WorkManager.getInstance(context).enqueueUniquePeriodicWork(
    "hourly-sync",                          // unique name
    ExistingPeriodicWorkPolicy.KEEP,        // keep the existing one if running
    periodicSync
)

WorkManager.getInstance(context).enqueueUniqueWork(
    "one-time-upload",
    ExistingWorkPolicy.REPLACE,             // cancel existing, enqueue new
    uploadRequest
)
```

| Policy | Behaviour |
| --- | --- |
| `KEEP` | If a job with the same name is already enqueued/running, ignore the new request |
| `REPLACE` | Cancel the existing job and enqueue the new one |
| `APPEND` | New work runs after the existing chain completes |
| `APPEND_OR_REPLACE` | Appends unless existing work is cancelled/failed, then replaces |

---

## Work Chaining

WorkManager supports sequential and parallel chains of workers.

```kotlin
// Sequential chain
WorkManager.getInstance(context)
    .beginWith(cleanupRequest)
    .then(uploadRequest)
    .then(notifyRequest)
    .enqueue()

// Parallel then merge
val parallel = WorkManager.getInstance(context)
    .beginWith(listOf(fetchImagesRequest, fetchMetadataRequest))   // run in parallel
    .then(mergeRequest)                                            // runs after both finish
    .enqueue()
```

Output data from one worker is passed as input data to the next via `Result.success(workDataOf(...))`.

---

## Expedited Work

For urgent tasks that need to run as soon as possible while the app may be in the background. Requires the worker to call `getForegroundInfo()`.

```kotlin
class UrgentSyncWorker(ctx: Context, params: WorkerParameters)
    : CoroutineWorker(ctx, params) {

    override suspend fun getForegroundInfo(): ForegroundInfo =
        ForegroundInfo(
            NOTIFICATION_ID,
            buildNotification(applicationContext)
        )

    override suspend fun doWork(): Result {
        // urgent work here
        return Result.success()
    }
}

val expedited = OneTimeWorkRequestBuilder<UrgentSyncWorker>()
    .setExpedited(OutOfQuotaPolicy.RUN_AS_NON_EXPEDITED_WORK_REQUEST)
    .build()
```

*Google — WorkManager expedited work guide*

---

## Observing Work

```kotlin
// Observe by ID
WorkManager.getInstance(context)
    .getWorkInfoByIdLiveData(syncRequest.id)
    .observe(lifecycleOwner) { info ->
        when (info?.state) {
            WorkInfo.State.ENQUEUED  -> showStatus("Queued")
            WorkInfo.State.RUNNING   -> showStatus("Running")
            WorkInfo.State.SUCCEEDED -> {
                val count = info.outputData.getInt("synced_count", 0)
                showStatus("Synced $count items")
            }
            WorkInfo.State.FAILED    -> showStatus("Failed")
            WorkInfo.State.CANCELLED -> showStatus("Cancelled")
            else -> Unit
        }
    }

// Observe by tag (Flow-based)
WorkManager.getInstance(context)
    .getWorkInfosByTagFlow("sync")
    .collect { infos -> /* ... */ }
```

---

## Input and Output Data

`Data` is a lightweight key-value store (max 10 KB) for passing parameters in and results out.

```kotlin
// Input — pass to worker at enqueue time
val input = workDataOf(
    "image_url" to "https://example.com/photo.jpg",
    "compress" to true,
    "quality" to 80
)

// Inside doWork()
val url    = inputData.getString("image_url") ?: return Result.failure()
val compress = inputData.getBoolean("compress", false)
val quality  = inputData.getInt("quality", 100)

// Output — returned from doWork()
Result.success(workDataOf("saved_path" to "/data/user/0/.../photo.jpg"))
```

---

## Retry and Backoff

```kotlin
OneTimeWorkRequestBuilder<SyncWorker>()
    .setBackoffCriteria(
        BackoffPolicy.EXPONENTIAL,      // or LINEAR
        WorkRequest.MIN_BACKOFF_MILLIS, // 10 000 ms minimum
        TimeUnit.MILLISECONDS
    )
    .build()
```

- `BackoffPolicy.EXPONENTIAL`: delay doubles each retry (10 s → 20 s → 40 s …, up to 5 hours)
- `BackoffPolicy.LINEAR`: delay grows linearly (10 s, 20 s, 30 s …)
- `Result.retry()` in `doWork()` triggers the next attempt; `runAttemptCount` tracks how many times it has been tried

---

## Testing

```kotlin
// Use the synchronous executor in tests
val config = Configuration.Builder()
    .setMinimumLoggingLevel(Log.DEBUG)
    .setExecutor(SynchronousExecutor())
    .build()

WorkManagerTestInitHelper.initializeTestWorkManager(context, config)
val workManager = WorkManager.getInstance(context)

val request = OneTimeWorkRequestBuilder<SyncWorker>().build()
workManager.enqueue(request).result.get()

val info = workManager.getWorkInfoById(request.id).get()
assertThat(info.state).isEqualTo(WorkInfo.State.SUCCEEDED)
```

---

← [↑ Chapter Index](../) · [Next: BroadcastReceiver →](../02-broadcast-receiver/)
