# Chapter 12: Android Lifecycle

*Activity, Fragment, Compose, configuration changes, and surviving process death*

The previous chapter explained how your code is *built* into an app. This one explains how that app *lives* at runtime. Android components do not run from start to finish like a desktop program with a main() that owns the process — the system creates, pauses, resumes, and destroys them in response to user actions and resource pressure. Understanding the lifecycle is what separates an app that leaks memory and loses state on rotation from one that behaves correctly. It also ties together threads we have already pulled: why viewModelScope survives rotation, why repeatOnLifecycle exists, and why onNewIntent matters for deep links.

## Why a Lifecycle Exists

Android runs on resource-constrained devices and must juggle many apps. Rather than let every app hold its resources indefinitely, the system actively manages component lifetimes: it can stop a screen the user navigated away from, and reclaim its memory when another app needs it. Your job is to react to these transitions — acquiring resources when a component becomes active and releasing them when it does not — so the app stays responsive and leak-free.

## The Activity Lifecycle

An Activity moves through a fixed sequence of callbacks as it is created, becomes visible, comes to the foreground, and is torn down again. There are **seven** callbacks — the six most people remember, plus **onRestart()**, which is the one usually forgotten and the key to understanding what happens when the user comes back. Each callback is the place to do — and to undo — one specific kind of work.

| Callback | Called when… | Typical work |
| --- | --- | --- |
| onCreate() | The Activity is first created (once per instance) | Inflate UI, init ViewModel, one-time setup |
| onStart() | It becomes visible to the user | Register observers, start UI updates |
| onResume() | It reaches the foreground and is interactive | Resume animations, acquire camera/sensors |
| onPause() | It is losing the foreground (still partly visible) | Pause animations, release the camera quickly |
| onStop() | It is no longer visible | Stop heavy UI work, unregister observers |
| onRestart() | A stopped Activity is about to become visible again | Re-prepare anything torn down in onStop() |
| onDestroy() | It is being destroyed (finished or recreated) | Final cleanup of remaining resources |

### The full launch-to-destroy sequence

On a cold launch the callbacks fire strictly in order until the Activity is interactive; on the way out they fire in the reverse order. The crucial detail the diagrams omit is that the Activity does *not* always re-enter at the top — where it re-enters depends on how far down it went.

*The ordered sequence and where each transition returns*

```kotlin
LAUNCH (cold start):
  onCreate() -> onStart() -> onResume()        // now interactive

FINISH / destroy:
  onPause() -> onStop() -> onDestroy()         // reverse order

// Where it RE-ENTERS depends on how far down it went:

A) Another activity/dialog partially covers it (still partly visible):
  onPause()                    // stops here
  -> onResume()                // returns straight to onResume (NOT onStart)

B) Fully hidden (Home pressed, or another full-screen activity opens):
  onPause() -> onStop()        // stops here
  -> onRestart() -> onStart() -> onResume()   // comes back via onRestart
  // NOTE: it does NOT call onCreate again -- the instance still exists

C) Process / instance destroyed (back pressed, or system reclaim):
  onPause() -> onStop() -> onDestroy()
  -> onCreate() -> onStart() -> onResume()    // a BRAND-NEW instance
```

The three return paths above are what most explanations gloss over. The rule of thumb: if the Activity was only **paused** (case A), it resumes directly through **onResume()**. If it was fully **stopped** but the instance survived (case B), it returns through **onRestart() → onStart() → onResume()** — note that **onRestart()** runs *before* **onStart()**, and **onCreate()** is *not* called because the object was never destroyed. Only if the instance was actually **destroyed** (case C) does the cycle begin again at **onCreate()**, with a fresh instance.

### The three nested lifetimes

The callbacks pair up into three nested lifetimes, and the pairing tells you exactly where to acquire and release each kind of resource: whatever you start in one half, undo in its partner.

*Acquire and release in symmetric pairs*

