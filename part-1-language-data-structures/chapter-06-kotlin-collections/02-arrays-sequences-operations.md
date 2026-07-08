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

## String vs StringBuilder

`String` in Kotlin (and Java) is **immutable**. Every concatenation with `+` creates a brand-new `String` object on the heap and copies all the characters from the operands. In isolation that is fine. Inside a loop, it compounds:

```kotlin
var result = ""
for (item in list) {
    result += item  // new String allocated on every iteration
}
```

If `list` has N items of average length L, the first iteration copies L characters, the second 2L, the third 3L — the total work is L + 2L + 3L + … + NL = **O(N² · L)**. A loop over 10,000 items with 10-character strings does ~500 million character copies.

`StringBuilder` maintains a mutable `char[]` internally and appends in place, doubling capacity when the buffer fills — the same amortised strategy as `ArrayList`. Total work: **O(N · L)**.

```kotlin
val sb = StringBuilder()
for (item in list) {
    sb.append(item)      // O(1) amortised — no copy of previous content
}
val result = sb.toString()  // one final String allocation
```

**When Kotlin handles it for you:** string templates (`"$a $b"`) and simple `+` chains outside loops are compiled to `StringBuilder` automatically by `kotlinc`. The danger is explicit `+=` inside a loop — the compiler does not optimize that pattern, and the quadratic cost is real.

> **Interview Tip:**
>
> If asked to build a string from a list, always reach for `joinToString()` (which uses `StringBuilder` internally) or `buildString {}`. Never accumulate with `+=` in a loop.

---

## SparseArray — Android's Integer-Key Map

`HashMap<Int, V>` on the JVM requires **boxing**: every `Int` key is wrapped into an `Integer` object, adding object-header overhead and GC pressure. For a map with 500 view positions or resource IDs, that is 500 unnecessary heap allocations.

`SparseArray<V>` eliminates boxing entirely. It stores keys as a plain `int[]` and values in a parallel `Object[]`, with no wrapper objects. Internally it maintains the key array in sorted order and uses **binary search** for lookups — O(log N) instead of O(1) — but the eliminated boxing and improved cache locality make it faster than `HashMap<Int, V>` in practice for the small collections typical in Android code.

| Type | Key storage | Lookup | Memory | Best for |
| --- | --- | --- | --- | --- |
| `HashMap<Int, V>` | Boxed `Integer` | O(1) avg | Higher (object overhead) | Large N, O(1) needed |
| `SparseArray<V>` | Primitive `int` | O(log N) | Lower (no boxing) | Small N (< ~1000), int keys |

Android provides specialised variants for both ends:

| Class | Key | Value | Use case |
| --- | --- | --- | --- |
| `SparseArray<V>` | `int` | Object | General int-keyed map |
| `SparseIntArray` | `int` | `int` | Both sides unboxed (e.g. position → count) |
| `SparseBooleanArray` | `int` | `boolean` | Checked states, selection flags |
| `SparseLongArray` | `int` | `long` | ID → timestamp maps |

```kotlin
// HashMap<Int, String> -- Int is boxed to Integer on every put/get
val map = HashMap<Int, String>()
map[42] = "item"

// SparseArray<String> -- 42 stored as primitive int, no boxing
val sparse = SparseArray<String>()
sparse.put(42, "item")
val value = sparse.get(42)     // "item"
sparse.delete(42)
val size = sparse.size()       // 0
```

**When to use SparseArray:** when the keys are integers and the map stays small — view IDs, adapter positions, resource IDs, checked item indices. The binary-search overhead is negligible at these sizes, and the memory savings and reduced GC pressure are real.

**When to prefer HashMap:** when the collection can grow large (thousands of entries), when O(1) guarantees matter, or when you are in a context that expects a `Map<Int, V>` interface (interop, libraries).

---

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
| Thread-safe concurrent read/write | ConcurrentHashMap (Chapter 8) |
| Int-keyed map, small N, no boxing | SparseArray / SparseIntArray |
| Build a string from many parts | StringBuilder / buildString {} |

### Best practices

