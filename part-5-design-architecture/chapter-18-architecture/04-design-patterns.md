---
layout: default
title: Design Patterns
parent: "Architecture & Pragmatic Wisdom"
nav_order: 4
---

*GoF creational, structural, and behavioral patterns with Kotlin examples*

Design patterns are reusable solutions to recurring design problems. The Gang of Four (GoF) catalog organises them into three categories based on what they address. Knowing them matters for interviews not because you will implement every one from scratch, but because they are the shared vocabulary that names the solutions already present in the Android SDK and in every well-structured app.

## Three Pattern Categories

| Category | Concern | Examples |
| --- | --- | --- |
| Creational | How objects are created | Factory Method, Abstract Factory, Builder, Singleton |
| Structural | How objects are composed | Adapter, Decorator, Facade |
| Behavioral | How objects communicate | Observer, Strategy, State, Command |

---

## Creational Patterns

Creational patterns abstract the instantiation process. They make the system independent of *how* its objects are created, composed, and represented.

### Factory Method

**Intent:** Define an interface for creating an object, but let subclasses decide which class to instantiate.

```kotlin
abstract class NotificationFactory {
    abstract fun create(context: Context): Notification

    fun show(context: Context, id: Int) {
        val notification = create(context)
        NotificationManagerCompat.from(context).notify(id, notification)
    }
}

class AlertNotificationFactory : NotificationFactory() {
    override fun create(context: Context) = NotificationCompat.Builder(context, "alerts")
        .setContentTitle("Alert")
        .setSmallIcon(R.drawable.ic_alert)
        .setPriority(NotificationCompat.PRIORITY_HIGH)
        .build()
}

class SilentNotificationFactory : NotificationFactory() {
    override fun create(context: Context) = NotificationCompat.Builder(context, "updates")
        .setContentTitle("Update")
        .setSmallIcon(R.drawable.ic_update)
        .setSilent(true)
        .build()
}
```

Android sightings: `LayoutInflater` (creates Views from XML), `ViewModelProvider.Factory` (creates ViewModels with dependencies).

---

### Abstract Factory (also known as Kit)

**Intent:** Provide an interface for creating *families* of related objects without specifying their concrete classes.

The GoF's motivation example is a UI toolkit (WidgetFactory) that needs to support multiple look-and-feels — each concrete factory creates a consistent set of widgets. The point is not just creation but **consistency of the family**: *"a Motif scroll bar should be used with a Motif button and a Motif text editor, and that constraint is enforced automatically as a consequence of using a MotifWidgetFactory."* Clients call the creation operations but *"have no knowledge of the concrete classes they are using"* — you choose the family once, by instantiating one concrete factory, and from then on the whole application uses it consistently. The key applicability rule highlighted in the book: *"use when a system must be independent of how its products are created, composed, and represented."*

```kotlin
// Abstract factory declares the family
interface ThemeFactory {
    fun createButton(): ButtonStyle
    fun createCard(): CardStyle
    fun createTypography(): TypographyStyle
}

// Concrete factories produce consistent product families
class MaterialThemeFactory : ThemeFactory {
    override fun createButton()     = MaterialButton()
    override fun createCard()       = ElevatedCard()
    override fun createTypography() = MaterialTypography()
}

class HighContrastThemeFactory : ThemeFactory {
    override fun createButton()     = HighContrastButton()
    override fun createCard()       = OutlinedCard()
    override fun createTypography() = LargeTypography()
}

// Client code never references concrete product classes
class ThemeRenderer(private val factory: ThemeFactory) {
    fun render() {
        val button = factory.createButton()
        val card   = factory.createCard()
        button.apply(); card.apply()
    }
}

// Swap an entire theme by changing the factory
val renderer = ThemeRenderer(HighContrastThemeFactory())
```

The GoF implementation notes show the factory being selected **at run time** — an environment variable decides between `MotifFactory` and `PMFactory` at startup — and suggest a more sophisticated variant: *"you can keep a registry that maps strings to factory objects,"* so new factory subclasses can be registered without modifying existing code. The same moves work in Kotlin:

```kotlin
// Select the family once at startup (build flavor, remote config, user setting...)
val factory: ThemeFactory = when (settings.theme) {
    Theme.HIGH_CONTRAST -> HighContrastThemeFactory()
    else                -> MaterialThemeFactory()
}

// Or a registry — new families plug in without touching this code
val registry = mutableMapOf<String, () -> ThemeFactory>(
    "material"      to ::MaterialThemeFactory,
    "high_contrast" to ::HighContrastThemeFactory,
)
val chosen = registry.getValue(settings.themeKey).invoke()
```

