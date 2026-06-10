---
layout: page
title: "Chapter 19: Testing — Testing Strategies"
---

## Integration Tests

An integration test verifies that several units work correctly *together*, rather than in isolation — a repository implementation against its data source, or a repository plus its mapper against a fake API. The point is to catch the bugs that live in the seams between units, which pure unit tests miss because they stub those seams out. A repository test that exercises the real mapping and delegation, with only the lowest-level data source mocked, is a common and valuable example.

*A repository integration test*

```kotlin
class UserRepositoryImplTest {
    private lateinit var dataSource: UserDataSource
    private lateinit var context: Context
    private lateinit var repository: UserRepositoryImpl

    @BeforeEach
    fun setUp() {
        dataSource = mockk(relaxed = true)   // relaxed: unstubbed calls return defaults
        context = mockk(relaxed = true)
        repository = UserRepositoryImpl(context, dataSource)
    }

    @AfterEach
    fun tearDown() = unmockkAll()

    @Test
    fun `When get users, expect a user list`() = runTest {
        // Given -- the data source returns two users
        val users = listOf(
            User(id = "1", name = "Ana"),
            User(id = "2", name = "Bruno")
        )
        coEvery { dataSource.getUsers() } returns users

        // When -- the repository delegates and maps
        val result = repository.getUsers()

        // Then -- the seam between repository and data source works
        assertEquals(2, result.size)
        assertEquals(users, result)
    }

    @Test
    fun `When insert user, expect user to be inserted`() = runTest {
        // Given
        val user = User(id = "1", name = "Ana")
        coEvery { dataSource.insertUser(user) } returns Unit

        // When
        repository.insertUser(user)

        // Then -- verify the side effect reached the data source
        coVerify { dataSource.insertUser(user) }
    }
}
```

> **Interview Tip:**
>
> For tests that exercise a real local database rather than a mocked data source, **Room.inMemoryDatabaseBuilder(...)** gives a real Room instance that lives only for the test — real DAO queries, discarded afterwards. Those run as instrumented tests (next section) because Room needs the Android runtime.

## Instrumented & UI Tests

Instrumented tests run on a device or emulator (in **androidTest/**) with the full Android framework available. UI tests are the main use: they drive the interface and assert what the user would see. The crucial modern point is *which* tool to use, because it depends on how the UI is built.

### Espresso (Views) vs Compose UI Test

**Espresso** is Google's UI-testing framework for the classic **View/XML** system. It is fast and reliable, but it is built around the View hierarchy. For **Jetpack Compose** there is a dedicated library — **androidx.compose.ui:ui-test-junit4** — designed for Compose's declarative model. Espresso does not natively understand composables: it targets the View tree, and a Compose screen is a single View hosting a composition. While an interop bridge exists, the idiomatic choice for a Compose UI is the Compose test library, which works through **semantics** — the same accessibility tree screen readers use — rather than View matchers.

|   | Espresso | Compose UI Test |
| --- | --- | --- |
| Targets | View / XML hierarchy | Composable semantics tree |
| Dependency | espresso-core | ui-test-junit4 |
| Finds elements by | View id, text matchers | Semantics: text, contentDescription, testTag |
| Use for | Legacy View-based screens | Jetpack Compose screens |

A Compose UI test uses a **composeTestRule** to set the content (or launch the Activity), then finds nodes by their semantics and performs actions or assertions on them. Because it keys off semantics, writing testable Compose also improves accessibility — a **testTag** or a meaningful **contentDescription** serves both.

*A Compose UI test with composeTestRule*

```kotlin
class SearchScreenTest {
    @get:Rule val composeTestRule = createComposeRule()

    @Test
    fun `tapping search emits the search event`() {
        var lastEvent: SearchEvent? = null
        composeTestRule.setContent {
            SearchScreen(
                state = SearchState(query = "kotlin"),
                onEvent = { lastEvent = it },
                events = MutableSharedFlow()
            )
        }

        // find by semantics, act, assert
        composeTestRule.onNodeWithContentDescription("Search").performClick()
        assertEquals(SearchEvent.OnSearchClick, lastEvent)
    }
}
```

## End-to-End Tests

End-to-end (E2E) tests are black-box tests that run *outside* the app and drive it exactly as a user would — tapping, typing, navigating across whole flows, and even crossing app boundaries (permission dialogs, switching apps). Unlike unit and instrumented tests, they exercise the complete, integrated system. They are the slowest and most fragile tests, so the pyramid keeps them few — reserved for critical journeys like sign-in or checkout.

### Maestro

**Maestro** is a modern, open-source E2E framework that has become a popular default for mobile. Its appeal is simplicity: flows are written in plain, readable **YAML** and it works at the UI layer through the visual and accessibility trees, with no code instrumentation or framework-specific drivers. Because it is framework-agnostic, the same approach drives a Compose Android app, a SwiftUI iOS app, or React Native/Flutter. It also handles system-level actions (permissions, toggling settings, notifications) that in-app tests cannot, and offers Maestro Studio, a visual editor for building flows without hand-writing YAML.

*A Maestro flow (login.yaml) -- readable end-to-end test*

```kotlin
appId: com.example.myapp
---
- launchApp
- tapOn: "Email"
- inputText: "leo@example.com"
- tapOn: "Password"
- inputText: "secret123"
- tapOn: "Sign in"
- assertVisible: "Welcome back"      # the whole login journey, as a user
```

### The wider landscape

Maestro is a strong starting point, but it is worth knowing the alternatives honestly. **Appium** is the long-established cross-platform option, driver-based (it uses UiAutomator2 or Espresso under the hood on Android, XCUITest on iOS), extremely capable but heavier to set up and maintain. A newer category of **AI vision-based** tools (such as Drizz) identifies elements visually rather than by selectors, aiming to reduce the brittleness of selector-based tests — promising, but less established. For a Kotlin/Android team wanting readable tests with a gentle learning curve, Maestro is the pragmatic first choice; Appium earns its place when you need deep cross-platform coverage with a dedicated QA team.

| Tool | Approach | Best for |
| --- | --- | --- |
| Maestro | YAML flows, UI/accessibility layer | Readable E2E, quick start, cross-platform |
| Appium | Driver-based (UiAutomator2/XCUITest) | Deep cross-platform, dedicated QA teams |
| AI vision (e.g. Drizz) | Visual element recognition | Reducing selector brittleness (newer, less proven) |

## Best Practices

- Test behaviour, not implementation: assert observable outputs (returned values, emitted state), not which internal methods were called.
- Follow the pyramid: many unit tests, fewer integration tests, a handful of E2E tests for critical journeys.
- Keep logic in the JVM-testable layer (use cases, ViewModels) so most tests need no device.
- Use the **Robot pattern** for UI tests: a robot class wraps the screen's interactions (loginRobot.enterEmail(...).submit()), so tests read as intent and survive UI changes in one place.
- Name tests for the scenario in backticks: **`When get users, expect a list of users`** reads as a spec and beats **`testGetUsers2`**; a **When … expect …** phrasing pairs naturally with Given/When/Then bodies.
- Inject dispatchers and clocks so async tests are deterministic (Repeatable).
- Run the unit and integration suites on every push in CI; run the slower E2E suite on a schedule or before release.
- Treat a flaky test as a bug: fix or delete it — a suite you cannot trust is worse than none.

---

← [Previous: Testing Fundamentals](../01-testing-fundamentals/) · [↑ Chapter Index](../)
