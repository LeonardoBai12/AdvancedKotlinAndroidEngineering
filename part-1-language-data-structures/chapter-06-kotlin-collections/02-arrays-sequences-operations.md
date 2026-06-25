---
layout: default
title: Arrays Sequences Operations
parent: Kotlin Collections
nav_order: 2
---

## Arrays & Primitive Arrays

How an array works at the level of memory — a contiguous block giving O(1) indexed access and O(N) resizing — was covered in the Memory & Hashing Fundamentals chapter. Here we focus on the one array decision that matters most in day-to-day Android code: **boxed vs primitive**. **Array<Int>** stores boxed **Integer** objects, each carrying object-header overhead; **IntArray** stores raw **int** values in a contiguous primitive buffer. For large numeric datasets the memory difference is roughly fourfold, and the primitive variant also generates far less GC pressure.

| Type | Element | JVM Representation | Memory @ 1M elements |
| --- | --- | --- | --- |
| Array<Int> | Boxed Integer | Object[] | ~16 MB |
| IntArray | Primitive int | int[] | ~4 MB |
| LongArray | Primitive long | long[] | ~8 MB |
| DoubleArray | Primitive double | double[] | ~8 MB |
| BooleanArray | Primitive boolean | boolean[] | ~1 MB |

*Boxed vs primitive array allocation*

```kotlin
// Boxed -- a million Integer objects, each ~16 bytes of overhead
val boxed = Array(1_000_000) { it }      // ~16 MB

// Primitive -- one contiguous int buffer, 4 bytes per element
val primitive = IntArray(1_000_000) { it }  // ~4 MB
```

## Sequences — Lazy Evaluation

Collection operations in Kotlin are **eager** by default: each operator in a chain runs to completion and produces a brand-new intermediate list before the next operator begins. For a three-operator chain over a large list, that is three full passes and two throwaway allocations. **Sequences** are the lazy alternative: operators are deferred and fused into a single pass that runs only when a terminal operator (such as **toList()**, **first()**, or **sum()**) demands a result. Crucially, a Sequence can also stop early.

*Eager collections vs lazy sequences*

```kotlin
// EAGER -- 2 full passes over 1,000,000 elements + 2 intermediate lists
val eager = (1..1_000_000)
    .map { it * 2 }          // allocates a list of 1,000,000
    .filter { it > 1000 }    // allocates ANOTHER large list
    .take(10)                // finally slices off 10

// LAZY -- single fused pass; stops the instant 10 results exist
val lazy = (1..1_000_000).asSequence()
    .map { it * 2 }          // deferred -- nothing happens yet
    .filter { it > 1000 }    // deferred
    .take(10)                // still deferred
    .toList()                // terminal -> runs, stops after 10
```

> **Interview Tip:**
>
> Use a Sequence when the collection is large (rule of thumb: more than ~100 elements) AND you chain multiple operations, or when early termination is possible. For small collections or a single operation, the per-element overhead of a Sequence outweighs the savings — a plain eager collection is faster.

## The Common Operation Toolkit

Kotlin's standard library provides a rich, expressive set of collection operators. Knowing them fluently lets you replace imperative loops with declarative one-liners. They group into a few families.

| Family | Operators |
| --- | --- |
| Transform | map, mapNotNull, flatMap, flatten |
| Filter | filter, filterNot, filterNotNull, take, drop, takeWhile |
| Aggregate | reduce, fold, sum, count, min, max, average |
| Element | first, last, single, find, elementAt, getOrNull |
| Order | sorted, sortedBy, sortedByDescending, reversed, shuffled |
| Group | groupBy, partition, chunked, windowed, associateBy |

### Transformation: map, flatMap, flatten

These three are constantly confused in interviews, so be precise. **map** transforms each element and returns a new collection of the *same size*. **flatMap** transforms each element into a *collection*, then flattens all those collections into one. **flatten** takes an existing collection-of-collections and flattens it into a single collection.

*map vs flatMap vs flatten*

