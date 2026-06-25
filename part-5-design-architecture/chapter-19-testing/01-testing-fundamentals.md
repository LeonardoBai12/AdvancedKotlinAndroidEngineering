---
layout: default
title: "Chapter 19: Testing"
parent: "Chapter 19: Testing"
nav_order: 1
---

*The testing pyramid, FIRST, unit/integration/instrumented tests, and end-to-end with Maestro*

A well-architected app is a testable app — every boundary we drew in the previous chapters (use cases, repository interfaces, the State Holder pattern, dependency injection) exists partly so that pieces can be verified in isolation. This chapter covers what to test, how to test each layer, and the principles that separate a useful test suite from a brittle one. It is also a frequent interview topic: being able to explain the testing pyramid and the FIRST principles, and to write a clean ViewModel test, signals senior maturity.

## Why Test, and the Testing Pyramid

Tests exist to let you change code with confidence. Without them, every refactor is a gamble; with them, the suite tells you immediately when a change breaks behaviour. But not all tests are equal in cost or speed, which is captured by the **testing pyramid**: many fast, cheap tests at the bottom, few slow, expensive ones at the top.

| Level | What it tests | Speed / cost | Proportion |
| --- | --- | --- | --- |
| Unit | One class/function in isolation | Milliseconds, JVM-only | Most (the base) |
| Integration | Several units working together | Slower, may touch a DB | Some (the middle) |
| End-to-end (UI) | Whole flows as a user, on a device | Slowest, most fragile | Few (the tip) |

The shape matters: unit tests are fast and stable, so they form the broad base and catch most logic errors in milliseconds. End-to-end tests are invaluable but slow and prone to flakiness, so you keep them few and reserve them for critical user journeys. An inverted pyramid — mostly slow UI tests — produces a suite that is slow to run and painful to maintain.

> **Key Insight:**
>
> On Android the split is physical. Tests in the **test/** source set run on your machine's JVM with no device — use it for ViewModels, use cases, and business logic. Tests in the **androidTest/** source set are instrumented: they run on a device or emulator with the full Android framework — use it for UI tests. Keeping logic in the JVM-testable set (which clean architecture naturally encourages) is what keeps the pyramid's base fast.

## FIRST — Principles of a Good Test

The Pragmatic Programmer (and Clean Code) summarise what makes a unit test trustworthy with the acronym **FIRST**. A test that violates these is often worse than no test, because it erodes confidence in the whole suite.

| Letter | Principle | Meaning |
| --- | --- | --- |
| F | Fast | Runs in milliseconds, so the suite runs constantly |
| I | Independent | No test depends on another or on shared mutable state or ordering |
| R | Repeatable | Same result every run, on any machine — no reliance on network, clock, or device |
| S | Self-validating | Passes or fails with a clear assertion — no manual log inspection |
| T | Timely | Written with (or before) the code, not bolted on months later |

> **Interview Tip:**
>
> The most common violations in Android: a test that hits a real network (not Repeatable, not Fast), tests that must run in a specific order because they share state (not Independent), and 'tests' that print to logcat for a human to eyeball (not Self-validating). Designing for testability — injecting dependencies so they can be faked — is what makes FIRST achievable.

## Unit Tests

A unit test verifies one unit — a use case, a ViewModel, a mapper — in isolation, replacing its collaborators with test doubles. It lives in **test/**, runs on the JVM, and uses JUnit plus an assertion library. (These examples use JUnit 5, hence **@BeforeEach**/**@AfterEach**; JUnit 4's equivalents are **@Before**/**@After**.) The conventional structure is **given / when / then** (also called arrange / act / assert): set up the inputs, perform the action, assert the outcome — and marking those three phases with comments keeps tests readable.

*A use-case unit test (Given / When / Then)*

```kotlin
class GetUsersUseCaseTest {
    private lateinit var repository: UserRepository
    private lateinit var useCase: GetUsersUseCase

    @BeforeEach
    fun setUp() {
        repository = mockk()              // MockK: a configurable test double
        useCase = GetUsersUseCase(repository)
    }

    @AfterEach
    fun tearDown() {
        unmockkAll()                      // reset MockK between tests (Independent)
    }

    @Test
    fun `When get users, expect a list of users`() = runTest {
        // Given -- the repository returns two users
        val users = listOf(
            User(id = "1", name = "Ana"),
            User(id = "2", name = "Bruno")
        )
        coEvery { repository.getUsers() } returns users

        // When -- the use case is collected (it emits a Flow<Resource>)
        val states = mutableListOf<Resource<List<User>>>()
        val result = useCase().toCollection(states)

        // Then -- it emits Loading first, then Success with the data
        assert(states.first() is Resource.Loading)
        assert(result.last() is Resource.Success)
        assertEquals(users, result.last().data)
    }

    @Test
    fun `When get users fails, expect an error`() = runTest {
        // Given -- the repository throws
        coEvery { repository.getUsers() } throws Exception("Error")

        // When
        val states = mutableListOf<Resource<List<User>>>()
        val result = useCase().toCollection(states)

        // Then -- Loading first, then Error carrying the message
        assert(states.first() is Resource.Loading)
        assert(result.last() is Resource.Error)
        assertEquals("Error", result.last().message)
    }
}
```

