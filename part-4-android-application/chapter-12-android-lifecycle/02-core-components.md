---
layout: default
title: Core Components
parent: Android Lifecycle
nav_order: 2
---

*Service, BroadcastReceiver, ContentProvider — and how they fit in Clean Architecture*

Android's component model includes four application entry points the system knows how to start and route to: Activity, Service, BroadcastReceiver, and ContentProvider. Activity and Fragment lifecycles are covered in the main chapter. This section covers the other three — and closes with a concrete, real-world scenario that shows how they compose with Clean Architecture.

## Service

A Service runs in the background without a UI. It is **not** a coroutine: coroutines belong to a scope (ViewModel or lifecycle scope) and are cancelled when the scope ends. A Service has its own lifecycle, managed by the system, and survives navigation away from the screen.

### Three types of Service

| Type | Started by | Lifecycle | Use for |
| --- | --- | --- | --- |
| Started (background) | `startService` | Runs until `stopSelf()` or `stopService()` | Fire-and-forget; severely restricted on API 26+ |
| Foreground | `startForegroundService` + `startForeground()` | Runs until explicitly stopped; shows a persistent notification | Ongoing visible work: media playback, navigation, file download |
| Bound | `bindService` | Lives as long as at least one client is bound | Client-server within the app or across apps |

> **Android 8+ background restriction**: the system kills started background services shortly after the app enters the background. For deferrable background work, use **WorkManager**. For work that must run right now with no UI, use a **Foreground Service**.

---

### Foreground Service

A Foreground Service is visible to the user through a persistent notification. The system will not kill it under normal memory pressure.

```kotlin
class MusicPlaybackService : Service() {

    private lateinit var player: MediaPlayer

    override fun onCreate() {
        super.onCreate()
        player = MediaPlayer()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        // Must call startForeground within 5 seconds of the service starting
        startForeground(NOTIFICATION_ID, buildNotification())

        when (intent?.action) {
            ACTION_PLAY  -> player.start()
            ACTION_PAUSE -> player.pause()
            ACTION_STOP  -> { player.stop(); stopSelf() }
        }
        return START_STICKY  // system re-starts the service if killed
    }

    override fun onBind(intent: Intent?) = null  // not a bound service

    override fun onDestroy() {
        player.release()
        super.onDestroy()
    }

    private fun buildNotification(): Notification =
        NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("Now Playing")
            .setSmallIcon(R.drawable.ic_music)
            .addAction(
                R.drawable.ic_pause, "Pause",
                PendingIntent.getService(
                    this, 0,
                    Intent(this, MusicPlaybackService::class.java).apply { action = ACTION_PAUSE },
                    PendingIntent.FLAG_IMMUTABLE
                )
            )
            .build()

    companion object {
        const val ACTION_PLAY  = "play"
        const val ACTION_PAUSE = "pause"
        const val ACTION_STOP  = "stop"
        const val NOTIFICATION_ID = 1001
        const val CHANNEL_ID = "playback"
    }
}
```

**Manifest declaration** (required for every Service):

```xml
<service
    android:name=".MusicPlaybackService"
    android:foregroundServiceType="mediaPlayback"
    android:exported="false" />
```

---

### Bound Service

A Bound Service acts as a server. Clients bind to it, call methods via the returned `IBinder`, and unbind when done. The service is destroyed automatically when all clients unbind.

```kotlin
class DownloadService : Service() {
    private val binder = DownloadBinder()
    private var progress = 0

    inner class DownloadBinder : Binder() {
        fun getService(): DownloadService = this@DownloadService
    }

    fun getProgress() = progress

    override fun onBind(intent: Intent): IBinder = binder
}

// Client (Activity/Fragment) side
class DownloadActivity : ComponentActivity() {
    private var downloadService: DownloadService? = null
    private var bound = false

    private val connection = object : ServiceConnection {
        override fun onServiceConnected(name: ComponentName, service: IBinder) {
            downloadService = (service as DownloadService.DownloadBinder).getService()
            bound = true
        }
        override fun onServiceDisconnected(name: ComponentName) {
            bound = false
        }
    }

    override fun onStart() {
        super.onStart()
        bindService(Intent(this, DownloadService::class.java), connection, BIND_AUTO_CREATE)
    }

    override fun onStop() {
        super.onStop()
        if (bound) { unbindService(connection); bound = false }
    }
}
```