```kotlin
val numbers = listOf(1, 2, 3)

// map -- transforms each element; result has the SAME size (3 -> 3)
numbers.map { it * 2 }                  // [2, 4, 6]

// flatMap -- each element becomes a collection, then all are flattened
numbers.flatMap { listOf(it, it * 10) } // [1, 10, 2, 20, 3, 30]

// flatten -- collapses a collection of collections into one
listOf(listOf(1, 2), listOf(3, 4)).flatten()  // [1, 2, 3, 4]

// Real example: all tags across all articles, de-duplicated
val allTags = articles.flatMap { it.tags }.toSet()
```

### Grouping: groupBy, partition, chunked

**groupBy** takes a key selector and returns a **Map** from each key to the list of elements that produced it. **partition** takes a boolean predicate and splits the collection into a **Pair** of two lists — those that matched and those that did not. **chunked** divides the collection into smaller lists of at most N elements each; the final chunk may be smaller than N.

*groupBy, partition, chunked*

```kotlin
val words = listOf("apple", "ant", "banana", "cherry", "avocado")

// groupBy -- builds a Map<Key, List<T>>
val byFirst = words.groupBy { it.first() }
// {a=[apple, ant, avocado], b=[banana], c=[cherry]}

// partition -- splits into Pair<matched, notMatched> by a boolean
val (short, long) = words.partition { it.length <= 5 }
// short = [apple, ant];  long = [banana, cherry, avocado]

// chunked -- sub-lists of at most N; the last one may be smaller
listOf(1, 2, 3, 4, 5).chunked(2)   // [[1, 2], [3, 4], [5]]
```

### Aggregation and element access

**reduce** combines elements left-to-right with no seed value (and throws on an empty collection). **fold** is the safer cousin: it takes an explicit initial accumulator, so it works on empty collections and lets the result type differ from the element type. **find** returns the first match or null; **single** returns the one and only element, throwing if there are zero or more than one.

*reduce, fold, find, single*

```kotlin
val nums = listOf(1, 2, 3, 4, 5)

nums.sum()                           // 15
nums.reduce { acc, n -> acc + n }    // 15  (no seed; throws if empty)
nums.fold(100) { acc, n -> acc + n } // 115 (seed = 100; safe on empty)
nums.find { it > 3 }                 // 4   (first match, or null)
nums.single { it == 3 }              // 3   (throws if 0 or >1 match)

// fold can change the result type: build a String from Ints
nums.fold("") { acc, n -> "$acc$n" }  // "12345"
```

## Quick Decision Guide

| You need… | Use |
| --- | --- |
| Ordered elements, duplicates allowed | List (ArrayList) |
| Frequent random access by index | ArrayList |
| Frequent insert/remove at the ends | ArrayDeque / LinkedList |
| Unique elements, fastest membership test | HashSet |
| Unique elements in insertion order | LinkedHashSet |
| Unique elements kept sorted | TreeSet |
| Key-value pairs, O(1) access | HashMap |
| Key-value pairs sorted by key | TreeMap |
| Fixed-size numeric data, memory-critical | IntArray / LongArray |
| Large collection + multiple chained ops | Sequence (asSequence) |
| Thread-safe concurrent read/write | ConcurrentHashMap (Chapter 5) |

### Best practices

- Prefer **List** over **Array** for almost everything; reserve primitive arrays for performance-critical numeric code.
- Declare variables with the interface type (**List**, not **ArrayList**) so the implementation can change freely.
- Expose **read-only** interfaces (List, Set, Map) from public APIs — never leak a mutable collection.
- Use immutable factories (**listOf**, **setOf**, **mapOf**) by default; reach for the mutable variants only when you actually mutate.
- Replace hand-written loops with operators (**map**, **filter**, **groupBy**) — they are clearer and less error-prone.
- Use a **Sequence** for large multi-step pipelines to avoid intermediate allocations.

---

← [Previous: Collection Types](../01-collection-types/) · [↑ Chapter Index](../)
