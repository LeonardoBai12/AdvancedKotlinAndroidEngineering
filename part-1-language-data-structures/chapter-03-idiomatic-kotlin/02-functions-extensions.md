# Chapter 3: Idiomatic Kotlin — Functions & Extensions

## inline functions

When you call a higher-order function (one that takes a lambda), Kotlin normally allocates an object for that lambda on every call. Marking the function **inline** tells the compiler to copy the function's body — and the lambda's body — directly into the call site at compile time, eliminating the lambda allocation and the call overhead entirely. **This is the 'why' behind inline:** it removes per-call object allocation, which matters in hot paths and tight loops. The Kotlin standard library's **map**, **filter**, **let**, **apply**, and friends are all inline for exactly this reason.

*inline -- no lambda object is allocated*

```kotlin
inline fun measure(block: () -> Unit): Long {
    val start = System.nanoTime()
    block()                        // body copied into the call site
    return System.nanoTime() - start
}

val elapsed = measure { doWork() } // no lambda object created
```

### What inline unlocks: reified and crossinline

- **reified** type parameters: because the body is inlined, the concrete type is known at the call site, so you can write **inline fun <reified T> ...** and use **T::class** or **is T** — impossible in a normal generic function due to type erasure.
- **crossinline**: forbids a non-local return from a lambda that is passed to another execution context; **noinline**: opts a specific lambda parameter out of inlining.
- Caveat: don't inline large functions or those called in many places — copying a big body everywhere bloats the bytecode. Inline is for small higher-order functions.

*reified -- usable only because the function is inline*

```kotlin
inline fun <reified T> Gson.fromJson(json: String): T =
    fromJson(json, T::class.java)   // T::class works thanks to reified

val user: User = gson.fromJson(jsonString)  // no need to pass User::class
```

## value class (inline class)

A **@JvmInline value class** wraps a single value to create a distinct type, but the compiler *inlines* the underlying value wherever possible, so at runtime there is usually **no wrapper object allocated** — you get the type safety of a wrapper with the performance of the raw value.

**Why use it:** to stop mixing up values that happen to share a primitive representation. A function taking **(UserId, OrderId)** — both backed by String — will reject the arguments in the wrong order at compile time, whereas plain Strings (or a **typealias**) would compile and fail at runtime. That is the compile-time safety of a dedicated type, delivered without the usual allocation cost.

*value class -- type safety with no runtime wrapper*

```kotlin
@JvmInline value class UserId(val value: String)
@JvmInline value class OrderId(val value: String)

fun fetch(user: UserId, order: OrderId) { /* ... */ }

val u = UserId("u1")
val o = OrderId("o1")
fetch(u, o)        // OK
// fetch(o, u)     // COMPILE ERROR -- types don't match (caught early!)
// At runtime, UserId is represented directly as a String -- no allocation.
```

|   | typealias | value class |
| --- | --- | --- |
| Creates a new type? | No — just another name | Yes — a distinct type |
| Type safety? | None (interchangeable) | Full (mismatches rejected) |
| Runtime cost | Zero | Usually zero (inlined) |
| Use when | Improving readability | Preventing value mix-ups |

## Scope functions: let, run, with, apply, also

The five scope functions run a block in the context of an object; they differ in two ways: how the object is referenced inside the block (as **it** or as **this**), and what the block returns (the object itself, or the lambda result). Choosing the right one makes intent obvious.

| Function | Object referenced as | Returns | Typical use |
| --- | --- | --- | --- |
| let | it | lambda result | Null-safe transforms on a value |
| run | this | lambda result | Compute a result from an object |
| with | this (argument) | lambda result | Group calls on one object |
| apply | this | the object | Configure an object (builder style) |
| also | it | the object | Side effects (logging, validation) |

*Each scope function in context*

```kotlin
// let -- null-safe transform; runs only if non-null
user?.let { sendEmail(it.email) }

// run -- compute a result using the receiver
val area = rectangle.run { width * height }

// with -- group operations on one object (not an extension)
with(canvas) { drawLine(); drawCircle(); flush() }

// apply -- configure and return the same object (builder pattern)
val intent = Intent(this, DetailActivity::class.java).apply {
    putExtra("id", id)
    flags = Intent.FLAG_ACTIVITY_NEW_TASK
}

// also -- side effect, returns the object unchanged
val list = mutableListOf(1, 2).also { println("created: $it") }
```

## Extension functions & properties

Extensions let you add functions or properties to an existing type — even one you don't own, like String or a framework class — without inheriting from it.

**Why use it:** they keep call-sites fluent and put behaviour where it reads naturally, and they are a perfect tool for the Open-Closed Principle (extend without modifying). They are resolved statically — they do not actually modify the class — so they cannot access private members.

*Extensions*

```kotlin
fun String.isValidEmail(): Boolean = contains("@") && contains(".")
"a@b.com".isValidEmail()    // true

val String.lastChar: Char get() = this[length - 1]   // extension property

// Extension on a domain type, used elsewhere in this guide:
fun List<Task>.filterBy(query: String) = filter {
    query.lowercase() in it.title.lowercase()
}
```

## Delegation with by

Kotlin makes delegation a language feature via **by**. **Class delegation** forwards an interface's implementation to another object (composition over inheritance). **Property delegation** hands a property's get/set logic to a delegate — the standard library provides **lazy** (compute once on first access), **observable** (react to changes), and Android uses it heavily (e.g. **by viewModels()**).

*Property and class delegation*

```kotlin
// lazy -- computed once, on first access, thread-safe by default
val config: Config by lazy { loadExpensiveConfig() }

// observable -- run a callback on every change
var name: String by Delegates.observable("") { _, old, new ->
    println("$old -> $new")
}

// class delegation -- Repository gets Logger behaviour by composition
class Repository(logger: Logger) : Logger by logger

// Android: ViewModel delegation
private val viewModel: MyViewModel by viewModels()
```

---

← [Previous: Class Types](./01-class-types.md) · [↑ Chapter Index](./README.md) · [Next: Language Features →](./03-language-features.md)
