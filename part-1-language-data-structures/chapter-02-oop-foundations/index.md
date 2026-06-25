---
layout: default
title: OOP Foundations
parent: "Part I — Language & Data Structures"
nav_order: 2
has_children: true
---
*The four pillars of Object-Oriented Programming, with idiomatic Kotlin*

Object-Oriented Programming is the paradigm that underpins virtually every Android application. Before we explore SOLID principles, Clean Architecture, and the more advanced topics in this guide, it is worth grounding ourselves in the four pillars of OOP. These are not academic curiosities — every architectural decision you make later (why expose an interface, why favour composition, why hide a field) is a direct application of one of these four ideas. We cover each pillar with a precise definition, a worked Kotlin example, and the Kotlin-specific mechanisms that express it.

## 1. Encapsulation

Encapsulation bundles data (fields) and the behaviour that operates on that data (methods) together inside a single unit — the class — while restricting direct external access to the internal state. The outside world interacts only through a well-defined public interface. This is the mechanism behind **information hiding**: callers depend on what an object does, never on how it stores its data internally.

In Kotlin, encapsulation is expressed through visibility modifiers. There are four: **public** (the default — visible everywhere), **internal** (visible within the same Gradle module), **protected** (visible to the class and its subclasses), and **private** (visible only within the declaring class or file).

*Encapsulation — hidden state with controlled mutation*

```kotlin
class BankAccount(initialBalance: Double) {
    // Internal state is private: nobody can assign to it directly
    private var balance: Double = initialBalance

    // Public methods enforce the rules (invariants) of the class
    fun deposit(amount: Double) {
        require(amount > 0) { "Deposit must be positive" }
        balance += amount
    }

    fun withdraw(amount: Double): Boolean {
        if (amount <= 0 || amount > balance) return false
        balance -= amount
        return true
    }

    // Read-only access -- callers can observe but not mutate
    fun currentBalance(): Double = balance
}

val account = BankAccount(100.0)
account.deposit(50.0)        // OK -- goes through the rule check
// account.balance = -9999.0 // COMPILE ERROR -- balance is private
println(account.currentBalance())  // 150.0
```

Without encapsulation, any caller could set **balance** to a negative number, bypassing the business rule entirely. By making the field private and forcing all mutation through **deposit()** and **withdraw()**, the class guarantees its own consistency — the invariant 'balance is never negative' can never be violated from outside.

### The backing property pattern

A pervasive Android idiom is the backing property: a private, mutable holder paired with a public, read-only view. This is exactly how a ViewModel exposes state — the ViewModel can mutate **_state** internally, but the UI receives an immutable **StateFlow** it cannot tamper with.

*Backing property — mutable inside, read-only outside*

```kotlin
class UserViewModel : ViewModel() {
    // Private mutable backing field
    private val _state = MutableStateFlow<UiState>(UiState.Loading)

    // Public read-only exposure -- callers cannot call .value = ...
    val state: StateFlow<UiState> = _state.asStateFlow()

    fun refresh() {
        _state.value = UiState.Loading   // only the ViewModel can mutate
    }
}
```

> **Interview Tip:**
>
> Kotlin data classes expose their constructor properties publicly by default. For value objects this is fine, but prefer immutable **val** properties and the generated **copy()** method over mutable **var** fields, so the object cannot be changed under you after creation.

Martin makes a pointed observation in *Clean Architecture* (Ch. 5 — Object-Oriented Programming): Java and Kotlin actually weakened encapsulation compared to what C achieved through header files. In C, callers could see only the function signatures in the header — the private member variables were invisible. In Java and Kotlin the class declaration and its implementation live in the same file, so the compiler technically sees the private fields even though it cannot access them. *"OO certainly depends on the idea that programmers are well-behaved enough not to circumvent encapsulated data."* (Martin, ibid.) In practice this is not a crisis, but it is a useful reminder that encapsulation is partly a convention upheld by the type system and partly a discipline upheld by the team.

## 2. Inheritance

Inheritance allows a subclass to acquire the properties and behaviour of a superclass, establishing an *IS-A* relationship and enabling code reuse. A **Dog** IS-A **Animal**; it inherits the ability to breathe and can override how it makes a sound.

A critical Kotlin design decision: all classes and methods are **final by default**. To permit subclassing you must explicitly mark the class **open**, and to permit overriding a method you must mark that method **open** as well. This is the opposite of Java and is a deliberate nudge toward composition: inheritance is opt-in, not the path of least resistance.

*Inheritance — open class hierarchy with overrides*

