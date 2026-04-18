import SwiftUI

@main
struct HealthAnalyzerApp: App {
    @StateObject private var auth = AuthStore()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(auth)
                .preferredColorScheme(.dark)
        }
    }
}
