import SwiftUI

struct RegisterView: View {
    @EnvironmentObject var auth: AuthStore
    @Environment(\.dismiss) var dismiss

    @State private var email = ""
    @State private var password = ""
    @State private var fullName = ""
    @State private var age = ""
    @State private var heightCm = ""
    @State private var weightKg = ""
    @State private var gender = ""
    @State private var isLoading = false
    @State private var error: String?

    var body: some View {
        ZStack {
            Color.black.ignoresSafeArea()

            ScrollView {
                VStack(spacing: 20) {
                    Text("Create Account")
                        .font(.largeTitle.bold())
                        .foregroundStyle(.white)
                        .frame(maxWidth: .infinity, alignment: .leading)

                    Group {
                        field("Email *", text: $email, keyboard: .emailAddress, caps: .never)
                        secureField("Password *", text: $password)
                        field("Full Name", text: $fullName)

                        HStack(spacing: 12) {
                            field("Age", text: $age, keyboard: .numberPad)
                            field("Gender (M/F/O)", text: $gender)
                        }
                        HStack(spacing: 12) {
                            field("Height (cm)", text: $heightCm, keyboard: .decimalPad)
                            field("Weight (kg)", text: $weightKg, keyboard: .decimalPad)
                        }
                    }

                    if let error {
                        Text(error)
                            .foregroundStyle(.red)
                            .font(.footnote)
                            .multilineTextAlignment(.center)
                    }

                    Button {
                        Task { await register() }
                    } label: {
                        Group {
                            if isLoading { ProgressView().tint(.white) }
                            else { Text("Create Account").fontWeight(.semibold) }
                        }
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(.cyan, in: RoundedRectangle(cornerRadius: 12))
                        .foregroundStyle(.white)
                    }
                    .disabled(isLoading || email.isEmpty || password.isEmpty)
                }
                .padding(28)
            }
        }
        .navigationBarBackButtonHidden(false)
    }

    @ViewBuilder
    private func field(
        _ placeholder: String,
        text: Binding<String>,
        keyboard: UIKeyboardType = .default,
        caps: TextInputAutocapitalization = .words
    ) -> some View {
        TextField(placeholder, text: text)
            .textFieldStyle(.plain)
            .padding()
            .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 12))
            .keyboardType(keyboard)
            .textInputAutocapitalization(caps)
            .autocorrectionDisabled()
    }

    @ViewBuilder
    private func secureField(_ placeholder: String, text: Binding<String>) -> some View {
        SecureField(placeholder, text: text)
            .textFieldStyle(.plain)
            .padding()
            .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 12))
    }

    private func register() async {
        isLoading = true
        error = nil
        do {
            try await auth.register(
                email: email.trimmed,
                password: password,
                fullName: fullName.trimmed.nilIfEmpty,
                age: Int(age),
                heightCm: Double(heightCm),
                weightKg: Double(weightKg),
                gender: gender.trimmed.nilIfEmpty
            )
        } catch {
            self.error = error.localizedDescription
        }
        isLoading = false
    }
}
