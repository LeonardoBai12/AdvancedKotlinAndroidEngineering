---
layout: page
title: "Chapter 5: Garbage Collection"
---
*Automatic memory management, reachability, leaks, and cleanup hooks*

The previous chapter showed how objects are laid out in memory. This one answers the next question: who frees that memory when an object is no longer needed? On the JVM and ART, the answer is the **garbage collector** (GC) — a background process that automatically reclaims memory occupied by objects the program can no longer reach. Understanding how it decides what to collect, why memory can still leak despite it, and how (and how not) to hook into the cleanup process is essential for writing apps that stay responsive and do not grow without bound.

## Manual vs Automatic Memory Management

In languages like C and C++ the programmer manages memory by hand: you allocate a block, and you are responsible for freeing it. This is powerful but error-prone — forget to free and you leak memory; free too early and you leave a **dangling pointer** to memory that may since have been reallocated for another purpose. Java and Kotlin instead delegate this to the garbage collector: you allocate freely, and the runtime frees what you stop using. You trade fine-grained control for safety and convenience.

### A tale of two NULLs (from The Pragmatic Programmer)

The Pragmatic Programmer poses a pair of exercises that perfectly illustrate the difference. First: why do some C/C++ developers set a pointer to NULL right after freeing the memory it references? Because the freed memory may soon be reallocated elsewhere, and a leftover pointer into it — a rogue reference — would silently read or corrupt unrelated data. Setting the pointer to NULL turns that latent corruption into an immediate, detectable failure: dereferencing NULL throws at runtime instead of quietly misbehaving.

Second, and more relevant to us: why do some Java (and Kotlin) developers set an object variable to null after they are finished with it? The motivation is completely different. Here you are not preventing a dangling pointer — the GC makes those impossible — you are *helping the GC collect sooner*. Nulling the reference removes one pointer to the object; once the last reference is gone, the object becomes eligible for collection and its memory can be reclaimed. This matters mainly in **long-running programs**, where you want to ensure memory usage does not creep upward over time.

|   | C / C++ (manual) | Java / Kotlin (GC) |
| --- | --- | --- |
| Who frees memory | The programmer | The garbage collector |
| Why set to NULL/null | Avoid a dangling pointer to freed memory | Drop a reference so the object can be collected |
| Risk it prevents | Reading/corrupting reallocated memory | Memory creeping up in a long-running app |
| Failure if you don't | Use-after-free, hard crashes | Higher memory use / a leak |

> **Key Insight:**
>
> The key insight: in C++, nulling a pointer defends against a *dangling reference* to memory you already freed. In Kotlin, nulling a reference is the opposite situation — you are telling the GC 'I'm done with this', letting it free memory you cannot free yourself. Same gesture, opposite purpose.

*Nulling a reference to let the GC reclaim it*

```kotlin
class ReportGenerator {
    private var hugeBuffer: ByteArray? = loadGigabytes()

    fun process() {
        useBuffer(hugeBuffer!!)
        hugeBuffer = null   // done with it -> now eligible for collection
        // In a long-running process this frees the memory promptly,
        // instead of holding gigabytes until the object itself dies.
    }
}
```

> **Warning:**
>
> Do not sprinkle **= null** everywhere. For ordinary short-lived local variables the GC collects them the moment the method returns and the reference goes out of scope — nulling adds noise and no benefit. Reserve it for genuinely large objects held by long-lived owners (a singleton, a cache, a long-running coroutine).

## Reachability — What 'Garbage' Means

