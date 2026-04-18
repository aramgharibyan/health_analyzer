import SwiftUI
import AuthenticationServices

private let OAUTH_PLATFORMS = ["whoop", "withings", "fitbod", "yazio", "larq"]

struct IntegrationsView: View {
    @State private var integrations: [Integration] = []
    @State private var isLoading = true
    @State private var busyPlatform: String?
    @State private var errorMessage: String?
    @State private var showAlert = false

    var body: some View {
        NavigationStack {
            ZStack {
                Color.black.ignoresSafeArea()
                if isLoading {
                    ProgressView().tint(.cyan)
                } else {
                    List(integrations) { integration in
                        IntegrationRow(
                            integration: integration,
                            isBusy: busyPlatform == integration.platform,
                            onConnect: { Task { await connect(integration) } },
                            onSync:    { Task { await sync(integration.platform) } },
                            onDisconnect: { Task { await disconnect(integration.platform) } }
                        )
                        .listRowBackground(Color.clear)
                        .listRowSeparator(.hidden)
                    }
                    .listStyle(.plain)
                    .refreshable { await load() }
                }
            }
            .navigationTitle("Integrations")
            .alert("Error", isPresented: $showAlert, presenting: errorMessage) { _ in
                Button("OK", role: .cancel) {}
            } message: { msg in Text(msg) }
        }
        .task { await load() }
    }

    // MARK: - Actions

    private func connect(_ integration: Integration) async {
        busyPlatform = integration.platform

        if integration.platform == "apple_health" {
            await connectAppleHealth()
        } else if OAUTH_PLATFORMS.contains(integration.platform) {
            await connectOAuth(integration.platform)
        }

        busyPlatform = nil
        await load()
    }

    private func connectOAuth(_ platform: String) async {
        do {
            let response = try await APIClient.shared.connectIntegration(platform: platform)
            guard let authURL = URL(string: response.authUrl) else { return }

            // ASWebAuthenticationSession opens system browser and catches the redirect
            let code = try await withCheckedThrowingContinuation { (cont: CheckedContinuation<String, Error>) in
                let session = ASWebAuthenticationSession(
                    url: authURL,
                    callbackURLScheme: "healthanalyzer"
                ) { callbackURL, error in
                    if let error {
                        cont.resume(throwing: error)
                        return
                    }
                    guard let url = callbackURL,
                          let code = URLComponents(url: url, resolvingAgainstBaseURL: false)?
                              .queryItems?.first(where: { $0.name == "code" })?.value
                    else {
                        cont.resume(throwing: APIError.badStatus(0, "No code in callback URL"))
                        return
                    }
                    cont.resume(returning: code)
                }
                session.prefersEphemeralWebBrowserSession = false
                session.presentationContextProvider = WindowProvider.shared
                session.start()
            }

            // Exchange code via backend callback endpoint
            let state = "" // state already validated server-side via user_id
            let _: EmptyResponse = try await APIClient.shared.request(
                "/integrations/\(platform)/callback?code=\(code)&state=\(state)"
            )
        } catch {
            errorMessage = error.localizedDescription
            showAlert = true
        }
    }

    private func connectAppleHealth() async {
        guard HealthKitManager.isAvailable else {
            errorMessage = "Apple Health is not available on this device."
            showAlert = true
            return
        }
        do {
            let result = try await HealthKitManager.shared.syncToBackend(days: 30)
            errorMessage = "Synced \(result.recordsSynced) records from Apple Health."
            showAlert = true
        } catch {
            errorMessage = error.localizedDescription
            showAlert = true
        }
    }

    private func sync(_ platform: String) async {
        busyPlatform = platform
        do { try await APIClient.shared.syncIntegration(platform: platform) }
        catch {
            errorMessage = error.localizedDescription
            showAlert = true
        }
        busyPlatform = nil
        await load()
    }

    private func disconnect(_ platform: String) async {
        busyPlatform = platform
        do { try await APIClient.shared.disconnectIntegration(platform: platform) }
        catch {
            errorMessage = error.localizedDescription
            showAlert = true
        }
        busyPlatform = nil
        await load()
    }

    private func load() async {
        isLoading = integrations.isEmpty
        do { integrations = try await APIClient.shared.integrationStatus() }
        catch {}
        isLoading = false
    }
}

// MARK: - Row

struct IntegrationRow: View {
    let integration: Integration
    let isBusy: Bool
    let onConnect: () -> Void
    let onSync: () -> Void
    let onDisconnect: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                VStack(alignment: .leading, spacing: 3) {
                    Text(integration.name).font(.headline).foregroundStyle(.white)
                    Text(integration.description).font(.caption).foregroundStyle(.secondary)
                }
                Spacer()
                Capsule()
                    .fill(integration.isConnected ? Color.green.opacity(0.2) : Color.gray.opacity(0.2))
                    .frame(width: 80, height: 26)
                    .overlay(
                        Text(integration.isConnected ? "Connected" : "Off")
                            .font(.caption.bold())
                            .foregroundStyle(integration.isConnected ? .green : .gray)
                    )
            }

            if let date = integration.lastSyncedAt {
                Text("Last sync: \(date.asRelativeDate)")
                    .font(.caption2).foregroundStyle(.tertiary)
            }

            if isBusy {
                ProgressView().tint(.cyan)
            } else if integration.isConnected {
                HStack(spacing: 8) {
                    Button("Sync") { onSync() }
                        .buttonStyle(.borderedProminent)
                        .tint(.cyan)
                    Button("Disconnect") { onDisconnect() }
                        .buttonStyle(.bordered)
                        .tint(.red)
                }
            } else {
                Button("Connect \(integration.name)") { onConnect() }
                    .buttonStyle(.borderedProminent)
                    .tint(.cyan)
                    .frame(maxWidth: .infinity)
            }
        }
        .padding()
        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 14))
        .padding(.vertical, 4)
    }
}

// MARK: - ASWebAuthenticationSession presentation context

final class WindowProvider: NSObject, ASWebAuthenticationPresentationContextProviding {
    static let shared = WindowProvider()

    func presentationAnchor(for session: ASWebAuthenticationSession) -> ASPresentationAnchor {
        UIApplication.shared.connectedScenes
            .compactMap { $0 as? UIWindowScene }
            .flatMap { $0.windows }
            .first { $0.isKeyWindow } ?? ASPresentationAnchor()
    }
}

// MARK: - Date helper

private extension String {
    var asRelativeDate: String {
        guard let date = ISO8601DateFormatter().date(from: self) else { return self }
        let fmt = RelativeDateTimeFormatter()
        fmt.unitsStyle = .short
        return fmt.localizedString(for: date, relativeTo: Date())
    }
}