**Abstract Factory vs Factory Method:** Factory Method uses inheritance (a subclass overrides one creator method). Abstract Factory uses composition (you inject an entire factory object that creates a family). In Kotlin Multiplatform the two blend naturally: an `expect class HttpClientFactory { fun create(): HttpClient }` with `actual` implementations per platform is a factory whose "family" is *everything platform-specific* — each platform's source set is, in effect, one concrete factory guaranteeing a consistent set of platform products.

---

### Builder

**Intent:** Construct complex objects step by step. The same construction process can produce different representations.

Every major builder in the Android SDK uses this pattern:

```kotlin
// OkHttp — real SDK Builder
val client = OkHttpClient.Builder()
    .connectTimeout(30, TimeUnit.SECONDS)
    .addInterceptor(loggingInterceptor)
    .certificatePinner(pinner)
    .build()

// Notification — real SDK Builder
val notification = NotificationCompat.Builder(context, CHANNEL_ID)
    .setContentTitle("Downloading")
    .setProgress(100, progress, false)
    .setOngoing(true)
    .build()

// Custom Builder for a domain object
data class SearchQuery private constructor(
    val table: String,
    val limit: Int,
    val orderBy: String?,
    val filter: String?
) {
    class Builder(private val table: String) {
        private var limit   = 20
        private var orderBy: String? = null
        private var filter:  String? = null

        fun limit(n: Int)         = apply { limit   = n    }
        fun orderBy(col: String)  = apply { orderBy = col  }
        fun filter(expr: String)  = apply { filter  = expr }

        fun build() = SearchQuery(table, limit, orderBy, filter)
    }
}

val query = SearchQuery.Builder("users")
    .limit(50)
    .orderBy("name")
    .filter("active = 1")
    .build()
```

Use Builder when the constructor would take many parameters, some optional, and the order of configuration does not matter.

---

### Singleton

**Intent:** Ensure a class has only one instance and provide a global access point to it.

Kotlin's `object` declaration is a compile-time Singleton, initialised lazily and guaranteed thread-safe by the JVM class loader:

```kotlin
object AppConfig {
    val baseUrl: String = BuildConfig.BASE_URL
    var loggingEnabled = false
}

// Access from anywhere — no getInstance() boilerplate
AppConfig.loggingEnabled = BuildConfig.DEBUG
```

