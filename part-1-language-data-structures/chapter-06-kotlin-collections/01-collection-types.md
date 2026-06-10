# Chapter 6: Kotlin Collections

*Hierarchy, Lists, Sets, Maps, Arrays, Sequences, and the full operation toolkit*

Choosing the right collection is one of the most consequential micro-decisions an Android engineer makes. The wrong choice silently degrades performance — an O(N) lookup inside **onBindViewHolder** drops frames; an unnecessary intermediate list allocates megabytes. This chapter covers Kotlin's collection framework end to end: the type hierarchy, every major collection with its internal structure and complexity, lazy Sequences, and the complete operation toolkit you are expected to know fluently in interviews and on the job.

## The Collection Hierarchy

Kotlin's collection framework is built on a hierarchy whose defining feature is **mutability separation at the type level**. Read-only and mutable interfaces are distinct types. A function that accepts a **List<T>** is telling you, in the type system itself, that it will not modify the collection.

*The type hierarchy*

```kotlin
Iterable
  Collection (read-only)
    List<out E>      -- ordered, indexed, allows duplicates
    Set<out E>       -- unordered, no duplicates
    (Map is NOT a Collection -- it is a separate hierarchy)
  MutableCollection
    MutableList<E>
    MutableSet<E>
    (MutableMap is separate too)
```

> **Warning:**
>
> Read-only is not the same as immutable. A **List<String>** reference simply does not *expose* mutation methods — but the underlying object may still be a MutableList. If you hold a List reference to a MutableList and cast it back, you can mutate it at runtime. To get true immutability guarantees, never leak a mutable reference, and expose only the read-only interface from your public API.

*Read-only vs immutable — a subtle but important distinction*

```kotlin
val readOnly: List<String> = mutableListOf("A", "B")
// readOnly.add("C")        // COMPILE ERROR -- List has no add()

// But the underlying object IS mutable:
val backdoor = readOnly as MutableList<String>
backdoor.add("C")           // works at runtime!
println(readOnly)            // [A, B, C] -- the 'read-only' view changed
```

## Lists — Ordered Collections

Lists are ordered, indexed collections that allow duplicates. Kotlin offers two backing implementations with very different performance characteristics: ArrayList and LinkedList. Understanding which is which is a perennial interview question.

| Type | Mutability | Backed By | Variance |
| --- | --- | --- | --- |
| List<out E> | Read-only | Wrapper over an array | Covariant |
| MutableList<E> | Mutable | ArrayList (default) | Invariant |
| ArrayList<E> | Mutable | Dynamic array | Invariant |
| LinkedList<E> | Mutable | Doubly linked list | Invariant |

*Creating lists*

```kotlin
// Immutable (read-only) -- preferred default
val fruits = listOf("Apple", "Banana", "Cherry")

// Mutable
val numbers = mutableListOf(1, 2, 3)
numbers.add(4)

// ArrayList explicitly (rarely needed -- mutableListOf returns one)
val arrayList = ArrayList<String>()
```

### ArrayList — fast random access, slow mid-list insertion

ArrayList is backed by a **dynamic array** that grows automatically as elements are added. On the JVM, Kotlin's ArrayList is literally a typealias for **java.util.ArrayList**. Its defining strength is **O(1) random access by index**: the address of element *i* is computed arithmetically as *base_address + i × element_size*, requiring no traversal. Its weakness is mid-list insertion and removal, which is **O(n)** because every subsequent element must be shifted to fill or open the gap. Detecting an element by value (**contains**, **indexOf**) is also O(n) because there is no index to jump to.

*ArrayList complexity*

```kotlin
Access by index     O(1)         -- base + index * element_size
Add at end          O(1) amort.  -- occasional resize amortised away
Insert at position  O(n)         -- shifts all following elements
Remove at position  O(n)         -- shifts all following elements
Search (contains)   O(n)         -- linear scan, no index available
```

### LinkedList — slow random access, fast end insertion

