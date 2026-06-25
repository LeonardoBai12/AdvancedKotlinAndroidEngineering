---
layout: default
title: Cohesion Dependencies
parent: "Gradle & Multi-Module Architecture"
nav_order: 2
---

## Component Cohesion — REP, CCP, and CRP

The two strategies above tell you *how* to draw module boundaries. Robert C. Martin's *Clean Architecture* (Chapter 13) provides the principled answer to *what* should live inside each boundary. Martin defines three **component cohesion principles** that together govern every modularization decision — knowing them transforms "feels right" into a reasoned argument.

### REP — Reuse/Release Equivalence Principle

*"The granularity of reuse is the granularity of release"* (Martin, *Clean Architecture*, Ch. 13). Classes and modules grouped into a component must be **releasable as a unit**: they must share a coherent theme or purpose that makes sense both to the author who publishes them and to the consumer who depends on them. Without versioned releases, consumers cannot guarantee compatibility when a component changes; without a coherent theme, the release documentation is meaningless.

The practical implication: a `:core:network` module that bundles Retrofit client configuration, authentication interceptors, and logging utilities is releasable as a unit because they all serve the same purpose — network communication. If you add unrelated analytics utilities to it, you've violated REP: now every consumer of the analytics utilities must accept unnecessary releases whenever the network stack changes.

```kotlin
// Respects REP: one purpose, one versioned release
// :core:network — all networking concerns together
class RetrofitClient { ... }
class AuthInterceptor { ... }
class NetworkLogger { ... }

// Violates REP: analytics and network have different reasons to release
// :core:network — mixed concerns
class RetrofitClient { ... }
class AnalyticsTracker { ... }  // belongs in :core:analytics
```

### CCP — Common Closure Principle

*"Gather into components the classes that change for the same reasons at the same times. Separate into different components the classes that change at different times and for different reasons."* (Martin, *Clean Architecture*, Ch. 13). This is SRP applied at the module level: just as a class should have only one reason to change, a module should have only one reason to change.

Martin's emphasis is practical: in most applications, **maintainability matters more than reusability**. When a requirement changes, you want all the affected code to live in one module — so you revalidate and redeploy that one module, and leave the rest untouched. If a single requirement change ripples across five modules, CCP is being violated.

CCP has a direct relationship with OCP: we want our modules to be *closed* to the most common types of change. Classes that are likely to change for the same reasons should be grouped together so a single change touches as few modules as possible.

```kotlin
// Respects CCP: all payment-flow classes change together when payment rules change
// :feature:checkout
class CheckoutViewModel { ... }
class PaymentValidator { ... }
class OrderSummaryScreen { ... }

// Violates CCP: auth logic buried inside a feature module
// :feature:checkout
class CheckoutViewModel { ... }
class TokenRefreshHandler { ... }  // auth changes → rebuilds unrelated checkout
```

> **Similarity with SRP (Martin, *Clean Architecture*):**
> *"Gather everything that changes at the same time for the same reasons. Separate everything that changes at different times for different reasons."* CCP is CCP-as-component, SRP is CCP-as-class.

### CRP — Common Reuse Principle

*"Do not force users of a component to depend on things they do not need."* (Martin, *Clean Architecture*, Ch. 13). When module A depends on module B, it depends on **all** of B's classes — even the ones it never uses. If any class in B changes, A must be recompiled, revalidated, and potentially redeployed, even if the changed class is irrelevant to A. CRP says: don't create that burden. Classes that are not used together should not live in the same module.

Martin notes that CRP tells us more about which classes **should not** be together than which should. The question is not just "do these classes share a theme?" but also "does depending on one force you to depend on all the others?"

```kotlin
// Violates CRP: :core:utils bundles unrelated utilities
// A feature needing only date formatting depends on the whole module,
// and gets recompiled whenever the bitmap utilities change.
// :core:utils
object DateFormatter { ... }
object BitmapHelper { ... }     // ← unrelated to date formatting
object StringExtensions { ... } // ← unrelated

// Respects CRP: split by cohesive reuse
// :core:formatting — DateFormatter, StringExtensions (used together in UI)
// :core:media      — BitmapHelper, VideoThumbnailLoader (used together in media)
```

> **Relationship with ISP (Martin, *Clean Architecture*):**
> *"CRP is a generic version of ISP. ISP advises not to depend on classes that contain methods we do not use. CRP advises not to depend on components that contain classes we do not use."* Both reduce to the same rule: *don't depend on things you don't need.*

### The Tension Diagram

The three principles pull against each other, and the tension is by design (Martin, *Clean Architecture*, Figure 13.1). REP and CCP are *inclusive* — they push modules to grow by pulling related things together. CRP is *exclusive* — it pushes modules to shrink by separating things that don't change or get reused together.

```text
              CCP
         (group for maintenance)
              /\
             /  \
            /    \
  too many /      \ too many component
  releases/        \ changes
          /        \
        REP ——————— CRP
  (group for     (split to avoid
   reuse)       unnecessary releases)
                     ↑
              hard to reuse
```

| If you ignore… | The cost you pay |
| --- | --- |
| CRP (focus only on REP + CCP) | Many components impacted by simple changes; unnecessary rebuilds |
| CCP (focus only on REP + CRP) | Requirement changes spread across many modules; painful maintenance |
| REP (focus only on CCP + CRP) | Too many fine-grained releases; components hard to reuse meaningfully |

A good architect finds the position in that triangle that fits the current stage of the project. Early-stage: lean toward CCP (fewer, cohesive modules are easier to maintain). Mature library code: lean toward REP and CRP (stable, reusable, minimal surface). The position is not fixed — it shifts as the project and its consumers evolve.

> *(Source: Martin, R.C. — Clean Architecture: A Craftsman's Guide to Software Structure and Design, Ch. 13 — Component Cohesion)*

## api vs implementation — Controlling the Graph

How you declare a dependency controls whether it leaks to other modules. **implementation** keeps the dependency private to the module — modules that depend on you cannot see it. **api** exposes it transitively — anyone depending on you also gets it on their compile classpath. Prefer **implementation** by default: it shrinks the compile classpath of downstream modules, which both speeds up builds (fewer modules recompile when the dependency changes) and prevents accidental coupling. Reach for **api** only when a type from that dependency genuinely appears in your module's public API.

*implementation vs api*

```kotlin
dependencies {
    // Private: :core:network's use of OkHttp is hidden from consumers
    implementation(libs.okhttp)

    // Exposed: a module returning a Retrofit type in its public API
    // must expose Retrofit so callers can use that type
    api(libs.retrofit)
}
// Rule of thumb: implementation unless a consumer needs the type -> then api.
```

---

← [Previous: Gradle & Modules](../01-gradle-and-modules/) · [↑ Chapter Index](../) · [Next: Build Tooling →](../03-build-tooling/)
