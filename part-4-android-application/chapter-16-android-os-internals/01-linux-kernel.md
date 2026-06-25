---
layout: default
title: "Chapter 16: Android OS Internals — Linux Kernel & Architecture"
parent: "Chapter 16: Android OS Internals"
nav_order: 1
---

## The Android Software Stack

Android is a Linux-based operating system, but it is not standard Linux. Google built a purpose-specific software stack on top of a modified Linux kernel, adding components the upstream kernel does not have. Understanding the layers and what lives in each one is the foundation for every other OS-internals topic.

```
┌─────────────────────────────────────────────────┐
│              Android Apps (APKs)                │  Java/Kotlin, runs on ART
├─────────────────────────────────────────────────┤
│         Android Framework (Java/Kotlin)         │  ActivityManager, WindowManager,
│                                                 │  PackageManager, TelephonyManager…
├─────────────────────────────────────────────────┤
│  Native Libraries             ART / Dalvik VM   │  libc (Bionic), OpenGL ES, SQLite,
│                                                 │  WebKit, ART runtime
├─────────────────────────────────────────────────┤
│      HAL — Hardware Abstraction Layer           │  C/C++ interface between framework
│                                                 │  and hardware drivers
├─────────────────────────────────────────────────┤
│         Linux Kernel (modified)                 │  Binder IPC driver, Wakelocks,
│                                                 │  ION allocator, Low Memory Killer,
│                                                 │  Paranoid Networking, SELinux
└─────────────────────────────────────────────────┘
```

Each layer can only call downward — the kernel does not know about Activities, and the framework does not access hardware directly. The HAL is the deliberate interface that lets hardware vendors ship proprietary drivers in user space without modifying the kernel, which must remain open-source under the GPL.

## Kernel Space vs User Space

The Linux kernel enforces a hard boundary between two address spaces that exists on every modern OS:

| | Kernel Space | User Space |
|---|---|---|
| **Who runs here** | Kernel code, device drivers | Every app, system services, ART |
| **Privilege level** | Full (ring 0 on x86, EL1 on ARM) | Restricted (ring 3 / EL0) |
| **Hardware access** | Direct | None — must ask the kernel |
| **Memory** | Shared among all kernel code | Private per-process (virtual memory) |
| **Crash consequence** | Kernel panic (system halts) | Process is killed, system continues |

Apps live entirely in user space. To do anything privileged — open a file, write to the network, allocate memory pages — they must cross the boundary via a **system call**. On ARM64 (the dominant Android architecture), this is the `svc #0` instruction, which triggers a synchronous exception that switches the CPU to EL1.

```
User space:   open("/data/app/com.example/base.apk", O_RDONLY)
                     │
                     ▼  svc #0  (system call instruction)
Kernel space: sys_openat() → VFS lookup → file descriptor returned
                     │
                     ▼  eret   (return from exception)
User space:   fd = 7  (file descriptor)
```

## What Makes Android's Kernel Different

The upstream Linux kernel is not shipped directly. Android's kernel carries several patches that are specific to mobile:

| Feature | Description | Why it exists |
|---|---|---|
| **Binder IPC driver** | Character device at `/dev/binder` | Efficient cross-process calls; the backbone of all Android IPC |
| **Wakelocks** | Prevent CPU from sleeping while held | Background work (sync, alarms) can keep the device awake |
| **ION memory allocator** | Shared contiguous memory between processes | Zero-copy camera frame sharing between camera HAL and encoder |
| **Low Memory Killer (LMK)** | Kills background processes by priority | Reclaims RAM before the OOM killer would |
| **Paranoid Networking** | UID-based network access control | Per-app internet permission enforced at kernel level |
| **ashmem** | Anonymous shared memory | Predecessor to `memfd_create`; used for Binder shared buffers |

### Monolithic kernel

Android uses a **monolithic kernel** — drivers run in kernel space, sharing the same address space as the kernel itself. This is in contrast to a microkernel architecture (like QNX or L4), where drivers live in user space and communicate via IPC. The monolithic approach gives better performance at the cost of a larger kernel attack surface.

## Bionic libc

Android does not use glibc (the standard GNU C Library). It uses **Bionic**, a purpose-built libc designed for mobile:

- Smaller binary footprint (no locale support, stripped-down math)
- BSD-licensed (avoids GPL contamination in user space)
- Built-in `pthread` (POSIX threads) and `dl` (dynamic linking)
- Native support for Android's TLS (thread-local storage) model

Every NDK app links against Bionic. When you call `malloc()` from C/C++ code, you are calling Bionic's allocator, not glibc's.

---

← [↑ Chapter Index](../) · [Next: App Launch & Zygote →](../02-app-launch-zygote/)
