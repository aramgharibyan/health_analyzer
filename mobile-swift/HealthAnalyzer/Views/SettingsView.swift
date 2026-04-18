import SwiftUI

struct SettingsView: View {
    @EnvironmentObject var auth: AuthStore
    @State private var fullName = ""
    @State private var age = ""
    @State private var heightCm = ""
    @State private var weightKg = ""
    @State private var gender = ""
    @State private var isSaving = false
    @State private var saveError: String?
    @State private var showSavedBanner = false

    var body: some View {
        NavigationStack {
            ZStack {
                Color.black.ignoresSafeArea()
                ScrollView {
                    VStack(spacing: 20) {
                        profileSection
                        accountSection
                    }
                    .padding(20)
                }
            }
            .navigationTitle("Settings")
            .onAppear { populate() }
            .overlay(alignment: .top) {
                if showSavedBanner {
                    Text("Saved!")
                        .font(.subheadline.weight(.semibold))
                        .foregroundStyle(.white)
                        .padding(.horizontal, 20)
                        .padding(.vertical, 10)
                        .background(.green, in: Capsule())
                        .transition(.move(edge: .top).combined(with: .opacity))
                        .padding(.top, 8)
                }
            }
            .animation(.easeInOut, value: showSavedBanner)
        }
    }

    // MARK: - Profile section

    private var profileSection: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Profile")
                .font(.headline)
                .foregroundStyle(.secondary)

            field("Full Name", text: $fullName)
            field("Age", text: $age, keyboard: .numberPad)
            field("Gender (M / F / O)", text: $gender)

            HStack(spacing: 12) {
                field("Height (cm)", text: $heightCm, keyboard: .decimalPad)
                field("Weight (kg)", text: $weightKg, keyboard: .decimalPad)
            }

            if let err = saveError {
                Text(err).foregroundStyle(.red).font(.footnote)
            }

            Button {
                Task { await save() }
            } label: {
                Group {
                    if isSaving { ProgressView().tint(.white) }
                    else { Text("Save Changes").fontWeight(.semibold) }
                }
                .frame(maxWidth: .infinity)
                .padding()
                .background(.cyan, in: RoundedRectangle(cornerRadius: 12))
                .foregroundStyle(.white)
            }
            .disabled(isSaving)
        }
        .padding()
        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 14))
    }

    // MARK: - Account section

    private var accountSection: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Account")
                .font(.headline)
                .foregroundStyle(.secondary)

            if let email = auth.user?.email {
                HStack {
                    Text("Email").foregroundStyle(.secondary)
                    Spacer()
                    Text(email).foregroundStyle(.white)
                }
                .font(.subheadline)
            }

            Button(role: .destructive) {
                auth.logout()
            } label: {
                Text("Sign Out")
                    .fontWeight(.semibold)
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(.red.opacity(0.15), in: RoundedRectangle(cornerRadius: 12))
                    .foregroundStyle(.red)
            }
        }
        .padding()
        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 14))
    }

    // MARK: - Helpers

    @ViewBuilder
    private func field(
        _ placeholder: String,
        text: Binding<String>,
        keyboard: UIKeyboardType = .default
    ) -> some View {
        TextField(placeholder, text: text)
            .textFieldStyle(.plain)
            .padding()
            .background(Color.white.opacity(0.06), in: RoundedRectangle(cornerRadius: 10))
            .keyboardType(keyboard)
            .autocorrectionDisabled()
    }

    private func populate() {
        guard let u = auth.user else { return }
        fullName = u.fullName ?? ""
        age      = u.age.map(String.init) ?? ""
        heightCm = u.heightCm.map { String(format: "%.0f", $0) } ?? ""
        weightKg = u.weightKg.map { String(format: "%.1f", $0) } ?? ""
        gender   = u.gender ?? ""
    }

    private func save() async {
        isSaving = true
        saveError = nil
        do {
            let updated: User = try await APIClient.shared.request(
                "/users/me",
                method: "PATCH",
                body: [
                    "full_name":  fullName.trimmed.nilIfEmpty as Any,
                    "age":        Int(age) as Any,
                    "height_cm":  Double(heightCm) as Any,
                    "weight_kg":  Double(weightKg) as Any,
                    "gender":     gender.trimmed.nilIfEmpty as Any,
                ]
            )
            auth.updateUser(updated)
            showSavedBanner = true
            Task {
                try? await Task.sleep(nanoseconds: 2_000_000_000)
                showSavedBanner = false
            }
        } catch {
            saveError = error.localizedDescription
        }
        isSaving = false
    }
}
