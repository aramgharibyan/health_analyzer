import Foundation

@MainActor
final class AuthStore: ObservableObject {
    @Published var user: User?
    @Published var isAuthenticated = false

    private let tokenKey = "ha_jwt_token"
    private let userKey  = "ha_user_json"

    init() {
        // Restore session from Keychain on launch
        if let token = Keychain.read(key: tokenKey),
           let json  = Keychain.read(key: userKey),
           let data  = json.data(using: .utf8),
           let user  = try? JSONDecoder().decode(User.self, from: data) {
            self.user = user
            self.isAuthenticated = true
            APIClient.shared.token = token
        }
    }

    func login(email: String, password: String) async throws {
        let response = try await APIClient.shared.login(email: email, password: password)
        persist(token: response.accessToken, user: response.user)
    }

    func register(
        email: String, password: String, fullName: String?,
        age: Int?, heightCm: Double?, weightKg: Double?, gender: String?
    ) async throws {
        let response = try await APIClient.shared.register(
            email: email, password: password, fullName: fullName,
            age: age, heightCm: heightCm, weightKg: weightKg, gender: gender
        )
        persist(token: response.accessToken, user: response.user)
    }

    func updateUser(_ user: User) {
        self.user = user
        if let data = try? JSONEncoder().encode(user),
           let json = String(data: data, encoding: .utf8) {
            Keychain.save(json, for: userKey)
        }
    }

    func logout() {
        Keychain.delete(key: tokenKey)
        Keychain.delete(key: userKey)
        APIClient.shared.token = nil
        user = nil
        isAuthenticated = false
    }

    private func persist(token: String, user: User) {
        APIClient.shared.token = token
        Keychain.save(token, for: tokenKey)
        if let data = try? JSONEncoder().encode(user),
           let json = String(data: data, encoding: .utf8) {
            Keychain.save(json, for: userKey)
        }
        self.user = user
        self.isAuthenticated = true
    }
}
