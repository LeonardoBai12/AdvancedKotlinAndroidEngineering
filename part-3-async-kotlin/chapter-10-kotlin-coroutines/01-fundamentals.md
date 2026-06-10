---
layout: page
title: "Chapter 10: Kotlin Coroutines"
---

*Suspension, scopes, dispatchers, builders, cancellation, Flow, and Android lifecycle*

Coroutines are Kotlin's answer to asynchronous programming. They let you write sequential, readable code that nonetheless runs concurrently, without the callback pyramids of the past. This is the longest chapter in the guide because coroutines touch everything in modern Android: networking, database access, UI state, and lifecycle management. We build up from first principles — what suspension actually is — through scopes, dispatchers, builders, structured concurrency, cancellation, and the entire Flow family.

## Part 1 · Fundamentals

## What Is a Coroutine?

A coroutine is a **suspendable computation** — a piece of code that can pause its execution and resume later, without blocking the thread it was running on. That single property — suspend without block — is what makes coroutines both powerful and lightweight.

### Why coroutines are lightweight

A thread is an expensive, OS-managed resource: roughly 1 MB of stack memory each, with a practical ceiling around 2,000 threads on a 2 GB device. A coroutine is a cheap, JVM-managed object: roughly 100 bytes (a Continuation), and you can create millions of them. The catch, and a frequent interview clarification, is that 'lightweight' does not mean threads aren't used — it means coroutines are multiplexed onto a small pool of reusable threads.

*100,000 coroutines on 8 threads*

```kotlin
repeat(100_000) {
    launch(Dispatchers.Default) {
        delay(1000)        // suspends -- releases the thread
        println("Done")
    }
}
// Executes on only ~8 threads (assuming 8 CPU cores). How?
//   1. 100,000 Continuation objects are created in memory.
//   2. The dispatcher's pool has 8 threads.
//   3. At delay(), the coroutine SUSPENDS and the thread is released.
//   4. The freed thread picks up the next coroutine from the queue.
//   5. After the delay, the coroutine is re-queued and resumed.
```

### The suspension mechanism

The difference between blocking and suspending is the heart of the matter. **Thread.sleep()** blocks the thread — it sits there, occupied and wasted, doing nothing. **delay()** suspends the coroutine and frees the thread to run other work, resuming the coroutine later when the delay elapses.

*Blocking vs suspending*

```kotlin
// Regular function -- BLOCKS the thread for 1 second (wasted)
fun loadDataBlocking(): Data {
    Thread.sleep(1000)
    return data
}

// Suspend function -- SUSPENDS the coroutine, frees the thread
suspend fun loadData(): Data {
    delay(1000)        // thread is free to do other work meanwhile
    return data
}
```

## Scope vs Dispatcher

These two concepts are fundamental and serve completely different purposes. Confusing them is the root of most coroutine bugs.

| Concept | Governs | The question it answers |
| --- | --- | --- |
| CoroutineScope | Lifecycle — WHEN and HOW LONG coroutines run | When does this get cancelled? |
| CoroutineDispatcher | Threading — WHERE coroutines execute | Which thread runs this code? |

### CoroutineScope — the lifecycle boundary

A scope defines the lifecycle boundary for the coroutines launched inside it. When the scope is cancelled, every coroutine within it is cancelled too. This is the basis of **structured concurrency** — coroutines form a parent-child tree, and cancelling a parent cancels the whole subtree, which is what prevents leaks.

*Scope structure and cancellation*

```kotlin
val scope = CoroutineScope(Dispatchers.Main + Job())
scope.launch { /* coroutine 1 */ }
scope.launch { /* coroutine 2 */ }
scope.launch { /* coroutine 3 */ }

scope.cancel()   // cancels ALL coroutines in this scope at once
```

### Common scopes in Android

| Scope | Lifetime | Default dispatcher |
| --- | --- | --- |
| GlobalScope | Application lifetime — avoid! Never auto-cancelled | Dispatchers.Default |
| lifecycleScope | Activity / Fragment — cancelled on destroy (rotation) | Main.immediate |
| viewModelScope | ViewModel — survives rotation, cancelled when cleared | Main.immediate |
| Custom scope | Whatever you define — you must cancel it yourself | Whatever you configure |

*A custom scope must be cancelled explicitly*

```kotlin
class MyRepository {
    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    fun cleanup() {
        scope.cancel()   // otherwise its coroutines leak
    }
}
```

### CoroutineDispatcher — the thread scheduler

A dispatcher decides which thread or thread pool runs the coroutine. You can switch dispatchers mid-coroutine with **withContext** without creating a new scope.

| Dispatcher | Thread pool | Use for |
| --- | --- | --- |
| Dispatchers.Main | Single UI thread | UI updates, lightweight work |
| Dispatchers.Main.immediate | UI thread, skips re-dispatch if already there | Performance-critical UI updates |
| Dispatchers.IO | Up to 64 threads (shared with Default) | Network, database, file I/O |
| Dispatchers.Default | Threads = CPU cores (min 2) | Parsing, sorting, heavy computation |
| Dispatchers.Unconfined | Caller thread, then wherever it resumes | Testing only — unpredictable |

*Switching threads within one coroutine*

```kotlin
launch(Dispatchers.Main) {
    updateUI()                       // on the Main thread
    withContext(Dispatchers.IO) {
        fetchData()                  // switched to an IO thread
    }
    updateUI()                       // back on Main automatically
}
```

> **Warning:**
>
> Dispatchers.IO and Dispatchers.Default share the same 64-thread pool, just configured differently. Dispatchers.Unconfined starts on the caller thread but resumes on whatever thread the suspending function happened to use — so the thread changes after every suspension point. That makes it dangerous for UI code; reserve it for tests.

## Job and its Lifecycle

A **Job** represents a cancellable unit of work with a lifecycle. Every coroutine builder returns one (or a subtype). A Job moves through states: New, Active, Completing, Completed — or, if cancelled, Cancelling then Cancelled.

*Job state and joining*

```kotlin
val job = launch {
    delay(1000)
    println("Done")
}
println(job.isActive)     // true
println(job.isCompleted)  // false
println(job.isCancelled)  // false

job.join()    // suspend until the job finishes
// job.cancel()  // request cancellation
```

## Job vs SupervisorJob

This distinction controls how failure propagates among sibling coroutines. With a plain **Job**, if one child fails it cancels the parent and therefore all its siblings — all-or-nothing. With a **SupervisorJob**, children fail independently: one failure does not touch the others.

| Aspect | Job | SupervisorJob |
| --- | --- | --- |
| A child fails | Cancels parent and all siblings | Only that child fails |
| Exception propagation | Propagates up to the root | Contained to the failed child |
| Use case | All-or-nothing (transaction-like) | Independent operations |
| Example | A multi-step DB transaction | Several independent API calls |

*Job vs SupervisorJob behaviour*

```kotlin
// Job -- one failure cancels the sibling
val scope = CoroutineScope(Job())
scope.launch { delay(1000); throw Exception("Failed!") }
scope.launch { delay(2000); println("NOT printed -- cancelled") }

// SupervisorJob -- failures are isolated
val supScope = CoroutineScope(SupervisorJob())
supScope.launch { delay(1000); throw Exception("Failed!") }
supScope.launch { delay(2000); println("WILL print -- unaffected") }
```

---

[↑ Chapter Index](../) · [Next: Coroutine Builders →](../02-coroutine-builders/)
