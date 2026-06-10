# Chapter 10: Kotlin Coroutines — Coroutine Builders

## Part 2 · Coroutine Builders

## launch — Fire and Forget

**launch** starts a coroutine and returns immediately with a **Job** for lifecycle control, but no result value. Use it for side effects: UI updates, logging, fire-and-forget work. Its exception behaviour: exceptions propagate immediately to the parent, cancelling siblings (unless under a SupervisorJob).

*launch returns a Job, not a value*

```kotlin
val job = viewModelScope.launch {
    val data = fetchData()
    updateUI(data)         // side effect; nothing is returned
}
job.cancel()               // we can control its lifecycle
```

## async / await — Concurrent Computation

**async** starts a coroutine that returns a result through a **Deferred<T>**, Kotlin's equivalent of a Future or Promise. Call **await()** to suspend until the value is ready. Its primary use is running independent operations in parallel.

*Sequential vs parallel — the key win of async*

```kotlin
// Sequential (slow): 2 seconds total
suspend fun loadDataSequential() {
    val user  = fetchUser()    // 1 second
    val posts = fetchPosts()   // 1 second
}

// Parallel (fast): 1 second total
suspend fun loadDataParallel() {
    val userDeferred  = async { fetchUser() }   // starts immediately
    val postsDeferred = async { fetchPosts() }  // starts immediately
    val user  = userDeferred.await()            // both already running
    val posts = postsDeferred.await()
}
```

*Real-world parallel load in a ViewModel*

```kotlin
fun loadUserData(userId: String) {
    viewModelScope.launch {
        try {
            // All three run in parallel
            val userDef      = async { userApi.getUser(userId) }
            val postsDef     = async { postsApi.getPosts(userId) }
            val followersDef = async { followersApi.getFollowers(userId) }

            _uiState.value = UiState.Success(
                userDef.await(), postsDef.await(), followersDef.await()
            )
        } catch (e: Exception) {
            _uiState.value = UiState.Error(e.message)
        }
    }
}
```

> **Warning:**
>
> Critical async gotcha: exceptions are NOT thrown immediately. They are stored inside the Deferred and re-thrown only when you call **await()**. A CoroutineExceptionHandler does NOT catch them — you must wrap the **await()** in try-catch.

## Deferred Methods (from the manuscript)

A **Deferred<T>** is like a Promise — it represents a future value. Beyond **await()** it offers several useful methods.

*The Deferred API*

```kotlin
// await() -- suspends until the result is ready, then returns it
val user = deferred.await()

// awaitAll() -- waits for multiple Deferred in parallel
val users = userIds.map { id -> async { api.getUser(id) } }.awaitAll()

// isCompleted -- check if ready (non-suspending)
if (deferred.isCompleted) { /* ... */ }

// getCompleted() -- get the result WITHOUT suspending;
//                   throws if it is not ready yet
val result = deferred.getCompleted()

// cancel() -- cancel the computation
deferred.cancel()
```

## withContext — Switch Execution Context

**withContext** suspends, switches the dispatcher (or other context element), runs its block, and returns the result — all without creating a new scope. It is the idiomatic way to move heavy work off the main thread inside a suspend function. Prefer it over launching a new coroutine just to change threads.

*withContext for thread switching*

```kotlin
viewModelScope.launch {                     // on Main
    _uiState.value = UiState.Loading
    val user = withContext(Dispatchers.IO) {
        database.getUser()                  // switched to IO
    }                                       // back to Main
    _uiState.value = UiState.Success(user)
}
```

## withTimeout — Enforce a Time Limit

*withTimeout and withTimeoutOrNull*

```kotlin
// Throws TimeoutCancellationException on timeout
try {
    val result = withTimeout(5000) { fetchFromSlowApi() }
} catch (e: TimeoutCancellationException) {
    println("Operation timed out")
}

// Returns null instead of throwing
val result = withTimeoutOrNull(5000) { fetchFromSlowApi() }
if (result == null) println("Timed out")
```

## runBlocking — The Blocking Bridge

**runBlocking** blocks the current thread until all coroutines inside it complete. It bridges blocking and non-blocking worlds, and its legitimate uses are narrow: the **main()** function and tests. Never use it in production Android code — blocking a thread (especially Main) defeats the entire purpose of coroutines and causes ANRs.

*runBlocking — tests and main() only*

```kotlin
fun main() = runBlocking {
    launch { delay(1000); println("World") }
    println("Hello")
}
// Output: Hello, World
```

## Builder Decision Guide

| Need | Builder |
| --- | --- |
| A result value | async |
| Fire-and-forget | launch |
| Switch thread/context | withContext |
| A timeout | withTimeout / withTimeoutOrNull |
| A blocking bridge (tests only) | runBlocking |

---

← [Previous: Fundamentals](./01-fundamentals.md) · [↑ Chapter Index](./README.md) · [Next: Cancellation & Exceptions →](./03-cancellation-exceptions.md)
