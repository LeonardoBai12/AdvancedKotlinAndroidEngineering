---
layout: page
title: "Chapter 9: The N+1 Problem"
---
*API design, BFF, GraphQL, ORM lazy loading, and cache-aside*

The N+1 problem is a classic performance anti-pattern: an application makes one initial request to fetch a list of items (the '1') and then fires one additional request per item to fetch related data (the 'N'), for N+1 total round trips instead of a possible one or two. It appears in two distinct places — between the frontend and the backend (API calls), and between the backend and the database (ORM queries). Fixing one while ignoring the other leaves the bottleneck in place, so a senior engineer addresses both.

## N+1 on the Network — Frontend to Backend

*The N+1 pattern — 50 users with their posts*

```kotlin
// Request 1 -- fetch the user list
GET /users  ->  [{ id: 1 }, { id: 2 }, ..., { id: 50 }]

// Requests 2..51 -- one per user
GET /users/1/posts    // 100ms
GET /users/2/posts    // 100ms
// ...
GET /users/50/posts   // 100ms

// Total: 51 requests x 100ms = ~5 seconds of serial latency,
// plus 50 extra open connections and 50x the backend CPU cost.
```

### Why it got worse: SSR to SPA

In the server-side-rendering era (Django, Rails, Laravel) the server assembled the full HTML page and the N+1 problem lived entirely inside the server, hidden from the network. The shift to Single Page Applications turned the frontend into an independent app fetching from API endpoints — which replicated the internal database N+1 onto the public network layer, making it both more visible and far more costly, since each round trip now crosses the internet rather than a loopback.

## Solution 1 — Batch IDs (the 1+1 pattern)

Instead of N separate requests, send all the IDs in one. This turns N+1 into 1+1: one request for the users, one for all their posts at once.

*Batch IDs — two requests total*

```kotlin
GET /users  ->  [{ id: 1 }, ..., { id: 50 }]
GET /posts?userIds=1,2,3,...,50  ->  all posts for all users

// Limitation: GET URLs have a length limit.
//   Alternative: POST /posts/batch with a JSON body of IDs.
// New problem: how do you paginate the nested posts?
```

### Where batch IDs break down: pagination

Batching fixes the request count but exposes a deeper design problem. Suppose you paginate users 20 per page, but each user has 1,000 posts. Do you return all 1,000 posts per user (gigabytes of data)? Cap it at 3 per user (then the frontend needs another call to load more)? Add a per-user posts offset inside the same request (now you carry two independent pagination states in one endpoint)? Every option either dumps too much data or reintroduces N+1 for the nested resource. This dead end is precisely what motivates BFF and GraphQL.

## Solution 2 — BFF (Backend For Frontend)

A BFF is an endpoint or service layer built specifically for the needs of one UI surface. Rather than the frontend assembling data from several generic calls, the BFF returns exactly the shape the screen needs in a single response.

*BFF — a purpose-built endpoint*

```kotlin
// Instead of generic endpoints (/users, /users/:id/posts), expose:
GET /users-with-posts

// Returns precisely what the screen renders:
// [
//   { id: 1, name: "Alice", posts: [{ title: ... }, ...] },
//   { id: 2, name: "Bob",   posts: [{ title: ... }, ...] }
// ]

// Frontend: 1 request, gets everything.
// Cost: as screens multiply (mobile, web, tablet) the backend
//       accumulates many tightly-coupled, hard-to-maintain endpoints.
```

## Solution 3 — GraphQL

GraphQL was created by Meta specifically to solve the nested-data problem at scale. Rather than the backend creating one endpoint per screen, it exposes data as a generalist graph. The frontend declares exactly the shape it wants — including nested relations — in a single request, and the server resolves the whole tree at once.

*GraphQL — one request, any nested shape the client wants*

```kotlin
query {
  users {
    id
    name
    posts {          # nested relation, resolved server-side
      title
      comments {     # arbitrarily deep nesting
        body
      }
    }
  }
}

// Exactly 1 POST request. No endpoint proliferation.
// The frontend owns the query shape; the backend stays generic.
```

## N+1 in the Backend — ORM Lazy Loading

An ORM (Object-Relational Mapper) bridges object-oriented code and a relational database, translating method calls into SQL automatically. Popular examples in the Kotlin/Android world are Room and SQLDelight; in Java, Hibernate; in Node, Prisma and Drizzle. The convenience comes at a cost: the ORM decides when and how each query runs, and those decisions are not always efficient.

