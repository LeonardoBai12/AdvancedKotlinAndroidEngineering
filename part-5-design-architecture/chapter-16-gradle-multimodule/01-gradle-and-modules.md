---
layout: page
title: "Chapter 16: Gradle & Multi-Module Architecture"
---

*The build system, modularization, incremental builds, and parallel teams*

Before discussing SOLID and Clean Architecture, we need a structural foundation those principles assume but rarely state: how an Android project is physically organised into **modules**, and how the **Gradle** build system ties them together. A small app can live in a single module, but every serious app — and certainly any app worked on by more than one team — is split into many. Understanding why, and how, is what lets the architecture chapters that follow talk about real projects instead of toy monoliths.

## What Gradle Does

**Gradle** is the build system Android uses. It takes your source, resources, and dependencies and orchestrates the entire pipeline — compiling, running annotation processors, merging resources, packaging — into an APK or AAB. You configure it through build scripts, written in Kotlin (**build.gradle.kts**) or Groovy (**build.gradle**), that declare what your project is made of: its plugins, its dependencies, its build types, and — the subject of this chapter — its modules.

*A typical module build script (build.gradle.kts)*

```kotlin
plugins {
    id("com.android.library")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.example.feature.profile"
    compileSdk = 34
}

dependencies {
    implementation(project(":core:designsystem"))  // depend on another module
    implementation(project(":core:network"))
    implementation(libs.retrofit)                   // external dependency
}
```

## What a Module Is

A **module** is an independently compilable unit of code with its own build script, its own dependencies, and a declared set of other modules it depends on. Every Android project has at least one — the **app** module that produces the installable application. Modularization is the practice of splitting the codebase into several modules with clear boundaries and a well-defined dependency graph between them.

| Module type | Role | Example |
| --- | --- | --- |
| app | Entry point; wires everything together, produces the APK/AAB | :app |
| feature | One user-facing feature, end to end | :feature:profile |
| core / common | Shared infrastructure used by many modules | :core:network |
| data | Repositories, data sources, DTOs | :core:data |
| domain | Business models and use cases (pure Kotlin) | :core:domain |
| designsystem | Shared UI components, theme, tokens | :core:designsystem |

### Module paths: grouping with the colon

Modules do not have to sit flat at the project root — they can be nested in folders, and the folder structure becomes the module's **path**, with each level separated by a colon. A folder **core** containing sub-modules **network** and **data** yields the module paths **:core:network** and **:core:data**; a folder **checkout** containing **domain** and **presentation** yields **:checkout:domain** and **:checkout:presentation**. The colon is just the path separator, exactly like a slash in a file path — it is how you refer to a module when declaring a dependency on it. This grouping is purely organisational: it keeps related modules together on disk and in the build, without changing how they compile.

*Folder grouping maps to colon-separated module paths*

```kotlin
// Project layout on disk:           // Resulting Gradle module path:
//   common/
//     data/                         :common:data
//     shared/                       :common:shared
//   checkout/
//     core/                         :checkout:core
//     data/                         :checkout:data
//     domain/                       :checkout:domain
//     presentation/                 :checkout:presentation

// settings.gradle.kts registers each one by its path:
include(":common:data", ":common:shared")
include(":checkout:domain", ":checkout:presentation")

// and you depend on one by that same path:
// (in :checkout:presentation's build.gradle.kts)
//   implementation(project(":checkout:domain"))
```

