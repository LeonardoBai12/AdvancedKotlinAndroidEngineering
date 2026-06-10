---
layout: page
title: "Chapter 8: ConcurrentHashMap & Concurrent Collections"
---
*Thread safety, atomic operations, and real-world Android caching*

A plain HashMap is not thread-safe. When two threads read and write simultaneously, the internal array can corrupt *silently* — no exception is thrown, you just get wrong or missing data, and in pathological cases (a resize racing a read) an infinite loop. Even a simple read-modify-write is unsafe without external synchronisation.

*The race condition a plain HashMap permits*

```kotlin
val map = HashMap<String, Int>()   // NOT thread-safe

// Thread A and Thread B run this simultaneously:
// map["count"] = (map["count"] ?: 0) + 1
//
// Both read 0, both write 1 -> final value is 1, not 2 (lost update).
// Worse, a concurrent resize can corrupt the bucket array entirely.
```

## Three Approaches — Why ConcurrentHashMap Wins

| Approach | Thread-safe | Performance | Use case |
| --- | --- | --- | --- |
| HashMap | No | Fast | Single-threaded only |
| Collections.synchronizedMap() | Yes | Slow — one global lock | Low concurrency |
| Hashtable | Yes | Slow — one global lock | Legacy code only |
| ConcurrentHashMap | Yes | Fast — CAS + bucket locks | Production multithreading |

ConcurrentHashMap divides its data into independent buckets. Instead of locking the entire map on every operation, it uses **CAS (Compare-And-Swap)** for reads (which are mostly lock-free) and fine-grained **per-bucket locks** for writes. Threads operating on different buckets proceed in parallel; a synchronised map serialises everything behind a single lock.

## Big O Under Concurrency

ConcurrentHashMap shares HashMap's Big O — all operations are amortised O(1). The difference is not asymptotic but in constant factors: atomic operations carry a small overhead from CAS or a bucket lock. Under low contention that overhead is negligible; under high contention it remains far cheaper than a fully synchronised map.

| Operation | HashMap | ConcurrentHashMap | Note |
| --- | --- | --- | --- |
| get(key) | O(1) | O(1) | Lock-free read via CAS |
| put(key, value) | O(1) avg | O(1) avg | Bucket-level lock on write |
| putIfAbsent | manual | O(1) | Atomic — no external sync |
| computeIfAbsent | manual | O(1)* | Lambda runs only on a cache miss |
| merge | manual | O(1)* | Atomic insert-or-combine |
| size() | O(1) | O(1) | Approximate under concurrency |

* The map access is O(1); the lambda you pass may have its own complexity — that cost is yours, not the map's.

## Atomic Operations Reference

Atomic operations are the real reason to choose ConcurrentHashMap over 'HashMap plus a lock'. Each executes as a single indivisible unit — no thread can interrupt it midway — which eliminates race conditions without any manual **synchronized** block.

### putIfAbsent — insert only if the key is missing

Inserts the pair only if the key is absent. Returns the existing value if the key was present, or null if it was absent and the insert succeeded. Beware: the value expression is *always* evaluated, even when it will not be used — so never pass an expensive call here.

*putIfAbsent*

```kotlin
val map = ConcurrentHashMap<String, Int>()
map["key"] = 5

val a = map.putIfAbsent("key", 99)  // key exists -> a = 5, map unchanged
val b = map.putIfAbsent("new", 99)  // key absent -> b = null, inserts 99

// WARNING: 99 is always computed. Avoid expensive args:
// map.putIfAbsent("key", expensiveOperation())  // wasteful on hit
```

### computeIfAbsent — lazy cache population

The lambda runs only on a cache miss, which makes this the primary pattern for thread-safe lazy initialisation — a clean replacement for double-checked locking.

*computeIfAbsent*

```kotlin
val cache = ConcurrentHashMap<String, UserProfile>()

// Lambda runs ONLY when the key is absent -- expensive call avoided on a hit
val profile = cache.computeIfAbsent("user123") {
    database.fetchProfile(it)
}

// Second call: key present -> lambda never runs, cached value returned
cache.computeIfAbsent("user123") { database.fetchProfile(it) }
```

### computeIfPresent — update only if the key exists

*computeIfPresent*

