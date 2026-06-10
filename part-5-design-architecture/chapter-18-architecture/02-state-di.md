---
layout: page
title: "Chapter 18: Architecture & Pragmatic Wisdom — State & DI"
---

## State & Events — The State Holder Pattern

MVVM says *state flows down, events flow up*, but it does not say how to *shape* that state and those events. The pattern that scales — and the one Google's guidance converges on — models the screen's entire state as a single immutable object and the user's actions as a single sealed event type. This keeps a screen's contract tiny: the View renders one state object and emits events through one function.

### One state object, not many flows

Rather than exposing several StateFlows (one for loading, one for the list, one for the input), collect everything the screen needs into a single **data class** exposed through one StateFlow. Updates use **copy()** so the state stays immutable — the **update { }** helper does this atomically. A single object also means the UI never sees an inconsistent combination of half-updated fields.

*A single state object*

```kotlin
data class SearchState(
    val query: String = "",
    val results: List<Item> = emptyList(),
    val isLoading: Boolean = false
)
```

### One sealed event type, one onEvent function

Instead of a separate ViewModel method per action (**onQueryChange**, **onSearchClick**, …), model the actions as a **sealed interface** and expose one **onEvent(event)** function. The View only needs to know about **onEvent**; adding a new action means adding a subtype, and the exhaustive **when** inside **onEvent** forces you to handle it. This is the sealed-class exhaustiveness from Part I doing real work.

*Events as a sealed interface + a single handler*

```kotlin
sealed interface SearchEvent {
    data class OnQueryChange(val query: String) : SearchEvent
    data object OnSearchClick : SearchEvent
}
```

### State vs one-shot events: StateFlow vs SharedFlow

There are two kinds of thing flowing out of a ViewModel, and they need different tools. **State** is what the screen *is* right now — it must survive rotation and be re-read by a fresh View, so it goes in a **StateFlow**. A **one-shot UI event** is something that should happen *once* — a toast, a navigation, a snackbar — and must *not* replay when the screen is recreated, so it goes in a **SharedFlow**. Putting a one-shot event in StateFlow re-fires it on every rotation (a duplicate toast, a navigation loop); this is the single most common state-management bug, and the StateFlow/SharedFlow split is the fix.

*The complete ViewModel -- state, events, and one-shot UI events*

```kotlin
class SearchViewModel(
    private val search: SearchUseCase,             // injected via constructor
    private val getSuggestions: GetSuggestionsUseCase
) : ViewModel() {

    // One-shot UI events the View consumes once (toasts, navigation)
    sealed interface UiEvent {
        data class ShowToast(val text: String) : UiEvent
    }

    // STATE -- survives rotation, always has a current value
    private val _state = MutableStateFlow(SearchState())
    val state = _state.asStateFlow()

    // ONE-SHOT EVENTS -- must not replay on recreation
    private val _events = MutableSharedFlow<UiEvent>()
    val events = _events.asSharedFlow()

    // The single entry point for everything the user does
    fun onEvent(event: SearchEvent) {
        when (event) {
            is SearchEvent.OnQueryChange ->
                _state.update { it.copy(query = event.query) }
            SearchEvent.OnSearchClick -> runSearch()
        }
    }

    private fun runSearch() {
        viewModelScope.launch {
            search(_state.value.query).collect { resource ->
                when (resource) {
                    is Resource.Loading ->
                        _state.update { it.copy(isLoading = true) }
                    is Resource.Success ->
                        _state.update { it.copy(isLoading = false, results = resource.data) }
                    is Resource.Error -> {
                        _state.update { it.copy(isLoading = false) }
                        _events.emit(UiEvent.ShowToast(resource.message))
                    }
                }
            }
        }
    }
}
```

### The stateless Composable and the Activity

The screen Composable is kept **stateless**: it receives the **state** to render, an **onEvent** callback to report actions, and the **events** flow to consume one-shot UI events — it owns no state itself. This makes it trivial to preview (just pass a hand-made state) and to test. The Activity wires the ViewModel to the Composable, collecting state as Compose state and forwarding the event flow.

