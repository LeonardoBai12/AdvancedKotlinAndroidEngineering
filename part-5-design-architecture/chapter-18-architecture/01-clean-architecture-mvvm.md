---
layout: page
title: "Chapter 18: Architecture & Pragmatic Wisdom"
---

*Clean Architecture layers, MVVM, core classes, feature organisation, and pragmatic principles*

Architecture is the set of decisions that are expensive to change later — the shape of the system, the boundaries between its parts, and the direction of dependencies between them. This chapter brings together everything before it: the module boundaries of the previous chapter, the SOLID principles, and the language features from Part I all converge here into a concrete, buildable structure. We define each layer and each role precisely — no hand-waving — then show how the pieces fit in a real, multi-module, feature-organised app.

## Clean Architecture — The Three Layers

Clean Architecture organises code into concentric layers governed by one strict rule, the **dependency rule**: source-code dependencies point *inward only*. On Android this is usually expressed as three layers — **presentation**, **domain**, and **data** — where presentation and data both depend on domain, and domain depends on nothing. This is the Dependency Inversion Principle applied at the scale of an entire app, and (as the previous chapter showed) it maps directly onto a module graph.

### Domain — the innermost layer

The **domain** layer is the heart of the app: pure business logic with *no* knowledge of Android, databases, or networking. It is ideally plain Kotlin, so it compiles and tests without an emulator. It contains three kinds of thing:

- **Entities / models**: the core business objects (a **User**, an **Order**), expressed as plain data classes with no framework annotations.
- **Use cases (interactors)**: one class per business action (**GetProfileUseCase**, **PlaceOrderUseCase**), each doing one thing — the Single Responsibility Principle in practice.
- **Repository interfaces**: the *abstractions* the domain needs (**UserRepository**), declared here but implemented in the data layer — this is what inverts the dependency.

*Domain layer -- pure Kotlin, no Android*

```kotlin
// Entity / model
data class User(val id: String, val name: String, val email: String)

// Resource -- a sealed wrapper for an operation's outcome, used across layers
sealed interface Resource<out T> {
    data class Success<T>(val data: T) : Resource<T>
    data class Error(val message: String) : Resource<Nothing>
    data object Loading : Resource<Nothing>
}

// Repository interface -- the abstraction lives in domain
interface UserRepository {
    suspend fun getUser(id: String): User
}

// Use case -- emits Loading, then Success or Error, as a Flow
class GetUserUseCase(private val repo: UserRepository) {
    operator fun invoke(id: String): Flow<Resource<User>> = flow {
        emit(Resource.Loading)
        try {
            emit(Resource.Success(repo.getUser(id)))
        } catch (e: Exception) {
            emit(Resource.Error(e.message ?: "Unknown error"))
        }
    }
}
```

### Data — implements the domain's abstractions

The **data** layer provides the concrete implementations of the repository interfaces the domain declared. It is where Android and third-party frameworks live: Retrofit for network, Room for the local database, DataStore for preferences. It also owns the **data models** (DTOs and entities that mirror the API or the database tables) and the **mappers** that translate between those and the clean domain models, so framework shapes never leak inward.

*Data layer -- repository implementation + mapping*

```kotlin
// DTO -- mirrors the JSON the API returns (lives in data, not domain)
data class UserDto(val id: String, val full_name: String, val email: String)

fun UserDto.toDomain() = User(id = id, name = full_name, email = email)  // mapper

class UserRepositoryImpl(
    private val api: UserApi,          // Retrofit -- a data-layer detail
    private val dao: UserDao           // Room     -- a data-layer detail
) : UserRepository {                   // implements the DOMAIN interface
    override suspend fun getUser(id: String): User = try {
        api.fetchUser(id).toDomain().also { dao.cache(it) }
    } catch (e: Exception) {
        dao.getCached(id).toDomain()   // offline fallback
    }
}
```

### Presentation — the UI layer

The **presentation** layer turns domain data into pixels and turns user actions into use-case calls. It depends on domain (it calls use cases) but knows nothing about data — it cannot tell whether a user came from the network or the cache. It contains the **ViewModels** and the **UI** itself (Composables or XML Views). This is where the MVVM pattern lives, which the next section dissects.

| Layer | Contains | Knows about | Android-dependent? |
| --- | --- | --- | --- |
| Presentation | ViewModels, UI (Compose/Views) | Domain | Yes |
| Domain | Models, use cases, repo interfaces | Nothing | No (pure Kotlin) |
| Data | Repo impls, DTOs, Retrofit, Room, mappers | Domain | Yes |

> **Key Insight:**
>
> The dependency rule in one sentence: **domain depends on nothing; everything depends on domain**. Because the domain owns the repository *interface* and the data layer implements it, the arrow from data points inward — even though, at runtime, control flows outward from the ViewModel into the database. Inverting that source-code dependency is the whole trick.

## MVVM — Model, View, ViewModel, Piece by Piece

MVVM (Model-View-ViewModel) is the presentation-layer pattern Google recommends for Android. Its three roles are precise, and the value comes from keeping them strictly separated. The governing rule is **state flows down, events flow up**.

### Model

The **Model** is the data and business logic the screen works with — in Clean Architecture terms, the domain models and use cases from the layers above. It is *not* a UI concept and holds no reference to the View or ViewModel. It simply represents and produces the data.

### View

The **View** is the UI: Composables (or, in the older system, an Activity/Fragment with XML). Its only jobs are to *render* the state the ViewModel exposes and to *forward* user actions to the ViewModel as events. It contains no business logic and makes no decisions — a 'dumb' View is a feature, not a flaw, because logic in the View cannot be unit-tested and does not survive configuration changes.

### ViewModel

The **ViewModel** is the bridge. It holds and exposes the UI state (as a StateFlow), receives events from the View, runs the appropriate use cases, and updates the state with the result. It survives configuration changes (its scope outlives a rotation), and crucially it has *no reference to the View* — it exposes state and the View observes it, rather than the ViewModel pushing into the View. That one-way relationship is what makes the screen testable and rotation-safe.

*MVVM wired correctly -- state down, events up*

```kotlin
class ProfileViewModel(
    private val getUser: GetUserUseCase      // depends on DOMAIN, not data
) : ViewModel() {
    // State flows DOWN: private mutable, public read-only (encapsulation)
    private val _state = MutableStateFlow<ProfileUiState>(ProfileUiState.Loading)
    val state: StateFlow<ProfileUiState> = _state.asStateFlow()

    // Events flow UP: the View calls this; the ViewModel never calls the View
    fun onProfileOpened(userId: String) {
        viewModelScope.launch {                      // survives rotation
            getUser(userId).collect { resource ->    // a Flow<Resource<User>>
                _state.value = when (resource) {
                    is Resource.Loading -> ProfileUiState.Loading
                    is Resource.Success -> ProfileUiState.Success(resource.data)
                    is Resource.Error   -> ProfileUiState.Error(resource.message)
                }
            }
        }
    }
}

@Composable
fun ProfileScreen(viewModel: ProfileViewModel, userId: String) {
    val state by viewModel.state.collectAsStateWithLifecycle()  // observes state
    LaunchedEffect(userId) { viewModel.onProfileOpened(userId) } // sends an event
    when (state) { /* render each state -- no logic here */ }
}
```

> **Warning:**
>
> Common MVVM mistakes: putting business logic in the View; giving the ViewModel a reference to the Activity/Context (a leak — use AndroidViewModel or inject what you need); and exposing mutable state (**MutableStateFlow**) directly instead of a read-only **StateFlow**. Each breaks testability or correctness.

---

[↑ Chapter Index](../) · [Next: State & DI →](../02-state-di/)
