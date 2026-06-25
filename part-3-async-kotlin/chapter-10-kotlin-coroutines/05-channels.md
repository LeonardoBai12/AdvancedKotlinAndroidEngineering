---
layout: default
title: Channels
parent: Kotlin Coroutines
nav_order: 5
---

## Part 5 · Channels — Coroutine Communication Primitives

## What Is a Channel?

A **Channel** is a non-blocking communication primitive for passing values between coroutines. Think of it as a concurrent queue: one coroutine sends values in, another receives them out, and both can suspend rather than block while waiting.

Where a Flow is a declarative, cold data stream, a Channel is an imperative, hot data pipe — the producer and consumer are active, independent coroutines that communicate through a shared buffer.

*Channel basics*

```kotlin
val channel = Channel<Int>()

// Producer coroutine
launch {
    for (i in 1..5) {
        channel.send(i)         // suspends if the buffer is full
    }
    channel.close()             // signals no more values are coming
}

// Consumer coroutine
launch {
    for (value in channel) {    // suspends if no value is available
        println(value)          // prints 1, 2, 3, 4, 5
    }
}
```

> **Channel vs Flow:** A Channel is a *hot* communication primitive — values sent before a consumer is ready are buffered or the producer suspends. A Flow is *cold* — it only runs when collected. Prefer Flow for data streams with operators and lifecycle management; prefer Channels for producer–consumer pipelines and fan-out patterns.

*Kotlinx.coroutines documentation — Channel*

---

## Channel Types (Capacity)

The `Channel()` factory accepts a `capacity` parameter that controls buffering behaviour.

| Capacity | Factory constant | Behaviour |
| --- | --- | --- |
| 0 | `Channel.RENDEZVOUS` | Producer suspends until consumer is ready; no buffer |
| N | `Channel(N)` | Buffered up to N items; producer suspends only when full |
| `Int.MAX_VALUE` | `Channel.UNLIMITED` | Never suspends the producer; unlimited buffer (risk: OOM) |
| Conflated | `Channel.CONFLATED` | Buffer of 1; new value overwrites old; consumer always gets the latest |

*Rendezvous — strict handshake*

```kotlin
val rendezvous = Channel<String>(Channel.RENDEZVOUS)
// producer suspends at send() until consumer is at receive()
// guarantees that every value is handed off directly — no buffering at all
```

*Buffered — decouple producer from consumer*

```kotlin
val buffered = Channel<Int>(capacity = 64)
// producer can get 64 values ahead before it starts suspending
// smooths out burst production without losing values
```

*Conflated — only the latest matters*

```kotlin
val conflated = Channel<Float>(Channel.CONFLATED)
// old value is overwritten if the consumer hasn't picked it up yet
// useful for position updates, sensor data, progress values
conflated.send(0.1f)
conflated.send(0.5f)   // 0.1f is discarded
conflated.send(0.9f)   // 0.5f is discarded
println(conflated.receive())  // 0.9f
```

---

## The `produce` Builder

`produce` is the idiomatic way to create a producer coroutine. It returns a `ReceiveChannel<T>` and automatically closes the channel when the block completes or throws.

```kotlin
fun CoroutineScope.fibonacci(): ReceiveChannel<Long> = produce {
    var a = 0L
    var b = 1L
    while (true) {
        send(a)
        val next = a + b
        a = b
        b = next
    }
}

// Consumer
val fibs = fibonacci()
repeat(10) {
    print("${fibs.receive()} ")   // 0 1 1 2 3 5 8 13 21 34
}
fibs.cancel()
```

`produce` is structurally sound: when the consuming coroutine is cancelled, the producer coroutine is cancelled too. When the producer finishes or throws, the channel is closed and the consumer's `for (x in channel)` loop exits cleanly.

---

## Receiving from a Channel

Three ways to read from a `ReceiveChannel`:

```kotlin
// 1. receive() — suspends until a value is available (throws if channel is closed+empty)
val value = channel.receive()

// 2. receiveCatching() — returns ChannelResult, does not throw
val result = channel.receiveCatching()
result.getOrNull()?.let { println(it) }   // null if closed

// 3. for loop — iterates until the channel is closed
for (item in channel) {
    process(item)
}

// 4. consumeEach — convenience extension on ReceiveChannel
channel.consumeEach { process(it) }
```

