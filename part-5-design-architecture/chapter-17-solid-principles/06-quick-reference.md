---
layout: default
title: Quick Reference
parent: SOLID Principles
nav_order: 6
---

| Principle | Question that triggers it | Solution |
| --- | --- | --- |
| SRP | Do multiple actors change this class? | Split by actor / responsibility |
| OCP | Am I editing old code for a new feature? | Use abstractions / strategy |
| LSP | Can a subtype not replace the base type? | Separate the abstractions |
| ISP | Am I implementing unused methods? | Split into focused interfaces |
| DIP | Does business logic know the framework? | Depend on abstractions |

> **Interview Tip:**
>
> The goal is not to follow SOLID blindly, but to understand WHY each principle exists and apply it when it makes your code easier to change. Don't over-engineer simple features — a plain data class needs no interface. Apply incrementally, and refactor when pain points emerge.

---

← [Previous: DIP](../05-dip/) · [↑ Chapter Index](../)
