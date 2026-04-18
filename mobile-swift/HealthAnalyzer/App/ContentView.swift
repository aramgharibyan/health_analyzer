import SwiftUI

struct ContentView: View {
    @EnvironmentObject var auth: AuthStore

    var body: some View {
        if auth.isAuthenticated {
            MainTabView()
        } else {
            LoginView()
        }
    }
}

struct MainTabView: View {
    var body: some View {
        TabView {
            DashboardView()
                .tabItem { Label("Dashboard", systemImage: "chart.bar.fill") }

            IntegrationsView()
                .tabItem { Label("Integrations", systemImage: "link.circle.fill") }

            LabTestsView()
                .tabItem { Label("Lab Tests", systemImage: "flask.fill") }

            AIAssistantView()
                .tabItem { Label("AI", systemImage: "brain.head.profile") }

            SettingsView()
                .tabItem { Label("Settings", systemImage: "gearshape.fill") }
        }
        .tint(.cyan)
    }
}
