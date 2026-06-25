---
layout: default
title: "Chapter 16: Android OS Internals"
parent: "Part IV — Android Application Layer"
nav_order: 6
has_children: true
---

*[← Back to Part](../)*

*Linux kernel, app launch, Zygote, Binder IPC, sandboxing, and SELinux*

Most Android engineers spend their careers at the framework layer — Activities, ViewModels, Retrofit. But the interview topics that separate senior candidates from the rest probe one level deeper: what is the OS actually doing when your app launches? How does one process communicate with another without shared memory? How does the kernel prevent an app from reading another app's files?

This chapter answers those questions by tracing Android from the Linux kernel up through the security model, mapping each interview topic to the layer where it lives.

## Contents

1. [Linux Kernel & Architecture](./01-linux-kernel/)
2. [App Launch & Zygote](./02-app-launch-zygote/)
3. [IPC Mechanisms](./03-ipc-mechanisms/)
4. [Security Model: Sandboxing & SELinux](./04-security-model/)
