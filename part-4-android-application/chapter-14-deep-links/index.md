---
layout: page
title: "Chapter 14: Android Deep Links"
---
*Custom links, web links, App Links, Compose navigation, testing, and verification*

Deep links are URLs that direct users to specific content inside an Android app rather than just opening it at the home screen — like bookmarking a specific page in a book instead of opening it at the cover. The obvious use is external: they improve user experience and engagement, power marketing campaigns that land users on a product or promotion, enable re-engagement from notifications, and let apps share specific content with one another. There is a second, less obvious use that matters just as much in large apps — they serve as an *internal* navigation contract between modules and teams — which we cover after the mechanics.

## The Three Types of Deep Links

| Type | Scheme | Verified | Dialog | Use case |
| --- | --- | --- | --- | --- |
| Custom | myapp:// | No | Yes | Development, internal links |
| Web Link | https:// | No | Yes | Shareable; Android 12+ opens browser first |
| App Link | https:// | Yes | No | Production — opens directly, best UX |

- **Custom deep links** use a custom scheme like **myapp://product/123**. They work offline, but may conflict if another app claims the same scheme.
- **Web links** use the standard **https://** scheme. They fall back to the website if the app is not installed, but on Android 12+ they open in the browser first unless verified.
- **App Links** are web links verified via a domain association file. They open directly in the app with no disambiguation dialog — the best production experience.

## Implementation

### 1 — Configure the AndroidManifest

*Custom deep link intent-filter*

```kotlin
<activity android:name=".ProductDetailActivity" android:exported="true">
    <intent-filter>
        <action android:name="android.intent.action.VIEW" />
        <category android:name="android.intent.category.DEFAULT" />
        <category android:name="android.intent.category.BROWSABLE" />
        <data android:scheme="myapp" android:host="product" />
    </intent-filter>
</activity>
<!-- Accepts myapp://product and myapp://product/123 -->
```

*App Link (verified) intent-filter*

```kotlin
<activity android:name=".ProductDetailActivity" android:exported="true">
    <intent-filter android:autoVerify="true">
        <action android:name="android.intent.action.VIEW" />
        <category android:name="android.intent.category.DEFAULT" />
        <category android:name="android.intent.category.BROWSABLE" />
        <data android:scheme="https"
              android:host="www.example.com"
              android:pathPrefix="/product" />
    </intent-filter>
</activity>
<!-- autoVerify=true triggers verification against assetlinks.json -->
```

### 2 — Handle the link in the Activity

**onCreate()** handles the link that launched the Activity; **onNewIntent()** handles links that arrive while the Activity already exists. Always call **setIntent()** inside **onNewIntent()** so the Activity's stored intent is updated.

*Processing the URI*

```kotlin
class ProductDetailActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        handleDeepLink(intent)
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)          // IMPORTANT
        handleDeepLink(intent)
    }

    private fun handleDeepLink(intent: Intent?) {
        val data: Uri = intent?.data ?: return
        // myapp://product/123?color=red
        val productId = data.lastPathSegment          // "123"
        val color     = data.getQueryParameter("color") // "red"
        loadProduct(productId, color)
    }
}
```

> **Warning:**
>
> Always implement onNewIntent() alongside onCreate(). Without it, deep links delivered while the Activity is already open are silently dropped. Use launchMode="singleTask" (or singleTop) to avoid spawning multiple Activity instances.

### 3 — Compose Navigation deep links

*navDeepLink inside a NavHost*

```kotlin
NavHost(navController, startDestination = "home") {
    composable(
        route = "product/{id}?color={color}",
        arguments = listOf(
            navArgument("id")    { type = NavType.StringType },
            navArgument("color") {
                type = NavType.StringType; defaultValue = "default"
            }
        ),
        deepLinks = listOf(
            navDeepLink { uriPattern = "myapp://product/{id}?color={color}" }
        )
    ) { backStackEntry ->
        val id    = backStackEntry.arguments?.getString("id")
        val color = backStackEntry.arguments?.getString("color")
        ProductScreen(id, color)
    }
}
// Compose still needs the manifest intent-filter declared manually.
```

| Feature | XML Navigation | Compose Navigation |
| --- | --- | --- |
| Visual editor | Yes | No |
| Auto intent-filters | Yes (<nav-graph>) | No (manual manifest) |
| Type safety | Safe Args | Manual |
| Flexibility | Limited | High |
| Boilerplate | Less | More |

