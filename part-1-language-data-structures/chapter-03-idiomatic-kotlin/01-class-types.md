---
layout: page
title: "Chapter 3: Idiomatic Kotlin"
---

*The language features that set Kotlin apart — and when to reach for each*

Kotlin's real value is not just being 'Java with less boilerplate' — it is a set of features that change how you model problems. This chapter surveys the constructs that distinguish idiomatic Kotlin from merely correct Kotlin. For each, we give a concrete example and, more importantly, the *why*: when and why you would reach for it. Several of these (inline functions, value classes) have compile-time and performance implications that are easy to use without understanding — we make those explicit.

## data class

A **data class** auto-generates **equals()**, **hashCode()**, **toString()**, **copy()**, and **componentN()** functions from its constructor properties.

**Why use it:** for any class whose purpose is to hold data — models, DTOs, UI state, API responses. It removes dozens of lines of error-prone boilerplate and gives you correct value semantics for free (two instances with equal contents are equal).

*data class*

```kotlin
data class User(val id: String, val name: String, val age: Int)

val a = User("1", "Leo", 30)
val b = User("1", "Leo", 30)
println(a == b)           // true  -- structural equality, not reference
println(a)                // User(id=1, name=Leo, age=30) -- readable toString

// copy() -- create a modified clone without mutating the original
val older = a.copy(age = 31)
```

### componentN() and destructuring

For each property in the primary constructor, a data class generates a numbered **component** function: **component1()** returns the first property, **component2()** the second, and so on. You rarely call these by name — their purpose is to power **destructuring declarations**, where Kotlin calls them positionally behind the scenes to unpack an object into several variables in one line. The order follows the constructor, not the variable names you choose, so the assignment is by position.

*componentN powers destructuring*

```kotlin
data class User(val id: String, val name: String, val age: Int)
val user = User("1", "Leo", 30)

// These two lines are equivalent -- destructuring calls componentN():
val (id, name, age) = user
// val id = user.component1(); val name = user.component2(); ...

// Matched BY POSITION, not by name -- this compiles but mislabels:
val (theId, theAge, theName) = user   // theAge actually holds the name!

// Skip ones you don't need with an underscore:
val (_, justName) = user              // takes component2() only
```

> **Interview Tip:**
>
> Keep data class properties as **val** and treat instances as immutable values; use **copy()** to derive new states. A data class with **var** properties undermines the value semantics and can break its use as a HashMap key (its hashCode would change after insertion).

## sealed class / sealed interface

A **sealed** type has a fixed, compiler-known set of direct subtypes, all declared in the same module/package.

**Why use it:** to model a closed set of possibilities — the states a screen can be in, the variants of a result — so that a **when** over it is *exhaustive* and needs no **else**. Add a new subtype and every non-exhaustive **when** fails to compile, turning a whole class of runtime bugs into compile errors.

*sealed for exhaustive state modelling*

```kotlin
sealed interface UiState {
    data object Loading : UiState
    data class Success(val users: List<User>) : UiState
    data class Error(val message: String) : UiState
}

fun render(state: UiState) = when (state) {   // no 'else' needed
    UiState.Loading    -> showSpinner()
    is UiState.Success -> showList(state.users) // smart-cast
    is UiState.Error   -> showError(state.message)
}
```

### A concrete payoff: a typed network result

Consider a repository call that can succeed, fail with a typed error, or report no connectivity. Modelling the outcome as a sealed type forces every caller to handle each case explicitly — and the day you add a new outcome (say, **Unauthorized**), the compiler points you at every **when** that has not yet handled it. Compare this with returning a nullable value or throwing exceptions, where a forgotten case simply slips through to a runtime crash.

*A sealed Result the caller cannot mishandle*

```kotlin
sealed interface NetworkResult<out T> {
    data class Success<T>(val data: T) : NetworkResult<T>
    data class Failure(val code: Int, val message: String) : NetworkResult<Nothing>
    data object NoConnection : NetworkResult<Nothing>
}

fun handleUsers(result: NetworkResult<List<User>>) = when (result) {
    is NetworkResult.Success    -> showList(result.data)      // smart-cast to Success
    is NetworkResult.Failure    -> showError(result.message)  // smart-cast to Failure
    NetworkResult.NoConnection  -> showOfflineBanner()
    // Add a new subtype later and this 'when' stops compiling
    // until you handle it -- the bug is caught at build time.
}
```

### Class vs interface — which to pick

- **sealed interface**: preferred default. A subtype can implement multiple interfaces, so it is more flexible; use it unless you need shared state or constructor logic.
- **sealed class**: use when the variants share state or behaviour you want to declare once (stored properties, an abstract method with a common helper). A class allows only single inheritance.

## enum class

An **enum class** is a fixed set of named constant instances, optionally carrying data and methods.

**Why use it** instead of sealed: when the set is a flat list of singletons with uniform shape (days of the week, HTTP methods, sort orders). Reach for **sealed** instead when the variants need to carry *different* data — enums all share one shape, sealed subtypes do not.

*enum class with data and behaviour*

```kotlin
enum class Priority(val weight: Int) {
    LOW(1), MEDIUM(5), HIGH(10);
    fun isUrgent() = weight >= 10
}

Priority.HIGH.weight     // 10
Priority.HIGH.isUrgent() // true
Priority.values()        // all constants, useful for dropdowns
```

## object & companion object

**object** declares a singleton — a class with exactly one instance, created lazily and thread-safely on first use.

**Why use it:** for stateless utilities, coordinators, or a single shared registry. A **companion object** is a singleton tied to a class, holding what other languages call static members — factory functions and constants associated with the type.

*object and companion object*

```kotlin
object Analytics {                 // singleton
    fun track(event: String) { /* ... */ }
}
Analytics.track("screen_view")

class User private constructor(val id: String) {
    companion object {             // 'static' members of User
        const val TABLE = "users"
        fun create(id: String) = User(id)   // factory function
    }
}
User.create("42")                  // called on the type, not an instance
```

## typealias

**typealias** gives an existing type a new name.

**Why use it:** readability — it tames verbose generic or function types and documents intent. It is purely a compile-time alias: it creates no new type and has **zero runtime cost**, so it provides no type safety (the alias and the original are interchangeable). For real type safety, use a value class instead.

*typealias for readability*

```kotlin
typealias UserId = String
typealias ClickHandler = (View) -> Unit
typealias Cache = HashMap<String, List<User>>

fun register(id: UserId, onClick: ClickHandler) { /* ... */ }
// At runtime UserId IS String -- no new type, no checking, no cost.
```

## nested class vs inner class

By default, a class declared inside another is a **nested** class: it does *not* hold a reference to an instance of the outer class — it is just namespaced. Marking it **inner** gives it an implicit reference to the outer instance, so it can access the outer's members.

**Why this matters:** that hidden reference is a classic memory-leak source on Android — an **inner** class (or a non-static handler/callback) can keep an Activity alive. Prefer **nested** (the default) unless you genuinely need the outer instance.

*nested (default) vs inner*

```kotlin
class Outer(val value: Int) {
    class Nested {              // no reference to Outer
        fun show() = "nested"    // cannot see Outer.value
    }
    inner class Inner {         // holds a reference to Outer
        fun show() = "value is $value"  // CAN see Outer.value
    }
}
Outer.Nested().show()           // no Outer instance needed
Outer(10).Inner().show()        // needs an Outer instance
```

---

[↑ Chapter Index](../) · [Next: Functions & Extensions →](../02-functions-extensions/)
