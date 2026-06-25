---
layout: default
title: "Chapter 7: Algorithm Analysis & Big O — Practical Analysis"
parent: "Chapter 7: Algorithm Analysis & Big O"
nav_order: 3
---

## The Interview Flow — Two Sum as a Case Study

In a real interview you are expected to follow a four-step arc: (1) propose a working solution, (2) state its Big O, (3) say whether it is optimal, and (4) improve it. The Two Sum problem — given an array and a target, find two numbers that sum to the target — is the canonical vehicle for demonstrating this arc.

*Two Sum — brute force O(N²) then optimal O(N)*

```kotlin
// Input: [12, 3, 4, 11, 25], target = 14

// BRUTE FORCE -- O(N^2): test every pair
fun twoSumBrute(nums: IntArray, target: Int): IntArray {
    for (i in nums.indices) {
        for (j in nums.indices) {
            if (i != j && nums[i] + nums[j] == target)
                return intArrayOf(i, j)
        }
    }
    return intArrayOf()
}

// OPTIMAL -- O(N): one pass, HashMap stores values already seen
fun twoSumOptimal(nums: IntArray, target: Int): IntArray {
    val seen = HashMap<Int, Int>()        // value -> index
    for ((i, num) in nums.withIndex()) {
        val complement = target - num     // what completes the pair
        if (complement in seen)           // O(1) lookup
            return intArrayOf(seen[complement]!!, i)
        seen[num] = i                     // remember for later
    }
    return intArrayOf()
}

// Time:  O(N^2) -> O(N)
// Space: O(1)   -> O(N)   (we trade memory for speed)
```

> **Interview Tip:**
>
> Always state the brute-force Big O *before* proposing the optimisation. Saying 'this is O(N²), which isn't ideal — I can bring it to O(N) with a HashMap by trading space for time' demonstrates exactly the reasoning the interviewer is probing for. The code alone is not enough; the narration is the signal.

## HashMap Internals — How O(1) Is Achieved

The Memory & Hashing Fundamentals chapter introduced hash tables — an array of buckets indexed by a key's hashCode. Here we put that to work and analyse the complexity precisely. HashMap delivers O(1) lookup through its hash function: when you write **map[key]**, the runtime computes **key.hashCode()**, applies modular arithmetic to derive a bucket index, and retrieves the value from that bucket directly — no iteration over other entries, regardless of how many entries the map holds.

*HashMap lookup — the three internal steps*

```kotlin
// When you write: map["userId"]
val hash  = "userId".hashCode()   // step 1: compute the hash, e.g. 3598625
val index = hash % buckets.size   // step 2: pick a bucket, e.g. 3598625 % 16 = 1
val value = buckets[index]        // step 3: O(1) array access
// Three O(1) steps -> overall O(1), independent of map size
```

### String keys and hashCode caching

**String.hashCode()** is technically O(k) in the string length k, because it iterates every character. But the JVM caches the computed hash inside the String object after the first call, so repeated lookups using the same String instance are effectively O(1) — the cached integer is returned without re-walking the characters. String literals are interned, so the same instance is reused across your code; strings built by concatenation recompute on first use.

### Collisions and the Java 8+ tree fallback

Recall from the Memory & Hashing chapter that a collision occurs when two different keys hash to the same bucket; the bucket then holds several entries and a secondary search using **equals()** is required. Stated in Big O terms: before Java 8 a heavily collided bucket degraded to a linked list, making worst-case lookup O(n). From Java 8 onward (which Kotlin targets on the JVM), once a bucket exceeds 8 entries the linked list is automatically converted into a Red-Black tree, capping the worst case at O(log n). The table below summarises the three regimes and the condition that triggers each.

| Bucket state | Structure | Lookup | Condition |
| --- | --- | --- | --- |
| No collision | Single entry | O(1) | Default, the happy path |
| Few collisions | Linked list | O(n) | Fewer than 8 entries in the bucket |
| Many collisions | Red-Black tree | O(log n) | 8 or more entries in the bucket |

In practice a well-distributed hashCode() keeps almost every bucket at 0–1 entries, so amortised complexity stays O(1). The tree fallback is a safety net, not the norm.

### Reducing hash computation cost — a classic follow-up

A frequent interview follow-up to 'what is the complexity of HashMap access?' is 'how would you reduce the cost of hashing?'. Several strategies apply.

- **Use simpler key types.** Int and Long hashCode() is trivially O(1) — essentially the value itself. Prefer numeric keys over long strings when the domain allows.
- **Set initialCapacity to avoid rehashing.** When a HashMap exceeds its load factor (default 0.75) it allocates a bigger array and recomputes every bucket index — an O(n) rehash. If you know the size in advance, pre-size the map.
- **Override hashCode() for custom keys.** A data class hashes all its properties; if only one field uniquely identifies the object, hash just that field.
- **Cache an expensive hashCode manually** in a private field for keys that are costly to hash and reused often — exactly what String does internally.

*Pre-sizing and custom hashCode*

