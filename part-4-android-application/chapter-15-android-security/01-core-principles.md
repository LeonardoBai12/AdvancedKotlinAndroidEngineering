---
layout: page
title: "Chapter 15: Android Security"
---

*Five pragmatic practices, secure storage, networking, crypto, and OWASP*

Security is not a feature you bolt on at the end — it is a fundamental architectural concern from day one, and every line of code that touches user data, network requests, or sensitive operations is a potential attack surface. The most important thing to internalise first: security is not a feature, not a set of features, and not something you hire someone to configure once and then it is 'done'. Above all, security is a **culture** — not clicking suspicious emails or links, enabling multi-factor authentication on important accounts, and never committing a database password to GitHub. The last word on security belongs to a security specialist, but security itself is everyone's responsibility, and a developer who cares about it ships safer software.

This chapter is organised around five pragmatic practices drawn directly from The Pragmatic Programmer — minimise the attack surface, least privilege, secure defaults, encrypt sensitive data, and patch fast — each adapted to the realities of Android development. We then cover Android's concrete storage, networking, and cryptography mechanisms, and close with the OWASP Mobile Top 10.

## Core Security Principles

| Principle | Description |
| --- | --- |
| Minimize Attack Surface | Reduce code complexity, public endpoints, and exposed data |
| Least Privilege | Every service, user, and endpoint gets only the permissions it needs |
| Secure Defaults | The default state is the safe state |
| Encrypt Sensitive Data | Never store or transmit sensitive data in plaintext |
| Patch Fast | Apply security updates as quickly as possible |
| Defense in Depth | Multiple independent layers — no single point of failure |
| Zero Trust | Verify everything; trust nothing, not even internal services |

## Practice 1 — Minimize the Attack Surface

The attack surface is the total contact area between your software and the world: how much code exists, how many parts there are, how those parts touch each other, and how much of that touches reality. A million lines of code is a million lines where a bug, an exploit, or a vulnerability can live. Every user input, every public endpoint, every service-to-service call, and — surprisingly — every output is part of that surface. The first and arguably most important security practice is to keep that surface as small as possible.

### User input is always a potential vector

Anything a user sends you may carry a vulnerability — a name, an email, a password, an uploaded file. The canonical example is the XKCD 'Bobby Tables' comic: a school enters a new student whose name is literally **Robert'); DROP TABLE Students;--**. If that input is concatenated straight into a SQL statement without sanitisation, it executes and wipes the table. That is SQL injection. Treat everything the user sends as suspect and sanitise it before use. On Android the equivalents are Room queries, deep-link URIs, and WebView inputs — all covered later in this chapter.

### Unauthenticated endpoints and public URLs

Your backend exposes an API consumed by the app, and every endpoint that does not require authentication is a possible attack vector — a bot can spam it for a DDoS, scan it for available data, or probe it for an exploit. Expose the minimum number of public endpoints. The same caution applies to public storage URLs. A common mistake is making an S3 object publicly readable behind a 'random' UUID and assuming nobody will guess it. But URLs are not treated as secrets the way passwords are: your browser does not protect a URL the way it protects a password. URLs end up in browser history, router logs, and caches all over the internet. A storage bucket holding sensitive documents needs real authentication, not an unguessable URL.

> **Warning:**
>
> Sequential IDs in URLs are an enumeration vulnerability. If **/api/images/123** returns an image, an attacker simply increments: 124, 125, 126… and scrapes every image in the service. Never rely on the obscurity of an identifier in a URL for access control — authenticate and authorise the request itself.

### Outputs are vectors too — including timing

Inputs are obvious vectors; outputs are the ones people forget. Logging sensitive data — passwords, tokens, personal information — to Logcat, analytics, or a server log turns that log into a vulnerability. Even subtler: a response's *timing* can leak information. The classic example is a naive password check that compares character by character and returns as soon as a character mismatches. Suppose the real password starts with 'g'. An attacker tries 'aaaa', 'baaa', … and measures the response time of each. The guesses that fail on the first character return fastest; the moment a guess starts with the correct first character, the check proceeds to the second character and takes measurably longer. By following the slowest response the attacker recovers the password one character at a time, turning an astronomically large search (26 × 26 × 26 …) into a tiny linear one (26 + 26 + 26 …). The defence is a **constant-time comparison** that always examines every character regardless of where the first mismatch occurs.

## Practice 2 — Least Privilege

A service should have exactly the privileges it needs to do its job — nothing more. This applies not only to services but to employees and to anyone interacting with the company's API: everyone gets the minimum privilege required for their task. The payoff is damage containment. Imagine an old, vulnerable backend whose SSH key leaks. If that backend has read-only access to the database, the attacker can read but cannot modify or destroy data — the blast radius is limited. Least privilege does not prevent every breach, but it makes every breach less bad.

On the infrastructure side, your database should live inside a VPC with no path to it from outside. The frontend should never reach the database directly; someone outside the VPC should not be able to connect to it at all. When a developer genuinely needs database access — to run migrations on an older system, say — route it through a bastion host (a small EC2 instance inside the VPC) over SSH, rather than exposing the database endpoint and its credentials to the outside world.

