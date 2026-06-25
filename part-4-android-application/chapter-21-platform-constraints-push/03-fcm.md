---
layout: default
title: Fcm
parent: "Platform Constraints & Push"
nav_order: 3
---

## Section 3 · Firebase Cloud Messaging

*Server-to-device push — token management, message types, Doze bypass, and handling messages in all app states*

---

## What FCM Is

**Firebase Cloud Messaging (FCM)** is Google's cross-platform messaging solution for delivering push notifications and data payloads from a server to Android devices. FCM maintains a persistent connection between the device and Google's infrastructure — your server sends a message to FCM, and FCM delivers it to the target device or devices.

FCM is the standard push mechanism for Android. It is also the only reliable way to wake an app from Doze using a **high-priority message**, because the FCM connection is maintained by Google Play Services outside your app's process.

*Firebase Docs — Firebase Cloud Messaging*

---

## Dependency

```kotlin
// build.gradle.kts (app)
dependencies {
    implementation(platform("com.google.firebase:firebase-bom:33.0.0"))
    implementation("com.google.firebase:firebase-messaging-ktx")
}
```

The Firebase BOM manages all Firebase library versions consistently — you do not specify individual versions when using the BOM.

---

## Registration Token

Every app installation on every device has a unique **FCM registration token**. Your server needs this token to address messages to a specific device. Tokens can change (app re-install, app data cleared, Play Services update), so your app must handle token refresh events.

### Getting the Initial Token

```kotlin
FirebaseMessaging.getInstance().token.addOnCompleteListener { task ->
    if (!task.isSuccessful) {
        Log.w(TAG, "Failed to get FCM token", task.exception)
        return@addOnCompleteListener
    }
    val token = task.result
    sendTokenToServer(token)   // register with your backend
}
```

### Listening for Token Refresh

Override `onNewToken` in your `FirebaseMessagingService`:

```kotlin
class MyFirebaseMessagingService : FirebaseMessagingService() {

    override fun onNewToken(token: String) {
        super.onNewToken(token)
        // Token has changed — update your server immediately
        // This fires on: fresh install, app re-install, app data cleared,
        //                Play Services update, device restore
        sendTokenToServer(token)
    }
}
```

```xml
<!-- AndroidManifest.xml -->
<service
    android:name=".MyFirebaseMessagingService"
    android:exported="false">
    <intent-filter>
        <action android:name="com.google.firebase.MESSAGING_EVENT" />
    </intent-filter>
</service>
```

### Token Lifecycle Events

| Event | Result |
| --- | --- |
| First app install | New token generated |
| App re-installed | New token generated |
| App data cleared by user | New token generated |
| Play Services updated | Possible token refresh |
| App restored from backup on new device | New token generated |
| User changes device | New token generated |

Your backend must handle stale tokens (HTTP 404 from FCM send API → delete that token from your database).

---

## Message Types

FCM messages fall into two categories with fundamentally different delivery and handling behaviour.

### Notification Messages

The FCM server sends a `notification` payload. When the **app is in the background or killed**, the FCM SDK itself displays the notification — your code does not run at all. When the **app is in the foreground**, your `onMessageReceived` is called and you decide how to display it.

```json
{
  "message": {
    "token": "device_registration_token",
    "notification": {
      "title": "New message",
      "body": "Alice sent you a message"
    }
  }
}
```

### Data Messages

The FCM server sends a `data` payload only. **Your `onMessageReceived` is always called**, regardless of whether the app is foreground, background, or killed. You are fully responsible for displaying a notification (if desired) and processing the data.

```json
{
  "message": {
    "token": "device_registration_token",
    "data": {
      "type": "new_order",
      "order_id": "12345",
      "amount": "59.99"
    }
  }
}
```

### Combined Messages

A message can have both `notification` and `data` payloads. Background/killed behaviour follows the `notification` payload (FCM displays it); foreground behaviour calls `onMessageReceived` with both payloads in the `remoteMessage`.

