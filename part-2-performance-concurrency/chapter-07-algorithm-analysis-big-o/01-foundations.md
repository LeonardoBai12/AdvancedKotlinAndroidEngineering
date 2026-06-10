---
layout: page
title: "Chapter 7: Algorithm Analysis & Big O"
---

*Complexity fundamentals, the interview flow, and HashMap internals*

Big O notation is the standard language for describing how an algorithm's performance scales as its input grows. Think of the **O** as standing for *"on the order of"* — it expresses the **upper bound** of the growth rate: the time or memory will not grow faster than this. By convention we keep only the dominant term and drop constants, so two engineers comparing algorithms on different machines arrive at the same notation. As *The Pragmatic Programmer* (Hunt & Thomas) puts it: "whenever we write anything containing loops or recursive calls, we subconsciously check the runtime and memory requirements — Big-O notation is what comes in handy when we need to be more precise about it."

> **Key Insight:**
>
> Big O counts operations, not milliseconds. It measures how the number of steps grows as input N grows — not wall-clock time, which varies per device. Equally important: Big O describes *scale, not speed*. For tiny inputs an O(N²) algorithm may beat an O(N) one; the whole point of Big O is what happens as N grows toward millions, which is where the difference becomes the difference between a responsive app and an ANR.

## Why It Matters for Android

- **UI performance**: O(N²) work on the main thread with large lists causes jank and ANRs.
- **Memory pressure**: poor space complexity leads to OutOfMemory crashes on low-end devices.
- **Database & API queries**: the wrong collection or query shape silently degrades throughput.
- **Interviews**: complexity analysis is expected knowledge at every mid-to-senior position.

## The Complexity Classes

| Notation | Name | Growth Behaviour | Signal |
| --- | --- | --- | --- |
| O(1) | Constant | Fixed, regardless of N | >> Excellent |
| O(log N) | Logarithmic | Halves the problem each step | >> Great |
| O(N) | Linear | Grows 1:1 with N | >> Good |
| O(N log N) | Linearithmic | N × log N — optimal sorting | ~ Fair |
| O(N²) | Quadratic | Grows with the square of N | !! Bad |
| O(N³) | Cubic | Grows with the cube of N | !! Bad |
| O(2^N) | Exponential | Doubles for every +1 in N | !! Terrible |
| O(N!) | Factorial | N × (N-1) × … × 1 | !! Unusable |

Rule of thumb: each step up the ladder degrades dramatically at scale. O(N²) at N = 1 million is one trillion operations.

## Asymptotic Analysis — Drop the Constants

When we compute Big O we discard constant factors and lower-order terms, keeping only the **dominant term** — the one that governs behaviour as N tends to infinity. A loop that runs 3N times is still O(N); a function that is O(N²) plus O(N) is just O(N²), because for large N the quadratic term swamps the linear one.

| Raw expression | Simplified | Reason |
| --- | --- | --- |
| O(3N) | O(N) | Constant factor 3 is dropped |
| O(N + 50) | O(N) | Constant 50 is a lower-order term |
| O(N² + N) | O(N²) | N² dominates N at scale |
| O(1) + O(N) + O(N²) | O(N²) | The highest-order term always wins |

> **What Big O does *not* tell you:**
>
> One O(N²) algorithm can be 1,000× faster than another O(N²) algorithm in practice — and the notation won't show it. Big O never gives you actual numbers for time or memory; it only tells you *how those values change as the input grows*. Two algorithms with the same class can differ enormously in their constant factors, cache behaviour, and branch predictability. This is why benchmarking real data always beats guessing from the class alone. *(Hunt & Thomas, The Pragmatic Programmer, Topic 39)*

## Reading Code for Complexity

*The Pragmatic Programmer* (Hunt & Thomas) offers a set of common-sense heuristics for estimating the Big O of a piece of code before you ever run it — just by reading its shape.

| Code shape | Typical Big O | Why |
| --- | --- | --- |
| Simple loop from 1 to n | O(n) | n iterations, constant work per step |
| Nested loops (m × n) | O(m × n) | Outer runs m times, inner runs n times each |
| Loop that halves its range each step | O(log n) | Binary chop: halves the remaining work |
| Recursive split + merge across all n elements | O(n log n) | log n levels of splitting, n work at each level |
| Examining all permutations of n things | O(n!) | n × (n-1) × … × 1 — combinatoric explosion |

**Examples of each shape in Kotlin:**

```kotlin
// O(n) — simple loop
for (item in list) process(item)

// O(n²) — nested loops
for (i in list) for (j in list) compare(i, j)

// O(log n) — binary chop: binarySearch above
// O(n log n) — divide and conquer: list.sorted()

// O(n!) — generating all permutations (rarely seen in production)
fun permutations(items: List<Int>): List<List<Int>> { /* ... */ }
```

> **Pragmatic Tip (from *The Pragmatic Programmer*, Topic 39):**
>
> You can estimate the order of many basic algorithms using common sense. Sorting n items? O(n log n). Inverting an m × n matrix? O(m × n). The *size* of the input drives the algorithm; Big-O is just the notation we use to write that relationship down precisely.

---

[↑ Chapter Index](../) · [Next: Complexity Classes →](../02-complexity-classes/)
