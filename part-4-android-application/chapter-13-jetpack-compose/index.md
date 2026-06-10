---
layout: page
title: "Chapter 13: Jetpack Compose Fundamentals"
---
*Declarative UI, recomposition, state, and unidirectional data flow*

Jetpack Compose is Android's modern declarative UI toolkit. It accelerates and greatly simplifies UI development by combining declarative programming with the expressiveness of Kotlin. Instead of imperatively wiring up and mutating individual views, you describe what the UI should look like for a given state, and Compose efficiently figures out what to update. This chapter sits deliberately after the Coroutines chapter, because Compose state and Flow are deeply intertwined.

## Composable Functions

Composable functions are ordinary Kotlin functions annotated with **@Composable**. They represent UI widgets and describe *what* the UI should look like, not *how* to build it step by step. A key convention: name them as nouns describing the UI, never as verbs describing an action.

| Correct (noun — describes UI) | Incorrect (verb — describes action) |
| --- | --- |
| UserProfile() | ShowUser() |
| SearchBar() | DisplaySearch() |
| ProductCard() | RenderProduct() |

*Composable functions*

```kotlin
@Composable
fun Greeting(name: String) {
    Text("Hello, $name!")
}

@Composable
fun ProductCard(product: Product) {
    Card {
        Text(product.name)
        Text("$${product.price}")
    }
}
```

### Lazy initialization

Just like Kotlin's **lazy**, composables are created only when actually needed. A **LazyColumn** renders only the items currently visible on screen — a list of a thousand items materialises only the ~20 that fit, creating the rest on demand as the user scrolls.

*LazyColumn renders only what is visible*

```kotlin
@Composable
fun MyScreen() {
    LazyColumn {
        items(1000) { index -> Text("Item $index") }
    }
    // Only ~20 items exist for the visible area;
    // the rest are created on-demand while scrolling.
}
```

## Imperative vs Declarative

In the traditional View system you program imperatively: views hold internal state and expose setters and getters, and you must manually push each new state into each widget. Every manual mutation is a chance to introduce a bug, and the possible states sprawl across many sub-states. Compose flips this: you describe the entire UI for a given state, and Compose handles every update automatically, relying only on Kotlin.

| Aspect | Imperative (Views) | Declarative (Compose) |
| --- | --- | --- |
| Your code | Manually updates each view | Describes the whole UI for a state |
| What happens | You control every change | Compose computes the changes |
| Approach | Tell it HOW to update | Describe WHAT to show |
| Mental model | "Change this view" | "UI = function of state" |

*The same loading screen, both ways*

```kotlin
// IMPERATIVE (Views) -- a sequence of manual mutations
progressBar.visibility = View.VISIBLE
textView.text = "Loading..."
fetchData()
textView.text = data.name
progressBar.visibility = View.GONE

// DECLARATIVE (Compose) -- describe the UI for each state
@Composable
fun UserScreen(viewModel: UserViewModel) {
    val uiState by viewModel.uiState.collectAsState()
    when (uiState) {
        is Loading -> CircularProgressIndicator()
        is Success -> Text(uiState.data.name)
        is Error   -> Text("Error!")
    }
}
```

## Recomposition

Recomposition is the process of calling your composable functions again when their inputs change. Compose tracks which composables read which state, and recomposes only those that read the changed state — stable, unchanged composables are skipped entirely. This is automatic, granular, and efficient.

*Selective recomposition*

```kotlin
@Composable
fun SearchScreen() {
    var searchQuery by remember { mutableStateOf("") }
    Column {
        TextField(value = searchQuery, onValueChange = { searchQuery = it })
        Text("Searching for: $searchQuery")   // reads query -> RECOMPOSES
        Text("Fixed Header")                   // no read   -> SKIPPED
        Button(onClick = { }) { Text("Submit") } // no read  -> SKIPPED
    }
}
// Type one letter: only TextField and the 'Searching for' Text
// recompose. The header and button cost nothing.
```

> **Key Insight:**
>
> The four principles of recomposition: it is **efficient** (only changed parts update), **automatic** (Compose tracks dependencies for you), **granular** (it can recompose a single composable), and **smart** (it skips stable, unchanged parts).

## State

State is any value that can change over time and that the UI depends on. State lets an object alter its behaviour as its internal state changes, at runtime. In Compose, **remember** preserves a value across recompositions (without it, the value would reset on every recomposition), and **mutableStateOf** makes Compose observe the value so that reading composables recompose when it changes.

*remember + mutableStateOf*