In production Android, prefer injecting a **singleton-scoped dependency via Hilt/Dagger** over raw `object` declarations. An `object` is globally accessible, which makes testing harder (you can't replace it with a fake). A Hilt `@Singleton` achieves the same single-instance guarantee while remaining injectable and testable.

---

## Structural Patterns

Structural patterns describe how classes and objects are composed to form larger structures.

### Adapter (also known as Wrapper)

**Intent:** Convert the interface of a class into another interface clients expect. Allows classes with incompatible interfaces to work together — *"which otherwise would be impossible."*

The GoF motivation: *"sometimes a toolkit class, designed for reuse, isn't reusable because its interface doesn't match the domain-specific interface an application requires."* Their example is a drawing editor whose shapes implement a `Shape` interface, and an existing, sophisticated `TextView` class that knows nothing about `Shape`. Changing `TextView` is not viable (you may not own the source, and a toolkit shouldn't adopt one app's interfaces), so you define a `TextShape` that *adapts* `TextView` to `Shape`. The book gives **two ways** to do it:

1. **Class adapter** — inherit `Shape`'s interface *and* `TextView`'s implementation (multiple inheritance in C++; in Kotlin, interface + delegation gets close).
2. **Object adapter** — implement `Shape` and hold a `TextView` *instance* inside, forwarding calls to it.

The object adapter — composition — is the one that survives in modern practice: it works with any subclass of the adaptee, keeps the adapter independent of the adaptee's internals, and needs no inheritance gymnastics. The Adapter does not change either side; it bridges the gap between them.

```kotlin
// Third-party SDK returns its own Location type
class ThirdPartyLocation(val lat: Double, val lng: Double, val accuracyMeters: Float)

// Our domain expects this contract
interface LocationSource {
    fun latitude(): Double
    fun longitude(): Double
    fun accuracy(): Float
}

// Adapter bridges the gap — no changes to ThirdPartyLocation or LocationSource
class ThirdPartyLocationAdapter(
    private val src: ThirdPartyLocation
) : LocationSource {
    override fun latitude()  = src.lat
    override fun longitude() = src.lng
    override fun accuracy()  = src.accuracyMeters
}

// Client code works with LocationSource — unaware of the third-party type
fun formatCoordinate(loc: LocationSource) =
    "%.6f, %.6f (±%.0fm)".format(loc.latitude(), loc.longitude(), loc.accuracy())
```

Android SDK sightings:

- `RecyclerView.Adapter` — adapts a `List<T>` to `View`s
- `CursorAdapter` — adapts a database `Cursor` to `ListView` rows
- `OkHttp`'s `Call.Factory` — adapts different HTTP backends to a uniform interface

A modern cross-platform sighting: in a Kotlin Multiplatform app, a shared ViewModel exposes state as a `StateFlow` — which SwiftUI cannot observe. The iOS side wraps it in an `ObservableObject` that subscribes to the shared flow and republishes values through `@Published` properties, forwarding user events back to the shared `onEvent`. That wrapper is a textbook object adapter: the shared ViewModel and SwiftUI are both unchanged; one class bridges their incompatible observation contracts.

---

### Decorator

**Intent:** Attach additional responsibilities to an object dynamically by wrapping it. Provides a flexible alternative to subclassing for extending functionality.

OkHttp's `Interceptor` is a textbook Decorator — each interceptor wraps the chain, adding behaviour before or after delegating:

```kotlin
class AuthInterceptor(private val tokenProvider: TokenProvider) : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val request = chain.request().newBuilder()
            .addHeader("Authorization", "Bearer ${tokenProvider.token}")
            .build()
        return chain.proceed(request)   // delegate, then receive response
    }
}

class RetryInterceptor(private val maxRetries: Int = 3) : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        var attempt = 0
        var response = chain.proceed(chain.request())
        while (!response.isSuccessful && attempt < maxRetries) {
            response.close()
            response = chain.proceed(chain.request())
            attempt++
        }
        return response
    }
}

// Decorators compose — order matters
val client = OkHttpClient.Builder()
    .addInterceptor(AuthInterceptor(tokenProvider))   // auth first
    .addInterceptor(RetryInterceptor(3))              // then retry
    .build()
```

Compose `Modifier` follows the same structure — each modifier wraps the previous, adding behaviour (padding, clipping, click handling) without subclassing:

```kotlin
Box(
    modifier = Modifier
        .fillMaxSize()
        .padding(16.dp)               // each call wraps the Modifier before it
        .clip(RoundedCornerShape(8.dp))
        .background(MaterialTheme.colorScheme.surface)
        .clickable { onAction() }
)
```

---

### Facade

**Intent:** Provide a simplified interface to a complex subsystem, hiding its internal complexity.

The **Repository** pattern in Clean Architecture is a Facade: it hides the complexity of Room + Retrofit + caching behind a single `get/save` interface that the domain layer calls without knowing what is behind it.

```kotlin
// The complex subsystem — three different technologies
class UserApi   // Retrofit interface
class UserDao   // Room DAO
class UserCache // In-memory LRU cache

// The Facade — one clean contract for the rest of the app
class UserRepositoryImpl(
    private val api:   UserApi,
    private val dao:   UserDao,
    private val cache: UserCache
) : UserRepository {

    override fun getUser(id: String): Flow<User> = flow {
        cache.get(id)?.let { emit(it); return@flow }   // cache hit — done
        emitAll(dao.observeUser(id))                    // emit Room data immediately
        val remote = api.fetchUser(id)                  // fetch remote in parallel
        dao.upsert(remote)                              // Room Flow auto-notifies
        cache.put(id, remote)
    }
}

// Use case sees only the interface — completely unaware of Room or Retrofit
class GetUserUseCase(private val repo: UserRepository) {
    operator fun invoke(id: String) = repo.getUser(id)
}
```

Other Facade examples: `Glide`/`Coil` (hide HTTP + disk cache + bitmap decoding behind a one-liner), `WorkManager` (hides `JobScheduler`/`AlarmManager`/`Firebase JobDispatcher` behind a single API).

---

## Behavioral Patterns

Behavioral patterns are concerned with algorithms and the assignment of responsibilities between objects.

### Observer

**Intent:** Define a one-to-many dependency so that when one object changes state, all its dependents are notified and updated automatically.

Kotlin/Android has first-class Observer support through `Flow` and `StateFlow`:

```kotlin
// Subject: ViewModel publishes state changes
class FeedViewModel(private val getUsers: GetUsersUseCase) : ViewModel() {
    private val _state = MutableStateFlow<FeedState>(FeedState.Loading)
    val state: StateFlow<FeedState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            getUsers().collect { users ->
                _state.value = FeedState.Success(users)
            }
        }
    }
}

// Observers: Compose reacts automatically
@Composable
fun FeedScreen(viewModel: FeedViewModel = viewModel()) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    when (state) {
        is FeedState.Loading -> CircularProgressIndicator()
        is FeedState.Success -> LazyColumn { items(state.users) { UserRow(it) } }
        is FeedState.Error   -> ErrorView(state.message)
    }
}
```

From the Compose book: *"State changes over time because of events. The UI should observe state changes so it can update accordingly."* — `StateFlow` + `collectAsStateWithLifecycle` is the Android idiom for Observer.

Room DAOs returning `Flow<List<T>>` make the database itself an observable subject — the DAO emits a new list every time the underlying table changes, without polling.

In the XML View era the canonical Observer was **LiveData**: `liveData.observe(lifecycleOwner) { render(it) }` registers a callback exactly as the GoF describe, and its lifecycle-awareness fixes the pattern's classic housekeeping problem — observers auto-deregister on `DESTROYED`, so a rotated Activity never leaks or receives updates it cannot render.

Hunt and Thomas point out the pattern's two structural limits (*The Pragmatic Programmer*, Topic 29): every observer must register directly with the observable, which **couples** them, and callbacks run synchronously inline, so a slow observer becomes a **bottleneck** — problems addressed by Publish/Subscribe and reactive streams, covered in [Patterns & Principles](../03-patterns-principles/). RxJava and `Flow` are that evolution: the *subscriber* of a stream is the Observer pattern generalised over time and freed from synchronous delivery.

---

### Strategy

**Intent:** Define a family of algorithms, encapsulate each one, and make them interchangeable. Lets the algorithm vary independently from the clients that use it.

```kotlin
// Strategy interface
fun interface SortStrategy<T> {
    fun sort(items: List<T>): List<T>
}

// Concrete strategies
val alphabetical = SortStrategy<String> { it.sorted() }
val recentFirst  = SortStrategy<Post>   { it.sortedByDescending { p -> p.timestamp } }
val byPopularity = SortStrategy<Post>   { it.sortedByDescending { p -> p.likeCount } }

// Context — uses whichever strategy is injected or switched at runtime
class FeedSorter<T>(private var strategy: SortStrategy<T>) {
    fun sort(items: List<T>)          = strategy.sort(items)
    fun changeStrategy(s: SortStrategy<T>) { strategy = s }
}

val sorter = FeedSorter(recentFirst)
sorter.sort(posts)
sorter.changeStrategy(byPopularity)
sorter.sort(posts)  // same context, different algorithm
```

In Kotlin, a strategy often collapses to a function type — `(List<T>) -> List<T>` — which is idiomatic for simple cases. Use the full interface pattern when the strategy needs its own state or multiple methods.

---

### State (also known as Objects for States)

**Intent:** Allow an object to alter its behavior when its internal state changes. The object appears to change its class.

From the GoF book: `TCPConnection` behaves differently in `Established`, `Listening`, and `Closed` states. An abstract `TCPState` declares the common interface (`Open()`, `Close()`, `Acknowledge()`); each subclass implements the behaviour for one state; and whenever the connection changes state, `TCPConnection` swaps the state object it delegates to. The GoF give two applicability signals:

- an object's behavior depends on its state, and it must change its behavior **at run time** depending on that state;
- operations have *"large, multipart conditional statements that depend on the object's state"* — the same conditional structure repeated across several operations. *"The State pattern puts each branch of the conditional in a separate class. This lets you treat the object's state as an object in its own right."*

So rather than a massive `when(state)` repeated everywhere, each state is a class that implements only the transitions relevant to it.

```kotlin
// State interface — all operations the context can perform
sealed interface PlayerState {
    fun play(player: AudioPlayer):  PlayerState
    fun pause(player: AudioPlayer): PlayerState
    fun stop(player: AudioPlayer):  PlayerState
}

object IdleState : PlayerState {
    override fun play(player: AudioPlayer): PlayerState {
        player.start(); return PlayingState
    }
    override fun pause(player: AudioPlayer) = this  // no-op: already idle
    override fun stop(player: AudioPlayer)  = this  // no-op: already idle
}

object PlayingState : PlayerState {
    override fun play(player: AudioPlayer)  = this  // no-op: already playing
    override fun pause(player: AudioPlayer): PlayerState {
        player.pause(); return PausedState
    }
    override fun stop(player: AudioPlayer): PlayerState {
        player.stop(); return IdleState
    }
}

object PausedState : PlayerState {
    override fun play(player: AudioPlayer): PlayerState {
        player.start(); return PlayingState
    }
    override fun pause(player: AudioPlayer) = this  // no-op: already paused
    override fun stop(player: AudioPlayer): PlayerState {
        player.stop(); return IdleState
    }
}

// Context delegates to the current state — transitions are self-contained
class MusicController(private val player: AudioPlayer) {
    private var state: PlayerState = IdleState

    fun play()  { state = state.play(player)  }
    fun pause() { state = state.pause(player) }
    fun stop()  { state = state.stop(player)  }
}
```

Use when an object has complex conditional logic that depends on internal state and that logic keeps growing. State eliminates the `when`/`if` chains by distributing behavior into dedicated classes.

The State pattern is the object-oriented formulation of a **finite state machine** — the same machine that *The Pragmatic Programmer* recommends expressing as a transition table, and the same shape as a UDF ViewModel's sealed `UiState` + `onEvent` (see [State & DI](../02-state-di/)). The three are one idea at different weights: a transition table when the logic is pure data, a sealed hierarchy with one `when` for UI state, and full State-pattern classes when each state carries substantial behaviour of its own.

---

### Command

**Intent:** Encapsulate a request as an object, so you can parameterise clients with different requests, queue operations, log them, and support undo.

```kotlin
interface Command {
    fun execute()
    fun undo()
}

class AddItemCommand(
    private val cart: ShoppingCart,
    private val item: CartItem
) : Command {
    override fun execute() { cart.add(item) }
    override fun undo()    { cart.remove(item) }
}

class ApplyDiscountCommand(
    private val cart: ShoppingCart,
    private val code: String
) : Command {
    private var previousTotal = cart.total
    override fun execute() { cart.applyDiscount(code); previousTotal = cart.total }
    override fun undo()    { cart.removeDiscount(code) }
}

// Invoker — can queue, batch, and undo
class CommandHistory {
    private val history = ArrayDeque<Command>()

    fun execute(cmd: Command) { cmd.execute(); history.addLast(cmd) }
    fun undo() { history.removeLastOrNull()?.undo() }
}

val history = CommandHistory()
history.execute(AddItemCommand(cart, headphones))
history.execute(ApplyDiscountCommand(cart, "SAVE20"))
history.undo()   // removes discount
history.undo()   // removes headphones
```

Android sightings: IME undo/redo stacks, `WorkRequest` (encapsulates a unit of background work), Room migrations (each migration step is a command that can be validated independently).

---

## Quick-Reference Table

| Pattern | Intent (one line) | Android sighting |
| --- | --- | --- |
| Factory Method | Subclasses choose which object to create | `LayoutInflater`, `ViewModelProvider.Factory` |
| Abstract Factory | Create families of related objects | Theme systems, multi-platform UI layers |
| Builder | Construct objects step by step | `OkHttpClient.Builder`, `NotificationCompat.Builder`, `AlertDialog.Builder` |
| Singleton | One instance, global access | `object` declarations, Hilt `@Singleton` |
| Adapter / Wrapper | Bridge incompatible interfaces | `RecyclerView.Adapter`, `CursorAdapter` |
| Decorator | Add behavior dynamically without subclassing | OkHttp `Interceptor`, Compose `Modifier` |
| Facade | Simple interface to a complex subsystem | `Repository` hiding Room + Retrofit, `Glide`/`Coil` |
| Observer | Notify dependents on state change | `StateFlow`, `Flow`, Room DAO `Flow<T>` |
| Strategy | Swap algorithms at runtime | Sort strategies, retry policies, auth schemes |
| State | Behavior changes with internal state | Media player states, auth flow states, download states |
| Command | Encapsulate requests as objects | WorkManager `WorkRequest`, undo/redo, migrations |

---

← [Previous: Patterns & Principles](../03-patterns-principles/) · [↑ Chapter Index](../)
