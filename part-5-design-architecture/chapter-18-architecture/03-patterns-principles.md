---
layout: page
title: "Chapter 18: Architecture & Pragmatic Wisdom — Patterns & Principles"
---

## Putting It Together — A Feature in a Multi-Module App

Combine the previous chapter's modularization with these layers and a single feature becomes a self-contained vertical slice. A **:feature:profile** module contains the profile screen and its ViewModel (presentation); it depends on **:core:domain** for the user model and use cases, and on **:core:data** for the repository implementation; shared UI comes from **:core:designsystem**. The thin **:app** module wires the features together and owns navigation between them.

*One feature as a vertical slice across modules*

```kotlin
:feature:profile        // ProfileScreen + ProfileViewModel   (presentation)
    depends on:
      :core:domain       // User, GetUserUseCase, UserRepository interface
      :core:data         // UserRepositoryImpl, UserApi, UserDao
      :core:designsystem // shared Composables, theme

:app                     // wires features + navigation; depends on each feature

// The dependency rule holds across modules:
//   :feature:profile -> :core:domain   (presentation depends on domain)
//   :core:data       -> :core:domain   (data depends on domain)
//   :core:domain     -> nothing        (pure Kotlin centre)
```

Notice how navigation between features raises a coupling question: if **:app** (or one feature) had to know every screen and its arguments in every other feature, the modules would be tightly coupled and the app module would balloon. This is exactly the decoupling problem that deep links solve at the module boundary, as discussed in the Deep Links chapter — a feature exposes a URI contract, and callers navigate to it without a compile-time dependency on its internals.

## Pragmatic Principles

The principles below come from *The Pragmatic Programmer* (Hunt & Thomas, 2nd ed.) and are the philosophical backbone behind the architectural decisions throughout this guide.

### ETC — Easier To Change

Hunt and Thomas distil good design to a single criterion: **"A thing is well designed if it adapts to the people who use it. For code, that means it must adapt by changing"** — hence *Easier to Change*, or ETC (Tip 14). Crucially, they argue that every major design principle is just ETC in a specific context: decoupling is ETC because isolated concerns are individually easier to change; SRP is ETC because a change in requirements maps to a change in exactly one module; good naming is ETC because readable code is changeable code.

ETC is a **value, not a rule** — it is a guide for your instincts when the right path isn't obvious. When facing a design decision, ask: *which option leaves the door more open?* If you genuinely can't tell, try to write code that is **replaceable** — keep it decoupled and cohesive — so that whichever direction things evolve, the cost of the next change stays low.

In Android terms: this is why the domain layer is pure Kotlin with no framework imports, why ViewModels expose state through interfaces rather than concrete classes, and why features navigate by URI contract rather than direct class references.

### DRY — Don't Repeat Yourself

*"Every piece of knowledge must have a single, unambiguous, authoritative representation within a system"* (Tip 15, Hunt & Thomas). The common misreading is that DRY is about avoiding copy-pasted code; Hunt and Thomas are explicit that it is far broader — it is about the **duplication of knowledge and intent**. Two code fragments that look identical but encode different business rules are *not* a DRY violation; forcing them together to eliminate the textual duplication would couple things that should evolve independently.

The deeper motivation is that **knowledge is never stable**. Requirements change following a meeting with a client, a government changes a regulation, a business logic rule is revised. Hunt and Thomas make the striking point that most people assume maintenance begins when an application is released — in reality, *maintenance is the entire development process*, not a phase at the end. When knowledge has a single authoritative home, maintaining it means changing exactly one place.

The practical acid test: when some single facet of the system has to change, do you find yourself touching multiple files, formats, or representations — code and documentation, or a struct and the database schema that mirrors it? If yes, knowledge is duplicated, and the next change will cost proportionally more.

### Orthogonality

The term comes from geometry: two lines are orthogonal when they meet at right angles — each axis is fully independent of the other. Moving north changes your latitude and nothing else. In computing, Hunt and Thomas define it as: **"Two or more things are orthogonal if changes in one do not affect any of the others"** (Topic 10). In a well-designed system you can change the user interface without touching the database, and swap the database without changing the interface.

