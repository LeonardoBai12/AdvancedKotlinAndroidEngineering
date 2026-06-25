---
layout: default
title: "Chapter 7: Algorithm Analysis & Big O — Complexity Classes"
parent: "Chapter 7: Algorithm Analysis & Big O"
nav_order: 2
---

## O(1) — Constant Time

An algorithm is O(1) when its execution time does not change as the input grows. A crucial subtlety: O(1) does *not* mean 'a single operation'. It means a *constant* number of operations — fixed and independent of N. Accessing an array index performs several internal steps, but the count of those steps never grows with the array size.

*O(1) — array index and hash lookup*

```kotlin
val list = listOf(10, 20, 30, 40, 50)
val first = list[0]    // O(1) -- direct address arithmetic
val last  = list[4]    // O(1) -- same cost no matter the size
val size  = list.size  // O(1) -- stored counter, not recomputed

val map = hashMapOf("userId" to "leonardo", "role" to "senior")
val user = map["userId"]  // O(1) -- hash -> bucket -> value, no scan
```

| Operation | Collection | Why O(1) |
| --- | --- | --- |
| get(index) | ArrayList | Address = base + index × element_size |
| put / get by key | HashMap | Hash function maps key straight to a bucket |
| add / remove at end | ArrayDeque | Tail pointer, no element shifting |
| size / isEmpty | Any | Stored as a counter field, updated on mutation |
| push / pop / peek | Stack / Deque | Top pointer maintained, no traversal |

## O(N) — Linear Time

An algorithm is O(N) when its operation count grows in direct proportion to the input: double the input, double the work. This is the most common complexity in collection traversal. The canonical interview comparison pits **List.contains()** against **HashSet.contains()** — identical at the call site, fundamentally different in cost.

*List.contains() O(N) vs HashSet.contains() O(1)*

```kotlin
val userIdList = listOf("a1", "b2", "c3" /* ... 100k items */)
val userIdSet  = hashSetOf("a1", "b2", "c3" /* ... 100k items */)

// O(N) -- scans up to 100k entries on EVERY call
if (userIdList.contains(incomingId)) { process() }
// 100k users x 100k events = 10,000,000,000 operations

// O(1) -- hash straight to the bucket, no scan
if (userIdSet.contains(incomingId)) { process() }
// 100k users x 100k events = 100,000 operations
```

> **Interview Tip:**
>
> Real Android scenario: checking whether a userId is in a blocked list inside **RecyclerView.onBindViewHolder()**. With **List.contains()** on a large list you drop frames on every single bind. Convert the list to a HashSet once, up front, and every subsequent lookup is O(1).

## O(log N) — Logarithmic Time

Each step halves the remaining problem, so as the input doubles the work grows by just one step. Binary search over a billion sorted elements needs only about thirty comparisons. This is the complexity of **TreeMap.get()** and **TreeSet.contains()**, which are backed by balanced (Red-Black) trees.

> **The base of the logarithm doesn't matter in Big O.** O(log₂N) and O(log₁₀N) differ only by a constant factor (log₂N = log₁₀N × 3.32), and constants are dropped by convention. So whether you write O(lg n), O(log n), or O(log₂n), they all mean the same class. *(The Pragmatic Programmer, Topic 39)*

Other O(log N) operations beyond binary search: traversing a balanced binary tree (each level halves the remaining nodes), and finding the first set bit in a machine word via bit-shifting.

*O(log N) — binary search*

```kotlin
fun binarySearch(sorted: List<Int>, target: Int): Int {
    var lo = 0
    var hi = sorted.lastIndex
    while (lo <= hi) {
        val mid = (lo + hi) / 2
        when {
            sorted[mid] == target -> return mid
            sorted[mid] <  target -> lo = mid + 1   // discard left half
            else                  -> hi = mid - 1   // discard right half
        }
    }
    return -1
}
```

## O(N²) — Quadratic Time

Nested loops that each iterate over N elements produce O(N²): for every one of the N outer iterations you do N inner iterations, giving N × N. At N = 1,000 that is a million operations; at N = 10,000 it is a hundred million. This is the most common *accidental* performance trap in Android — double loops hidden inside adapters, de-duplication routines, or matrix processing. Most O(N²) traps collapse to O(N) with a HashSet or HashMap.

*O(N²) trap and its O(N) fix — finding duplicates*

```kotlin
// BAD -- O(N^2): compare every element against every other
fun findDuplicatesSlow(list: List<Int>): List<Int> {
    val dupes = mutableListOf<Int>()
    for (i in list.indices) {
        for (j in list.indices) {        // O(N) inside O(N) = O(N^2)
            if (i != j && list[i] == list[j]) dupes.add(list[i])
        }
    }
    return dupes
}

// GOOD -- O(N): one pass, HashSet remembers what we've seen
fun findDuplicatesFast(list: List<Int>): List<Int> {
    val seen = HashSet<Int>()
    // add() returns false if the element was already present
    return list.filter { !seen.add(it) }
}
```

## O(N log N) — Linearithmic Time

This is the optimal complexity for comparison-based sorting — no comparison sort can do better in the general case. Kotlin's **sorted()**, **sortedBy()**, and **sortedByDescending()** all use TimSort internally, which is O(N log N) in **every** case.

*O(N log N) — Kotlin sorting*

```kotlin
val sorted   = list.sorted()                          // O(N log N)
val byName   = users.sortedBy { it.name }             // O(N log N)
val byAmount = payments.sortedByDescending { it.amount } // O(N log N)
// MergeSort, HeapSort, TimSort -- all O(N log N), the proven lower bound
```

> **Quicksort nuance (a classic interview follow-up):** Quicksort works by partitioning the data into two halves and recursively sorting each — a divide-and-conquer approach that yields O(N log N) *on average*. However, its behaviour degrades when fed already-sorted (or reverse-sorted) input: the partition always picks the worst pivot, producing O(N²) in the worst case. This is why most production sort implementations (including Kotlin's TimSort and Java's Arrays.sort for objects) prefer MergeSort or hybrid strategies that guarantee O(N log N) regardless of input order. *(The Pragmatic Programmer, Topic 39)*

---

← [Previous: Foundations](../01-foundations/) · [↑ Chapter Index](../) · [Next: Practical Analysis →](../03-practical-analysis/)