---

## Fan-Out — Multiple Consumers

A single channel can feed multiple consumer coroutines. Each value is delivered to exactly one consumer — the one that happens to call `receive()` first. This is the classic worker-pool pattern.

```kotlin
fun CoroutineScope.taskChannel(): ReceiveChannel<Task> = produce {
    tasks.forEach { send(it) }
}

fun CoroutineScope.startWorker(id: Int, tasks: ReceiveChannel<Task>) = launch {
    for (task in tasks) {
        println("Worker $id processing $task")
        processTask(task)
    }
}

val tasks = taskChannel()
repeat(4) { id -> startWorker(id, tasks) }
// each task goes to exactly one worker
```

---

## Fan-In — Multiple Producers

Multiple producer coroutines can send into the same channel, merging their output into a single stream.

```kotlin
fun CoroutineScope.merge(vararg channels: ReceiveChannel<Int>): ReceiveChannel<Int> =
    produce {
        channels.forEach { ch ->
            launch {
                for (value in ch) send(value)
            }
        }
    }
```

---

## Pipelines

Channels compose naturally into **pipelines**: a sequence of stages where each stage reads from one channel and writes to the next.

```kotlin
fun CoroutineScope.numbers(): ReceiveChannel<Int> = produce {
    var x = 1
    while (true) send(x++)
}

fun CoroutineScope.square(input: ReceiveChannel<Int>): ReceiveChannel<Int> = produce {
    for (n in input) send(n * n)
}

fun CoroutineScope.filter(input: ReceiveChannel<Int>, pred: (Int) -> Boolean)
    : ReceiveChannel<Int> = produce {
        for (n in input) if (pred(n)) send(n)
    }

// pipeline: numbers → filter evens → square
val numbers = numbers()
val evens   = filter(numbers) { it % 2 == 0 }
val squares = square(evens)

repeat(5) { print("${squares.receive()} ") }  // 4 16 36 64 100
squares.cancel()
```

---

## Channel vs Flow — When to Use Which

| Concern | Channel | Flow |
| --- | --- | --- |
| Hot / Cold | Hot — active by default | Cold — lazy on collection |
| Operators | Minimal (no built-in map/filter) | Rich operator set |
| Multiple consumers | Built-in fan-out | SharedFlow with `shareIn` |
| Lifecycle management | Manual cancel | `repeatOnLifecycle`, `stateIn` |
| Back-pressure | Suspend / buffer / conflate | `buffer()`, `conflate()` operators |
| Best use | Coroutine-to-coroutine communication, pipelines, worker pools | Data streams, UI state, API/DB results |

> **Interview Tip:**
>
> Channels are a *lower-level* primitive. In most Android code, Flow is the right default because it composes better, integrates with `repeatOnLifecycle`, and has richer operators. Reach for Channels when you need an explicit handoff queue between coroutines — a worker pool, a pipeline stage, or a message-passing design where the producer and consumer run at different rates.

---

## `select` — Waiting on Multiple Channels

`select` lets a coroutine wait for whichever of several channels (or deferred values) is ready first.

```kotlin
suspend fun selectExample(ch1: ReceiveChannel<String>, ch2: ReceiveChannel<Int>) {
    select {
        ch1.onReceive { value -> println("String: $value") }
        ch2.onReceive { value -> println("Int: $value") }
    }
    // executes the first branch that becomes available
}
```

---

## Closing and Cancellation

A channel is closed by calling `close()` on the `SendChannel`. Once closed and drained, consumers see a `ClosedReceiveChannelException` if they call `receive()`, or the for-loop exits cleanly.

```kotlin
val ch = Channel<Int>(5)
launch {
    (1..5).forEach { ch.send(it) }
    ch.close()                          // signal: no more sends
}

for (x in ch) println(x)               // 1 2 3 4 5 — then loop exits

// Cancelling the consuming scope also cancels the producer (with produce{})
```

**Key rule**: always close a channel when the producer finishes. An unclosed channel causes the consumer's for-loop to hang forever waiting for a value that never arrives.

---

← [Previous: Flow](../04-flow/) · [↑ Chapter Index](../)
