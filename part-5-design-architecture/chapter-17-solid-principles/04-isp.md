---
layout: page
title: "I — Interface Segregation Principle"
---

'Clients should not be forced to depend on interfaces they do not use.' Split large 'fat' interfaces into smaller, focused ones so an implementer only takes on what it actually needs. A fat interface forces classes to implement methods that make no sense for them — a `Robot` worker forced to implement `eat()` and `sleep()` ends up throwing `UnsupportedOperationException`.

*Fixed — focused, segregated interfaces*

```kotlin
interface Workable  { fun work() }
interface Eatable   { fun eat() }
interface Sleepable { fun sleep() }

// Robot implements only what applies
class RobotWorker : Workable {
    override fun work() = println("Working 24/7")
}
// Human implements the ones that apply
class HumanWorker : Workable, Eatable, Sleepable {
    override fun work()  { /* ... */ }
    override fun eat()   { /* ... */ }
    override fun sleep() { /* ... */ }
}
```

*Android — segregated repositories*

```kotlin
interface AuthRepository {
    suspend fun login(email: String, password: String)
    suspend fun logout()
}
interface ProfileRepository {
    suspend fun getProfile(): UserProfile
    suspend fun updateProfile(profile: UserProfile)
}

// Each ViewModel depends only on the interface it needs
class LoginViewModel(private val authRepo: AuthRepository) : ViewModel()
class ProfileViewModel(private val profileRepo: ProfileRepository) : ViewModel()
```

### ISP at the architecture level

Martin's deeper concern in *Clean Architecture* (Ch. 10) is **architectural**: *"in general, it is harmful to depend on modules that contain more elements than you need."* The harm shows up not just in unused method implementations but in transitive recompilation and redeployment.

Consider: System S integrates Framework F, which was compiled with Database D as a transitive dependency. If D contains features that neither F nor S needs, a change to those unused features in D can still force recompilation and redeployment of F — and by transitivity, of S. A failure in an unused part of D can cascade up to S. *"Learn this lesson: depending on something that contains unnecessary items can cause unexpected problems."* (Martin, R.C. — Clean Architecture, Ch. 10 — The Interface Segregation Principle)

This architectural reading of ISP is why the CRP (Common Reuse Principle, in the Gradle/Multi-Module chapter) uses almost the same language: *"don't force users of a component to depend on things they don't need."* ISP and CRP are the same idea stated at different scales — class-level vs. module/component-level.

---

← [Previous: LSP](../03-lsp/) · [↑ Chapter Index](../) · [Next: DIP →](../05-dip/)