- Prefer **List** over **Array** for almost everything; reserve primitive arrays for performance-critical numeric code.
- Declare variables with the interface type (**List**, not **ArrayList**) so the implementation can change freely.
- Expose **read-only** interfaces (List, Set, Map) from public APIs — never leak a mutable collection.
- Use immutable factories (**listOf**, **setOf**, **mapOf**) by default; reach for the mutable variants only when you actually mutate.
- Replace hand-written loops with operators (**map**, **filter**, **groupBy**) — they are clearer and less error-prone.
- Use a **Sequence** for large multi-step pipelines to avoid intermediate allocations.

---

---

## Sorting Complexity and the Two-Pointer Technique

### `.sorted()` and `.sortedBy()` — O(n log n)

Kotlin's `sorted()`, `sortedBy()`, and `sortedWith()` delegate to Java's `Arrays.sort()` / `Collections.sort()`, which use **TimSort** — a hybrid merge sort / insertion sort algorithm. The complexity is **O(n log n)** in all cases (best, average, and worst). You do not control the internal algorithm; calling `.sorted()` on a list of size n always pays the full O(n log n) cost plus a full traversal to build the output list.

```kotlin
val nums = listOf(3, 1, 4, 1, 5, 9, 2, 6)
val sorted = nums.sorted()       // O(n log n) — TimSort under the hood
val byLen = words.sortedBy { it.length }  // same complexity, custom key
```

**Interview context:** When asked about the complexity of `.sorted()`, the correct answer is O(n log n) — it must traverse the entire collection and sort it, and no comparison-based sort can do better than O(n log n) in the general case. The constant factor depends on the input (TimSort is particularly fast on nearly-sorted data), but asymptotically it is always O(n log n).

---

### The Two-Pointer Technique

The two-pointer pattern is one of the most effective tools for achieving O(n) time on problems that would otherwise require O(n log n) sorting or O(n²) nested loops. It works by placing one pointer at each end of a sorted array and moving them toward each other based on a comparison condition.

**Key insight:** if the input is already sorted, you can exploit that structure to avoid a second sort pass.

---

#### Problem: Squares of a Sorted Array

Given an integer array `nums` sorted in non-decreasing order, return an array of the squares of each number, also sorted in non-decreasing order.

```
Input:  [-4, -1, 0, 3, 10]
Output: [0, 1, 9, 16, 100]

Input:  [-7, -3, 2, 3, 11]
Output: [4, 9, 9, 49, 121]
```

**Naive approach — O(n log n):**
```kotlin
fun sortedSquares(nums: IntArray): IntArray =
    nums.map { it * it }.toIntArray().also { it.sort() }
```
This works but discards the sorted structure of the input. The sort inside costs O(n log n).

**Optimised approach — O(n) with two pointers:**

The largest squares always come from the elements with the largest absolute value — which are always at the two ends of the sorted input (the most negative or the most positive). Fill the result array from right to left by comparing both ends.

```kotlin
import kotlin.math.abs

fun sortedSquares(nums: IntArray): IntArray {
    val result = IntArray(nums.size)
    var left = 0
    var right = nums.lastIndex

    for (i in nums.lastIndex downTo 0) {
        if (abs(nums[left]) < abs(nums[right])) {
            result[i] = nums[right] * nums[right]
            right--
        } else {
            result[i] = nums[left] * nums[left]
            left++
        }
    }
    return result
}
```

**Why this is O(n):** Each element is visited exactly once. `left` and `right` move toward each other and together cover every index exactly once. No secondary sort is needed because we fill the result in the correct order directly.

**Why it works:** The input is sorted, so the absolute values increase toward both ends. At each step, whichever end has the larger absolute value produces the next largest square and gets moved inward.

| Approach | Time | Space | Notes |
|---|---|---|---|
| map + sort | O(n log n) | O(n) | Ignores existing sort order |
| Two pointers | O(n) | O(n) | Exploits sorted input; fills result from largest to smallest |

---

### When to Reach for Two Pointers

| Signal in the problem | Two-pointer likely applies |
|---|---|
| Input is sorted | ✅ Strong signal |
| Looking for a pair/triple that meets a condition | ✅ (classic two-sum on sorted array) |
| Need to merge or compare from both ends | ✅ |
| Subarray or substring with a target property | Consider sliding window instead |

Common two-pointer problems: Two Sum (sorted), Container With Most Water, Valid Palindrome, 3Sum, Trapping Rain Water.

← [Previous: Collection Types](../01-collection-types/) · [↑ Chapter Index](../)
