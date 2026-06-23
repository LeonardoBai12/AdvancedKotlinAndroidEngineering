---
layout: page
title: "Part IV — Android Application Layer"
---

*[← Back to Guide Index](../)*

Android-specific internals: the compilation pipeline, lifecycle, Jetpack Compose, navigation, security, and OS internals.

## Chapters

| # | Chapter | Topics |
| --- | --- | --- |
| 11 | [The Compilation Pipeline](./chapter-11-compilation-pipeline/) | Source → bytecode → DEX → ART, R8, ProGuard, NDK/JNI, Reflection |
| 12 | [Android Lifecycle](./chapter-12-android-lifecycle/) | Activity/Fragment lifecycle, ViewModel scope, process death, Service, BroadcastReceiver, ContentProvider, offline-first pattern |
| 13 | [Jetpack Compose](./chapter-13-jetpack-compose/) | Composables, state, recomposition, side effects |
| 14 | [Deep Links & Navigation](./chapter-14-deep-links/) | URI routing, explicit/implicit deep links, NavController |
| 15 | [Android Security](./chapter-15-android-security/) | Attack surface, encryption, secrets, TLS, certificate pinning, permissions, emulator detection, app signing, OWASP Mobile Top 10 |
| 16 | [Android OS Internals](./chapter-16-android-os-internals/) | Linux kernel, app launch at kernel level, Zygote, Binder IPC, sandboxing, SELinux |
| 20 | [Background Work & Notifications](./chapter-20-background-work-notifications/) | Services (started/bound/hybrid, Binder, Messenger, AIDL, IntentService history), WorkManager (constraints, chaining, unique work, expedited), BroadcastReceiver (static/dynamic, goAsync, Android 8+ restrictions, NetworkCallback), Notifications (channels, styles, scheduling, permissions), Foreground Services (types, Android 14 enforcement) |
| 21 | [Platform Constraints & Push](./chapter-21-platform-constraints-push/) | Doze Mode, App Standby Buckets, battery optimisation, AlarmManager (full API), FCM (push notifications, data vs notification messages, token management), background execution limits history |
