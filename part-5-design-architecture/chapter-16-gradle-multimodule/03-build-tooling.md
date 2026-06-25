---
layout: default
title: "Chapter 16: Gradle & Multi-Module Architecture — Build Tooling"
parent: "Chapter 16: Gradle & Multi-Module Architecture"
nav_order: 3
---

## Version Catalogs — the libs.versions.toml

You may have noticed every dependency above written as **libs.something**. That **libs** comes from a **version catalog**: a single TOML file, **gradle/libs.versions.toml**, that declares every dependency and its version in one place. Without it, each module's build script hard-codes version strings, and keeping a dozen modules on the same version of Compose or Coroutines becomes manual and error-prone. The catalog centralises that, and Gradle generates a type-safe **libs** accessor from it — so you get autocomplete and a compile error on a typo, instead of a string that silently fails to resolve.

### The three sections

A catalog has three tables. **[versions]** defines named version numbers. **[libraries]** defines dependencies, each referencing a version (by **version.ref**) or pinning one directly. **[plugins]** defines Gradle plugins the same way. A fourth optional table, **[bundles]**, groups libraries that are always used together so they can be added in one line.

*gradle/libs.versions.toml*

```kotlin
[versions]
compileSdk = "34"
minSdk = "24"
kotlin = "1.9.22"
coroutines = "1.8.0"
composeBom = "2024.02.00"

[libraries]
# group:name, with the version pulled from [versions] via version.ref
androidx-core-ktx = { group = "androidx.core", name = "core-ktx", version.ref = "coreKtx" }
kotlinx-coroutines-android = { module = "org.jetbrains.kotlinx:kotlinx-coroutines-android", version.ref = "coroutines" }
compose-bom = { module = "androidx.compose:compose-bom", version.ref = "composeBom" }
# a BOM-managed library needs no version of its own:
compose-ui = { module = "androidx.compose.ui:ui" }
mockk = { module = "io.mockk:mockk", version = "1.13.10" }  # pinned directly

[plugins]
android-library = { id = "com.android.library", version.ref = "agp" }
kotlin-android = { id = "org.jetbrains.kotlin.android", version.ref = "kotlin" }

[bundles]
# libraries that travel together, added as one dependency
compose = ["compose-ui", "compose-ui-graphics", "compose-material3"]
```

### How names map to the libs accessor

Gradle converts each catalog entry into a nested accessor, turning the dash- (or dot-) separated name into dots: **androidx-core-ktx** becomes **libs.androidx.core.ktx**, **kotlinx-coroutines-android** becomes **libs.kotlinx.coroutines.android**, a bundle is **libs.bundles.compose**, and a plugin is **libs.plugins.android.library**. This is exactly the **libs.androidx.core.ktx** form used throughout this chapter.

*Consuming the catalog in a build script*

```kotlin
plugins {
    alias(libs.plugins.android.library)      // from [plugins]
    alias(libs.plugins.kotlin.android)
}
dependencies {
    implementation(libs.androidx.core.ktx)            // a single library
    implementation(libs.kotlinx.coroutines.android)
    implementation(platform(libs.compose.bom))        // a BOM
    implementation(libs.bundles.compose)              // a whole bundle
    testImplementation(libs.mockk)
}
```

> **Key Insight:**
>
> Catalog best practices: keep *all* versions in **[versions]** (never inline a number in a build script); share one **version.ref** across libraries that must move together (all Compose artifacts, all Coroutines artifacts) so they can never drift apart; use a **BOM** (bill of materials) plus version-less entries for families like Compose so the BOM dictates versions; and group always-together libraries into a **[bundles]** entry to shrink build scripts. One file becomes the single source of truth for the whole project's dependencies.

## Convention Plugins — Sharing Build Logic

The version catalog removes duplicated *version numbers*, but it does not remove duplicated *build logic*. In a multi-module app, every Android library module needs the same plugins applied, the same compile/min SDK, the same Java/Kotlin version, the same baseline dependencies (Compose, Coroutines, the test stack). Copying that block into twenty **build.gradle.kts** files means twenty places to update when anything changes. A **convention plugin** is the fix: a custom Gradle plugin, written once in a dedicated **build-logic** module, that encapsulates a module's conventions. Each real module then applies a single plugin instead of repeating the configuration.

### A convention plugin, written plainly

A convention plugin implements **Plugin<Project>** and, in **apply()**, does what you would otherwise write in a build script: apply the needed plugins, configure the Android and Kotlin options, and declare the baseline dependencies. Written directly against the raw Gradle API it is correct but verbose — dependencies are added by calling **add("implementation", …)** with a string configuration name, repeated for every dependency and every configuration (implementation, testImplementation, and so on).

*A convention plugin using the raw API (verbose)*

```kotlin
class AndroidLibraryConventionPlugin : Plugin<Project> {
    override fun apply(target: Project) = with(target) {
        // 1. apply the plugins every library module needs
        with(pluginManager) {
            apply("com.android.library")
            apply("org.jetbrains.kotlin.android")
            apply("org.jetbrains.kotlin.plugin.compose")
        }

        // 2. configure the Android/Kotlin options once (see next section)
        extensions.configure<LibraryExtension> { configureKotlinAndroid(this) }

        // 3. declare the baseline dependencies -- raw API: add(config, dep)
        dependencies {
            add("implementation", libs.findLibrary("androidx-core-ktx").get())
            add("implementation", libs.findLibrary("kotlinx-coroutines-android").get())
            add("testImplementation", libs.findLibrary("mockk").get())
            add("testImplementation", libs.findLibrary("junit-jupiter-api").get())
            add("androidTestImplementation", libs.findLibrary("androidx-espresso-core").get())
            add("debugImplementation", libs.findLibrary("androidx-ui-tooling").get())
        }
    }
}
```

