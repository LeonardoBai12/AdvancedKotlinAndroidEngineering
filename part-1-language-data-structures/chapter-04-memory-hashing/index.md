---
layout: page
title: "Chapter 4: Memory & Hashing Fundamentals"
---
*Arrays under the hood, the equals/hashCode contract, and how hashing works*

Before surveying Kotlin's collections, it pays to understand the two low-level mechanisms every collection is built on: the **array** (a contiguous block of memory) and **hashing** (the trick that turns a key into a memory location in constant time). Almost every collection is ultimately an array, a hash table, or a combination of the two. This chapter also nails down the **equals/hashCode** contract — the thing a data class implements for you, and the thing that silently breaks HashSet and HashMap when you get it wrong.

## Arrays Under the Hood

'Array' is one of the most overloaded words in computing, and it is one of the most misunderstood data structures — you use one almost every day without necessarily knowing what it is. There are two answers to 'what is an array?': the high-level, freestyle answer (what JavaScript or Python calls an array or list), and the low-level, computer-science answer. We start with the low-level one, because that is what interviews and data-structures courses actually mean.

### An array is a contiguous block of memory

The simplest accurate definition: an array is a **contiguous span of memory** that we choose to interpret as a sequence of elements. The computer allocates one unbroken region of physical memory; there is no gap between the elements. That same binary region — an *array buffer* — can be *viewed* in different ways: the same 8 bytes can be read as eight 1-byte elements, or four 2-byte elements, or two 4-byte elements. The bytes do not change; only the interpretation (the *view*) does. JavaScript's ArrayBuffer with Int8Array / Int32Array views makes this literal, but the principle underlies every array in every language.

*One buffer, several views (conceptual)*

```kotlin
// The same contiguous bytes, interpreted three ways:
[ 41 00 00 00  41 00 00 00 ]   // raw 8-byte buffer

// as eight 1-byte elements:  [41][00][00][00][41][00][00][00]
// as two   4-byte elements:  [   0x00000041   ][   0x00000041   ]
// The data is identical -- only the 'view' changes how we read it.
```

### Why random access is O(1)

Because the elements are contiguous and each one has a known fixed size, the address of any element is computed by simple arithmetic — no traversal required. The array variable holds a pointer to where the array begins; to find element *i*, the machine computes **base_address + i × element_size**. For 32-bit integers, the third element (index 2) begins 32 × 2 = 64 bits after the start; the millionth element is found by the same single calculation. That is why accessing element 0, element 8, or element 1,000,000 all take the same constant time: the position of every element is known in advance, so reading *and* writing a known index is **O(1)**.

*Address arithmetic -- the heart of O(1) access*

```kotlin
// A Kotlin IntArray of [1, 2, 3, 4], each Int = 32 bits.
// The array variable points at the start of the block.
//
//   index 0 -> base + 32*0   (right where the pointer points)
//   index 1 -> base + 32*1
//   index 2 -> base + 32*2   = base + 64 bits
//   index i -> base + 32*i
//
// No scanning. One multiply + add -> O(1), the same cost for any index.
val arr = intArrayOf(1, 2, 3, 4)
val third = arr[2]      // O(1) -- computed directly, not searched
arr[2] = 99             // O(1) -- write the same way
```

### Why resizing and shifting are O(N)

The flip side of contiguity: an array cannot necessarily grow in place. The memory immediately after it may already be occupied by something else, so there is no guarantee of free adjacent space. To 'grow' an array you must allocate a new, larger block and copy every element across — which is **O(N)**. The same cost applies to inserting at the front: every existing element must shift one slot to make room, so a front-insert or front-remove is O(N) as well. This is the fundamental trade-off of the array: unbeatable random access, expensive structural change.

*Resize and shift both cost O(N)*

```kotlin
// Imagine [1, 2, 3, 4] sitting in memory with NO free slot after it.
// Adding a 5th element cannot happen in place:
//   1. allocate a new, bigger block
//   2. copy all 4 existing elements over   <- O(N)
//   3. write the new element

// Inserting at the front shifts everything right:
//   [_, 1, 2, 3, 4]  each element moves one slot  <- O(N)
```

> **Key Insight:**
>
> This is exactly why ArrayList's add-at-end is only *amortised* O(1): most adds are O(1), but when the backing array fills up it allocates a bigger one and copies everything (an O(N) resize). Averaged over many adds, the occasional copy washes out to O(1). The Collections chapter builds directly on this.

### The 'freestyle' array: JS/Python lists are objects

A low-level array has a fixed type and a fixed size — which is why Kotlin (like Rust) requires you to state both: **IntArray(4)** says 'four 32-bit ints, contiguous'. The language can then guarantee the O(1) access above. JavaScript and Python, by contrast, let you write **[1, "banana", [3, 4]]** — mixed types, growable, nestable. That flexibility is not free: what those languages call an 'array' or 'list' is actually a **complex object** (in V8, a heavily optimised C++ structure with several internal element-kinds and pointers to other blocks). It is no longer a simple contiguous span. The lesson for interviews: when someone asks about 'arrays', they mean the low-level contiguous structure — not the freestyle object.

*Fixed array (Kotlin) vs freestyle list (the object kind)*

```kotlin
// Kotlin -- type and size fixed; true contiguous array, O(1) access
val arr: IntArray = intArrayOf(1, 2, 3, 4)

// 'Freestyle': mixed types, growable -- this is a complex OBJECT,
// not a low-level contiguous array. (JS/Python style.)
//   [1, "banana", [3, 4]]
// Kotlin's growable equivalent is ArrayList<Any> -- still backed by
// an array internally, but boxed and dynamically resized.
```