*Stateless screen + Activity wiring*

```kotlin
@Composable
fun SearchScreen(
    state: SearchState,
    onEvent: (SearchEvent) -> Unit,
    events: SharedFlow<SearchViewModel.UiEvent>
) {
    val context = LocalContext.current
    LaunchedEffect(Unit) {                      // collect one-shot events once
        events.collect { event ->
            when (event) {
                is SearchViewModel.UiEvent.ShowToast ->
                    Toast.makeText(context, event.text, Toast.LENGTH_LONG).show()
            }
        }
    }
    // ... render state.query, state.results, state.isLoading;
    //     report actions via onEvent(SearchEvent.OnSearchClick) ...
}

class MainActivity : ComponentActivity() {
    private val viewModel: SearchViewModel by viewModels { factory }
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MyAppTheme {
                SearchScreen(
                    state = viewModel.state.collectAsStateWithLifecycle().value,
                    onEvent = viewModel::onEvent,
                    events = viewModel.events
                )
            }
        }
    }
}
```

> **Key Insight:**
>
> This is the State Holder pattern: a single immutable **state** object (StateFlow), a single sealed **event** type funnelled through **onEvent**, and one-shot **UI events** (SharedFlow) kept separate from state. It scales because the screen's entire contract is three things — render this state, call this function, consume these events — no matter how complex the screen becomes.

## Core Classes — Application, DI, and Cross-Cutting Concerns

Some responsibilities do not belong to any single feature — they are **cross-cutting**, needed everywhere. These live in core classes and modules, wired up once at the app's entry point.

### The Application class

The **Application** class is instantiated once, before any Activity, and lives for the entire process. It is the right place for process-wide initialisation: starting the dependency-injection container, configuring logging, initialising analytics or crash reporting. Keep it lean — heavy work here delays app startup — and never store screen state in it.

*A lean Application class*

```kotlin
class MyApp : Application() {
    override fun onCreate() {
        super.onCreate()
        // process-wide setup: logging, crash reporting, the DI container...
        // keep this method fast -- it runs on every cold start
    }
}
```

### Dependency injection

**Dependency injection** (DI) is the practice of giving a class its dependencies from outside rather than constructing them itself — the concrete form of the Dependency Inversion Principle. A ViewModel receives a use case; a use case receives a repository; a repository receives an API. At its core DI needs no library at all: it is just passing dependencies through constructors, with one place near the app's entry point — a **composition root** — that builds the object graph and decides which implementation satisfies each abstraction.

*DI by hand -- the concept, no library needed*

```kotlin
// Every class declares what it needs in its constructor and constructs
// nothing itself:
class GetUserUseCase(private val repo: UserRepository)
class UserRepositoryImpl(private val api: UserApi) : UserRepository

// A composition root wires the graph once, choosing the implementations:
object AppContainer {
    private val api: UserApi = RetrofitUserApi()
    val userRepository: UserRepository = UserRepositoryImpl(api)  // abstraction -> impl
    val getUser = GetUserUseCase(userRepository)
}
```

On a large app, wiring the graph by hand becomes tedious, so most teams adopt a DI framework that generates this wiring for them — there are several in the Android ecosystem, and the choice is a team decision rather than something this guide prescribes. Whichever you use, the principle is identical and is what matters: dependencies flow in from outside, and a single place chooses the concrete implementation behind each abstraction.

> **Interview Tip:**
>
> The payoff is the same with or without a framework: because a class receives its dependencies rather than constructing them, you can pass a fake in a unit test. A ViewModel that takes a **UserRepository** in its constructor is tested by handing it an in-memory fake repository — no network, no database. That testability is the practical reason DI is non-negotiable in a well-architected app.

---

← [Previous: Clean Architecture & MVVM](../01-clean-architecture-mvvm/) · [↑ Chapter Index](../) · [Next: Patterns & Principles →](../03-patterns-principles/)