```kotlin
open class Animal(val name: String) {
    // open -> subclasses are allowed to override this
    open fun sound(): String = "..."

    // final by default -> every Animal breathes the same way
    fun breathe() = println("$name is breathing")
}

class Dog(name: String) : Animal(name) {
    override fun sound() = "Woof"
}

class Cat(name: String) : Animal(name) {
    override fun sound() = "Meow"
}

val animals: List<Animal> = listOf(Dog("Rex"), Cat("Mia"))
animals.forEach { animal ->
    animal.breathe()                          // inherited unchanged
    println("${animal.name}: ${animal.sound()}")  // overridden per type
}
```

> **Key Insight:**
>
> Favour composition over inheritance. Inheritance couples the subclass tightly to the superclass: a change in the superclass can silently break every subclass (the 'fragile base class' problem). When the IS-A relationship is not truly natural, prefer interfaces plus delegation. Kotlin's **by** keyword makes delegation a first-class language feature.

*Composition via delegation — Kotlin's 'by' keyword*

```kotlin
interface Logger { fun log(msg: String) }

class ConsoleLogger : Logger {
    override fun log(msg: String) = println("[LOG] $msg")
}

// Repository gets Logger behaviour by DELEGATION, not inheritance.
// All Logger calls are forwarded to the injected instance automatically.
class UserRepository(logger: Logger) : Logger by logger {
    fun save(user: User) {
        log("Saving ${user.id}")  // delegated to ConsoleLogger
    }
}
```

Martin's observation in *Clean Architecture* (Ch. 5) is worth noting: inheritance is not entirely new to OO. *"Inheritance is simply the redeclaration of a group of variables and functions within a closed scope. But programmers were already able to do this manually in C long before OO languages existed."* (Martin, ibid.) What OO languages added was **compiler enforcement** — the is-a relationship, override validation, and virtual dispatch — turning what was a manual and fragile technique into a first-class, safe language feature. That enforcement is genuinely valuable; the insight is that the idea itself is not unique to OO.

## 3. Polymorphism

Polymorphism — from the Greek for 'many forms' — lets objects of different concrete types be treated through a common supertype. Code written against an interface or base class works correctly for any implementation, present or future, without modification. This is the single most important enabler of extensible software, and it is the mechanism behind the Open-Closed Principle we cover later.

There are two flavours. **Subtype (runtime) polymorphism** resolves which implementation to call based on the actual object at runtime. **Parametric polymorphism** (generics) lets a single piece of code operate over many types in a type-safe way.

*Subtype polymorphism — one contract, many shapes*

```kotlin
interface Shape {
    fun area(): Double
    fun perimeter(): Double
}

class Circle(val radius: Double) : Shape {
    override fun area() = Math.PI * radius * radius
    override fun perimeter() = 2 * Math.PI * radius
}

class Rectangle(val w: Double, val h: Double) : Shape {
    override fun area() = w * h
    override fun perimeter() = 2 * (w + h)
}

// This function never changes, even when you add a new Shape later.
fun describe(shape: Shape) {
    println("area=%.2f perimeter=%.2f".format(shape.area(), shape.perimeter()))
}

listOf(Circle(5.0), Rectangle(4.0, 6.0)).forEach(::describe)
```

Kotlin's **sealed** classes are a powerful, exhaustively-checked form of polymorphism. Because the compiler knows every possible subtype, a **when** expression over a sealed type requires no **else** branch — and if you add a new subtype, every **when** that doesn't handle it fails to compile. This is the idiomatic way to model UI state.

*Sealed classes — exhaustive polymorphism for UI state*

```kotlin
sealed interface UiState {
    data object Loading : UiState
    data class Success(val data: List<User>) : UiState
    data class Error(val message: String) : UiState
}

fun render(state: UiState) = when (state) {  // no 'else' needed
    is UiState.Loading -> showSpinner()
    is UiState.Success -> showList(state.data)   // smart-cast to Success
    is UiState.Error   -> showError(state.message)
}
```

### The architectural power: polymorphism enables dependency inversion

Polymorphic behaviour predates OO languages. In Unix's C-based I/O system, every device driver exposes five standard functions: `open`, `close`, `read`, `write`, and `seek`. The kernel calls these functions through what are effectively function-pointer tables — it does not know whether it is talking to a disk, a terminal, or a network socket; it just calls the same five functions. *"It is as though STDIN and STDOUT were Java-style interfaces, with implementations for each device."* (Martin, R.C. — Clean Architecture, Ch. 5 — Object-Oriented Programming) The polymorphic behaviour was there; what it lacked was safety and convenience — one wrong pointer assignment and the program crashed silently.

