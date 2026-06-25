---
layout: default
title: "O — Open-Closed Principle"
parent: "Chapter 17: SOLID Principles"
nav_order: 2
---

The OCP was coined in 1988 by Bertrand Meyer. Martin's formulation:

> *"A software artifact should be open for extension but closed for modification."*
> *(Martin, R.C. — Clean Architecture, Ch. 8 — The Open-Closed Principle)*

The behaviour of an artifact should be extensible without modifying that artifact. This is, according to Martin, the primary reason to study software architecture at all: when simple extensions to requirements force massive rewrites, the architects of that system are in the middle of a spectacular failure. His architectural statement of the goal: *"Uma boa arquitetura de software deve reduzir a quantidade de código a ser mudado para o mínimo possível. Zero seria o ideal."*

At the component level the OCP creates a **protection hierarchy**: high-level components are shielded from changes in low-level components. The mechanism is source-code dependency direction — arrows point *toward* whatever we want to protect. The component containing the highest-level policy should never know about, or depend on, any component containing lower-level details. Components at a higher level in the hierarchy are protected from changes in the components at a lower level. The principle that governs *how* to direct those arrows is the Dependency Inversion Principle.

The classic symptom of an OCP violation is a growing `when`/`switch` over a type tag that you must edit every time a new variant appears.

*Violation — must edit the class for every new type*

```kotlin
// BAD: adding PayPal means modifying this class
class PaymentProcessor {
    fun process(amount: Double, type: String) = when (type) {
        "CREDIT_CARD" -> processCreditCard(amount)
        "PIX"         -> processPix(amount)
        // Need PayPal? MODIFY THIS CLASS!
        else -> throw Exception("Unknown type")
    }
}
```

*Fixed — Strategy pattern + Kotlin extension functions*

```kotlin
interface PaymentMethod { fun process(amount: Double): PaymentResult }

class CreditCardPayment : PaymentMethod {
    override fun process(amount: Double) = PaymentResult.Success
}
class PixPayment : PaymentMethod {
    override fun process(amount: Double) = PaymentResult.Success
}
// New method added -- zero changes to existing code
class PayPalPayment : PaymentMethod {
    override fun process(amount: Double) = PaymentResult.Success
}

// The processor is closed: it never changes
class PaymentProcessor(private val method: PaymentMethod) {
    fun process(amount: Double) = method.process(amount)
}

// Kotlin extension functions are a natural OCP tool:
data class Product(val name: String, val price: Double)          // CLOSED
fun Product.discountedPrice(pct: Double) = price * (1 - pct / 100) // OPEN
```

---

← [Previous: SRP](../01-srp/) · [↑ Chapter Index](../) · [Next: LSP →](../03-lsp/)
