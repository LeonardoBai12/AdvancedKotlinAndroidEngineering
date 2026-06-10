---
layout: page
title: "Chapter 1: Kotlin Foundations — Variables & Operators"
---

## Variables

Variables store and manipulate data flexibly — think of them as labelled drawers in the computer's memory. They are readable names associated with a memory location, making code more comprehensible. Kotlin offers three forms.

### var — reassignable

A variable declared with **var** can be reassigned after its initial declaration.

*var*

```kotlin
fun main() {
    var name = "My Name"               // type inferred as String
    var lastName: String = "My Surname" // type stated explicitly
    var height: Int? = null             // nullable Int

    name = "Another name"               // OK -- var can be reassigned
    height = 170
    height = null
}
```

### val — read-only

A variable declared with **val** is immutable after its initial assignment — its value cannot be changed. Prefer **val** by default and reach for **var** only when reassignment is genuinely needed; this makes code easier to reason about.

*val*

```kotlin
fun main() {
    val name = "My Name"
    val lastName: String = "My Surname"

    name = "Another name"        // ERROR -- cannot reassign a val
    lastName = "Another Surname" // ERROR -- cannot reassign a val
}
```

### lateinit var — deferred initialization

**lateinit var** lets you postpone initialising a non-null variable until it is actually needed. Informally, you 'promise' the compiler the variable will be assigned at some point before it is read. Useful for dependency injection and test setup; accessing it before assignment throws an UninitializedPropertyAccessException.

*lateinit var*

```kotlin
fun main() {
    lateinit var name: String
    lateinit var lastName: String

    name = "Another name"
    lastName = "Another Surname"
}
```

## Operators

### Assignment and arithmetic

The assignment operator **=** writes a value into a variable. The arithmetic operators **+**, **-**, `*`, **/**, and **%** (modulo / remainder) perform calculations. Standard mathematical precedence applies — multiplication and division before addition and subtraction — and parentheses override it, so **(a * b) + c** equals **a * b + c**.

### Augmented assignment

These combine an assignment with an arithmetic operation in one step. Each is shorthand for the expanded form.

| Operator | Meaning | Equivalent to |
| --- | --- | --- |
| `a += b` | Add and assign | `a = a + b` |
| `a -= b` | Subtract and assign | `a = a - b` |
| `a *= b` | Multiply and assign | `a = a * b` |
| `a /= b` | Divide and assign | `a = a / b` |
| `a %= b` | Modulo and assign | `a = a % b` |
| `a++` | Increment | `a = a + 1` |
| `a--` | Decrement | `a = a - 1` |

### Relational

Relational operators compare values and appear in conditions, evaluating to true or false: **<** (less than), **<=** (less or equal), **>** (greater than), **>=** (greater or equal), **!=** (not equal), **==** (equal), and **in** (contained in).

### Logical

Logical operators act on boolean expressions and return a boolean. **NOT** (**!** or **.not()**) inverts a value. **AND** (**&&**) is true only if both sides are true. **OR** (**||**) is true if at least one side is true. Both **&&** and **||** short-circuit — they stop evaluating as soon as the result is determined.

*Logical operators*

```kotlin
val condition = true

val lie   = !condition          // false
val lie2  = condition.not()     // false (method form)
val truth = !condition.not()    // true

val a = true && false           // false -- AND needs both true
val b = true || false           // true  -- OR needs at least one
```

---

← [Previous: Language Basics](../01-language-basics/) · [↑ Chapter Index](../) · [Next: Control Flow & Style →](../03-control-flow-style/)
