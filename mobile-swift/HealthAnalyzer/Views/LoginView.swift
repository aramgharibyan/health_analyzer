import SwiftUI

struct LoginView: View {
    @EnvironmentObject var auth: AuthStore
    @State private var email = ""
    @State private var password = ""
    @State private var isLoading = false
    @State private var error: String?
    @State private var showRegister = false

    var body: some View {
        NavigationStack {
            ZStack {
                Color.black.ignoresSafeArea()

                VStack(spacing: 24) {
                    Spacer()

                    VStack(spacing: 8) {
                        Text("❤️").font(.system(size: 56))
                        Text("Health Analyzer")
                            .font(.largeTitle.bold())
                            .foregroundStyle(.white)
                        Text("Sign in to your account")
                            .foregroundStyle(.secondary)
                    }

                    VStack(spacing: 12) {
                        TextField("Email", text: $email)
                            .textFieldStyle(.plain)
                            .padding()
                            .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 12))
                            .keyboardType(.emailAddress)
                            .autocorrectionDisabled()
                            .textInputAutocapitalization(.never)

                        SecureField("Password", text: $password)
                            .textFieldStyle(.plain)
                            .padding()
                            .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 12))
                    }

                    if let error {
                        Text(error)
                            .foregroundStyle(.red)
                            .font(.footnote)
                            .multilineTextAlignment(.center)
                    }

                    Button {
                        Task { await login() }
                    } label: {
                        Group {
                            if isLoading {
                                ProgressView().tint(.white)
                            } else {
                                Text("Sign In").fontWeight(.semibold)
                            }
                        }
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(.cyan, in: RoundedRectangle(cornerRadius: 12))
                        .foregroundStyle(.white)
                    }
                    .disabled(isLoading || email.isEmpty || password.isEmpty)

                    Button("Don't have an account? Create one") {
                        showRegister = true
                    }
                    .foregroundStyle(.cyan)
                    .font(.footnote)

                    Spacer()
                }
                .padding(.horizontal, 28)
            }
            .navigationDestination(isPresented: $showRegister) {
                RegisterView()
            }
        }
    }

    private func login() async {
        isLoading = true
        error = nil
        do {
            try await auth.login(email: email.trimmed, password: password)
        } catch {
            self.error = error.localizedDescription
        }
        isLoading = false
    }
}
