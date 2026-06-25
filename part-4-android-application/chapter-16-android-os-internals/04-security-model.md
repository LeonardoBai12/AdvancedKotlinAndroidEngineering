---
layout: default
title: Security Model
parent: Android OS Internals
nav_order: 4
---

## Android's Security Model

Android's security model has two complementary layers:

1. **DAC (Discretionary Access Control)** — Linux UID-based file permissions, enforced by the kernel. Each app has a unique UID; the kernel blocks any filesystem access where the UID doesn't match.
2. **MAC (Mandatory Access Control)** — SELinux policies enforced by the kernel. Even if UID permissions allow an action, SELinux can independently deny it. Neither layer can be overridden by the other.

The combination means a compromised app process faces *two* independent permission systems to escape from.

## Layer 1 — UID-Based Sandboxing (DAC)

Every Android app is assigned a unique Linux user ID at install time (e.g., `u0_a105` — user 0, app 105). The kernel uses this UID to enforce standard Linux file permissions:

```
/data/data/com.yourapp/           rwx------  u0_a105  u0_a105
/data/data/com.yourapp/files/     rwx------  u0_a105  u0_a105
/data/data/com.otherapp/          rwx------  u0_a150  u0_a150   ← different UID
```

Your app process runs as `u0_a105` and cannot open any file owned by `u0_a150`. The kernel rejects the `open()` syscall with `EACCES`. No Android API, no JNI call, no root-level trick can bypass this without a kernel exploit.

### Multiple users

In multi-user Android (work profiles, secondary users), the convention extends: user 0 apps are `u0_aXXX`, user 10 apps are `u10_aXXX`. Same UID-based isolation applies within each user, plus cross-user isolation.

### Shared UID (deprecated)

Two apps that declare `android:sharedUserId` in their manifest **and** share the same signing certificate can run under the same UID, seeing each other's files. This was used historically for tightly-coupled apps (e.g., Google Play Services packages). It is deprecated in API level 29+ and will be removed — the modern alternative is `ContentProvider` or explicit file sharing via `FileProvider`.

## Layer 2 — SELinux (MAC)

**Security-Enhanced Linux** is a Linux Security Module (LSM) that enforces a policy governing what every process is allowed to do, independently of UID. It was introduced in Android 4.3 (permissive), fully enforced in Android 5.0, and extended to per-app domains in Android 9.

### How SELinux works

Every object in the system — processes, files, sockets, Binder nodes — has a **security label** (context). A policy ruleset defines which labels can interact and how.

```
# Context format:  user:role:type:sensitivity[:categories]

# A third-party app process:
u:r:untrusted_app:s0:c512,c768

# The app's data directory:
u:object_r:app_data_file:s0:c512,c768

# System server process:
u:r:system_server:s0
```

Each access attempt generates a **policy check**: "can label X perform action Y on label Z?" If the policy has no matching `allow` rule, the kernel **denies** the operation and logs it:

```
avc: denied { read } for pid=1234 name="foo" scontext=u:r:untrusted_app:s0
             tcontext=u:object_r:system_file:s0 tclass=file permissive=0
```

### SELinux domains in Android

| API level | Third-party app domain | Effect |
|---|---|---|
| 4.3–4.4 | Permissive / single domain | Violations logged but not enforced |
| 5.0–8.1 | `untrusted_app` (shared) | All third-party apps in the same SELinux domain — inter-app isolation via UID only |
| 9.0+ (targetSdk ≥ 28) | `untrusted_app_27` per-app | Each app in its own domain with unique MLS categories (`c512,c768`) |

The MLS categories (the `c512,c768` suffix) are unique to each app. This means app A's files and app B's files both have `app_data_file` type, but different categories. The policy requires categories to match, so A's process cannot access B's files even though both are `untrusted_app`.

### Debugging SELinux

```bash
# On a rooted/dev device: see all AVC denials in real time
adb shell logcat | grep "avc:"

# Check a file's SELinux context
adb shell ls -Z /data/data/com.yourapp/

# Check a process's SELinux context
adb shell ps -Z | grep com.yourapp

# Temporarily set to permissive (for debugging — never ship)
adb shell setenforce 0
```

## Seccomp-BPF — Syscall Filtering

Since Android 8.0, every app process has a **seccomp-BPF** (Berkeley Packet Filter) filter attached at startup. This is a kernel-level allowlist of syscalls the process is permitted to make. Any attempt to call a syscall not on the list results in `SIGKILL` — the process is killed immediately, with no chance to catch the signal.

This prevents an attacker who has compromised an app process from calling dangerous syscalls like `ptrace`, `setuid`, `mount`, or `init_module` (kernel module loading) — even if they find a way to execute arbitrary native code.

```c
// Example: attempting mount() from an app process
// → SIGKILL from seccomp filter
// → logged as: "seccomp killed thread X with filter failure"
long result = syscall(SYS_mount, ...);  // never returns
```

The seccomp filter is applied before SELinux in the permission check order, so both independently defend against privilege escalation.

## Security Model Summary

```
App process attempts an operation
          │
          ▼
  1. seccomp-BPF: is this syscall allowed?
          │ No → SIGKILL (no log, process dies)
          │ Yes ↓
          ▼
  2. Linux DAC: does the UID have file/socket permissions?
          │ No → EACCES / EPERM returned to caller
          │ Yes ↓
          ▼
  3. SELinux MAC: does the policy allow this label → label action?
          │ No → EACCES + avc: denied log
          │ Yes ↓
          ▼
  Operation succeeds
```

Three independent layers: an attacker who defeats one still faces the other two.

---

← [Previous: IPC Mechanisms](../03-ipc-mechanisms/) · [↑ Chapter Index](../)
