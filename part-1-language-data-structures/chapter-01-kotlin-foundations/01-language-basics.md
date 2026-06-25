---
layout: default
title: "Chapter 1: Kotlin Foundations"
parent: "Chapter 1: Kotlin Foundations"
nav_order: 1
---

*Programming basics, the JVM, data types, variables, operators, and control flow*

Before the advanced material, this chapter establishes the vocabulary the rest of the guide assumes. Even experienced engineers benefit from a precise restatement of the fundamentals, and interviews frequently probe exactly these basics. We start from what programming and an algorithm actually are, explain how Kotlin reaches the machine, and then walk through types, variables, operators, and control flow.

## Programming and Algorithms

Programming, in computing, is an approach to solving problems that spans specification, design, validation, and the organisation of programs and data. Programming languages are the primary tools of that craft. In short: **to program is to develop solutions**.

At the centre of programming sits the **algorithm** — a finite sequence of instructions, carefully ordered to accomplish a specific task. Something as everyday as getting dressed is an algorithm: deciding whether you put on the shirt or the trousers first. Both orders work, which shows that algorithms can vary in their details. Making a sandwich is another: take two slices of bread, spread mayonnaise, add lettuce and tomato, place the filling, join the slices, cut in half. We detail every step, exactly as we do when programming — the computer understands no intuition; it needs precise instructions.

Programming is essentially translating the solution to a problem, much like learning a new language. Programming languages make this easier, letting us express our algorithms more comprehensibly. For the computer to understand the commands, we rely on intermediaries — **compilers** and **interpreters** — that act as translators, converting the programming language into machine language.

### Compilers vs Interpreters

A **compiler** converts a program written in a high- or low-level language (the source program) into an equivalent program in machine language (the object program). Once compiled, we run the program directly, with no additional program required. An **interpreter** works differently: it translates and executes the program step by step, without producing a new program — which means the interpreter must be installed on the machine where the program runs.

|   | Compiled languages | Interpreted languages |
| --- | --- | --- |
| How it runs | Translated once to machine code, then run | Translated and run line by line |
| Needs a runtime present? | No (after compilation) | Yes (the interpreter) |
| Examples | Java, Kotlin, C#, Swift, Rust | Python, PHP, Ruby, JavaScript |

The workflow when solving a challenge: create an algorithm, express it in a programming language, and let the compiler or interpreter turn it into an executable program. A good language, well applied, should make good solutions easy to write — solutions that are pleasant to read, easy to understand, and built with maintenance in mind, always thinking of the next person who will work on them.

## Kotlin: A Quick Overview

Kotlin is a modern language created by JetBrains in 2011, named after Kotlin Island near St. Petersburg, Russia. It was motivated by the desire to overcome some of Java's limitations and offer a safer, more efficient alternative for software development. Kotlin became the official language for Android in 2017.

### Compilation and execution

Kotlin source is compiled to bytecode (**.class**), just like Java, making it compatible with the JVM (Java Virtual Machine). That means Kotlin programs run on any JVM-capable environment. Kotlin can also compile to JavaScript (Kotlin/JS) for the web, and to native code through Kotlin/Native — the basis of Kotlin Multiplatform.

The **JVM** is a virtual machine that runs Java/Kotlin programs across different operating systems and hardware architectures, sitting as an intermediary layer between source and hardware and guaranteeing portability from desktops to servers to mobile devices. On Android, the role of the JVM is filled by **ART (Android Runtime)**, which executes the app's compiled bytecode on the device and lets a single project mix Java and Kotlin freely.

### What makes Kotlin distinctive

- **Type safety** — a strong type system that catches many errors at compile time.
- **Conciseness** — far less boilerplate than Java.
- **Interoperability** — seamless use of existing Java code, enabling gradual migration.
- **Null safety** — the type system distinguishes nullable from non-nullable, largely eliminating the dreaded NullPointerException.

## Data Types

Data types determine how information is represented and manipulated. Kotlin's basic types fall into three everyday groups.

### Numeric

| Type | Represents | Examples |
| --- | --- | --- |
| Int | Whole numbers, no fractional part | 42, -7, 0 |
| Long | Very large whole numbers (beyond Int) | 1234567890L |
| Double | Floating-point numbers | 3.14, -0.5, 2.0 |
| Float | Lower-precision floating point | 3.14f |

### Textual

**Char** represents a single character, like **'a'**, **'5'**, or **'&'**. **String** represents a sequence of characters, like **"Hello, world!"** or **"12345"**. The distinction matters: **'a'** is a Char (single quotes), while **"abc"** is a String (double quotes).

### Boolean

**Boolean** holds a logical value, **true** or **false**. Booleans are the foundation of decision-making, letting code choose between paths based on logical conditions.

---

[↑ Chapter Index](../) · [Next: Variables & Operators →](../02-variables-operators/)
