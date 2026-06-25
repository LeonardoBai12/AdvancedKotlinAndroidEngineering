---
layout: default
title: Ipc Mechanisms
parent: Android OS Internals
nav_order: 3
---

## Why IPC Exists

Android apps run in isolated processes — by design, no process can read another's memory. But the system is built from many processes that must cooperate: your app, `system_server`, `surfaceflinger`, `mediaserver`, and dozens of others. Inter-Process Communication (IPC) is the kernel-controlled bridge between them.

Android has multiple IPC mechanisms, each with different trade-offs. **Binder** is the primary and most important one.

## IPC Mechanisms Overview

| Mechanism | Layer | Primary use | Copies |
|---|---|---|---|
| **Binder** | Kernel driver | App ↔ system services, AIDL | 1 |
| **Unix domain sockets** | POSIX | Zygote, `adbd`, system daemons | 2 |
| **Shared memory (ashmem / memfd)** | Kernel | Large data: camera frames, bitmaps | 0 |
| **Pipes** | POSIX | Simple native process stdio | 2 |
| **Signals** | POSIX | Process termination, basic notification | 0 (no data) |
| **Intent / Broadcast** | Framework | Loose-coupled app ↔ app messaging | N/A (over Binder) |
| **ContentProvider** | Framework | Structured data sharing between apps | N/A (over Binder) |

## Binder — The Core IPC Driver

Binder is a Linux character device driver (`drivers/android/binder.c`) that ships in Android's kernel. It provides **one-copy** RPC — when process A sends data to process B, the data crosses the process boundary in a single kernel copy instead of the two copies required by pipes and sockets.

### How Binder achieves one-copy

Traditional IPC: `copy_from_user()` (user → kernel buffer) + `copy_to_user()` (kernel buffer → user).

Binder: at startup, each process calls `mmap()` on `/dev/binder`. The kernel maps a shared region that is simultaneously visible in user space (via the process's virtual address) and in kernel space. When data arrives, `copy_from_user()` copies it once directly into the receiver's mapped region — the receiver can read it from user space without a second copy.

```
Process A (client)                  /dev/binder (kernel)           Process B (server)
     │                                     │                               │
     ├── open("/dev/binder") ─────────────►│                               │
     ├── mmap() ──────────────────────────►│  maps shared region           │
     │                                     │◄─── open("/dev/binder") ──────┤
     │                                     │◄─── mmap() ───────────────────┤
     │                                     │                               │
     ├── ioctl(BC_TRANSACTION, parcel) ───►│                               │
     │                                     │── copy_from_user() ──────────►│
     │                                     │   (ONE copy into B's mmap)    │
     │                                     │── wake B's thread ───────────►│
     │                                     │                               ├── read from mmap (zero copy)
     │                                     │                               ├── process request
     │◄────────────────────── ioctl(BC_REPLY, result) ─────────────────────┤
```

### Binder Transactions

Each Binder call is a **transaction**. A transaction carries:

- **Parcel**: the serialized method arguments (primitives, Parcelables, file descriptors, or IBinder references)
- **Transaction code**: which method is being called
- **Flags**: one-way (async, no reply) or two-way (sync, waits for reply)

The client side packs a `Parcel` and issues `ioctl(BC_TRANSACTION)`. The kernel wakes a thread in the server process, delivers the Parcel, and the server calls `ioctl(BC_REPLY)` to send the return value back.

### AIDL — Interface Definition Layer

Writing raw Parcel packing/unpacking by hand is error-prone. **AIDL** (Android Interface Definition Language) generates the boilerplate:

```kotlin
// IMyService.aidl
interface IMyService {
    int computeSum(int a, int b);
}
```

AIDL generates:
- **Proxy** (client side): packs arguments into a `Parcel`, calls `transact()`
- **Stub** (server side): unpacks the `Parcel`, calls the real implementation, packs the result

The generated `Stub` class is what you extend in a `Service`:

```kotlin
class MyService : Service() {
    private val binder = object : IMyService.Stub() {
        override fun computeSum(a: Int, b: Int): Int = a + b
    }
    override fun onBind(intent: Intent): IBinder = binder
}
```

### Binder Identity — IBinder and Tokens

Every Binder object has a unique kernel identity. When you pass an `IBinder` across process boundaries (e.g., as an `Intent` extra), the kernel does not copy the object — it passes a **handle** that refers back to the original object in the original process. This is how Android implements **death recipients** (you can register a callback that fires if the remote process dies) and **tokens** (the Activity back stack uses Binder tokens to identify windows without revealing app internals to other apps).

## Messenger

`Messenger` is a thin wrapper around AIDL that routes messages through a `Handler`. It is simpler than raw AIDL but single-threaded (messages are processed sequentially in the Handler's looper).

```kotlin
// Service side
val messenger = Messenger(Handler(Looper.getMainLooper()) { msg ->
    when (msg.what) {
        MSG_PING -> msg.replyTo?.send(Message.obtain(null, MSG_PONG))
    }
    true
})
override fun onBind(intent: Intent): IBinder = messenger.binder
```

Use Messenger when you need simple request/reply between processes and don't need concurrent method calls.

## Shared Memory — Zero-Copy Large Data

For large payloads (camera frames, decoded bitmaps, audio buffers), copying through Binder would be too slow. Android uses shared memory:

- **`ashmem`** (Android shared memory): legacy mechanism, accessible via `MemoryFile` in Java
- **`memfd_create`**: modern POSIX approach, used in Android 10+

A `Bitmap` can be backed by shared memory so it can be passed between processes (e.g., to `surfaceflinger` for rendering) without any data copy.

---

← [Previous: App Launch & Zygote](../02-app-launch-zygote/) · [↑ Chapter Index](../) · [Next: Security Model →](../04-security-model/)