Any module that applies this one plugin inherits the full setup. The build script of a feature module shrinks to almost nothing:

*A module's build.gradle.kts after the convention plugin*

```kotlin
plugins {
    id("io.lb.android.library")   // the convention plugin -- that's it
}
// no SDK versions, no Kotlin options, no baseline dependencies repeated here
android { namespace = "com.example.feature.profile" }
dependencies {
    implementation(project(":core:domain"))   // only this module's extras
}
```

### Optimising readability with extension functions

The repeated **add("implementation", …)** calls are noisy. Because Kotlin lets you add **extension functions** (Part I), you can give the **DependencyHandlerScope** the same fluent verbs a normal build script has — each a one-line wrapper over **add** — so the plugin reads like an ordinary dependencies block.

*Extension functions that wrap the raw add() calls*

```kotlin
fun DependencyHandlerScope.implementation(dep: Provider<MinimalExternalModuleDependency>) {
    add("implementation", dep)
}
fun DependencyHandlerScope.testImplementation(dep: Provider<MinimalExternalModuleDependency>) {
    add("testImplementation", dep)
}
fun DependencyHandlerScope.androidTestImplementation(dep: Provider<MinimalExternalModuleDependency>) {
    add("androidTestImplementation", dep)
}
fun DependencyHandlerScope.debugImplementation(dep: Provider<MinimalExternalModuleDependency>) {
    add("debugImplementation", dep)
}
```

With those in scope, the dependencies block of the plugin becomes as readable as a normal build script — the raw **add** calls disappear behind named verbs, and the catalog entries read fluently as **libs.androidx.core.ktx**:

*The same plugin, now reading like a build script*

```kotlin
class AndroidLibraryConventionPlugin : Plugin<Project> {
    override fun apply(target: Project) = with(target) {
        with(pluginManager) {
            apply("com.android.library")
            apply("org.jetbrains.kotlin.android")
            apply("org.jetbrains.kotlin.plugin.compose")
        }
        extensions.configure<LibraryExtension> { configureKotlinAndroid(this) }

        dependencies {
            with(libs) {
                implementation(androidx.core.ktx)
                implementation(platform(androidx.compose.bom))
                implementation(androidx.material3)
                implementation(kotlinx.coroutines.android)
                testImplementation(mockk)
                testImplementation(junit.jupiter.api)
                testImplementation(kotlinx.coroutines.test)
                androidTestImplementation(androidx.espresso.core)
                debugImplementation(androidx.ui.tooling.compose)
            }
        }
    }
}
```

### Sharing configuration logic too

The same idea applies to configuration, not just dependencies. The Android/Kotlin setup a convention plugin needs — SDK levels, Java version, compiler opt-ins, test framework — is extracted into a shared helper function so every plugin variant (library, application, JVM-only) calls the same code. Notice **versionOf("compileSdk")** reading from the catalog, and the single **COMPILE_VERSION** constant so the Java version is defined once.

*Shared configuration helper, reused by every convention plugin*

```kotlin
val COMPILE_VERSION = JavaVersion.VERSION_17

internal fun Project.configureKotlinAndroid(
    commonExtension: CommonExtension<*, *, *, *, *, *>
) {
    commonExtension.apply {
        compileSdk = versionOf("compileSdk")     // read from the catalog
        defaultConfig {
            minSdk = versionOf("minSdk")
            testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        }
        compileOptions {
            sourceCompatibility = COMPILE_VERSION   // one Java version, defined once
            targetCompatibility = COMPILE_VERSION
        }
    }
    configureKotlin()
}

private fun Project.configureKotlin() {
    tasks.withType<KotlinCompile>().configureEach {
        compilerOptions {
            jvmTarget.set(JvmTarget.fromTarget(COMPILE_VERSION.toString()))
            freeCompilerArgs.addAll("-opt-in=kotlin.RequiresOptIn")
        }
    }
    tasks.withType<Test> { useJUnitPlatform() }    // JUnit 5 for every module
}
```

> **Interview Tip:**
>
> The payoff scales with the project: change the compile SDK, the Java version, or the baseline test stack in **one** place — the convention plugin — and every module that applies it picks up the change. Combined with the version catalog (versions in one file, build logic in one plugin), a large multi-module project stays consistent with almost no per-module boilerplate. This is the same DRY and single-source-of-truth thinking from the architecture chapters, applied to the build itself.

## The Module Dependency Graph

Modules form a **directed acyclic graph** (DAG): dependencies point in one direction and cycles are forbidden — Gradle rejects a build where module A depends on B and B depends on A. This constraint is healthy: it forces you to think about direction, and it mirrors the dependency rule of Clean Architecture (covered in the Architecture chapter). The stable, shared code sits at the bottom of the graph with no outgoing dependencies; volatile feature code sits at the top, depending downward only.

- **:app** sits at the top — it depends on features but nothing depends on it.
- **:core:domain** sits at the bottom — pure Kotlin, depends on nothing, everything depends on it.
- A cycle between modules is a design smell and a hard build error; break it by extracting the shared piece into a lower module both can depend on.
- Keep the **app** module thin: its job is to wire modules together and host navigation, not to contain feature logic.

---

← [Previous: Cohesion & Dependencies](../02-cohesion-dependencies/) · [↑ Chapter Index](../)
