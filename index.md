---
layout: page
title: Advanced Kotlin & Android Engineering
---

A unified, deep-dive reference covering the Kotlin language, data structures, concurrency, the Android application layer, architecture, testing, and tooling — written for senior-level interview preparation and day-to-day engineering.

📦 **GitHub repository:** [github.com/LeonardoBai12/AdvancedKotlinAndroidEngineering](https://github.com/LeonardoBai12/AdvancedKotlinAndroidEngineering)

## About

Hi, I'm **Leonardo Bai**, an Android engineer from Brazil.

This repository started as a collection of notes, interview preparation material, handwritten manuscripts, video scripts, and concepts I revisited countless times until I truly understood them. Over the years, it evolved into a structured reference covering many of the topics that frequently appear in senior-level Android engineering discussions.

More importantly, this project is my interpretation of the **Knowledge Portfolio** concept introduced by **David Thomas** and **Andrew Hunt** in *The Pragmatic Programmer*.

In the book, the authors encourage developers to treat knowledge as an investment: something that must be accumulated continuously, diversified across different areas, reviewed regularly, and shared whenever possible. Technologies change, frameworks come and go, and expertise naturally depreciates over time. The ability to learn, adapt, and continuously invest in your own growth is one of the most valuable skills an engineer can develop.

This repository represents years of that investment.

It combines lessons learned from real-world Android development, technical interviews, official documentation, books, experimentation, teaching, writing, and even the occasional rubber duck debugging session. Many sections exist because I encountered a concept that I couldn't explain clearly enough, and decided to keep studying until I could.

While the primary focus is Kotlin and Android, the broader goal is to build a durable foundation in software engineering fundamentals — understanding not only *how* things work, but also *why* they work.

If you're building your own knowledge portfolio, I hope this repository can contribute to it.

---

## References & Inspirations

The content is heavily influenced by official documentation and several books that have shaped the way I think about software engineering:

* [Kotlin Documentation](https://kotlinlang.org/docs/home.html) — JetBrains
* [Android Developers Documentation](https://developer.android.com/docs) — Google
* **Clean Code** — Robert C. Martin
* **Clean Architecture** — Robert C. Martin
* **The Pragmatic Programmer** — David Thomas & Andrew Hunt

Special thanks to David Thomas and Andrew Hunt for introducing the Knowledge Portfolio mindset, which became one of the guiding principles behind this project.

---

## Built With

The site is built with [Jekyll](https://jekyllrb.com/) using the [Chirpy](https://github.com/cotes2020/jekyll-theme-chirpy) theme.

---

## Part I — Language & Data Structures

| Chapter                                                                                  | Topics                                                                      |
| ---------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| [1 · Kotlin Foundations](part-1-language-data-structures/chapter-01-kotlin-foundations/) | Algorithms, compilation, data types, variables, operators, control flow     |
| [2 · OOP Foundations](part-1-language-data-structures/chapter-02-oop-foundations/)       | Encapsulation, inheritance, polymorphism, abstraction, dependency inversion |
| [3 · Idiomatic Kotlin](part-1-language-data-structures/chapter-03-idiomatic-kotlin/)     | data/sealed/enum classes, scope functions, extensions, generics, variance   |
| [4 · Memory & Hashing](part-1-language-data-structures/chapter-04-memory-hashing/)       | Stack vs heap, object references, HashMap internals, equals/hashCode        |
| [5 · Garbage Collection](part-1-language-data-structures/chapter-05-garbage-collection/) | JVM GC, reference types, memory leaks, Android considerations               |
| [6 · Kotlin Collections](part-1-language-data-structures/chapter-06-kotlin-collections/) | List/Set/Map, arrays, sequences, lazy evaluation, common operations         |

## Part II — Performance & Concurrency Theory

| Chapter                                                                                               | Topics                                                                 |
| ----------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| [7 · Algorithm Analysis & Big O](part-2-performance-concurrency/chapter-07-algorithm-analysis-big-o/) | Complexity classes, asymptotic analysis, O(1)–O(N!), LeetCode patterns |
| [8 · Concurrent Collections](part-2-performance-concurrency/chapter-08-concurrent-collections/)       | ConcurrentHashMap, CopyOnWriteArrayList, thread-safe collections       |
| [9 · The N+1 Problem](part-2-performance-concurrency/chapter-09-n-plus-1-problem/)                    | Query batching, eager/lazy loading, Room relationship strategies       |

## Part III — Asynchronous Kotlin

| Chapter                                                                            | Topics                                                                      |
| ---------------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| [10 · Kotlin Coroutines & Flow](part-3-async-kotlin/chapter-10-kotlin-coroutines/) | Fundamentals, builders, dispatchers, cancellation, exception handling, Flow, Channels |

## Part IV — Android Application Layer

| Chapter                                                                                      | Topics                                                                     |
| -------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| [11 · The Compilation Pipeline](part-4-android-application/chapter-11-compilation-pipeline/) | Source → bytecode → DEX → ART, R8, ProGuard                                |
| [12 · Android Lifecycle](part-4-android-application/chapter-12-android-lifecycle/)           | Activity/Fragment lifecycle, ViewModel scope, process death                |
| [13 · Jetpack Compose](part-4-android-application/chapter-13-jetpack-compose/)               | Composables, state, recomposition, side effects                            |
| [14 · Deep Links & Navigation](part-4-android-application/chapter-14-deep-links/)            | URI routing, explicit/implicit deep links, NavController                   |
| [15 · Android Security](part-4-android-application/chapter-15-android-security/)             | Attack surface, encryption, secrets, network security, OWASP Mobile Top 10 |
| [20 · Background Work & Notifications](part-4-android-application/chapter-20-background-work-notifications/) | Services (started/bound, Binder, Messenger, AIDL), WorkManager, BroadcastReceiver, Notifications, Foreground Services |
| [21 · Platform Constraints & Push](part-4-android-application/chapter-21-platform-constraints-push/) | Doze Mode, App Standby Buckets, battery optimisation, AlarmManager, FCM, background limits history |

## Part V — Design & Architecture

| Chapter                                                                                              | Topics                                                               |
| ---------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| [16 · Gradle & Multi-Module Architecture](part-5-design-architecture/chapter-16-gradle-multimodule/) | Module types, REP/CCP/CRP, api vs implementation, convention plugins |
| [17 · SOLID Principles](part-5-design-architecture/chapter-17-solid-principles/)                     | SRP, OCP, LSP, ISP, DIP — with Kotlin examples                       |
| [18 · Architecture & Pragmatic Wisdom](part-5-design-architecture/chapter-18-architecture/)          | Clean Architecture layers, MVVM, state/events, DI                    |
| [19 · Testing](part-5-design-architecture/chapter-19-testing/)                                       | Testing pyramid, FIRST principles, unit/integration/UI/E2E tests     |

## Appendices

|                                                                                      | Topics                                                 |
| ------------------------------------------------------------------------------------ | ------------------------------------------------------ |
| [Appendix A · Profiling & Diagnostics](appendices/appendix-a-profiling-diagnostics/) | Android Studio Profiler, LeakCanary, CPU/Memory/Vitals |