LinkedList is backed by a **doubly linked list**: a chain of nodes where each node holds three things — the element (the data), a reference to the *next* node, and a reference to the *previous* node. This structure inverts ArrayList's trade-offs. Insertion and removal at the beginning or end is **O(1)** — only a couple of pointer references change, with no shifting. But random access by index is **O(n)**: there is no address arithmetic, so to reach element *i* the list must be traversed node by node from one end.

*LinkedList node structure (conceptual)*

```kotlin
Node {
    data: E              // the element value
    next: Node?          // reference to the following node
    prev: Node?          // reference to the preceding node
}

// [prev|A|next] <-> [prev|B|next] <-> [prev|C|next]
// Inserting at the head: create node, fix two pointers -- O(1)
// Getting element at index 500: walk 500 nodes -- O(n)
```

| Operation | ArrayList | LinkedList | Why the difference |
| --- | --- | --- | --- |
| get(index) | O(1) | O(n) | Array does address arithmetic; list must traverse |
| add at end | O(1) amort. | O(1) | ArrayList may resize; list updates the tail pointer |
| insert at start | O(n) | O(1) | ArrayList shifts everything; list fixes 2 pointers |
| remove by index | O(n) | O(n)* | Both must locate it; ArrayList then shifts |
| contains(value) | O(n) | O(n) | Neither has an index into values; both scan |

* LinkedList insertion/removal is O(1) only when you already hold a reference to the target node. Finding the position first is O(n). In practice on Android, ArrayList is almost always the right default — cache locality and O(1) indexing dominate real workloads.

## Sets — Unique Elements

Sets enforce uniqueness: each element appears at most once. Membership is decided by **equals()** and **hashCode()** — which is why data classes (with auto-generated equals/hashCode) work so well as set elements. The headline benefit of a hash-based set is **O(1) membership testing**, compared to O(n) for a List.

| Type | Order | Backed By | Lookup |
| --- | --- | --- | --- |
| hashSetOf() | None | Hash table | O(1) average |
| linkedSetOf() | Insertion order | Hash table + linked list | O(1) average |
| TreeSet (java.util) | Sorted | Red-Black tree | O(log n) |

*Set behaviour*

```kotlin
val set = mutableSetOf("A", "B", "A")
println(set)        // [A, B] -- duplicate silently dropped
println(set.size)   // 2

val ordered = linkedSetOf(3, 1, 2)
println(ordered)    // [3, 1, 2] -- insertion order preserved

val sorted = java.util.TreeSet(listOf(3, 1, 2))
println(sorted)     // [1, 2, 3] -- automatically sorted
```

> **Interview Tip:**
>
> The classic optimisation: if you repeatedly check membership against a large list, convert it to a HashSet once up front. **list.contains(x)** is O(n) per call; **set.contains(x)** is O(1). Inside a RecyclerView bind callback, that is the difference between smooth scrolling and dropped frames.

## Maps — Key-Value Pairs

Maps store associations between unique keys and values; each key maps to exactly one value. Maps are not Collections — they live in a separate part of the hierarchy — but they share the same hash-based performance story.

| Type | Order | Null Keys | Lookup |
| --- | --- | --- | --- |
| HashMap | None | One null key allowed | O(1) average |
| LinkedHashMap | Insertion order | One null key allowed | O(1) average |
| TreeMap (java.util) | Sorted by key | Not allowed (NPE) | O(log n) |

### How HashMap permits exactly one null key

A common interview curiosity: HashMap allows a single null key, even though calling **null.hashCode()** would throw. This works because the hash function special-cases null and assigns it hash 0, while TreeMap (which must call **compareTo** on keys to sort them) cannot, and throws a NullPointerException.

*The HashMap hash function (Java implementation)*

```kotlin
static final int hash(Object key) {
    int h;
    // null -> hash 0; otherwise spread the bits to reduce collisions
    return (key == null) ? 0 : (h = key.hashCode()) ^ (h >>> 16);
}

val map = mutableMapOf<String?, Int>()
map[null]  = 42      // OK -- the single null key, hashed to bucket 0
map["key"] = 100
println(map[null])   // 42
println(map.size)    // 2
```

---

[↑ Chapter Index](./README.md) · [Next: Arrays, Sequences & Operations →](./02-arrays-sequences-operations.md)
