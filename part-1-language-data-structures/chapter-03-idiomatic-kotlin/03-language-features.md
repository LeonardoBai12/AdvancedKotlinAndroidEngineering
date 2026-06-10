---
layout: page
title: "Chapter 3: Idiomatic Kotlin — Language Features"
---

## Null Safety

Kotlin's type system separates nullable (**String?**) from non-nullable (**String**) types, moving the NullPointerException from a runtime surprise to a compile-time concern. The operators that work with it are core idiom.

| Operator | Name | Behaviour |
| --- | --- | --- |
| `?.` | Safe call | Calls only if non-null; otherwise yields null |
| `?:` | Elvis | Provides a fallback when the left side is null |
| `!!` | Not-null assertion | Throws NPE if null — use sparingly |
| `?.let { }` | Safe-call + let | Runs a block only when non-null |

*Null-safety operators and smart casts*

```kotlin
val length = name?.length ?: 0       // safe call + Elvis fallback
val forced = name!!.length           // throws if name is null (avoid)

user?.let { register(it) }           // run only when non-null

// Smart cast: after a null check, the compiler treats it as non-null
if (name != null) {
    println(name.length)             // no ?. needed -- smart-cast to String
}
```

## Destructuring Declarations

Destructuring unpacks an object into several variables at once, using the **componentN()** operators introduced in the data class section — data classes, Pairs, and Map entries all provide them.

**Why use it:** it reads cleanly when you need several pieces of an object at once, especially when iterating.

*Destructuring*

```kotlin
val (id, name, age) = user                 // data class
val (key, value) = mapEntry                // Map.Entry
for ((index, item) in list.withIndex()) {} // index + element
val (success, failure) = list.partition { it.isValid }  // Pair
```

## infix Functions & Operator Overloading

An **infix** function can be called without the dot and parentheses, reading like a natural operator (**1 to "one"** uses the infix **to** function). **Operator overloading** lets your types respond to built-in operators (**+**, **[]**, **in**) by implementing specially-named **operator** functions.

**Why use it:** for domain types where an operator reads more clearly than a method — vectors, money, ranges — but use it judiciously; surprising operators hurt readability.

*infix and operator*

```kotlin
// infix -- 'to' builds a Pair; this is how mapOf entries are written
val pair = 1 to "one"
infix fun Int.times(s: String) = s.repeat(this)
3 times "ab"                      // "ababab"

// operator overloading
data class Vec(val x: Int, val y: Int) {
    operator fun plus(o: Vec) = Vec(x + o.x, y + o.y)
}
Vec(1, 2) + Vec(3, 4)             // Vec(4, 6)
```

## Generics

Generics let a class, interface, or function work over many types while staying type-safe. Instead of writing a separate container for every element type — or falling back to **Any** and losing all type information — you write the logic once with a **type parameter**, conventionally named **T** (or **E** for element, **K**/**V** for key/value). The compiler then enforces the concrete type at each use site. **List<String>** and **Map<K, V>** are the everyday examples.

### Why generics: the alternative is worse

Without generics you would either duplicate code per type or store everything as **Any**, which forces casting on the way out and defers type errors to runtime. A generic container keeps the element type, so the compiler catches mistakes and no cast is needed.

*Any (unsafe) vs a generic class (safe)*

```kotlin
// WITHOUT generics -- everything is Any; casts and runtime errors
class AnyBox(val value: Any)
val b = AnyBox("hello")
val s = b.value as String       // manual cast; blows up if it wasn't a String

// WITH a generic type parameter T -- type is preserved, no cast
class Box<T>(val value: T)
val box = Box("hello")          // T inferred as String
val str: String = box.value     // no cast -- the compiler knows it's String
val n = Box(42)                 // T inferred as Int
```

### Generic functions

A function can declare its own type parameter, written between **fun** and the function name. The type is usually inferred from the arguments, so callers rarely state it explicitly.

*Generic functions*

```kotlin
fun <T> firstOrNull(list: List<T>): T? = if (list.isEmpty()) null else list[0]

val name: String? = firstOrNull(listOf("a", "b"))  // T inferred as String
val num:  Int?    = firstOrNull(listOf(1, 2, 3))    // T inferred as Int

// A generic function with two type parameters
fun <K, V> pairOf(key: K, value: V): Pair<K, V> = Pair(key, value)
```

### Constraints (upper bounds)

By default a type parameter accepts any type, so inside the generic code you can only use the members of **Any?**. An **upper bound** constrains T to a supertype, which both restricts the accepted types and unlocks that supertype's members inside the body. Use the **:** syntax for a single bound, or a **where** clause for several.

*Constraining a type parameter*

```kotlin
// T must be Comparable, so we can call compareTo / use < and >
fun <T : Comparable<T>> max(a: T, b: T): T = if (a > b) a else b
max(3, 7)            // OK -- Int is Comparable
max("a", "b")        // OK -- String is Comparable
// max(User(), User()) // ERROR -- User is not Comparable

// Multiple bounds with 'where'
fun <T> sync(item: T) where T : Closeable, T : Runnable { /* ... */ }
```

## Variance — in, out, and invariance

Variance — a frequent interview trap — governs how a generic type relates across its type parameter's subtypes. The key question: given that Dog is a subtype of Animal, is **Box<Dog>** a subtype of **Box<Animal>**? There are three possible answers, and Kotlin lets you choose with **in**, **out**, or neither.

### Invariance — plain <T> (the default)

A plain type parameter with no modifier is **invariant**: **Box<Dog>** and **Box<Animal>** have *no* subtype relationship, even though Dog is an Animal. This is the default, and it is the safe choice for any type that both reads and writes T, because allowing either substitution would break type safety. A **MutableList<T>** is invariant for exactly this reason: if you could pass a **MutableList<Dog>** where a **MutableList<Animal>** is expected, the callee could legally add a Cat to it, corrupting your list of dogs.

*Invariant <T> -- no substitution either way*

```kotlin
class Box<T>(var value: T)        // invariant: both reads and writes T

