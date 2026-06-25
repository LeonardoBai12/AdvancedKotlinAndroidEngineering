---
layout: default
title: App Launch Zygote
parent: Android OS Internals
nav_order: 2
---

## What Is Zygote?

When your Android device boots, one of the first processes the `init` daemon spawns is **Zygote**. Zygote is a special process whose only job is to be the parent of every Android application process. Its name — from the Greek for "yoked together" — reflects its role: it pre-loads all the Java/Kotlin framework classes and the ART runtime once, at boot, and then spawns new app processes by forking itself.

This design solves a cold-start problem. Starting an Android app from scratch would require:
1. Starting a new Linux process
2. Starting the ART VM
3. Loading the core framework classes (~10,000+ classes from `android.jar`, `kotlin-stdlib`, etc.)

Steps 2 and 3 are expensive. Zygote does them once at boot. When your app launches, step 3 is already done — the child process gets a copy of Zygote's already-warmed VM via Linux's **copy-on-write** fork semantics.

## The Full Launch Sequence

```
User taps app icon
        │
        ▼
Launcher calls startActivity(intent)
        │  [Binder IPC via /dev/binder to system_server]
        ▼
ActivityManagerService (AMS) in system_server
        │  Checks: does this app's process already exist?
        │  No → need to fork a new process
        │
        ▼
AMS sends fork command to Zygote
        │  [Unix domain socket: /dev/socket/zygote — NOT Binder]
        ▼
Zygote receives command → calls fork()
        │
        │  fork() → clone() syscall in kernel
        │  Kernel creates child process:
        │  • Copies Zygote's virtual address space (CoW)
        │  • Pre-loaded classes already in memory
        │
        ▼
Child process: Zygote specialization
        │  1. setuid(appUid) / setgid(appGid)      ← assign Linux UID/GID
        │  2. Set SELinux context for this app
        │  3. Load app's own DEX files into ART
        │  4. Drop capabilities (least privilege)
        │
        ▼
ActivityThread.main() starts running
        │  [Binder IPC back to AMS: "I'm ready"]
        ▼
AMS delivers the pending Intent
        │
        ▼
Application.onCreate() → Activity.onCreate()
```

## Why Zygote Uses a Socket, Not Binder

This is a classic interview question. The AMS communicates with system services via Binder everywhere — except to Zygote. Instead, it uses a Unix domain socket. Why?

Binder maintains a thread pool. After `fork()`, the Linux kernel copies only the thread that called `fork()` — the other Binder threads are not copied, but the mutexes and internal state they held **are**. This creates an instant deadlock in the child: threads that were holding locks are gone, and the child process can never acquire those locks.

Sockets don't have this problem. A single blocking `recv()` on a socket requires no thread pool, so the child's copy is immediately usable.

> **Interview answer:** Zygote uses a socket instead of Binder because `fork()` only copies the calling thread. Binder's thread pool uses mutexes that would deadlock in the child. A socket-based protocol avoids this entirely.

## Copy-on-Write Memory

When `fork()` creates the child process, the kernel does not physically copy the parent's memory pages. Instead, it marks all shared pages as **copy-on-write (CoW)**:

```
Before write:
  Zygote process:   [page A → physical frame 0x1000]
  App process:      [page A → physical frame 0x1000]  ← same physical memory

On write (app modifies a page):
  Kernel copies frame 0x1000 → new frame 0x2000
  App process:      [page A → physical frame 0x2000]  ← now private copy
  Zygote process:   [page A → physical frame 0x1000]  ← unaffected
```

The pre-loaded framework classes in Zygote are read-only — the app never writes to them — so they stay CoW and are physically shared across all running app processes. This is why Zygote matters: it dramatically reduces the RAM cost of running many apps simultaneously.

## Process Specialization — What Happens in the Child

After `fork()` returns in the child, `ZygoteInit.java` calls through to native code (`com_android_internal_os_Zygote.cpp`) to perform specialization:

1. **Set UID/GID**: `setresuid(uid, uid, uid)` and `setresgid(gid, gid, gid)` — assigns the app its unique Linux user ID
2. **Set supplementary GIDs**: e.g., the `inet` group (for network access) if the app has `INTERNET` permission
3. **Set SELinux domain**: `selinux_android_setcontext()` — places the app in its own SELinux domain
4. **Mount namespace**: creates an isolated view of the filesystem (app can't see other apps' data dirs)
5. **Load app DEX**: the app's own classes are loaded into ART on top of the already-warmed VM
6. **Drop capabilities**: capabilities like `CAP_SYS_PTRACE` are removed — the app runs with minimum privileges

## Cold Start vs Warm Start vs Hot Start

| Type | What happens | Launch time |
|---|---|---|
| **Cold start** | No process, no Activity in memory — full fork + specialization + onCreate | Slowest (~500ms+) |
| **Warm start** | Process exists, Activity was destroyed — re-create Activity, skip fork | Medium |
| **Hot start** | Process and Activity both exist — just bring to foreground | Fastest (~100ms) |

Zygote only participates in a cold start. The key metric for cold start performance is **Time to Initial Display (TTID)**, visible in Logcat as `Displayed com.yourapp/.MainActivity: +523ms`.

---

← [Previous: Linux Kernel](../01-linux-kernel/) · [↑ Chapter Index](../) · [Next: IPC Mechanisms →](../03-ipc-mechanisms/)