| Operation | Array (contiguous) | Why |
| --- | --- | --- |
| Access by index | O(1) | Address = base + index × size |
| Write by index | O(1) | Same address arithmetic |
| Resize / grow | O(N) | No guaranteed adjacent space — reallocate + copy |
| Insert/remove at front | O(N) | All following elements must shift |
| Search by value | O(N) | No index into values — must scan |

## Equality: == vs ===

Before hashing makes sense, we need to be precise about equality, because hashing depends on it. Kotlin has two notions. **Structural equality** (**==**) asks 'do these have the same *contents*?' and is implemented by calling **equals()**. **Referential equality** (**===**) asks 'are these the *same object* in memory?'. For value-like types you almost always care about structural equality.

*== calls equals(); === compares references*

```kotlin
val a = User("1", "Leo")
val b = User("1", "Leo")

a == b      // structural: calls a.equals(b)  -> depends on the class
a === b     // referential: same object?      -> false (two instances)
a === a     // true -- literally the same reference
```

### What equals() does by default

By default — in a plain (non-data) class — **equals()** falls back to referential equality: two instances are 'equal' only if they are the very same object. That is rarely what you want for a model. A **data class** overrides **equals()** (and **hashCode()**) to compare all properties declared in the primary constructor, giving you correct structural equality automatically — this is one of the main reasons data classes exist.

*Default equals vs data class equals*

```kotlin
class PlainUser(val id: String)         // no override
PlainUser("1") == PlainUser("1")          // false! (reference comparison)

data class User(val id: String)          // generates equals + hashCode
User("1") == User("1")                    // true  (compares id)
```

## hashCode() and the Hash

A **hash function** takes an object and produces an integer — its **hashCode** — that acts as a compact fingerprint. A good hash function is fast, deterministic (the same input always yields the same hash), and spreads different inputs across the integer range so that distinct objects rarely collide. **hashCode()** is the method every Kotlin object exposes for this. Numeric types hash trivially (an Int's hashCode is essentially itself); String computes its hash by combining all its characters, then caches the result so repeat calls are free.

*hashCode() basics*

```kotlin
42.hashCode()          // 42  -- numbers hash to ~themselves
"userId".hashCode()    // e.g. 3598625 -- computed from the characters,
                       //                 then cached in the String object

data class User(val id: String, val name: String)
User("1", "Leo").hashCode()   // derived from id and name together
```

### The equals/hashCode contract

These two methods are bound by a contract that hash-based collections rely on absolutely: **if two objects are equal (equals returns true), they MUST have the same hashCode**. The reverse need not hold — two unequal objects may share a hashCode (a collision) — but equal objects with different hashCodes is a broken contract. Why it matters: a HashSet or HashMap first uses the hashCode to find the right bucket, then uses equals to confirm the match within that bucket. Break the contract and an object you just inserted becomes unfindable, because the collection looks in the wrong bucket entirely.

> **Key Insight:**
>
> Rules of the contract: (1) equal objects must have equal hashCodes; (2) hashCode must be consistent — the same object returns the same value while it is unchanged; (3) unequal objects *may* share a hashCode. A data class satisfies all three for free, which is why data classes are the safe default for HashMap keys and HashSet elements.

*Breaking the contract breaks HashSet*

```kotlin
// BAD: equals compares id, but hashCode ignores it (inconsistent)
class BadKey(val id: String) {
    override fun equals(other: Any?) = other is BadKey && other.id == id
    // no hashCode override -> uses identity hash, inconsistent with equals!
}
val set = hashSetOf(BadKey("1"))
set.contains(BadKey("1"))   // false! -- looked in the wrong bucket

// GOOD: let the data class generate both, consistently
data class GoodKey(val id: String)
hashSetOf(GoodKey("1")).contains(GoodKey("1"))   // true
```

## Hash Tables — Turning a Key into an Index

A hash table combines the two ideas in this chapter. It is backed by an array of **buckets**. To store a key, it computes **hashCode()**, reduces that to a bucket index with modular arithmetic (**hash % bucket_count**), and places the entry there. To look a key up, it repeats the same calculation — hash, then modulo — and jumps straight to the bucket. Because both steps are O(1), hash-table lookup is **O(1) on average**, no matter how many entries the table holds. This is the machinery behind HashSet and HashMap.

*Key -> bucket index -> value, all O(1)*

```kotlin
// Conceptually, for map["userId"]:
val hash  = "userId".hashCode()    // step 1: fingerprint the key
val index = hash % buckets.size    // step 2: reduce to a bucket index
val value = buckets[index]         // step 3: O(1) array access
// hashCode (cached) + modulo + array index = O(1) average lookup
```

### Collisions, briefly

Two different keys can reduce to the same bucket index — a **collision**. The bucket then holds more than one entry, and the table falls back to comparing keys with **equals()** within that bucket (which is the other half of why the equals/hashCode contract matters). When a bucket holds just a couple of entries this is cheap, but if a poor hashCode funnels many keys into one bucket, that bucket effectively becomes a small list that must be scanned — turning an O(1) lookup into O(n) in the worst case. The JVM mitigates this: once a single bucket grows past eight entries it converts that bucket from a list into a balanced (Red-Black) tree, which caps the worst case at O(log n) instead of O(n). A good hashCode keeps collisions rare in the first place, so in practice almost every bucket holds zero or one entry and the average lookup stays O(1).

> **Interview Tip:**
>
> This connects everything in this chapter: a hash table is an **array** of buckets (giving O(1) indexing), the bucket is chosen by a key's **hashCode**, and ties inside a bucket are broken by **equals**. Arrays supply the constant-time indexing; hashing supplies the key-to-index mapping; and the equals/hashCode contract keeps the whole thing correct. Every hash-based collection you will meet is a variation on this one idea.

---

[↑ Chapter Index](../)