```json
{
  "message": {
    "token": "device_registration_token",
    "notification": {
      "title": "Order confirmed",
      "body": "Your order #12345 has been confirmed"
    },
    "data": {
      "order_id": "12345",
      "deep_link": "myapp://orders/12345"
    }
  }
}
```

### Summary Table

| App state | Notification message | Data message | Combined |
| --- | --- | --- | --- |
| **Foreground** | `onMessageReceived` | `onMessageReceived` | `onMessageReceived` |
| **Background** | FCM SDK shows notification; tap opens app | `onMessageReceived` | FCM SDK shows notification; `onMessageReceived` for data |
| **Killed** | FCM SDK shows notification; tap opens app | `onMessageReceived` | FCM SDK shows notification; data in Intent extras on tap |

*Firebase Docs — Receive messages in an Android app*

---

## Handling Messages in `FirebaseMessagingService`

```kotlin
class MyFirebaseMessagingService : FirebaseMessagingService() {

    override fun onMessageReceived(remoteMessage: RemoteMessage) {
        super.onMessageReceived(remoteMessage)

        // Data payload — always available, process first
        val data = remoteMessage.data
        val type = data["type"]
        val orderId = data["order_id"]

        // Notification payload — present only for notification/combined messages
        remoteMessage.notification?.let { notification ->
            val title = notification.title
            val body = notification.body
        }

        when (type) {
            "new_order"   -> handleNewOrder(orderId)
            "chat_message" -> handleChatMessage(data)
            "promo"       -> showPromotionalNotification(remoteMessage)
            else          -> showGenericNotification(remoteMessage)
        }
    }

    private fun handleNewOrder(orderId: String?) {
        orderId ?: return
        // Option A: process immediately in a coroutine
        CoroutineScope(Dispatchers.IO).launch {
            orderRepository.syncOrder(orderId)
        }

        // Option B: enqueue durable work via WorkManager
        WorkManager.getInstance(applicationContext)
            .enqueue(
                OneTimeWorkRequestBuilder<OrderSyncWorker>()
                    .setInputData(workDataOf("order_id" to orderId))
                    .build()
            )
    }

    private fun showGenericNotification(remoteMessage: RemoteMessage) {
        val notification = remoteMessage.notification ?: return

        val notif = NotificationCompat.Builder(this, GENERAL_CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_notification)
            .setContentTitle(notification.title)
            .setContentText(notification.body)
            .setPriority(NotificationCompat.PRIORITY_DEFAULT)
            .setAutoCancel(true)
            .build()

        NotificationManagerCompat.from(this)
            .notify(System.currentTimeMillis().toInt(), notif)
    }

    override fun onNewToken(token: String) {
        sendTokenToServer(token)
    }
}
```

---

## Message Priority — Normal vs High

FCM messages have two priority levels that directly control Doze behaviour:

| Priority | FCM JSON field | Android behaviour |
| --- | --- | --- |
| `normal` (default) | `"priority": "normal"` | Delivered when device exits Doze; batched for efficiency |
| `high` | `"priority": "high"` | Wakes the device from Doze immediately; `onMessageReceived` fires right away |

High-priority messages are how FCM pierces Doze Mode. They are the correct solution for incoming calls (VoIP), urgent alerts, and any scenario that cannot tolerate a maintenance-window delay.

```json
{
  "message": {
    "token": "device_token",
    "android": {
      "priority": "HIGH"
    },
    "data": {
      "type": "incoming_call",
      "caller": "Alice"
    }
  }
}
```

> **Abuse warning:** Google monitors high-priority usage. Apps that send high-priority messages for non-urgent content (marketing, general chat) will have their priority silently downgraded by Google. Reserve high-priority for content that is genuinely time-critical.

---

## Notification Channel Override

FCM can specify which notification channel to use for background notification messages. Set `android.notification.channel_id` in the message payload — if the channel does not exist on the device, FCM falls back to the app's default channel.

```json
{
  "message": {
    "token": "device_token",
    "android": {
      "notification": {
        "channel_id": "alerts_channel",
        "title": "Payment failed",
        "body": "Your payment for order #12345 failed"
      }
    }
  }
}
```

