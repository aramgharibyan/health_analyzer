# Health Analyzer — iOS App Setup

## Requirements

- Mac with Xcode 15 or later
- iPhone running iOS 16 or later (or iOS 16+ Simulator)
- Apple Developer account (free account works for running on personal iPhone)
- Backend running (locally or on Azure)

---

## Step 1 — Create the Xcode project

1. Open Xcode → **Create New Project**
2. Choose **iOS → App**
3. Fill in:
   - **Product Name:** `HealthAnalyzer`
   - **Team:** your Apple ID / team
   - **Bundle Identifier:** `com.yourname.healthanalyzer` (match what's in Info.plist & entitlements)
   - **Interface:** SwiftUI
   - **Language:** Swift
4. Save the project **inside** `mobile-swift/` so it sits alongside the `HealthAnalyzer/` source folder

---

## Step 2 — Add source files to the Xcode project

In Xcode, right-click the `HealthAnalyzer` group in the Project Navigator and choose **Add Files to "HealthAnalyzer"…**

Add all files from `mobile-swift/HealthAnalyzer/`:

```
App/
  HealthAnalyzerApp.swift
  ContentView.swift
Core/
  Models.swift
  KeychainHelper.swift
  AuthStore.swift
  APIClient.swift
  HealthKitManager.swift
  StringExtensions.swift
Views/
  LoginView.swift
  RegisterView.swift
  DashboardView.swift
  IntegrationsView.swift
  LabTestsView.swift
  AIAssistantView.swift
  SettingsView.swift
```

Make sure **"Copy items if needed"** is **unchecked** (files are already in the right place).

---

## Step 3 — Replace generated files

Xcode creates `ContentView.swift` and `<AppName>App.swift` automatically. **Delete** those generated files (move to Trash) and use the ones from this repo.

Also replace the auto-generated `Info.plist` with `mobile-swift/HealthAnalyzer/Info.plist`.

---

## Step 4 — Configure the entitlements

1. Select the project in the Project Navigator → **Signing & Capabilities** tab
2. Click **+ Capability** → add **HealthKit**
3. Click **+ Capability** → add **Keychain Sharing** (add group `com.yourname.healthanalyzer`)
4. Xcode will generate an entitlements file — replace its contents with `HealthAnalyzer.entitlements` from this repo.

---

## Step 5 — Set the API base URL

Open `Core/APIClient.swift` and edit line 5:

```swift
// For local development:
let API_BASE = "http://localhost:8000"

// For production on Azure:
let API_BASE = "https://your-api.azurecontainerapps.io"
```

> **Local development tip:** Your iPhone and Mac must be on the same Wi-Fi. Use your Mac's local IP (e.g. `http://192.168.1.42:8000`) instead of `localhost`.

---

## Step 6 — Enable App Transport Security for local dev (optional)

If hitting an HTTP (non-HTTPS) backend during development, add to `Info.plist`:

```xml
<key>NSAppTransportSecurity</key>
<dict>
    <key>NSAllowsArbitraryLoads</key>
    <true/>
</dict>
```

Remove this before distributing the app.

---

## Step 7 — Run on your iPhone

1. Connect your iPhone via USB
2. In Xcode, select your iPhone from the device picker (top toolbar)
3. Press **⌘R** (Run)
4. First run: on iPhone go to **Settings → General → VPN & Device Management** → trust your developer certificate
5. The app opens — sign in or register

---

## OAuth Deep-link Setup

The `Info.plist` already registers the `healthanalyzer://` URL scheme. When an OAuth provider redirects to `healthanalyzer://oauth/whoop/callback?code=...`, iOS hands it to the app automatically via `ASWebAuthenticationSession` — no extra configuration needed.

---

## Apple HealthKit

- HealthKit is **iOS only** (not available on Simulator with real data, but permissions can be tested)
- On first tap of "Connect Apple Health", iOS shows a permission sheet listing all data types
- After granting, tap **Connect** again to sync the last 30 days to the backend

---

## Troubleshooting

| Problem | Fix |
|---|---|
| "Untrusted Developer" on iPhone | Settings → General → VPN & Device Management → trust |
| HealthKit not available | Only works on physical iPhone, not iPad or Mac |
| Network error on local dev | Use Mac's LAN IP, not `localhost`; check backend is running |
| OAuth redirect not captured | Ensure `CFBundleURLSchemes` contains `healthanalyzer` in Info.plist |
| Build error: missing type | Make sure all `.swift` files are added to the Xcode target (check Target Membership in File Inspector) |