## Testing Deep Links with ADB

*ADB commands*

```kotlin
# Custom deep link
adb shell am start -W -a android.intent.action.VIEW \
    -d "myapp://product/123" com.example.myapp

# With query parameters
adb shell am start -W -a android.intent.action.VIEW \
    -d "myapp://product/123?color=red&size=M" com.example.myapp

# Expected output:
#   Status: ok
#   Activity: com.example.myapp/.ProductDetailActivity
```

## App Links Verification

App Links require a digital asset link file hosted on your domain at **/.well-known/assetlinks.json**, declaring which app package is allowed to handle the domain's URLs and verifying it via the app's signing certificate fingerprint.

*assetlinks.json and verification*

```kotlin
// https://www.example.com/.well-known/assetlinks.json
[{
  "relation": ["delegate_permission/common.handle_all_urls"],
  "target": {
    "namespace": "android_app",
    "package_name": "com.example.myapp",
    "sha256_cert_fingerprints": ["14:6D:E9:83:C5:73:06:50:..."]
  }
}]

# Get the debug fingerprint:
keytool -list -v -keystore ~/.android/debug.keystore \
    -alias androiddebugkey -storepass android

# Verify and inspect:
adb shell pm verify-app-links --re-verify com.example.myapp
adb shell pm get-app-links com.example.myapp
```

## Deep Links as Inter-Module Navigation

In a multi-module, multi-team app (see the Gradle & Multi-Module chapter), deep links solve a coupling problem that has nothing to do with the outside world. If feature A needs to navigate to a screen in feature B, the naive approach is for A to depend directly on B — importing its screens, knowing its arguments, calling its navigation code. That creates a hard compile-time dependency between two features that should be independent, and it forces the **:app** module (or a navigation module) to know about every screen in every feature, which makes it balloon as the app grows.

A deep link breaks that coupling. Each feature *publishes* a URI pattern — a navigation contract — for the destinations it owns, and other features navigate to that URI without any compile-time knowledge of the destination's internals. The feature owns and can freely change everything behind its URI; callers depend only on the stable contract. This is the same decoupling deep links give external callers, applied internally between teams.

*Feature-to-feature navigation via a published URI*

```kotlin
// :feature:checkout owns this destination and publishes the contract:
//     myapp://order/{orderId}

// :feature:profile navigates to it WITHOUT depending on :feature:checkout
fun openOrder(orderId: String, navController: NavController) {
    val uri = "myapp://order/$orderId".toUri()
    navController.navigate(uri)        // resolved by whichever module owns it
}

// No import of checkout's screens or arguments. The URI is the only contract;
// the :app module wires the graph together without knowing each screen.
```

There is an important security caveat to this pattern. Because a deep link is a URL, it is not treated as secret — it can appear in logs, in the back stack, in analytics, and (for external links) in browser history. So a deep link should carry only **identifiers, never sensitive data**: pass an **orderId** and let the destination fetch the order through its repository, rather than passing the order's contents, a token, or personal data in the URI itself. Keeping the payload to opaque IDs keeps the navigation contract small and avoids leaking anything sensitive through a channel that was never designed to protect it.

> **Warning:**
>
> Rule of thumb for deep-link arguments: pass the smallest identifier the destination needs and let it load the rest. An **orderId** in the URI is fine; the order's total, the user's address, or an auth token is not. This keeps features decoupled *and* keeps sensitive data off a non-secret channel.

## Best Practices & Troubleshooting

- Use **launchMode="singleTask"** to avoid multiple instances, and always implement **onNewIntent()**.
- **Validate and sanitise all URI data** before use — never trust it blindly.
- Use App Links in production for the best UX; create a synthetic back stack for proper navigation.
- **Never expose sensitive data in URLs**, and never use deep links as an authentication mechanism (more on why in the Security chapter).
- Don't hard-code schemes — derive them from build config.

| Problem | Solution |
| --- | --- |
| Deep link doesn't open the app | Check android:exported="true", the intent-filter, and that the app is installed |
| Opens the browser instead of the app | Verify App Links: assetlinks.json, SHA-256 fingerprint, re-verify |
| App crashes on link | Check Logcat; null-safe the URI data; confirm the Activity exists |
| onNewIntent() not called | Use launchMode="singleTask" or "singleTop" |

---

[↑ Chapter Index](../)
