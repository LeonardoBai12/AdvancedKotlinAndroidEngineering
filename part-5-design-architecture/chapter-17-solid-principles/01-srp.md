---
layout: default
title: Srp
parent: SOLID Principles
nav_order: 1
---

*Five design principles by Robert C. Martin, in practical Kotlin and Android*

SOLID is an acronym for five design principles introduced by Robert C. Martin (Uncle Bob) that make software designs more understandable, flexible, and maintainable. Every one of them serves a single ultimate goal, which The Pragmatic Programmer captures in three letters: **ETC — Easier To Change**. Why use the Single Responsibility Principle? ETC. Why segregate interfaces? ETC. Why depend on abstractions? ETC. Keep that lens in mind throughout this chapter: SOLID is not dogma, it is a toolkit for making change cheap.

Martin defines the scope of SOLID precisely in *Clean Architecture* (Part III): the principles tell us how to organise functions and data structures into classes, and how those classes should be interconnected. "A class is merely a coupled grouping of functions and data", and every system has such groupings whether it calls them classes or not. The principles operate at the **mid-level** — above individual lines of code, inside the modules and components that shape the system — and they aim to create software structures that:

- **Tolerate change** — a single requirement change requires the minimum number of edits.
- **Are easy to understand** — a reader grasps intent without archaeology.
- **Form the base of reusable components** — they can be assembled into many different systems.

*(Source: Martin, R.C. — Clean Architecture: A Craftsman's Guide to Software Structure and Design, Part III — Design Principles)*

| Letter | Principle | Key concept |
| --- | --- | --- |
| S | Single Responsibility | One, and only one, reason to change |
| O | Open-Closed | Open for extension, closed for modification |
| L | Liskov Substitution | Subtypes must replace base types cleanly |
| I | Interface Segregation | No fat interfaces |
| D | Dependency Inversion | Depend on abstractions, not concretions |

## Single Responsibility Principle

Martin's formulation of SRP in *Clean Architecture* (Ch. 7) evolved through two stages. The initial statement — *"a module should have one, and only one, reason to change"* — while correct, invited a persistent misreading: people equated it with the refactoring heuristic that functions should do one thing. Martin is explicit that this is a separate, lower-level principle. SRP is about **actors** — the groups of users or stakeholders who drive change. The final, precise statement:

> *"A module should be responsible to one, and only one, actor."*
> *(Martin, R.C. — Clean Architecture, Ch. 7 — The Single Responsibility Principle)*

A module, in the simplest sense, is a source file — or more broadly, a cohesive set of functions and data structures. An actor is a group of users or stakeholders who share a reason for change. A Conway's Law corollary follows directly: the best architecture for a system is heavily influenced by the social structure of the organisation using it, such that each module has one, and only one, reason to change.

### The shared-algorithm trap

A subtle and consequential SRP violation occurs when two actors inadvertently share a function. Martin's canonical example in *Clean Architecture* (Ch. 7): an `Employee` class has both `calculatePay()` (owned by the CFO team for payroll) and `reportHours()` (owned by the COO/HR team). Both delegate to a shared helper `regularHours()`. The CFO team requests a change to how regular hours are computed for payroll; a developer edits `regularHours` — unaware that `reportHours` calls the same function. The COO's HR reports now carry wrong numbers, discovered only after the damage is done. *"These are problems that occur because we bring too close together the code that different actors depend on. That is why the SRP says to separate the code that different actors depend on."* (Martin, ibid.)

```kotlin
// RISKY: CFO and COO share a helper — editing it for one can silently break the other
class Employee(val hours: List<HourEntry>) {
    fun calculatePay(): Money      = regularHours() * payRate   // CFO actor
    fun reportHours(): HoursReport = HoursReport(regularHours()) // COO actor
    private fun regularHours(): Double = hours.sumOf { it.regular } // shared!
}

// FIXED: each actor owns its own calculation path
class PayCalculator(private val employee: Employee) {
    fun calculatePay(): Money =
        employee.hours.sumOf { it.regular } * employee.payRate
}
class HoursReporter(private val employee: Employee) {
    fun reportHours(): HoursReport =
        HoursReport(employee.hours.sumOf { it.regular })
}
```

*Violation — four actors, one class*

```kotlin
// BAD: Business, Security, Marketing, and Analytics all edit this
class UserManager(
    private val database: Database,
    private val emailService: EmailService
) {
    fun createUser(name: String, email: String): User { /* Business */ }
    fun validateUser(user: User): Boolean { /* Security */ }
    fun sendWelcomeEmail(user: User) { /* Marketing */ }
    fun generateUserReport(): String { /* Analytics */ }
}
```

*Fixed — one responsibility per class*

```kotlin
// Business team -- persistence
class UserRepository(private val db: Database) {
    fun save(user: User): User = db.saveUser(user)
}

// Security team -- validation
class UserValidator {
    fun validate(user: User): ValidationResult {
        val errors = mutableListOf<String>()
        if (!user.email.contains("@")) errors.add("Invalid email")
        return if (errors.isEmpty()) ValidationResult.Success
               else ValidationResult.Failure(errors)
    }
}

// Marketing team -- notifications
class UserEmailNotifier(private val emailService: EmailService) {
    fun sendWelcomeEmail(user: User) = emailService.send(user.email, "Welcome!")
}
```

- Easier to understand — each class has a clear, single purpose.
- Easier to test — responsibilities are isolated.
- Easier to change — a change affects only one actor's class.
- Fewer merge conflicts — different teams touch different files.

---

[↑ Chapter Index](../) · [Next: OCP →](../02-ocp/)