```kotlin
val scores = ConcurrentHashMap<String, Int>()
scores["player1"] = 100

// Key exists -> runs the lambda, updates the value
scores.computeIfPresent("player1") { _, current -> current + 50 } // 150

// Key absent -> does nothing, no entry created
scores.computeIfPresent("ghost") { _, current -> current + 50 }   // null

// Returning null removes the entry
scores.computeIfPresent("player1") { _, current ->
    if (current <= 0) null else current
}
```

### merge — insert or combine

The cleanest pattern for counters and accumulators. If the key is absent it inserts the value directly; if present it runs the lambda to combine the old and new values. Returning null removes the entry.

*merge — atomic counter*

```kotlin
val wordCount = ConcurrentHashMap<String, Int>()

wordCount.merge("kotlin", 1) { old, new -> old + new }  // absent -> inserts 1
wordCount.merge("kotlin", 1) { old, new -> old + new }  // present -> 1+1 = 2
wordCount.merge("kotlin", 1) { old, new -> old + new }  // 2+1 = 3
println(wordCount["kotlin"])  // 3

// Real analytics use:
fun trackEvent(userId: String) {
    eventCount.merge(userId, 1) { current, inc -> current + inc }
}
```

### compute — full control, always runs

*compute — session lifecycle in one atomic call*

```kotlin
sessions.compute(sessionId) { _, current ->
    when {
        current == null     -> Session.new()      // create
        current.isExpired() -> null               // remove (null deletes)
        else                -> current.refresh()  // extend
    }
}
```

### Choosing the right operation

| Operation | Key absent | Key exists | Lambda lazy? |
| --- | --- | --- | --- |
| put | Inserts | Overwrites | — |
| putIfAbsent | Inserts | Ignores | No — always evaluated |
| replace | Ignores | Overwrites | — |
| replace(k,old,new) | Ignores | Updates if value matches | — (CAS) |
| computeIfAbsent | Runs lambda, inserts | Ignores | Only on a miss |
| computeIfPresent | Ignores | Runs lambda, updates | Only on a hit |
| merge | Inserts value | Runs lambda, combines | Only on update |
| compute | Runs lambda | Runs lambda | Always runs |

## Real-World Android Patterns

### In-memory image cache

The canonical use case. **computeIfAbsent** guarantees the download runs exactly once per URL, even under concurrent access from many background threads.

*Thread-safe image cache*

```kotlin
class ImageCache {
    private val cache = ConcurrentHashMap<String, Bitmap>()

    fun get(url: String): Bitmap =
        cache.computeIfAbsent(url) { downloadImage(it) }  // once per URL

    fun invalidate(url: String) = cache.remove(url)
    fun clear() = cache.clear()
}

// GC-friendly variant for Bitmaps (prevents OOM):
val weakCache = ConcurrentHashMap<String, WeakReference<Bitmap>>()
```

### Analytics event counter

*AnalyticsTracker with merge*

```kotlin
class AnalyticsTracker {
    private val counts = ConcurrentHashMap<String, Int>()

    fun track(event: String) =
        counts.merge(event, 1) { current, inc -> current + inc }

    fun getCount(event: String) = counts.getOrDefault(event, 0)
    fun snapshot(): Map<String, Int> = HashMap(counts)  // safe copy
}
```

## ConcurrentHashMap vs Coroutine State

In modern Android, **StateFlow** and **Mutex** handle observable UI state better than a concurrent collection. ConcurrentHashMap remains the right tool for pure caches and lookup tables accessed from multiple threads outside a coroutine context.

| Tool | Best for |
| --- | --- |
| ConcurrentHashMap | Caches and lookup tables across threads |
| StateFlow | Observable UI state in ViewModels |
| Mutex | Complex state mutations inside coroutines (suspends, doesn't block) |

## Other Concurrent Collections

| Collection | Read | Write | Best for |
| --- | --- | --- | --- |
| ConcurrentHashMap | Fast (CAS) | Fast (bucket lock) | Cache, lookup table |
| CopyOnWriteArrayList | Fast (lock-free) | Slow O(N) — full copy | Listener lists, rare writes |
| CopyOnWriteArraySet | Fast (lock-free) | Slow O(N) | Small read-heavy sets |
| CHM.newKeySet() | Fast | Fast | High-write sets |
| ConcurrentLinkedQueue | Fast (CAS) | Fast (CAS) | Producer/consumer, no backpressure |
| LinkedBlockingQueue | Medium (lock) | Medium (lock) | Bounded work queue with backpressure |

---

[↑ Chapter Index](../)