**Lazy loading** is the default strategy of most ORMs: fetch only what was explicitly requested, and defer related data until it is actually accessed in code. The rationale is sound — why fetch posts you might not need? The problem is that the ORM cannot know in advance whether you will access that data inside a loop. When you do, it fires a fresh query per iteration, with no warning and no visible signal in the code.

*ORM lazy loading — the hidden N+1*

```kotlin
// Same pattern in any ORM, including Room and SQLDelight
val users = userDao.findAll()      // Query 1: SELECT * FROM users
for (user in users) {
    println(user.name)             // OK -- name is already in memory
    for (post in user.posts) {     // ORM fires a NEW query per user:
        println(post.title)        //   SELECT * FROM posts WHERE user_id = ?
    }
}
// 1 query for users + N queries for posts = N+1.
// 100 users -> 101 round trips, 101 connections held open.
```

> **Key Insight:**
>
> Lazy loading is not a bug — it is a deliberate design choice that works well for single-record access. It only becomes N+1 when combined with iteration over a collection, and the ORM cannot distinguish the two cases at query time.

### Backend fix — eager loading and JOINs

The fix is to tell the ORM up front what related data you will need, so it can fetch everything in one or two queries instead of N+1.

*Three equivalent backend fixes*

```kotlin
// 1. Django prefetch_related -- 2 queries total
users = User.objects.prefetch_related('posts').all()
#   Query 1: SELECT * FROM users
#   Query 2: SELECT * FROM posts WHERE user_id IN (1, 2, ..., 50)

// 2. Raw SQL LEFT JOIN -- 1 query, all data at once
SELECT users.*, posts.*
FROM users LEFT JOIN posts ON posts.user_id = users.id

// 3. Drizzle relational query (GraphQL-inspired) -- single JOIN
db.users.findMany({ with: { posts: true } })

// All three: O(1) database round trips regardless of user count.
```

## Cache-Aside — When N+1 Meets ConcurrentHashMap

When the external API has no batch endpoint, a cache-aside pattern eliminates repeat network calls. The first time a resource is requested the server fetches and stores it; subsequent requests are served from local memory at O(1). This maps directly onto **computeIfAbsent** on a ConcurrentHashMap.

*Cache-aside with per-key Mutex (stampede protection)*

```kotlin
class PokemonBff {
    private val cache = ConcurrentHashMap<Int, PokemonData>()
    private val locks = ConcurrentHashMap<Int, Mutex>()

    suspend fun getPokemon(id: Int): PokemonData {
        cache[id]?.let { return it }              // fast path: O(1) hit

        val mutex = locks.computeIfAbsent(id) { Mutex() }
        return mutex.withLock {
            cache[id]?.let { return it }          // double-check inside lock
            val data = pokeApi.fetchById(id)      // exactly one network call
            cache[id] = data
            data
        }
    }
}
// Session 1 (cold cache): N network calls.
// Session 2 (warm cache): 0 network calls -- all O(1) from memory.
```

> **Warning:**
>
> Cache stampede: if two coroutines request the same uncached ID at once, both miss and both hit the API. For low traffic this is harmless; under high concurrency a per-key Mutex guarantees exactly one fetch per ID while all other callers suspend and receive the shared result.

## Solution Comparison

| Strategy | Requests | Setup cost | Best for |
| --- | --- | --- | --- |
| N+1 (naive) | N+1 | Zero | Nothing — always avoid |
| Batch IDs (1+1) | 2 | Low | Simple cases, small ID lists |
| BFF / specialised endpoint | 1 | Medium | Stable screens, known shape |
| GraphQL | 1 | High | Many screens, evolving UI |
| ORM eager loading | 1–2 | Minimal | Backend ORM — always prefer |
| SQL JOIN | 1 | Low | Backend — maximum control |
| Cache-aside | 0* | Medium | External APIs, repeated lookups |

* Cache-aside costs one request on the first access per item; every subsequent access is O(1) from local memory.

> **Interview Tip:**
>
> N+1 exists in virtually every company at scale. Spotting it proactively — before it causes visible latency — is one of the things that distinguishes a senior engineer from a junior one. The fix is almost always straightforward once the pattern is recognised; the skill is in recognising it.

---

[↑ Chapter Index](../)
