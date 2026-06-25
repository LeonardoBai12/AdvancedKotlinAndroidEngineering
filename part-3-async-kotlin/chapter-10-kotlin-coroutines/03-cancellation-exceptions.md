---
layout: default
title: "Chapter 10: Kotlin Coroutines — Cancellation & Exceptions"
parent: "Chapter 10: Kotlin Coroutines"
nav_order: 3
---

## Part 3 · Cancellation & Exception Handling

## Cooperative Cancellation

Coroutines are not forcefully killed — cancellation is **cooperative**. A coroutine must check for cancellation, either at a suspension point (most suspend functions check automatically) or manually in long CPU-bound loops. A loop that never suspends and never checks **isActive** will keep running even after cancellation.

| Method | Behaviour | When to use |
| --- | --- | --- |
| isActive | Boolean check, no exception | Conditional work, manual loop checks |
| ensureActive() | Throws CancellationException if cancelled | Fast failure when cancelled |
| yield() | Suspends, checks cancellation, lets others run | Long CPU-intensive loops |

*Cooperative cancellation in a loop*

```kotlin
// Bad -- never checks, so cancellation is ignored
launch {
    while (true) { /* expensive work, never stops */ }
}

// Good -- checks isActive, stops promptly on cancel
launch {
    while (isActive) { /* expensive work */ }
}
```

*ensureActive() and yield() (from the manuscript)*

```kotlin
// ensureActive() -- throws if cancelled; fast-failure pattern
repeat(1000) {
    ensureActive()
    doWork()
}

// yield() -- throws CancellationException if cancelled, AND
//            suspends to let other coroutines run. Ideal for
//            CPU-intensive loops that must stay cooperative.
repeat(10000) {
    yield()
    heavyWork()
}
```

### Always re-throw CancellationException

**CancellationException** is used internally to implement cancellation. If you catch it in a broad **catch (e: Exception)** and swallow it, you break the cancellation machinery. Always re-throw it after any cleanup.

*Correct exception handling around cancellation*

```kotlin
launch {
    try {
        doWork()
    } catch (e: CancellationException) {
        cleanup()
        throw e            // MUST re-throw -- never swallow
    } catch (e: Exception) {
        handleError(e)     // handle real errors here
    }
}
```

## CoroutineExceptionHandler — Critical Rules (from the manuscript)

**CoroutineExceptionHandler** is a last-resort mechanism for *uncaught* exceptions, and it works only in very specific situations.

| Works with | Does NOT work with |
| --- | --- |
| Root coroutines launched with launch | async builder (exception lives in the Deferred) |
| Coroutines in supervisorScope | Child coroutines (they delegate to the parent) |
| A handler installed in the CoroutineScope | Non-root coroutines |

*Where the handler works and where it doesn't*

```kotlin
val handler = CoroutineExceptionHandler { _, e -> Log.e("TAG", "Caught: $e") }

// WORKS -- handler on a root launch
GlobalScope.launch(handler) { throw Exception() }   // caught

// DOES NOT WORK -- async stores the exception in the Deferred
val deferred = GlobalScope.async(handler) { throw Exception() }  // handler never called
// Correct way for async:
try { deferred.await() } catch (e: Exception) { /* handle here */ }
```

## Mutex — Mutual Exclusion (from the manuscript)

A **Mutex** is a lock that ensures only one coroutine accesses a shared resource at a time, avoiding race conditions. Unlike a thread lock, acquiring it suspends rather than blocks. The idiomatic form is **withLock**, which acquires and releases automatically — even if the body throws or is cancelled.

*Mutex with withLock*

```kotlin
val mutex = Mutex()

launch {
    mutex.withLock {
        // only one coroutine at a time runs here
        sharedCounter++
    }   // lock released automatically, even on exception/cancellation
}
```

### Atomic start — guaranteeing the finally block runs

A subtle but important manuscript note: when you must guarantee a critical cleanup (such as unlocking a Mutex) even if the coroutine is cancelled before it starts, launch it with **start = CoroutineStart.ATOMIC**. This guarantees the body begins executing even if cancellation arrives first, so your **finally** block runs and the Mutex is released.

*CoroutineStart.ATOMIC ensures finally runs*

```kotlin
mutex.lock()
val job = lifecycleScope.launch(start = CoroutineStart.ATOMIC) {
    try {
        // executes even if the activity is destroyed first
        doSomething()
    } finally {
        mutex.unlock()   // guaranteed to run, releasing the lock
    }
}
```

---

← [Previous: Coroutine Builders](../02-coroutine-builders/) · [↑ Chapter Index](../) · [Next: Flow →](../04-flow/)
