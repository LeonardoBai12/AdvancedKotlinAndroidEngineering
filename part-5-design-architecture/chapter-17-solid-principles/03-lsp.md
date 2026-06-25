---
layout: default
title: Lsp
parent: SOLID Principles
nav_order: 3
---

Barbara Liskov stated the principle in 1988:

> *"What we want here is something like the following substitution property: if for each object o1 of type S there is an object o2 of type T such that for all programs P defined in terms of T, the behaviour of P is unchanged when o1 is substituted for o2, then S is a subtype of T."*
> *(Liskov, B., 1988, as cited in Martin, R.C. — Clean Architecture, Ch. 9 — The Liskov Substitution Principle)*

In plain terms: **if code works correctly with the base type, it must continue to work correctly when any subtype is substituted** — no special-casing, no `is`-checks on the concrete type.

### What compliance looks like

Martin's canonical example of a correct LSP design in *Clean Architecture* (Ch. 9): a `Billing` application depends on a `License` interface. `PersonalLicense` and `BusinessLicense` are two implementations, each using a different fee algorithm. The application's behaviour does not depend on which subtype it receives — both are fully substitutable for `License`. *"This design complies with the LSP because the behaviour of the Billing application does not depend, in any way, on the use of either subtype. Both subtypes are substitutable for the License type."* (Martin, ibid.)

```kotlin
interface License { fun calcFee(): Money }

class PersonalLicense(private val user: User) : License {
    override fun calcFee() = BASE_FEE * user.subscriptionMonths
}
class BusinessLicense(private val users: List<User>) : License {
    override fun calcFee() = BASE_FEE * users.size * SEAT_MULTIPLIER
}

// Billing depends only on License — never on PersonalLicense or BusinessLicense
class Billing(private val license: License) {
    fun invoice() = Invoice(license.calcFee())
}
```

The textbook violation is `Square` inheriting from `Rectangle`: setting width and height independently is part of `Rectangle`'s contract, but `Square` breaks it by coupling the two dimensions.

*Violation — Square breaks Rectangle's contract*

```kotlin
open class Rectangle(open var width: Double, open var height: Double) {
    open fun area() = width * height
}
class Square(side: Double) : Rectangle(side, side) {
    override var width: Double
        get() = super.width
        set(value) { super.width = value; super.height = value } // breaks the contract
}

fun testRectangle(rect: Rectangle) {
    rect.width = 5.0; rect.height = 10.0
    assert(rect.area() == 50.0)   // PASSES for Rectangle, FAILS for Square (gives 25)
}
```

*Fixed — separate abstractions, no false IS-A*

```kotlin
interface Shape { fun area(): Double }
class Rectangle(val width: Double, val height: Double) : Shape {
    override fun area() = width * height
}
class Square(val side: Double) : Shape {
    override fun area() = side * side
}
fun totalArea(shapes: List<Shape>) = shapes.sumOf { it.area() }  // works for all
```

### LSP at the architecture level

The principle extends well beyond class hierarchies. Over the years the LSP evolved into a broader principle of software design applicable to interfaces and implementations of any kind — a Kotlin interface, a REST API, a service endpoint. Any interface that makes a promise must be kept by all its implementations.

Martin's architectural violation example in *Clean Architecture* (Ch. 9): a taxi-aggregator system dispatches rides by constructing a URI from each driver's record. All companies use `/driver/{id}/pickupRoute`, except one whose URI uses a different format. The dispatcher must now special-case that company with an `if`; every new non-standard company adds another branch. The dispatcher must be modified for every new exception — the OCP is violated. *"When the behaviour of the User depends on the type being used, those types are not substitutable"* (Martin, ibid.), and the whole system becomes fragile.

> **Interview Tip:**
>
> Android example: a `UserDataSource` interface returning a `Flow<Resource<List<User>>>`. Whether the implementation is `RemoteUserDataSource` or `LocalUserDataSource`, the repository can swap one for the other without changing behaviour — because both honour the same contract, including how they signal errors (a `Resource.Error` emission, never a thrown exception that callers don't expect).

---

← [Previous: OCP](../02-ocp/) · [↑ Chapter Index](../) · [Next: ISP →](../04-isp/)