```kotlin
onCreate()  <-> onDestroy()   // the ENTIRE lifetime (once each)
  onStart() <-> onStop()      //   the VISIBLE lifetime (may repeat)
    onResume() <-> onPause()  //     the FOREGROUND lifetime (may repeat)

// Register an observer in onStart(), unregister it in onStop().
// Acquire the camera in onResume(), release it in onPause().
// The visible and foreground lifetimes can repeat many times within
// a single create..destroy lifetime (cases A and B above).
```

> **Warning:**
>
> onPause() must be fast — the next Activity's onResume() will not run until your onPause() returns, so slow work here visibly delays the next screen. Do only quick things (release the camera, pause an animation) in onPause(); put anything heavier in onStop(), which has no such time pressure.

## The Fragment Lifecycle

Fragments have a lifecycle that mirrors the Activity's but adds view-specific callbacks, because a Fragment's *view* can be created and destroyed multiple times while the Fragment instance itself lives on (for example, when added to the back stack). This split is the source of the single most common Fragment bug.

- **onAttach() / onCreate()**: the Fragment is attached and created.
- **onCreateView() / onViewCreated()**: the Fragment's *view* is built — wire up the UI here.
- **onDestroyView()**: the view is torn down, but the Fragment instance may survive — release view references here.
- **onDestroy() / onDetach()**: the Fragment instance itself goes away.

