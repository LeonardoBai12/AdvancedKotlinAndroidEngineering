# Chapter 17: SOLID Principles — DIP & Quick Reference

## D — Dependency Inversion Principle

'High-level modules should not depend on low-level modules. Both should depend on abstractions.' Source-code dependencies are inverted relative to the flow of control: business logic does not depend on implementation details — the details depend on abstractions defined by the business logic. This is the backbone of Clean Architecture and of testability.

Martin states the flexible-system corollary in *Clean Architecture* (Ch. 11): *"os sistemas mais flexíveis são aqueles em que as dependências de código-fonte se referem apenas a abstrações e não a itens concretos."* In a statically typed language like Kotlin, `use`, `import`, and `include` statements should refer only to modules containing interfaces, abstract classes, or other abstract declarations — never to concrete implementations.

### Four coding rules

Martin distils the DIP into four concrete coding practices (Martin, R.C. — Clean Architecture, Ch. 11 — The Dependency Inversion Principle):

1. **Do not refer to volatile concrete classes.** Refer to abstract interfaces instead. This applies in all languages and generally forces the use of Abstract Factories for object creation.
2. **Do not derive from volatile concrete classes.** In a statically typed language, inheritance is the strongest and most rigid source-code relationship — use it with care. *"Não derive de classes concretas voláteis."*
3. **Do not override concrete functions.** Concrete functions carry source-code dependencies; overriding them inherits those dependencies rather than eliminating them. Declare the function abstract and provide multiple implementations instead.
4. **Never mention the name of anything concrete and volatile.** This is a restatement of the principle itself.

The word **volatile** is critical. Not every concrete class is dangerous to depend on — `String` in Kotlin is concrete, but stable enough that depending on it carries no practical risk. The classes to avoid depending on directly are the ones you are actively developing, the ones that change frequently.

### Stable abstractions

In *Clean Architecture* (Ch. 11), Martin observes: *"as mudanças nas implementações concretas normalmente ou nem sempre requerem mudanças nas interfaces que implementam. As interfaces são, portanto, menos voláteis que as implementações."* Good designers work hard to reduce interface volatility — they look for ways to add functionality in implementations without touching the interfaces. This is sometimes called *Software Design 101*.

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

The control flow runs `UserService` → `UserRepository` → `MySQLUserRepository` (at runtime). But the source-code dependency runs `UserService` → `UserRepository` ← `MySQLUserRepository` — `MySQLUserRepository` depends on the interface, not the other way around. *"As dependências de código-fonte estão invertidas em relação ao fluxo de controle — e é por isso que nos referimos a esse princípio como Inversão de Dependência."* (Martin, ibid.)

This inversion is what allows business rules to be deployed and tested independently of databases, frameworks, and delivery mechanisms. In Clean Architecture terms, the domain layer declares the `UserRepository` interface; the data layer provides `MySQLUserRepository`; and at runtime a factory or DI container wires them together — the only place where concrete classes are instantiated. The Abstract Factory pattern is the standard mechanism for creating objects while keeping the caller free of any concrete dependency.

DIP violations cannot be completely eliminated — every system needs at least one concrete component (commonly the `main` function or the composition root) that wires abstractions to implementations. The goal is not purity but containment: *"as violações do DIP não podem ser removidas completamente, mas é possível reuni-las em um número menor de componentes concretos para que fiquem separadas do resto do sistema."* (Martin, ibid.)

## Quick Reference & When to Apply

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

← [Previous: LSP & ISP](./02-lsp-isp.md) · [↑ Chapter Index](./README.md)
