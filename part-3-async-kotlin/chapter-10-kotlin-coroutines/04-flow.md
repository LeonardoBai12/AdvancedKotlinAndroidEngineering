---
layout: page
title: "Chapter 10: Kotlin Coroutines — Flow"
---

## Part 4 · Flow — Asynchronous Streams

## What Is a Flow?

A **Flow** is an asynchronous data stream that emits values over time. Think of it as a pipe through which data flows; you observe what comes out. Where a suspend function returns a single value, a Flow can emit many values, asynchronously, as they become available.

*A basic flow*

```kotlin
flow {
    emit(1)
    delay(100)
    emit(2)
    delay(100)
    emit(3)
}.collect { value ->
    println(value)   // prints 1, 2, 3
}
```

## The Three Flow Types

| Type | Hot / Cold | Holds a value? | Use case |
| --- | --- | --- | --- |
| Flow | Cold | No | API calls, DB queries, one-time operations |
| StateFlow | Hot | Yes (always) | UI state, current data, configuration |
| SharedFlow | Hot | No (configurable replay) | One-time events: navigation, toasts |

### Flow (Cold) — from the manuscript

Cold means the flow does not start running until someone collects it. Each collector gets a new, independent stream — collecting twice runs the producer twice. A cold flow stops when its work is done, which makes it ideal for database queries, API calls, and any one-time operation.

*Cold flow — each collection is a fresh execution*

```kotlin
val apiFlow = flow {
    println("Starting")
    emit(api.fetchData())   // the API is called here
}
// Nothing happens until collected:
apiFlow.collect { }   // API call #1
apiFlow.collect { }   // API call #2 -- a brand-new execution
```

### StateFlow (Hot) — from the manuscript

A StateFlow is always active and always holds a value. It requires an initial state, exposes a synchronous **.value**, and is conflated — it skips intermediate values, delivering only the latest to new collectors. Multiple collectors share the same state. It is the perfect tool for UI state, or anything with a 'current value' that behaves like Observable or LiveData.

*StateFlow in a ViewModel*

```kotlin
class MyViewModel : ViewModel() {
    private val _uiState = MutableStateFlow<UiState>(UiState.Loading)
    val uiState: StateFlow<UiState> = _uiState.asStateFlow()

    fun loadData() {
        viewModelScope.launch {
            _uiState.value = UiState.Loading
            try {
                _uiState.value = UiState.Success(repository.getData())
            } catch (e: Exception) {
                _uiState.value = UiState.Error(e.message)
            }
        }
    }
}
```

### SharedFlow (Hot) — from the manuscript

A SharedFlow is always active but holds no single 'current' value. It can replay a configurable number of past emissions, and unlike StateFlow it does *not* skip values — every emission matters. Multiple collectors share emissions, and importantly, actions do not repeat on configuration changes (rotation). This makes it the right choice for one-time events: navigation, toasts, snackbars, broadcasts, and notifications.

*SharedFlow for one-time events*

```kotlin
private val _events = MutableSharedFlow<Event>()
val events: SharedFlow<Event> = _events.asSharedFlow()

fun saveData() {
    viewModelScope.launch {
        try {
            repository.save()
            _events.emit(Event.ShowToast("Saved"))
            _events.emit(Event.NavigateBack)
        } catch (e: Exception) {
            _events.emit(Event.ShowError(e.message))
        }
    }
}
```