### Fakes vs mocks

Both are **test doubles** — stand-ins for real collaborators — and both are widely used; the choice is about what you are testing. A **mock** (here via the **MockK** library) is a generated object configured per test: **coEvery { ... } returns ...** stubs a suspending call, and **coVerify { ... }** asserts a call happened. It is concise and excels when you need to verify *interactions* or stub awkward types. A **fake** is a real, simplified implementation of an interface (an in-memory repository backed by a map); it is reusable across tests and survives refactors because it tests *behaviour* rather than calls. Many codebases use both: mocks for quick stubbing and interaction checks, fakes for collaborators exercised by many tests.

*The same dependency, mocked and faked*

```kotlin
// MOCK (MockK) -- configured per test; great for stubbing and verifying calls
val repository: UserRepository = mockk()
coEvery { repository.getUsers() } returns users        // stub a return
coEvery { repository.insertUser(user) } returns Unit
// ... exercise code ...
coVerify { repository.insertUser(user) }               // verify it was called

// FAKE -- a real, simple implementation; reusable and refactor-proof
class FakeUserRepository : UserRepository {
    private val stored = mutableListOf<User>()
    override suspend fun getUsers(): List<User> = stored
    override suspend fun insertUser(user: User) {
        stored += user
    }
}
```

> **Warning:**
>
> Whichever you choose, assert observable outcomes over call patterns where you can. A test dominated by **verify** on every internal call asserts *how* the code works and breaks on harmless refactors; a test that checks the emitted **Resource** or returned value asserts *what* it produces and survives them. Use **coVerify** deliberately — for genuine side effects like 'the score was persisted' — not as the default assertion.

### Testing coroutines and Flow

Asynchronous code needs deterministic control over time. **runTest** runs the body in a test scope with a virtual clock — delays are skipped and the scheduler is controllable — so suspending code completes instantly and predictably (satisfying Fast and Repeatable). For code that dispatches to the main thread (a ViewModel), set a test dispatcher as Main in setup with **Dispatchers.setMain(StandardTestDispatcher())** and reset it afterwards; **advanceUntilIdle()** then runs all pending coroutines to completion. For asserting the values a **StateFlow** emits over time, the **Turbine** library exposes them one at a time via **state.test { awaitItem() }**, far cleaner than collecting into a list by hand.

*Testing a ViewModel's StateFlow -- setMain + Turbine + MockK*

```kotlin
class ItemListViewModelTest {
    private lateinit var getItems: GetItemsUseCase
    private lateinit var viewModel: ItemListViewModel

    @BeforeEach
    fun setUp() {
        Dispatchers.setMain(StandardTestDispatcher())   // control Main in tests
        getItems = mockk()
    }

    @AfterEach
    fun tearDown() {
        Dispatchers.resetMain()
        unmockkAll()
    }

    @Test
    fun `When created, expect items to be fetched`() = runTest {
        // Given -- the use case emits Loading then Success, plus a SavedStateHandle
        val items = listOf(Item("1", "First"), Item("2", "Second"))
        every { getItems("food") } returns flowOf(Resource.Loading, Resource.Success(items))
        val savedStateHandle = mockk<SavedStateHandle>()
        every { savedStateHandle["category"] ?: "" } returns "food"

        // When -- the ViewModel is constructed (it loads on init)
        viewModel = ItemListViewModel(getItems, savedStateHandle)
        assert(viewModel.state.value.isLoading)          // loading immediately
        advanceUntilIdle()                               // run pending coroutines

        // Then -- state settles to the loaded items, no error
        viewModel.state.test {
            val emission = awaitItem()
            assert(emission.isLoading.not())
            assertEquals(items, emission.items)
            assertNull(emission.message)
        }
    }
}
```

> **Interview Tip:**
>
> Inject the dispatcher (or set Main as above) rather than hard-coding **Dispatchers.Main** or **IO** inside the ViewModel. A ViewModel that creates its own dispatchers cannot be tested deterministically; one whose Main is replaced by a **StandardTestDispatcher** can be driven with **advanceUntilIdle()**. This is the Dependency Inversion Principle applied to time itself. Note too how the mocked **SavedStateHandle** feeds the screen's argument — the same rotation-surviving state from the Lifecycle chapter, here supplied by the test.

---

[↑ Chapter Index](../) · [Next: Testing Strategies →](../02-testing-strategies/)