---

## Extracting Data from a Notification Tap (Background)

When the app is killed and a notification-type message is shown by the FCM SDK, tapping the notification opens the launcher Activity. The data payload is delivered via the `Intent` extras:

```kotlin
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Check if launched from an FCM notification tap
        intent.extras?.let { extras ->
            val orderId = extras.getString("order_id")
            val deepLink = extras.getString("deep_link")
            if (orderId != null) {
                navigateToOrder(orderId)
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        // Handle if Activity is already running (single-top / singleTask)
        intent.extras?.getString("order_id")?.let { navigateToOrder(it) }
    }
}
```

Set a `click_action` in the notification payload to route the tap to a specific Activity:

```json
{
  "notification": {
    "click_action": "OPEN_ORDER_ACTIVITY"
  }
}
```

```xml
<!-- AndroidManifest.xml — declare the intent filter on the target Activity -->
<activity android:name=".OrderActivity">
    <intent-filter>
        <action android:name="OPEN_ORDER_ACTIVITY" />
        <category android:name="android.intent.category.DEFAULT" />
    </intent-filter>
</activity>
```

---

## Topic Messaging

Subscribe devices to topics to send messages to multiple devices without managing token lists yourself:

```kotlin
// Subscribe
FirebaseMessaging.getInstance().subscribeToTopic("breaking_news")
    .addOnCompleteListener { task ->
        if (task.isSuccessful) Log.d(TAG, "Subscribed to breaking_news")
    }

// Unsubscribe
FirebaseMessaging.getInstance().unsubscribeFromTopic("breaking_news")
```

```json
{
  "message": {
    "topic": "breaking_news",
    "notification": {
      "title": "Breaking: Major earthquake detected",
      "body": "A 7.2 magnitude earthquake has been detected in…"
    }
  }
}
```

---

## Token Management — Server Side

Your server must:

1. Store the token on first registration and on every `onNewToken` update
2. Handle HTTP 404 responses from the FCM Send API (invalid token) by deleting that token from your database
3. Handle HTTP 400 `INVALID_ARGUMENT` / `UNREGISTERED` errors similarly

```kotlin
// Example server-side logic (Kotlin/Ktor backend)
suspend fun sendNotification(token: String, payload: NotificationPayload) {
    val response = fcmClient.send(token, payload)
    if (response.statusCode == 404) {
        // Token is invalid — device uninstalled the app or cleared data
        tokenRepository.delete(token)
    }
}
```

---

## FCM in the Background Execution Stack

FCM is not a background execution mechanism — it is a **wake-up signal**. The pattern is:

```
Server sends high-priority FCM data message
    │
    ▼
Device wakes from Doze (high-priority bypasses it)
    │
    ▼
onMessageReceived() fires in your FirebaseMessagingService
    │
    ├─ Short work → CoroutineScope(Dispatchers.IO).launch { }
    │
    └─ Durable work → WorkManager.enqueue(OneTimeWorkRequestBuilder<MyWorker>().build())
```

`onMessageReceived` has approximately **10 seconds** to complete its work on older versions (before the process may be killed). For anything longer, hand off to WorkManager immediately.

---

## Testing FCM Locally

### Firebase Console

Use the Firebase Console → Cloud Messaging → Send Test Message to send a single message to a specific registration token. This is the fastest way to test `onMessageReceived` and notification appearance.

### fcm-push CLI / cURL

```bash
curl -X POST \
  https://fcm.googleapis.com/v1/projects/YOUR_PROJECT_ID/messages:send \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  -d '{
    "message": {
      "token": "DEVICE_REGISTRATION_TOKEN",
      "data": { "type": "test", "value": "hello" },
      "android": { "priority": "HIGH" }
    }
  }'
```

### Emulator Support

FCM works on Android emulators that have the Play Store image (Google APIs). Standard AOSP emulators do not have Play Services and will not receive FCM messages.

---

← [Previous: AlarmManager](../02-alarm-manager/) · [↑ Chapter Index](../) · [Next: Background Limits History →](../04-background-limits-history/)