For cross-process bound services (IPC to another app), use AIDL — covered in Chapter 16 (IPC Mechanisms).

---

## BroadcastReceiver

A BroadcastReceiver responds to system-wide or app-internal broadcast Intents. Typical system broadcasts: device boot, network connectivity changes, battery level, incoming calls.

### Static vs Dynamic registration

| Registration | How | Survives app not running? | Use for |
| --- | --- | --- | --- |
| Static (manifest) | `<receiver>` in `AndroidManifest.xml` | Yes — with restrictions | `BOOT_COMPLETED`, install-triggered events |
| Dynamic (code) | `registerReceiver` / `unregisterReceiver` | Only while registered | UI-tied events, connectivity while app is active |

**Android 8+ implicit broadcast restriction**: most implicit broadcasts (e.g. `CONNECTIVITY_ACTION`) cannot be received by manifest-declared receivers — you register for them dynamically instead. Exceptions: `BOOT_COMPLETED`, locale and timezone changes.

```kotlin
// Dynamic receiver — tied to Activity/Fragment visibility
class NetworkActivity : ComponentActivity() {
    private val connectivityReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) {
            val cm = getSystemService(CONNECTIVITY_SERVICE) as ConnectivityManager
            val online = cm.activeNetworkInfo?.isConnectedOrConnecting == true
            if (online) viewModel.triggerSync()
        }
    }

    override fun onStart() {
        super.onStart()
        registerReceiver(
            connectivityReceiver,
            IntentFilter(ConnectivityManager.CONNECTIVITY_ACTION)
        )
    }

    override fun onStop() {
        super.onStop()
        unregisterReceiver(connectivityReceiver)
    }
}
```

```kotlin
// Static receiver — survives app death; schedule WorkManager here
class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Intent.ACTION_BOOT_COMPLETED) return
        WorkManager.getInstance(context).enqueueUniquePeriodicWork(
            "data-sync",
            ExistingPeriodicWorkPolicy.KEEP,
            PeriodicWorkRequestBuilder<SyncWorker>(1, TimeUnit.HOURS).build()
        )
    }
}
```

```xml
<receiver android:name=".BootReceiver" android:exported="false">
    <intent-filter>
        <action android:name="android.intent.action.BOOT_COMPLETED"/>
    </intent-filter>
</receiver>
<uses-permission android:name="android.permission.RECEIVE_BOOT_COMPLETED"/>
```

> `onReceive()` runs on the **main thread** with a **10-second timeout** — never do I/O or network calls here. Hand off immediately to WorkManager or launch a coroutine via `goAsync()`.

---

## ContentProvider

A ContentProvider exposes structured data to other apps (or within the same app) through a URI-based API backed by Binder IPC. It is Android's standard mechanism for controlled, cross-process data sharing.

### Structure

Every operation maps to one of five methods:

```kotlin
class NotesProvider : ContentProvider() {
    private lateinit var db: NotesDatabase

    override fun onCreate(): Boolean {
        db = NotesDatabase.getInstance(context!!)
        return true
    }

    // URI: content://com.example.notes/notes
    override fun query(
        uri: Uri, projection: Array<String>?, selection: String?,
        selectionArgs: Array<String>?, sortOrder: String?
    ): Cursor? = db.noteDao().rawQuery(selection, selectionArgs)

    override fun insert(uri: Uri, values: ContentValues?): Uri? { /* ... */ return null }
    override fun update(uri: Uri, values: ContentValues?,
                        selection: String?, args: Array<String>?) = 0
    override fun delete(uri: Uri, selection: String?, args: Array<String>?) = 0
    override fun getType(uri: Uri) = "vnd.android.cursor.dir/vnd.com.example.notes"
}
```

```xml
<provider
    android:name=".NotesProvider"
    android:authorities="com.example.notes"
    android:exported="false" />
```

