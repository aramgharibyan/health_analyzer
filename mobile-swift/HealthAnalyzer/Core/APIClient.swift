import Foundation

// Edit this URL to point at your server.
// Local dev (same Wi-Fi): "http://192.168.1.X:8000"
// Production: "https://your-app.azurecontainerapps.io"
let API_BASE = "http://localhost:8000"

enum APIError: LocalizedError {
    case badStatus(Int, String)
    case decodingError(Error)
    case network(Error)

    var errorDescription: String? {
        switch self {
        case .badStatus(_, let msg): return msg
        case .decodingError(let e): return "Decode error: \(e)"
        case .network(let e):       return e.localizedDescription
        }
    }
}

final class APIClient {
    static let shared = APIClient()
    var token: String?

    private let decoder: JSONDecoder = {
        let d = JSONDecoder()
        // Backend uses snake_case; decoder converts automatically
        d.keyDecodingStrategy = .convertFromSnakeCase
        return d
    }()

    private let encoder: JSONEncoder = {
        let e = JSONEncoder()
        e.keyEncodingStrategy = .convertToSnakeCase
        return e
    }()

    // MARK: - Core request

    func request<T: Decodable>(
        _ path: String,
        method: String = "GET",
        body: Data? = nil,
        contentType: String = "application/json"
    ) async throws -> T {
        guard let url = URL(string: "\(API_BASE)/api\(path)") else {
            throw URLError(.badURL)
        }
        var req = URLRequest(url: url)
        req.httpMethod = method
        req.setValue(contentType, forHTTPHeaderField: "Content-Type")
        if let token { req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization") }
        req.httpBody = body

        let (data, resp) = try await URLSession.shared.data(for: req)
        let code = (resp as? HTTPURLResponse)?.statusCode ?? 0

        if code == 401 { throw APIError.badStatus(401, "Unauthorised — please log in again.") }
        guard (200..<300).contains(code) else {
            let msg = (try? JSONSerialization.jsonObject(with: data) as? [String: Any])?["detail"] as? String
                      ?? HTTPURLResponse.localizedString(forStatusCode: code)
            throw APIError.badStatus(code, msg)
        }
        do { return try decoder.decode(T.self, from: data) }
        catch { throw APIError.decodingError(error) }
    }

    // Multipart upload — returns decoded response
    func upload<T: Decodable>(
        _ path: String,
        fields: [String: String],
        fileField: String,
        fileName: String,
        mimeType: String,
        fileData: Data
    ) async throws -> T {
        guard let url = URL(string: "\(API_BASE)/api\(path)") else { throw URLError(.badURL) }
        let boundary = "Boundary-\(UUID().uuidString)"
        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
        if let token { req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization") }

        var body = Data()
        for (key, value) in fields {
            body.append("--\(boundary)\r\nContent-Disposition: form-data; name=\"\(key)\"\r\n\r\n\(value)\r\n".utf8)
        }
        body.append("--\(boundary)\r\nContent-Disposition: form-data; name=\"\(fileField)\"; filename=\"\(fileName)\"\r\nContent-Type: \(mimeType)\r\n\r\n".utf8)
        body.append(fileData)
        body.append("\r\n--\(boundary)--\r\n".utf8)
        req.httpBody = body

        let (data, resp) = try await URLSession.shared.data(for: req)
        let code = (resp as? HTTPURLResponse)?.statusCode ?? 0
        guard (200..<300).contains(code) else {
            let msg = (try? JSONSerialization.jsonObject(with: data) as? [String: Any])?["detail"] as? String ?? "Upload failed"
            throw APIError.badStatus(code, msg)
        }
        do { return try decoder.decode(T.self, from: data) }
        catch { throw APIError.decodingError(error) }
    }

    // MARK: - Auth

    func login(email: String, password: String) async throws -> AuthResponse {
        // Login uses form-urlencoded
        guard let url = URL(string: "\(API_BASE)/api/auth/login") else { throw URLError(.badURL) }
        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.setValue("application/x-www-form-urlencoded", forHTTPHeaderField: "Content-Type")
        req.httpBody = "username=\(email.urlEncoded)&password=\(password.urlEncoded)".data(using: .utf8)

        let (data, resp) = try await URLSession.shared.data(for: req)
        let code = (resp as? HTTPURLResponse)?.statusCode ?? 0
        guard (200..<300).contains(code) else {
            let msg = (try? JSONSerialization.jsonObject(with: data) as? [String: Any])?["detail"] as? String ?? "Login failed"
            throw APIError.badStatus(code, msg)
        }
        do { return try decoder.decode(AuthResponse.self, from: data) }
        catch { throw APIError.decodingError(error) }
    }

    func register(
        email: String, password: String, fullName: String?,
        age: Int?, heightCm: Double?, weightKg: Double?, gender: String?
    ) async throws -> AuthResponse {
        var body: [String: Any] = ["email": email, "password": password]
        if let v = fullName  { body["full_name"]  = v }
        if let v = age       { body["age"]        = v }
        if let v = heightCm  { body["height_cm"]  = v }
        if let v = weightKg  { body["weight_kg"]  = v }
        if let v = gender    { body["gender"]      = v }
        let data = try JSONSerialization.data(withJSONObject: body)
        return try await request("/auth/register", method: "POST", body: data)
    }

    func me() async throws -> User {
        return try await request("/auth/me")
    }

    func updateMe(fullName: String?, age: Int?, heightCm: Double?, weightKg: Double?, gender: String?) async throws -> User {
        var body: [String: Any] = [:]
        if let v = fullName { body["full_name"] = v }
        if let v = age      { body["age"]       = v }
        if let v = heightCm { body["height_cm"] = v }
        if let v = weightKg { body["weight_kg"] = v }
        if let v = gender   { body["gender"]    = v }
        let data = try JSONSerialization.data(withJSONObject: body)
        return try await request("/auth/me", method: "PUT", body: data)
    }

    // MARK: - Health Data

    func dashboard() async throws -> DashboardSummary {
        return try await request("/health/dashboard")
    }

    // MARK: - Integrations

    func integrationStatus() async throws -> [Integration] {
        return try await request("/integrations/status")
    }

    func connectIntegration(platform: String) async throws -> ConnectResponse {
        return try await request("/integrations/\(platform)/connect?mobile=true")
    }

    func syncIntegration(platform: String) async throws {
        let _: EmptyResponse = try await request("/integrations/\(platform)/sync?days=30", method: "POST")
    }

    func disconnectIntegration(platform: String) async throws {
        let _: EmptyResponse = try await request("/integrations/\(platform)/disconnect", method: "POST")
    }

    func syncNativeAppleHealth(payload: Data) async throws -> SyncNativeResponse {
        return try await request("/integrations/apple-health/sync-native", method: "POST", body: payload)
    }

    // MARK: - Lab Tests

    func labTests() async throws -> [LabTest] {
        return try await request("/lab-tests/")
    }

    func deleteLabTest(id: Int) async throws {
        let _: EmptyResponse = try await request("/lab-tests/\(id)", method: "DELETE")
    }

    func uploadLabTest(fileName: String, mimeType: String, fileData: Data, testName: String) async throws -> LabTest {
        return try await upload(
            "/lab-tests/upload",
            fields: ["test_name": testName],
            fileField: "file",
            fileName: fileName,
            mimeType: mimeType,
            fileData: fileData
        )
    }

    // MARK: - AI

    func chat(message: String, history: [ChatMessage]) async throws -> ChatResponse {
        let histItems = history.map { ChatHistoryItem(role: $0.role, content: $0.content) }
        let req = ChatRequest(message: message, conversationHistory: histItems)
        let body = try encoder.encode(req)
        return try await request("/ai/chat", method: "POST", body: body)
    }

    func insights() async throws -> InsightsResponse {
        return try await request("/ai/insights")
    }

    func suggestedQuestions() async throws -> [String] {
        return try await request("/ai/suggested-questions")
    }
}

// MARK: - Helpers

struct EmptyResponse: Codable {}
struct SyncNativeResponse: Codable {
    let status: String
    let recordsSynced: Int
}

private extension String {
    var urlEncoded: String {
        addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? self
    }
}

private extension Data {
    mutating func append(_ string: String) {
        if let data = string.data(using: .utf8) { append(data) }
    }
}
