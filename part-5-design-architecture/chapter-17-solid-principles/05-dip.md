---
layout: default
title: Dip
parent: SOLID Principles
nav_order: 5
---

'High-level modules should not depend on low-level modules. Both should depend on abstractions.' Source-code dependencies are inverted relative to the flow of control: business logic does not depend on implementation details — the details depend on abstractions defined by the business logic. This is the backbone of Clean Architecture and of testability.

Martin states the flexible-system corollary in *Clean Architecture* (Ch. 11): *"the most flexible systems are those in which source-code dependencies refer only to abstractions, not to concretions."* In a statically typed language like Kotlin, `use`, `import`, and `include` statements should refer only to modules containing interfaces, abstract classes, or other abstract declarations — never to concrete implementations.

### Four coding rules

Martin distils the DIP into four concrete coding practices (Martin, R.C. — Clean Architecture, Ch. 11 — The Dependency Inversion Principle):

1. **Do not refer to volatile concrete classes.** Refer to abstract interfaces instead. This applies in all languages and generally forces the use of Abstract Factories for object creation.
2. **Do not derive from volatile concrete classes.** In a statically typed language, inheritance is the strongest and most rigid source-code relationship — use it with care. *"Do not derive from volatile concrete classes."*
3. **Do not override concrete functions.** Concrete functions carry source-code dependencies; overriding them inherits those dependencies rather than eliminating them. Declare the function abstract and provide multiple implementations instead.
4. **Never mention the name of anything concrete and volatile.** This is a restatement of the principle itself.

The word **volatile** is critical. Not every concrete class is dangerous to depend on — `String` in Kotlin is concrete, but stable enough that depending on it carries no practical risk. The classes to avoid depending on directly are the ones you are actively developing, the ones that change frequently.

### Stable abstractions

In *Clean Architecture* (Ch. 11), Martin observes: *"changes to concrete implementations do not usually — or in fact always — require changes to the interfaces they implement. Interfaces are therefore less volatile than implementations."* Good designers work hard to reduce interface volatility — they look for ways to add functionality in implementations without touching the interfaces. This is sometimes called *Software Design 101*.

*Violation — high-level tied to a concrete low-level class*

```kotlin
class MySQLDatabase { fun save(user: User) { /* MySQL-specific */ } }

class UserService(private val db: MySQLDatabase) {  // concrete dependency!
    fun registerUser(user: User) = db.save(user)    // tied to MySQL forever
}
// Problems: can't switch databases, can't unit-test without a real MySQL instance.
```

*Fixed — both depend on an abstraction*

```kotlin
interface UserRepository {                  // abstraction (stable)
    fun save(user: User)
    fun findById(id: String): User?
}

class UserService(private val repo: UserRepository) {  // depends on abstraction
    fun registerUser(user: User) = repo.save(user)
}

class MySQLUserRepository : UserRepository { /* ... */ }
class PostgreSQLUserRepository : UserRepository { /* ... */ }

// For tests: no database needed
class InMemoryUserRepository : UserRepository {
    private val users = mutableMapOf<String, User>()
    override fun save(user: User) { users[user.id] = user }
    override fun findById(id: String) = users[id]
}
```

### Why "inversion"

The control flow runs `UserService` → `UserRepository` → `MySQLUserRepository` (at runtime). But the source-code dependency runs `UserService` → `UserRepository` ← `MySQLUserRepository` — `MySQLUserRepository` depends on the interface, not the other way around. *"Source-code dependencies are inverted relative to the flow of control — and that is why we refer to this principle as Dependency Inversion."* (Martin, ibid.)

This inversion is what allows business rules to be deployed and tested independently of databases, frameworks, and delivery mechanisms. In Clean Architecture terms, the domain layer declares the `UserRepository` interface; the data layer provides `MySQLUserRepository`; and at runtime a factory or DI container wires them together — the only place where concrete classes are instantiated. The Abstract Factory pattern is the standard mechanism for creating objects while keeping the caller free of any concrete dependency.

DIP violations cannot be completely eliminated — every system needs at least one concrete component (commonly the `main` function or the composition root) that wires abstractions to implementations. The goal is not purity but containment: *"DIP violations cannot be eliminated entirely, but they can be gathered into a smaller number of concrete components so that they remain separated from the rest of the system."* (Martin, ibid.)

---

← [Previous: ISP](../04-isp/) · [↑ Chapter Index](../) · [Next: Quick Reference →](../06-quick-reference/)