### FileProvider — the most common ContentProvider use

`FileProvider` is a pre-built ContentProvider for sharing files with other apps securely. It replaces insecure `file://` URIs with `content://` URIs that carry temporary, permission-scoped access:

```kotlin
val photoFile = File(filesDir, "captured.jpg")
val contentUri: Uri = FileProvider.getUriForFile(
    this,
    "${applicationContext.packageName}.fileprovider",
    photoFile
)

val shareIntent = Intent(Intent.ACTION_SEND).apply {
    type = "image/jpeg"
    putExtra(Intent.EXTRA_STREAM, contentUri)
    addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)  // temporary read access
}
startActivity(Intent.createChooser(shareIntent, "Share photo"))
```

```xml
<provider
    android:name="androidx.core.content.FileProvider"
    android:authorities="${applicationId}.fileprovider"
    android:grantUriPermissions="true"
    android:exported="false">
    <meta-data
        android:name="android.support.FILE_PROVIDER_PATHS"
        android:resource="@xml/file_paths" />
</provider>
```

### When to use ContentProvider vs other mechanisms

| Mechanism | Best for |
| --- | --- |
| ContentProvider | Structured data shared across app boundaries; extending system APIs |
| FileProvider | File sharing via Intent with temporary, scoped permission |
| AIDL / Binder | Complex IPC with method calls between apps |
| Broadcast | One-way event notifications to multiple receivers |

Platform ContentProviders you already use every day: `ContactsContract` (contacts), `MediaStore` (photos, video, audio), `CalendarContract` (calendar events).

---

## Real Scenario: Offline-First with Clean Architecture

**Problem:** Show locally-cached data immediately while refreshing from the network in the background. No loading spinners. No stale data left on screen.

This is the "offline-first" / "single source of truth" pattern — the standard recommendation from the Android Developers documentation for production apps.

### How it works

```
User opens screen
       │
       ▼
  ViewModel collects from UseCase
       │
       ▼
  Repository: emit from Room immediately
       │
       ├──▶ UI shows cached data RIGHT NOW (no spinner)
       │
       ▼
  Repository: trigger remote refresh
       │
       ▼
  Remote data → upsert into Room
       │
       ▼
  Room's Flow auto-emits updated rows
       │
       ▼
  UI updates automatically — no manual refresh
```

### Layer by layer

```kotlin
// --- DOMAIN LAYER (pure Kotlin — zero Android imports) ---

interface UserRepository {
    fun getUsers(): Flow<List<User>>
    suspend fun syncUsers()
}

class GetUsersUseCase(private val repository: UserRepository) {
    operator fun invoke(): Flow<List<User>> = repository.getUsers()
}
```

```kotlin
// --- DATA LAYER ---

// Room DAO — returns a Flow that emits whenever the table changes
@Dao
interface UserDao {
    @Query("SELECT * FROM users ORDER BY name")
    fun observeAll(): Flow<List<UserEntity>>

    @Upsert
    suspend fun upsertAll(users: List<UserEntity>)
}

// Repository — Room is the source of truth; remote refreshes the local store
class UserRepositoryImpl(
    private val dao: UserDao,
    private val api: UserApi,
    private val ioDispatcher: CoroutineDispatcher = Dispatchers.IO
) : UserRepository {

    override fun getUsers(): Flow<List<User>> =
        dao.observeAll().map { entities -> entities.map { it.toDomain() } }

    override suspend fun syncUsers() = withContext(ioDispatcher) {
        val remote = api.getUsers()           // network call
        dao.upsertAll(remote.map { it.toEntity() })  // write to Room → triggers Flow
    }
}
```

```kotlin
// --- PRESENTATION LAYER ---

class UserListViewModel(
    private val getUsers: GetUsersUseCase,
    private val repository: UserRepository
) : ViewModel() {

    // StateFlow starts empty; Room emits as soon as the query runs
    val users: StateFlow<List<User>> = getUsers()
        .stateIn(
            scope = viewModelScope,
            started = SharingStarted.WhileSubscribed(5_000),
            initialValue = emptyList()
        )

    init {
        viewModelScope.launch { repository.syncUsers() }  // refresh on open
    }
}
```