```kotlin
// Bad: starts small, triggers several O(n) rehash cycles as it grows
val bad = HashMap<String, String>()
repeat(10_000) { bad["key$it"] = "v" }

// Good: pre-sized -> zero rehashes (capacity = expected / load_factor)
val good = HashMap<String, String>(16_000)  // ~10k / 0.75
repeat(10_000) { good["key$it"] = "v" }

// Custom hashCode: use only the field that discriminates
data class UserId(val id: String, val metadata: HeavyMetadata) {
    override fun hashCode(): Int = id.hashCode()   // skip metadata
    override fun equals(other: Any?) =
        other is UserId && id == other.id
}
```

## Space Complexity — The Input Rule

Space complexity measures the *additional* memory an algorithm allocates as the input grows. The rule that trips people up: **the input itself is never counted** — it was allocated by the caller, not by your algorithm. Only what you allocate inside the function counts toward its space complexity.

*What counts toward space complexity*

```kotlin
fun process(array: IntArray) {
    // 'array' parameter -> NOT counted (the caller allocated it)

    // O(1) space: one variable, reused every iteration
    for (num in array) { println(num) }   // 'num' is one slot, not N

    // O(N) space: a copy that grows with the input
    val dup = array.copyOf()

    // O(3N) -> simplified to O(N): constants are dropped
    val a = array.copyOf()
    val b = array.copyOf()
    val c = array.copyOf()   // 3N slots, still O(N)
}
```

> **Warning:**
>
> Common trap: 'I allocate the array once, so it must be O(1).' Wrong. If the structure you allocate grows proportionally to the input, it is O(N) — regardless of how many times you allocate it or whether it happens in a single call.

## Relative Timing — Why This Matters

Assume N = 1,000,000 records and that each basic operation takes 1 ms. The table makes visceral why O(N²) or worse is simply unacceptable on the Android main thread.

| Big O | Operations at N = 1M | Elapsed time | Verdict |
| --- | --- | --- | --- |
| O(1) | 1 | 1 ms | >> Excellent |
| O(log N) | ~20 | ~20 ms | >> Great |
| O(N) | 1,000,000 | ~16.7 minutes | >> Good |
| O(N log N) | ~20,000,000 | ~5.5 hours | ~ Fair |
| O(N²) | 1,000,000,000,000 | 11.57 days | !! Bad |
| O(N³) | 10^18 | 31.7 million years | !! Terrible |
| O(2^N) | 10^301,030 | Heat death of the universe | !! Unusable |

*The Pragmatic Programmer* illustrates this scaling with a more tangible example. Suppose a routine takes **1 second to process 100 records**. How long does it take to process **1,000 records** (10× more)?

| Algorithm | Time for 1,000 records | Reasoning |
| --- | --- | --- |
| O(1) | 1 second | No dependence on input size |
| O(n) | 10 seconds | Linear growth: 10× more records |
| O(n log n) | ~33 seconds | 10 × log₁₀(10) ≈ 10 × 3.3 |
| O(n²) | 100 seconds | Quadratic: (10)² = 100× slower |
| O(2^n) | ~10²⁶³ years | Exponential: 2¹⁰⁰⁰ / 2¹⁰⁰ — effectively never |

> Hunt, A. & Thomas, D., *The Pragmatic Programmer* (2nd ed.), Topic 39 "Algorithm Speed", pp. 203–208.

## Best Isn't Always Best

The fastest asymptotic complexity is not always the right choice in practice. *The Pragmatic Programmer* puts it plainly: "You also need to be pragmatic about choosing appropriate algorithms — the fastest one is not always the best for the job."

For **small, bounded inputs** a simpler O(n²) algorithm is often better than an O(n log n) one:

- It is faster to write and easier to debug.
- Its setup cost (allocations, recursion overhead) doesn't dwarf the runtime when n is small.
- A straightforward insertion sort on a 20-element list beats the constant overhead of Timsort's bookkeeping.

The corollary: be wary of **premature optimisation**. If input is always bounded and small, optimising for scale is wasted effort — and possibly introduces bugs. Reach for the complex algorithm when you have measured a problem with real data, not when you anticipate one.

> **Pragmatic Tip 63 (from *The Pragmatic Programmer*):** Estimate the order of your algorithms. If you're not sure how long your code will take, try running it — vary the input size, plot the results. Three or four data points show the curve: flat, straight, or bending upward tells you the class immediately.

## LeetCode Pattern Cheat Sheet

Almost every interview problem belongs to a recurring pattern, and problems within a pattern share the same Big O. Learn the pattern once and you know the complexity of its whole family.

| Pattern | Time | Space | Why |
| --- | --- | --- | --- |
| Two Pointers | O(N) | O(1) | Single pass, two indices moving inward |
| Sliding Window | O(N) | O(1)–O(k) | Window slides once across the array |
| Binary Search | O(log N) | O(1) | Halves the search space each step |
| HashMap / HashSet | O(N) | O(N) | One pass with O(1) lookups |
| DFS (recursive) | O(N) | O(H) | Each node once; H = tree height |
| BFS | O(N) | O(N) | Queue may hold up to N nodes |
| Merge Sort | O(N log N) | O(N) | log N levels, N work per level |
| Backtracking | O(2^N) | O(N) | Explores all subsets — exponential by nature |

---

← [Previous: Complexity Classes](../02-complexity-classes/) · [↑ Chapter Index](../)