This is why every example path in this chapter uses colons (**:feature:profile**, **:core:network**): they are nested modules grouped under a parent folder. Grouping by feature (a **checkout** folder holding that feature's own data/domain/presentation modules) and grouping shared code (a **common** or **core** folder) are the two patterns you will see most, and they combine naturally.

## Why Modularize — Four Concrete Wins

### 1. Faster, incremental builds

This is the most immediate, daily benefit. Gradle only recompiles modules whose inputs have changed, and the modules that depend on them — not the whole project. In a single-module app, every change recompiles everything; with 30 modules, editing one feature recompiles that feature and re-links the app, leaving the other 28 untouched and cached. On a large codebase this is the difference between a multi-minute build and a few seconds, repeated dozens of times a day. Independent modules also build in **parallel** across CPU cores.

> **Key Insight:**
>
> The build-time win compounds with discipline: if a low-level **core** module is edited, everything that depends on it must rebuild, so the cheapest changes are those confined to a leaf **feature** module that nothing else depends on. A good module graph keeps volatile code in the leaves and stable code in the shared core.

### 2. Enforced separation of concerns

Within a single module, nothing stops one class from reaching into another it has no business touching — the boundaries are conventions, easily violated. A module boundary is enforced by the compiler: module A can use module B *only* if it explicitly declares the dependency, and it can see only what B exposes. This turns architectural rules into build rules. If your **domain** module declares no dependency on Android, it is physically impossible to import an Activity into your business logic — the project will not compile.

### 3. Parallel work across teams

On a large product, several teams work simultaneously. When each team owns one or more feature modules, they work inside their own boundaries with minimal merge conflicts and clear ownership. A payments team changing **:feature:checkout** does not touch — and cannot accidentally break the internals of — the **:feature:profile** module owned by another team. The module's public surface becomes the contract between teams, and everything behind it is free to change.

### 4. Reusability and clear ownership

A well-factored **core** module — networking, design system, analytics — is written once and reused by every feature, rather than copy-pasted. Each module has an obvious owner and an obvious responsibility, which makes the codebase navigable: you know where code lives from the module graph alone.

## Two Modularization Strategies

There are two common ways to draw module boundaries, and real projects often combine them. Neither is universally correct — the right choice depends on team size, app complexity, and how the product is expected to grow.

### By layer

Split horizontally along architectural layers: one module for presentation, one for domain, one for data. The dependency direction matches Clean Architecture — presentation and data depend on domain, domain depends on nothing. This is simple to set up and makes the layering explicit, but it scales poorly: as the app grows, every layer module becomes enormous, and a single feature's code is scattered across all three, so teams constantly touch the same modules.

*By-layer module graph*

```kotlin
:app
  -> :presentation   (all ViewModels, all screens)
  -> :data           (all repositories, all data sources)
:presentation -> :domain
:data         -> :domain
:domain                       (pure Kotlin -- no Android, no deps)

// Simple, but every feature's code is spread across all three layers,
// and the layer modules grow without bound.
```

### By feature

Split vertically by user-facing feature: each feature is its own module containing its full stack (its UI, its ViewModels, and often its own data and domain code), and shared infrastructure lives in **core** modules every feature can use. This scales well — a feature is self-contained, owned by one team, and built and tested in isolation — at the cost of more modules and more up-front structure. It is the dominant strategy for large apps.

*By-feature module graph*

```kotlin
:app                          // wires features together, owns navigation
  -> :feature:profile
  -> :feature:checkout
  -> :feature:feed

// every feature depends on shared core modules:
:feature:profile  -> :core:designsystem, :core:data, :core:domain
:feature:checkout -> :core:designsystem, :core:data, :core:domain

:core:data   -> :core:domain, :core:network
:core:domain                  // pure Kotlin, the stable centre
```

> **Interview Tip:**
>
> Hybrid is common and recommended at scale: modularize **by feature** at the top level (:feature:profile, :feature:checkout) and apply **by-layer** separation *inside* each feature or in the shared core (:core:data, :core:domain). You get feature ownership and clean layering at the same time.

|   | By layer | By feature |
| --- | --- | --- |
| Boundary | Architectural layer | User-facing feature |
| Scales to large apps | Poorly | Well |
| Team ownership | Unclear (shared layers) | Clear (one team per feature) |
| Setup cost | Low | Higher |
| Best for | Small/medium apps | Large, multi-team apps |

---

[↑ Chapter Index](../) · [Next: Cohesion & Dependencies →](../02-cohesion-dependencies/)