```kotlin
// --- UI (Compose) ---

@Composable
fun UserListScreen(viewModel: UserListViewModel = viewModel()) {
    val users by viewModel.users.collectAsStateWithLifecycle()

    if (users.isEmpty()) {
        CircularProgressIndicator()  // only on truly first launch with empty DB
    } else {
        LazyColumn { items(users) { UserRow(it) } }
    }
}
```

### WorkManager for periodic background sync

For sync that must survive app death and run on a schedule, WorkManager is the right tool. It wraps `JobScheduler` under the hood and respects battery optimisation, network constraints, and device restarts.

```kotlin
// Worker lives in the data layer — calls only the Repository interface
@HiltWorker
class SyncUsersWorker @AssistedInject constructor(
    @Assisted context: Context,
    @Assisted params: WorkerParameters,
    private val repository: UserRepository   // injected by HiltWorkerFactory
) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result {
        return try {
            repository.syncUsers()
            Result.success()
        } catch (e: Exception) {
            if (runAttemptCount < 3) Result.retry() else Result.failure()
        }
    }
}

// Schedule once at app startup or from BootReceiver
fun schedulePeriodicSync(context: Context) {
    val request = PeriodicWorkRequestBuilder<SyncUsersWorker>(1, TimeUnit.HOURS)
        .setConstraints(
            Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED)
                .build()
        )
        .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 15, TimeUnit.MINUTES)
        .build()

    WorkManager.getInstance(context).enqueueUniquePeriodicWork(
        "user-sync",
        ExistingPeriodicWorkPolicy.KEEP,  // don't replace if already scheduled
        request
    )
}
```

### How BroadcastReceiver + WorkManager + Repository compose

```
BroadcastReceiver           WorkManager              Repository            Room
(connectivity restored)  →  Worker.doWork()  →  repository.syncUsers()  →  upsertAll()
       ▲                                                                       │
  system event                                                                 ▼
                                                                         Flow emits
                                                                               │
                                                                               ▼
                                                                     ViewModel StateFlow
                                                                               │
                                                                               ▼
                                                                         Compose UI
```

```kotlin
// BroadcastReceiver detects the signal, delegates immediately to WorkManager
class ConnectivityReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        // Never do I/O here — enqueue a Worker
        WorkManager.getInstance(context)
            .enqueue(OneTimeWorkRequestBuilder<SyncUsersWorker>().build())
    }
}
```

The critical property of this architecture: **no layer knows about the layer above it**.

- `BroadcastReceiver` knows only `WorkManager` — nothing about the ViewModel or UI
- `Worker` knows only the `UserRepository` interface — nothing about the scheduler or the UI
- `UserRepository` knows Room and Retrofit — nothing about the Worker or ViewModel
- `ViewModel` knows only use cases — nothing about Room, Retrofit, or WorkManager
- Compose knows only the `StateFlow` — nothing about any of the above

Each component is independently replaceable: swap the scheduler from WorkManager to AlarmManager, swap Room for another local store, swap Retrofit for Ktor — the rest of the app does not change.

### When to use which background mechanism

| Scenario | Mechanism | Reason |
| --- | --- | --- |
| Periodic data sync (hourly/daily) | WorkManager `PeriodicWorkRequest` | Survives reboots; respects battery optimisation; deferred |
| Immediate refresh while screen is visible | Coroutine in `viewModelScope` | Cancelled when user leaves — correct behavior |
| Long download the user must see progress for | Foreground Service | System requires a visible notification for long background work |
| Audio playback in the background | Foreground Service (`mediaPlayback`) | Must persist when app is backgrounded |
| React to network restored / device boot | BroadcastReceiver → WorkManager | Receiver detects the event; Worker does the work |
| Share a file with another app | FileProvider (ContentProvider) | `content://` URI with temporary permission grant |
| Cross-process API calls | Bound Service + AIDL | When another app needs to call methods on your service |

---

← [Chapter Index](../) · [Next: Jetpack Compose →](../../chapter-13-jetpack-compose/)