What OO languages gave us was polymorphism that is **safe and convenient**, without manually managing function-pointer tables. And from safe, convenient polymorphism follows a profound architectural consequence:

> *"Any source-code dependency, regardless of where it is, can be inverted."*
> *(Martin, R.C. — Clean Architecture, Ch. 5 — Object-Oriented Programming)*

Inserting an interface between a caller and a concrete class allows the source-code dependency to point in the *opposite direction* from the control flow at runtime:

```kotlin
// WITHOUT an interface — source-code dependency follows control flow
class OrderService {
    private val db = MySQLDatabase()   // depends on the concrete class
    fun placeOrder(order: Order) = db.save(order)
}

// WITH an interface — dependency is inverted
// The interface lives in the domain; the implementation lives in the data layer
interface OrderRepository { fun save(order: Order) }          // domain (stable)
class MySQLOrderRepository : OrderRepository { /* ... */ }    // data (detail)

// At runtime:  OrderService → calls → MySQLOrderRepository  (control flows forward)
// In source:   MySQLOrderRepository depends on OrderRepository  (dependency inverted)
class OrderService(private val repo: OrderRepository) {  // no knowledge of MySQL
    fun placeOrder(order: Order) = repo.save(order)
}
```

This is the mechanism behind Clean Architecture's dependency rule and the Dependency Inversion Principle. Because any dependency can be inverted, the architect is **not forced to align source-code dependencies with the flow of control**. It becomes possible to organise the system so that the UI and the database both depend on the business rules — not the reverse. The source code of the business rules never mentions the UI or the database.

Two capabilities follow directly (Martin, ibid.):

- **Independent deployment.** When the source code in one component changes, only that component needs to be redeployed. Changing the database implementation does not require rebuilding the business-rules module.
- **Independent development.** If modules can be deployed independently, they can be developed independently by separate teams. The domain team and the data team can work in parallel once the interface contract is agreed.

## 4. Abstraction

Abstraction hides complexity behind a simple, essential contract. Where encapsulation hides *data*, abstraction hides *implementation*. The caller depends on the *what* and is completely insulated from the *how*. In Kotlin we achieve abstraction through **interfaces** (pure contracts, no state) and **abstract classes** (partial contracts that may hold state and provide some implemented methods).

*Abstraction — interface as a contract the caller depends on*

```kotlin
// The contract -- says WHAT can be done, not HOW
interface UserRepository {
    suspend fun findById(id: String): User?
    suspend fun save(user: User)
    suspend fun delete(id: String)
}

// The ViewModel depends ONLY on the abstraction.
// It has no idea whether data comes from Room, Retrofit, or memory.
class UserViewModel(private val repo: UserRepository) : ViewModel() {
    fun load(id: String) {
        viewModelScope.launch {
            val user = repo.findById(id)
            _state.value = user?.let { UiState.Success(listOf(it)) }
                ?: UiState.Error("Not found")
        }
    }
}
```

Because the ViewModel depends on the abstraction, you can swap a real network repository for an in-memory fake in unit tests without touching a line of ViewModel code. This is the practical payoff of abstraction, and it leads directly into the Dependency Inversion Principle.

### The four pillars at a glance

| Pillar | Hides / Provides | Core Question | Kotlin Mechanism |
| --- | --- | --- | --- |
| Encapsulation | Hides internal data | Who can read or change this state? | private / internal / val, backing property |
| Inheritance | Reuses behaviour | Can this type reuse another's behaviour? | open class / override / by (delegation) |
| Polymorphism | Provides many forms | Can different types share one call site? | interface / sealed class / generics |
| Abstraction | Hides implementation | What is the contract, hiding the how? | interface / abstract class |

> **Key Insight:**
>
> Martin's conclusion in *Clean Architecture* (Ch. 5) reframes what OO actually is: *"OO is the ability to gain absolute control, through the use of polymorphism, over every source-code dependency in the system."* It allows architects to create a plug-in architecture with modules containing high-level policies that are independent of modules containing low-level details. Low-level details are relegated to plug-in modules that can be deployed and developed independently. Encapsulation and inheritance are supporting pillars; **polymorphism and the dependency inversion it enables is the core architectural gift of OO**.
> *(Martin, R.C. — Clean Architecture: A Craftsman's Guide to Software Structure and Design, Ch. 5 — Object-Oriented Programming)*

---

[↑ Chapter Index](../)