> **Avoid:**
>
> Always use **viewLifecycleOwner** (not the Fragment's own lifecycle) when observing LiveData or collecting flows tied to the view. The Fragment can outlive its view; observing with the wrong owner leaks the old view or updates a destroyed one.

## Configuration Changes — the Rotation Problem

By default, a configuration change — most famously a screen rotation, but also language, dark mode, or window-size changes — **destroys and recreates the Activity**. onDestroy() runs, then a fresh onCreate(). Any state held in plain fields is lost. There are three layered mechanisms for surviving this, each suited to a different kind of state.

| Mechanism | Survives rotation? | Survives process death? | Use for |
| --- | --- | --- | --- |
| Plain fields | No | No | Transient, recomputable state |
| ViewModel | Yes | No | Screen UI state, in-flight work |
| SavedStateHandle / onSaveInstanceState | Yes | Yes | Small, critical state (IDs, text) |
| Persistent storage (Room/DataStore) | Yes | Yes | Data that must truly persist |

This is precisely why **viewModelScope** survives rotation: the ViewModel is retained across the recreation, so coroutines launched in its scope are not cancelled when the Activity is rebuilt. It is also why one-time events belong in a SharedFlow rather than a StateFlow — a retained StateFlow would re-emit its last value into the freshly created UI, re-firing the event (a duplicate toast, or a navigation loop) after every rotation.

*ViewModel survives, SavedStateHandle survives more*

```kotlin
class EditorViewModel(
    private val savedState: SavedStateHandle
) : ViewModel() {
    // Survives rotation (ViewModel retained) AND process death (SavedState)
    var draftTitle: String
        get() = savedState["title"] ?: ""
        set(value) { savedState["title"] = value }

    // Survives rotation only -- lost if the process is killed in the background
    private val _results = MutableStateFlow<List<Item>>(emptyList())
    val results = _results.asStateFlow()
}
```

## Process Death — the State Most Apps Forget

When the app is in the background and the system needs memory, it may kill the entire process. On return, Android recreates the task and the user expects to land where they left off — but ViewModels and all in-memory state are gone. Only state saved through SavedStateHandle / onSaveInstanceState (for small, critical values) or persisted to storage (for real data) survives. A robust app treats process death as a normal event, not an edge case: save the minimum needed to reconstruct the screen, and restore it on recreation.

> **Interview Tip:**
>
> Test process death deliberately: background the app, then use 'Don't keep activities' in Developer Options, or run **adb shell am kill your.package.name**. Many bugs that never appear in normal use surface immediately under this test.

## The Compose Lifecycle

Compose adds its own lifecycle *on top of* the host Activity or Fragment lifecycle, and it is important to see that these are **two different levels** that coexist. The Activity lifecycle (onCreate … onDestroy) governs the screen as a whole; the Compose lifecycle governs individual composables *within* that screen, and it is organised around the **composition** — the tree of composables currently on screen — rather than around screen visibility. A composable has three phases.

| Phase | Meaning |
| --- | --- |
| Enters the composition | The composable runs for the first time |
| Recomposes | It re-runs because state it reads changed (0..N times) |
| Leaves the composition | It is removed from the UI tree |

### How the two levels connect

The composition is created inside the Activity's **setContent { }** call, so it lives within the Activity lifecycle: when the Activity is destroyed and recreated (a rotation), the entire composition is torn down and rebuilt from scratch. State that must survive that rebuild therefore cannot live in the composition alone — it belongs in a **ViewModel** (survives rotation) or, with **rememberSaveable**, in the saved-instance bundle. A plain **remember** only survives *recomposition*, not the Activity being recreated. This is the bridge between the two lifecycles: composables hold transient UI state, the ViewModel holds state that outlives the composition, and SavedStateHandle/rememberSaveable holds what must outlive even the process.

Side effects must respect the composition lifecycle, which is what the effect APIs are for. **LaunchedEffect** runs a coroutine tied to the composition, cancelled automatically when the composable leaves or its key changes. **DisposableEffect** registers something with a matching cleanup in its **onDispose**. **rememberCoroutineScope** gives a scope tied to the composition for launching work from callbacks.

*Compose effect APIs respect the composition lifecycle*

```kotlin
@Composable
fun UserScreen(userId: String, viewModel: UserViewModel) {
    // Runs when entering composition; re-runs if userId changes;
    // cancels automatically when leaving composition.
    LaunchedEffect(userId) {
        viewModel.load(userId)
    }

    // Register + guaranteed cleanup
    DisposableEffect(Unit) {
        val listener = registerSomeListener()
        onDispose { listener.unregister() }
    }

    val state by viewModel.state.collectAsStateWithLifecycle()  // lifecycle-aware
    // ... render state ...
}
```

The link back to the Activity lifecycle is **collectAsStateWithLifecycle()**. A plain **collectAsState()** keeps collecting even while the Activity is stopped (screen off, app backgrounded), wasting work and risking leaks. **collectAsStateWithLifecycle()** is the Compose analogue of **repeatOnLifecycle** from the Coroutines chapter: it ties flow collection to the host's STARTED state, automatically pausing when the Activity stops and resuming when it returns — connecting the composition-level collection to the Activity-level lifecycle.

## Lifecycle-Aware Components

Rather than manually wiring observers in onStart()/onStop(), modern Android exposes the lifecycle as an observable through **LifecycleOwner** and the Jetpack Lifecycle library. Components implement **DefaultLifecycleObserver** and react to transitions themselves, which keeps the Activity/Fragment thin and prevents the classic 'forgot to unregister in onStop' leak. **lifecycleScope** and **repeatOnLifecycle** are built on this same machinery.

*A lifecycle-aware observer*

```kotlin
class LocationObserver(
    private val onUpdate: (Location) -> Unit
) : DefaultLifecycleObserver {
    override fun onStart(owner: LifecycleOwner) { startUpdates() }
    override fun onStop(owner: LifecycleOwner)  { stopUpdates() }   // auto-cleanup
}

// In the Activity/Fragment:
lifecycle.addObserver(LocationObserver { updateMap(it) })
// start/stop now happen automatically -- nothing to remember to undo.
```

## Lifecycle Best Practices

- Acquire and release in symmetric pairs (onStart/onStop, onResume/onPause).
- Keep UI state in a ViewModel; keep small critical state in SavedStateHandle; persist real data to Room/DataStore.
- Always observe with **viewLifecycleOwner** in Fragments, never the Fragment's own lifecycle.
- Use **repeatOnLifecycle** (Views) or **collectAsStateWithLifecycle** (Compose) to collect hot flows safely.
- Prefer **DefaultLifecycleObserver** over manual register/unregister in lifecycle callbacks.
- Test rotation *and* process death — they fail differently and both are common in the wild.
- Avoid long work in lifecycle callbacks; they run on the main thread.

---

[↑ Chapter Index](./README.md)