The helicopter analogy from *The Pragmatic Programmer* makes the cost of *non*-orthogonality vivid: a helicopter's controls are deeply interdependent — adjusting the collective pitch changes the torque on the tail rotor, which requires compensating with the foot pedals, which changes the heading, which requires correcting with the cyclic stick. Every input causes secondary effects everywhere else; the pilot is never making one change at a time. Nonorthogonal code has the same property.

**Benefits of orthogonality** (Hunt & Thomas, Topic 10):

- **Gain Productivity.** Changes are localised: fixing a bug in an orthogonal component repairs that component and nothing else. Orthogonal components are also reusable — if *M* components do *M* distinct things and *N* other components do *N* distinct things, orthogonal design gives you *M + N* combinations; nonorthogonal overlap reduces the reusable surface.
- **Reduce Risk.** Diseased sections are isolated — a sick module can be sliced out and transplanted without spreading symptoms. Orthogonal components are easier to test because you can design and run tests on each component independently. And you will not be as tightly tied to a particular vendor, product, or platform, because the interfaces to third-party components will be isolated to smaller parts of the overall system.
- **Eliminate effects between unrelated things** (Tip 17: *"When components of any system are highly interdependent, there is no such thing as a local fix"*). The goal is components that are self-contained, independent, and with a single well-defined purpose — what Yourdon and Constantine call *cohesion*.

The layered, multi-module structure described earlier in this chapter is the practical implementation of orthogonality: each layer and each feature module is a boundary that prevents a change in one from propagating through to another.

### Reversibility

*"The mistake lies in assuming that any decision is cast in stone — and in not preparing for the contingencies that might arise"* (Tip 18, Hunt & Thomas). Requirements evolve, technology shifts, vendors get acquired or go under. Reversibility is not pessimism — it is the acknowledgement that we rarely make our best decisions on the first attempt.

Hunt and Thomas note a telling pattern: teams commit to a vendor or a technology early, only to discover later that a competitor offers something better, or that the original choice cannot scale. The practical antidote is not to avoid decisions but to **hide them behind abstraction layers**. If you wrap a third-party API in your own interface, replacing the underlying implementation is a local change. If you break the system into components, you can move them between deployment models (a monolith today, separate services tomorrow) without a rewrite.

Tip 19, *Forgo Following Fads*, follows directly: the architectural fashions of any decade — big iron, federations of commodity hardware, VMs, containers, serverless, and back again — rotate continuously. *"No one knows what the future may hold."* The code that survives is the code that was written to **rock on** when it can, and **roll with the punches** when it must — not the code that was soldered to whichever paradigm was popular at the time it was written.

In Android: this is why the data layer hides Retrofit and Room behind repository interfaces, why navigation is expressed as URI contracts rather than class references, and why the domain layer has no Android imports — each is a decision that can be reversed without cascading consequences.

### Fail Fast

Detect problems as early as possible and report them loudly — a crash at the point of error beats a misleading one five frames later. In Kotlin, lean on **require()**, **check()**, non-nullable types, and sealed result types to make illegal states unrepresentable.

## Uncle Bob's Adages

- **'The only way to go fast is to go well.'** Cutting quality to hit a deadline always costs more later.
- **'Clean code reads like well-written prose.'** If a function needs a comment to explain what it does, its name is wrong.
- **'Functions should do one thing. They should do it well. They should do it only.'**
- **'A class should have one, and only one, reason to change.'** SRP as a slogan.

## Architecture Decision Reference

| Question | Guidance |
| --- | --- |
| Where does business logic live? | Domain use cases — never in the ViewModel, View, or Activity |
| Where does UI state live? | ViewModel, as a read-only StateFlow that survives rotation |
| Where do one-time events live? | SharedFlow in the ViewModel — not StateFlow (it replays on rotation) |
| Should the View hold logic? | No — it renders state and emits events only |
| Where do framework details go? | Data layer (Retrofit, Room) — never in domain |
| When to add a use case? | Per business action; especially when ViewModels share logic |
| How to handle errors across layers? | A Resource/sealed result through every layer — don't throw across boundaries |
| How should features navigate? | Via a contract (e.g. deep links) — not a hard dependency on internals |
| Where does cross-cutting init go? | Application class + the composition root, wired once at startup |

---

← [Previous: State & DI](../02-state-di/) · [↑ Chapter Index](../)