val dogBox: Box<Dog> = Box(Dog())
// val a: Box<Animal> = dogBox    // ERROR -- not covariant
// val b: Box<Dog> = animalBox    // ERROR -- not contravariant
// You may only assign Box<Dog> to Box<Dog>.

// Why it must be invariant when writing is allowed:
// if Box<Dog> were a Box<Animal>, this would compile and corrupt the box:
//   val animals: Box<Animal> = dogBox   // (hypothetically)
//   animals.value = Cat()               // a Cat in a Box<Dog>!
```

### out — covariance (producers)

Mark a type parameter **out** when the type only ever *produces* (returns) T and never consumes it. Then **Box<Dog>** *is* a **Box<Animal>**. This is safe precisely because you can only read T out: reading a Dog where an Animal is expected is always fine. This is why the read-only **List<out E>** is covariant while the writable **MutableList<T>** is invariant.

### in — contravariance (consumers)

Mark a type parameter **in** when the type only ever *consumes* (accepts) T and never produces it. Then a **Comparator<Animal>** can be used where a **Comparator<Dog>** is expected — anything that can compare any two animals can certainly compare two dogs. Memory aid: **PECS** — Producer-**out**, Consumer-**in**.

*invariant vs out vs in*

```kotlin
// INVARIANT (default) -- reads AND writes T -> no substitution
class MutableBox<T>(var value: T)

// out -- covariant producer (only returns T)
class Box<out T>(val value: T)             // note: val, read-only
val dogs: Box<Dog> = Box(Dog())
val animals: Box<Animal> = dogs            // OK because of 'out'

// in -- contravariant consumer (only accepts T)
interface Sink<in T> { fun put(item: T) }  // only consumes T
val animalSink: Sink<Animal> = TODO()
val dogSink: Sink<Dog> = animalSink        // OK because of 'in'

// reified generic (needs inline -- see the inline functions section)
inline fun <reified T> List<*>.filterIsInstanceOf(): List<T> =
    filter { it is T }.map { it as T }
```

| Declaration | Variance | T is used to… | Subtyping |
| --- | --- | --- | --- |
| Box<T> | Invariant | Both read and write | None (Box<Dog> ≠ Box<Animal>) |
| Box<out T> | Covariant | Only produce (read) | Box<Dog> is a Box<Animal> |
| Box<in T> | Contravariant | Only consume (write) | Box<Animal> is a Box<Dog> |

> **Interview Tip:**
>
> Interview phrasing that signals mastery: 'Kotlin generics are invariant by default — that's the plain <T>, used whenever the type both reads and writes, like MutableList. I add **out** when it is only produced (like List) and **in** when it is only consumed (like Comparator) — Producer-out, Consumer-in.'

---

← [Previous: Functions & Extensions](../02-functions-extensions/) · [↑ Chapter Index](../)