The GC does not track when you are 'done' with an object directly — it tracks **reachability**. Starting from a set of **GC roots** (static fields, active local variables on a thread's stack, currently running threads), the collector walks every reference it can follow. Any object reachable from a root is kept; any object that *cannot* be reached by any chain of references is garbage and may be collected. 'No longer referenced' is the precise meaning of 'no longer needed'.

*Reachable vs unreachable*

```kotlin
var cache: Data? = Data()    // reachable from a root (the variable)
val temp = Data()            // reachable while 'temp' is in scope

cache = null                 // the first Data() is now UNREACHABLE -> garbage
// when the method holding 'temp' returns, that Data() becomes
// unreachable too, and both are eligible for the next GC cycle.
```

### Reference counting vs tracing

There are two broad ways to decide reachability. **Reference counting** keeps a count per object of how many references point to it, collecting when the count hits zero — simple, but it cannot reclaim **reference cycles** (two objects that point only to each other keep each other's count above zero forever). The JVM and ART instead use **tracing** collectors that walk the reference graph from the roots, which naturally handles cycles: two objects pointing at each other but unreachable from any root are both collected. (The Pragmatic Programmer exercise describes the intuition in reference-counting terms — 'reduce the count by one' — but the underlying tracing GC achieves the same effect without counting.)

## Generational Collection

Modern collectors exploit a well-observed pattern: **most objects die young**. A request handler allocates many short-lived objects that become garbage almost immediately, while a few objects (caches, singletons) live a long time. Generational GCs divide the heap into a **young generation** and an **old generation**. New objects start in the young generation, which is collected frequently and cheaply (a 'minor' GC); objects that survive several minor collections are promoted to the old generation, collected less often (a 'major' GC). This makes the common case — reclaiming short-lived garbage — fast.

> **Interview Tip:**
>
> On Android, GC pauses matter for jank. A collection that pauses the app for several milliseconds during scrolling drops frames. The practical defence is to *allocate less* in hot paths — avoid creating throwaway objects inside **onBindViewHolder**, per-frame draw code, or tight loops — so the GC has less young-generation garbage to chase. Primitive arrays over boxed collections (Memory chapter) is one concrete lever.

## Memory Leaks Despite a GC

Automatic collection does not make leaks impossible — it changes their shape. A **leak on the JVM/ART** is an object you no longer need that remains *reachable* from a GC root, so the collector is obliged to keep it. The memory is never reclaimed because, as far as the GC can tell, the object is still in use. On Android the classic culprits all involve a long-lived object holding a reference to a short-lived one.

- **A static (or singleton) reference to a Context or View**: the Activity is destroyed but the singleton still points at it, so the whole Activity and its view tree cannot be collected.
- **A non-static inner class or callback** (covered in the Idiomatic chapter): it implicitly holds the outer Activity, so an in-flight callback keeps the Activity alive.
- **A registered listener never unregistered**: the event source retains the listener, which retains whatever it closed over.
- **A coroutine in the wrong scope**: work launched in a scope that outlives the screen keeps the screen's objects reachable.

*A leak: a singleton pinning an Activity*

```kotlin
object SessionManager {
    var activity: Activity? = null   // DANGER: a static reference
}

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        SessionManager.activity = this  // the singleton now outlives the Activity
        // On rotation, this Activity is destroyed but cannot be collected:
        // SessionManager keeps it reachable -> the whole view tree leaks.
    }
}
// Fix: don't hold Activity/View in long-lived objects; use application
// Context where a Context is needed, and clear references in onDestroy().
```

## Hooking Into Cleanup

Sometimes an object owns a resource that the GC does *not* manage — a file handle, a socket, a native pointer. Reclaiming the object's Java memory does not close that resource, so you need a way to run cleanup code. There is a historical mechanism and a modern one; the difference is one of the more telling 'do not do this' lessons on the platform.

### finalize() — the historical hook, and why to avoid it

Historically you could override **finalize()**, a method the garbage collector calls on an object just before reclaiming it — in effect, adding your own step into the GC cycle. In principle this lets an object clean up after itself. In practice it is so problematic that it is deprecated, and you should not use it.

*finalize() -- DO NOT use this (shown for understanding)*

```kotlin
class FileWrapper {
    private val handle = openNativeFile()

    // Called by the GC before collecting -- but you cannot rely on it.
    protected fun finalize() {
        handle.close()   // intent: release the native file handle
    }
}
```

The problems are serious and compounding. There is **no guarantee finalize() ever runs**, and no guarantee about *when* — if the program exits or the object is never collected, the cleanup simply never happens, so a file or socket can stay open indefinitely. It imposes **overhead on the GC**: an object with a finalizer cannot be reclaimed in a single cycle — the collector must instead queue it, run the finalizer on a separate finalizer thread, and only free it on a *later* cycle, so finalizable objects live longer and pressure the heap. A slow or blocking finalizer stalls that shared thread and delays every other object's cleanup. And a finalizer can accidentally **resurrect** the object by storing **this** somewhere reachable, defeating the collection entirely.

### The modern replacements

The correct approach is to make cleanup *explicit and deterministic* rather than leaving it to the GC. Kotlin and the JDK provide the right tools.

- **AutoCloseable + use { }**: the idiomatic Kotlin pattern. An object that holds a resource implements **AutoCloseable**, and callers wrap it in **use { }**, which guarantees **close()** runs when the block ends — normally or via an exception. Cleanup is immediate and predictable, not whenever the GC happens to run.
- **Cleaner** (java.lang.ref.Cleaner): the sanctioned replacement for finalize() when you need a GC-triggered safety net. You register an object with a separate cleanup action that runs when the object becomes unreachable, without the resurrection and ordering hazards of finalize(). Treat it as a backstop, not the primary path.

*AutoCloseable + use {} -- deterministic cleanup*

```kotlin
class FileWrapper : AutoCloseable {
    private val handle = openNativeFile()
    override fun close() { handle.close() }   // explicit, predictable
}

// use {} calls close() automatically when the block ends -- even on throw
FileWrapper().use { wrapper ->
    wrapper.read()
}   // close() runs here, deterministically -- no waiting for the GC

// The standard library types already support this:
FileInputStream("data.bin").use { stream ->
    stream.readBytes()
}   // stream closed here, guaranteed
```

> **Key Insight:**
>
> Rule: manage resources with **use { }** / AutoCloseable, and manage memory by dropping references and letting the GC work. Never use finalize() — it is deprecated, unreliable, and adds GC overhead. If you need a GC-triggered backstop for a native resource, use **Cleaner**, but make the explicit **close()** the real cleanup path.

## Best Practices

- Let the GC do its job: allocate freely and drop references when done; do not micro-manage.
- Null out only **large** objects held by **long-lived** owners (singletons, caches) in long-running processes — not ordinary locals.
- Avoid allocation in hot paths (bind callbacks, per-frame code, tight loops) to reduce GC pauses and jank.
- Never hold an Activity/View/Context in a static or singleton field; prefer the application Context, and clear references on destroy.
- Use **use { }** / AutoCloseable for files, streams, and sockets — deterministic cleanup, no reliance on the GC.
- Never use **finalize()**; if a native-resource backstop is truly needed, use **Cleaner**.
- Profile suspected leaks with a tool such as LeakCanary, which reports objects retained after they should have been collected.

---

[↑ Chapter Index](../)