```kotlin
@Composable
fun Counter() {
    var count by remember { mutableStateOf(0) }
    Button(onClick = { count++ }) {
        Text("Count: $count")
        // Only the Text recomposes when count changes;
        // the Button structure is unchanged and is skipped.
    }
}
```

## ViewModel & Unidirectional Data Flow

The ViewModel is the heart of the MVVM pattern in Compose. It not only holds UI state, but also receives user-interaction events from the views, updates the state in response, holds and preserves the entire UI state (surviving rotation), requests or reloads data from repositories or other sources, and prepares data for display by applying transformations. The governing principle is simple and absolute: **state flows down, events flow up**.

*The unidirectional flow*

```kotlin
// ViewModel  -- business logic, data fetching
//    |  state flows DOWN
//    v
// Composable -- observes state, renders UI
//    ^
//    |  events flow UP (user actions)
// User       -- taps, types, scrolls
```

*SearchViewModel + SearchScreen*

```kotlin
class SearchViewModel : ViewModel() {
    private val _query = MutableStateFlow("")
    val query: StateFlow<String> = _query.asStateFlow()

    private val _results = MutableStateFlow<List<Result>>(emptyList())
    val results: StateFlow<List<Result>> = _results.asStateFlow()

    fun onQueryChanged(q: String) {            // event handler
        _query.value = q
        viewModelScope.launch {
            _results.value = repository.search(q)
        }
    }
}

@Composable
fun SearchScreen(viewModel: SearchViewModel) {
    val query   by viewModel.query.collectAsState()    // state DOWN
    val results by viewModel.results.collectAsState()
    Column {
        TextField(
            value = query,
            onValueChange = { viewModel.onQueryChanged(it) }  // event UP
        )
        LazyColumn { items(results) { Text(it.title) } }
    }
}
```

> **Interview Tip:**
>
> Mental model: think of Compose like a smart spreadsheet. You define formulas (composables); when input cells change (state); only dependent cells recalculate (smart recomposition).

## Navigation in Compose

Compose has its own navigation library built around a **NavController** (which holds the back stack) and a **NavHost** (which maps string *routes* to the Composable shown for each). You declare one **composable(route)** block per screen; calling **navController.navigate(route)** pushes that destination, and the system back gesture pops it. A clean, type-safe way to name routes is an **enum** of screens, so the route strings are never hand-typed and a typo cannot slip through.

*Routes as an enum + a NavHost*

```kotlin
enum class Screen { Home, Detail, Profile, Settings }

@Composable
fun AppNavigation() {
    val navController = rememberNavController()
    NavHost(
        navController = navController,
        startDestination = Screen.Home.name
    ) {
        composable(Screen.Home.name) {
            HomeScreen(
                onItemClick = { navController.navigate(Screen.Detail.name) },
                onSettings  = { navController.navigate(Screen.Settings.name) }
            )
        }
        composable(Screen.Detail.name) {
            DetailScreen(onBack = { navController.popBackStack() })
        }
        composable(Screen.Settings.name) {
            SettingsScreen(navController)
        }
        composable(Screen.Profile.name) { ProfileScreen() }
    }
}
```

### Passing arguments

Routes can carry arguments as path or query parameters, declared in the route string and read from the destination's **NavBackStackEntry**. Pass small identifiers — an id — and let the destination's ViewModel load the rest, rather than threading whole objects through the route (the same discipline the Deep Links chapter applies between modules).

*A route with an argument*

```kotlin
// Declaration: a route with a typed path argument
composable(
    route = "detail/{itemId}",
    arguments = listOf(navArgument("itemId") { type = NavType.StringType })
) { backStackEntry ->
    val itemId = backStackEntry.arguments?.getString("itemId") ?: ""
    DetailScreen(itemId = itemId)
}

// Navigation: substitute the value
navController.navigate("detail/42")
```

Keep navigation in the UI layer: the ViewModel signals *that* navigation should happen by emitting a one-shot event (the SharedFlow pattern from the architecture chapter), and the Composable observing that event calls **navController.navigate(...)**. The ViewModel never holds the NavController — that would couple it to the UI and leak the back stack.

## Advanced Concepts to Explore Next

- **Stability**: Compose skips composables whose inputs are stable and unchanged. Unstable types (a plain List, mutable classes) defeat this and cause needless recomposition.
- **derivedStateOf**: compute state from other state efficiently, recomputing only when the inputs that matter change.
- **Side effects**: **LaunchedEffect**, **DisposableEffect**, and **rememberCoroutineScope** run lifecycle-aware work tied to the composition.
- **collectAsStateWithLifecycle()**: the lifecycle-aware way to collect a Flow in Compose, pausing collection when the screen is not visible.

---

[↑ Chapter Index](../)