> **Interview Tip:**
>
> Use StateFlow for state that should survive and replay (the screen's current data), and SharedFlow for events that should fire exactly once (a navigation command). Using StateFlow for events causes the event to re-fire on rotation — a navigation loop or a duplicate toast.

## Flow Operators

### Transformation

*map, filter, transform*

```kotlin
flowOf(1, 2, 3).map { it * 2 }.collect { println(it) }       // 2, 4, 6
flowOf(1, 2, 3, 4).filter { it % 2 == 0 }.collect { }        // 2, 4

// transform -- emit multiple (or zero) values per input
flowOf(1, 2).transform { value ->
    emit(value)
    emit(value * 2)
}.collect { println(it) }   // 1, 2, 2, 4
```

### Combining and flattening

*combine, zip, flatMapConcat, flatMapLatest*

```kotlin
// combine -- latest value from each flow
combine(flow1, flow2) { a, b -> "$a$b" }.collect { }

// zip -- pair corresponding emissions
flowOf(1,2,3).zip(flowOf("A","B","C")) { n, l -> "$n$l" } // 1A, 2B, 3C

// flatMapLatest -- cancel the previous inner flow when a new value arrives
//                  (ideal for search-as-you-type)
queryFlow.flatMapLatest { query -> repository.search(query) }
```

### Side effects and context

*onEach, catch, flowOn*

```kotlin
flow { emit(1); throw Exception("Error!") }
    .onEach { println("emitting $it") }
    .catch { e -> emit(-1) }            // handle upstream errors, emit fallback
    .flowOn(Dispatchers.IO)             // upstream runs on IO
    .collect { println(it) }            // collection runs on the caller's dispatcher
```

## Flow Builders (from the manuscript)

| Builder | Use case |
| --- | --- |
| flow { } | Sequential emissions — the standard cold flow |
| callbackFlow { } | Convert a callback-based API into a Flow; awaitClose is mandatory |
| channelFlow { } | Concurrent emissions from multiple coroutines (uses send) |
| flowOf(...) | A fixed set of known values |
| asFlow() | Convert a collection or range into a flow |
| emptyFlow() | A flow that emits nothing |

### callbackFlow — converting callbacks

**callbackFlow** bridges callback-based APIs (location updates, sensor listeners) into the Flow world. Key functions: **trySend(value)** emits from inside the callback (non-blocking); **close(exception)** ends the flow; and **awaitClose { }** registers the cleanup that runs when the flow is cancelled — which is mandatory, or you leak the listener.

*callbackFlow with mandatory awaitClose*

```kotlin
fun observeLocation(): Flow<Location> = callbackFlow {
    val listener = object : LocationListener {
        override fun onLocationChanged(location: Location) {
            trySend(location)               // emit from the callback
        }
        override fun onProviderDisabled(p: String) {
            close(Exception("Location disabled"))
        }
    }
    locationManager.requestLocationUpdates(GPS_PROVIDER, 1000L, 10f, listener)

    awaitClose { locationManager.removeUpdates(listener) }   // MANDATORY cleanup
}
```

### channelFlow — concurrent emissions

A plain **flow { }** is sequential — you cannot emit from a launched child coroutine inside it. **channelFlow** lifts that restriction: it allows concurrent emissions from multiple coroutines via **send**, and completes automatically once all its launched blocks finish.

*channelFlow — parallel search across sources*

```kotlin
fun searchEverywhere(query: String): Flow<SearchResult> = channelFlow {
    launch { localDb.search(query).forEach { send(SearchResult.Local(it)) } }
    launch { remoteApi.search(query).forEach { send(SearchResult.Remote(it)) } }
    launch { cache.search(query).forEach { send(SearchResult.Cached(it)) } }
    // completes automatically when all three launch blocks finish
}
```

## Flow Lifecycle & Memory Leaks

Cold flows complete on their own after emitting all values — no leak risk. Hot flows (StateFlow, SharedFlow) are eternal: they never complete until their scope is cancelled. That is exactly where leaks creep in. If a Fragment collects a StateFlow in a raw **lifecycleScope.launch**, the collection never ends — on navigation away the Fragment is destroyed but the collector keeps running, and on return a second collector starts.

| Flow type | Completes when | Lifecycle |
| --- | --- | --- |
| Cold Flow | After emitting all values | Finite — self-completing |
| StateFlow | Never (until scope cancelled) | Eternal — needs lifecycle management |
| SharedFlow | Never (until scope cancelled) | Eternal — needs lifecycle management |

## Android Best Practices

### repeatOnLifecycle — the correct way to collect in UI

**repeatOnLifecycle** ties collection to a lifecycle state. It starts collecting when the lifecycle reaches the given state (typically STARTED) and automatically cancels collection when it drops below — then restarts on return. This is the standard, leak-free pattern for collecting hot flows in an Activity or Fragment.

*repeatOnLifecycle — no leaks*

```kotlin
class MyFragment : Fragment() {
    override fun onViewCreated(view: View, state: Bundle?) {
        viewLifecycleOwner.lifecycleScope.launch {
            viewLifecycleOwner.repeatOnLifecycle(Lifecycle.State.STARTED) {
                // collects when STARTED+, cancels when below STARTED,
                // restarts when STARTED again
                viewModel.state.collect { updateUI(it) }
            }
        }
    }
}
// In Compose, use collectAsStateWithLifecycle() instead.
```

### viewModelScope vs lifecycleScope

| viewModelScope | lifecycleScope |
| --- | --- |
| Survives configuration changes (rotation) | Tied to Activity/Fragment lifecycle |
| Cancelled when the ViewModel is cleared | Cancelled when destroyed |
| Use for business logic and data | Use for UI updates and flow collection |

## Common Pitfalls

- **GlobalScope** creates untracked coroutines that are hard to cancel and leak memory — use viewModelScope, lifecycleScope, or a managed custom scope.
- **runBlocking in production** blocks the thread and can cause ANRs — it is for tests and main() only.
- **Long work on Dispatchers.Main** freezes the UI — move it to IO or Default.
- **Expecting CoroutineExceptionHandler to catch async** — it won't; the exception is in the Deferred, so try-catch the await().
- **Not re-throwing CancellationException** breaks cancellation — always re-throw after cleanup.
- **Collecting flows directly in lifecycleScope** wastes resources when the UI is hidden — use repeatOnLifecycle.
- **Using Job() when you need SupervisorJob()** — one child's failure cancels every sibling.
- **Forgetting awaitClose in callbackFlow** — leaks the underlying listener.

---

← [Previous: Cancellation & Exceptions](../03-cancellation-exceptions/) · [↑ Chapter Index](../) · [Next: Channels →](../05-channels/)
