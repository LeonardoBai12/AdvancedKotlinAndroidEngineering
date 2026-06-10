# Chapter 1: Kotlin Foundations — Control Flow & Style

## Conditional Control Flow

### if / else / else if

**if** evaluates a boolean expression and runs a block when it is true; **else** runs when it is false; **else if** chains additional conditions. In Kotlin, **if** is also an *expression* — it returns a value — which is why Kotlin has no ternary operator: you simply assign the result of an if/else.

*if as a statement and as an expression*

```kotlin
// As a statement
if (score >= 90) {
    grade = "A"
} else if (score >= 80) {
    grade = "B"
} else {
    grade = "C"
}

// As an expression (replaces the ternary operator)
val grade = if (score >= 90) "A" else if (score >= 80) "B" else "C"
```

### when

When the decision depends on a single value, **when** is cleaner than a long else-if chain. It matches a value against several branches — single values, multiple values, or ranges — and, like if, it is an expression that can return a value.

*when*

```kotlin
when (numeric) {
    0       -> println("zero")
    11      -> println("eleven")
    1, 2, 10 -> println("one, two, or ten")  // multiple values
    in 5..9 -> println("between five and nine") // a range
    else    -> println("something else")
}

// As an expression
val label = when (numeric) {
    0 -> "zero"
    in 1..9 -> "single digit"
    else -> "large"
}
```

## Iterative Control Flow

### while

A **while** loop repeats its block *while* a condition stays true. The classic bug is the infinite loop: if nothing inside the loop changes the condition, it never ends. The fix is to update the control variable so the condition eventually becomes false. Note that if the condition is already false on entry, the block never runs.

*while -- the infinite-loop trap and its fix*

```kotlin
// INFINITE LOOP -- the variable never changes
val goals = 0
while (goals < 8) {
    println("$goals goals")   // runs forever
}

// FIXED -- increment the control variable
var goals = 0
while (goals < 8) {
    println("$goals goals")
    goals++                    // condition eventually becomes false
}
```

### do / while

When you need the block to run *at least once* regardless of the condition, use **do/while**: the **do** block executes first, and only then is the **while** condition checked to decide whether to repeat. So even if the condition is false from the start, the action runs once.

*do / while -- runs at least once*

```kotlin
var goals = 10
do {
    println("$goals goals")   // printed once, even though 10 < 8 is false
    goals++
} while (goals < 8)
```

### for

Kotlin's **for** iterates over anything that provides an iterator — ranges, arrays, collections. It is the idiomatic counted loop.

*for over ranges and collections*

```kotlin
for (i in 1..5) println(i)          // 1 2 3 4 5 (inclusive)
for (i in 1 until 5) println(i)     // 1 2 3 4   (excludes 5)
for (i in 5 downTo 1) println(i)    // 5 4 3 2 1
for (i in 0..10 step 2) println(i)  // 0 2 4 6 8 10

for (item in list) println(item)            // each element
for ((index, item) in list.withIndex())     // index + element
    println("$index: $item")
```

## Comments

Comments document intent and aid collaboration, but they are easy to overuse. Kotlin has three forms. **Single-line** comments start with **//** and run to the end of the line. **Multi-line** (block) comments are wrapped in **/* */** and, unlike in Java, can be nested. **KDoc** documentation comments use **/** */** above a declaration and are processed by documentation tools; they support tags such as **@param**, **@return**, and **@throws**, and you can reference other symbols with square brackets.

*The three comment forms*

```kotlin
// Single-line: a quick note to the end of the line

/*
   Multi-line block comment.
   /* Kotlin even allows nesting these. */
*/

/**
 * KDoc: filters tasks by their title and description.
 *
 * @param query the text to search for (case-insensitive)
 * @return the tasks whose title or description contains [query]
 */
fun List<Task>.filterBy(query: String) = filter {
    // why lowercase: makes the search case-insensitive
    query.lowercase() in it.title.lowercase() ||
    query.lowercase() in (it.description?.lowercase() ?: "")
}
```

### Comment the why, not the what

The single most useful guideline about comments: a function should be self-explanatory about *what* it does — through good naming and small, focused logic — so that a comment is rarely needed to restate it. A comment earns its place when it explains *why* the code does something a particular way: a non-obvious business rule, a workaround for a platform bug, a deliberate performance trade-off, a reference to a ticket or specification. A comment that merely narrates the code (**// increment i** above **i++**) adds noise and, worse, drifts out of date as the code changes — a misleading comment is more harmful than none.

*A comment that restates the code vs one that explains why*

```kotlin
// BAD -- the comment just repeats what the code already says
// add 1 to the counter
counter++

// GOOD -- the comment explains a non-obvious reason
// The vendor API rejects more than 50 ids per call (see TICKET-1234),
// so we chunk the request to stay under that limit.
ids.chunked(50).forEach { batch -> api.fetch(batch) }
```

A practical corollary: excessive commenting often signals uncertainty about the logic itself. If you feel a block needs a paragraph of explanation, that is frequently a hint to extract it into a well-named function whose name carries the explanation. Prefer self-documenting code, and reserve comments for the genuine *why*.

## Indentation

Indentation is the practice of adding leading whitespace so that the visual structure of the code mirrors its logical structure: the body of a function is indented inside the function, the body of a loop inside the loop, and so on. It is not cosmetic — consistent indentation is one of the strongest signals a reader uses to understand nesting and scope at a glance. The Kotlin convention is four spaces per level. Most teams enforce it automatically with a formatter (ktlint or the IDE's reformat action) so it never becomes a matter of debate or a source of noisy diffs.

*The same code without and with indentation*

```kotlin
// WITHOUT indentation -- structure is invisible, hard to read
class UpdateTaskUseCase(private val repository: TaskRepository) {
suspend operator fun invoke(task: Task, title: String) {
if (title.isBlank()) throw IllegalArgumentException("Title required")
repository.insert(task.copy(title = title)) } }

// WITH indentation -- nesting and scope are immediately clear
class UpdateTaskUseCase(
    private val repository: TaskRepository
) {
    suspend operator fun invoke(task: Task, title: String) {
        if (title.isBlank())
            throw IllegalArgumentException("Title required")
        repository.insert(
            task.copy(title = title)
        )
    }
}
```

> **Interview Tip:**
>
> Indentation conveys hierarchy; it does not enforce it. In Kotlin, blocks are delimited by braces **{ }**, not by whitespace (unlike Python). Misleading indentation that disagrees with the braces compiles fine but deceives the reader — which is exactly why an automatic formatter, keeping the visual structure honest, is worth adopting from day one.

---

← [Previous: Variables & Operators](./02-variables-operators.md) · [↑ Chapter Index](./README.md)