On Android, least privilege manifests as the permissions your app requests. Request only the permissions a feature actually needs, request them at the moment of use rather than all at launch, and prefer scoped alternatives (the Photo Picker over broad storage access, approximate over precise location when precise is not required). Every permission you hold is a privilege an attacker inherits if your app is compromised.

## Practice 3 — Secure Defaults

A secure default is the safe choice the system makes automatically, before the user does anything. A password field masks its characters by default and offers an optional reveal (the eye icon) — the default is safe, the reveal is opt-in. Deleting a cloud server does not happen on a single click; the console forces you to type a confirmation phrase first, protecting you from an accidental destructive action. Showing a password and deleting a server are both potentially destructive, so the default guards against them.

Onboarding is another place defaults matter: a well-run company requires a new hire to change their default password and enable 2FA within the first week. If the company does not force 2FA, the default is less secure than it could be — the default should be the secure path, even when it is mildly inconvenient. On Android, design your app the same way: biometric lock on by default for sensitive screens, analytics opt-in rather than opt-out, the most private sharing option pre-selected.

## Practice 4 — Encrypt Sensitive Data

Sensitive data — banking details, personal information, tokens — must be encrypted at rest, using established cryptographic standards and hashing where appropriate. The cardinal rule: never invent your own cryptography. Use the platform's vetted primitives. On Android that means the storage hierarchy, the Keystore, and AES-GCM, all covered in the sections that follow.

## Practice 5 — Patch Fast (and Scan Continuously)

Apply security updates as quickly as possible. You want tooling that tells you when a dependency you use has a known vulnerability. GitHub's **Dependabot** does this — it will flag, for example, that the version of a library you just committed has a known CVE and tell you which version to upgrade to. A complementary tool is a **SAST** (Static Application Security Testing) scanner such as SonarQube, which performs static analysis of your code and warns when, say, you execute something derived from client input (a possible SQL injection) or leave code open to XSS. SAST does not solve security on its own — you typically pair it with a web application firewall — but it raises the floor. Remember: security is a culture, not a single tool.

## Secrets Management — Never Commit Credentials

This deserves its own treatment because it is the practice most often violated. Database passwords, API keys, and any secret must **never** be committed to your codebase — ever. If you have committed a secret, change it immediately and treat it as compromised, even if the repository is private; Git history is permanent and a private repo is not protection.

How, then, does your app reach the values it needs? Locally, you keep a **.env** file (paired with a committed **.env.example** that contains only placeholder values) holding non-production credentials, and your **.gitignore** ensures the real file is never committed. For deployed builds, a dedicated secrets tool injects the values at runtime: GitHub Secrets injects environment variables when your app is deployed, and AWS Secrets Manager does the same on AWS. A valuable property of these tools is that once a secret is stored you can modify it but can no longer read it back — it is write-only from the UI, which is excellent for security.

On Android specifically, the equivalent pattern uses Gradle. Public configuration that may vary between builds (base URLs, public keys) goes in committed Gradle properties and is surfaced through **BuildConfig**. Real secrets go in **local.properties** (which is git-ignored) for local builds, and are injected from CI/CD environment variables for release builds.

| Data type | Storage location | Access in code |
| --- | --- | --- |
| Public API URLs | gradle.properties (committed) | BuildConfig.BASE_URL |
| Public API keys | gradle.properties (committed) | BuildConfig.API_KEY |
| Secret keys | local.properties (git-ignored) | BuildConfig.SECRET |
| Sensitive runtime config | Remote config | RemoteConfig.get() |
| User tokens | Encrypted DataStore | dataStore.data |

*BuildConfig + local.properties + CI/CD*

```kotlin
// gradle.properties (committed)
BASE_URL_PROD=https://api.production.com

// local.properties (git-ignored)
SECRET_API_KEY=sk_live_1234567890abcdef

// build.gradle.kts
android {
    defaultConfig {
        buildConfigField("String", "BASE_URL", "\"$BASE_URL_PROD\"")
    }
    buildTypes {
        debug {
            val props = Properties().apply {
                load(rootProject.file("local.properties").inputStream())
            }
            buildConfigField("String", "SECRET_KEY",
                "\"${props.getProperty("SECRET_API_KEY")}\"")
        }
        release {
            // CI/CD injects from the environment -- never hard-coded
            buildConfigField("String", "SECRET_KEY",
                "\"${System.getenv("SECRET_KEY")}\"")
        }
    }
}
```

> **Avoid:**
>
> A cautionary tale (purely fictional, of course): a company hard-coded its database password — first in a committed .env, then directly in the source in many places, and in the worst version the credentials lived in the *frontend*, which queried the database straight from the user's browser. The lesson stands regardless of the storyteller: credentials in client code are always visible to the client. The Android parallel is hard-coding an API secret in the APK — anyone can decompile it. Secrets that the client must not see belong on a backend the client calls, never in the client itself.

---

[↑ Chapter Index](../) · [Next: Data & Network Security →](../02-data-network-security/)
