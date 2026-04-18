import SwiftUI

struct AIAssistantView: View {
    @State private var messages: [ChatHistoryItem] = []
    @State private var input = ""
    @State private var isSending = false
    @State private var suggestedQuestions: [String] = []
    @State private var isLoadingSuggestions = true

    var body: some View {
        NavigationStack {
            ZStack {
                Color.black.ignoresSafeArea()
                VStack(spacing: 0) {
                    messageList
                    Divider().background(.ultraThinMaterial)
                    inputBar
                }
            }
            .navigationTitle("AI Assistant")
        }
        .task { await loadSuggestions() }
    }

    // MARK: - Message list

    private var messageList: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(spacing: 12) {
                    if messages.isEmpty {
                        suggestionsSection
                    }
                    ForEach(Array(messages.enumerated()), id: \.offset) { _, msg in
                        ChatBubbleView(message: msg)
                            .id(msg.role + "\(messages.firstIndex(where: { $0.content == msg.content }) ?? 0)")
                    }
                    if isSending {
                        HStack {
                            ProgressView().tint(.cyan)
                                .padding()
                                .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 16))
                            Spacer()
                        }
                        .padding(.horizontal)
                        .id("typing")
                    }
                }
                .padding(.vertical, 12)
            }
            .onChange(of: messages.count) { _, _ in
                withAnimation { proxy.scrollTo("typing", anchor: .bottom) }
            }
            .onChange(of: isSending) { _, _ in
                withAnimation { proxy.scrollTo("typing", anchor: .bottom) }
            }
        }
    }

    // MARK: - Suggestions

    private var suggestionsSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            if !isLoadingSuggestions && !suggestedQuestions.isEmpty {
                Text("Suggested Questions")
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(.secondary)
                    .padding(.horizontal)

                ForEach(suggestedQuestions, id: \.self) { q in
                    Button {
                        input = q
                        Task { await send() }
                    } label: {
                        Text(q)
                            .font(.subheadline)
                            .foregroundStyle(.cyan)
                            .multilineTextAlignment(.leading)
                            .padding(12)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 12))
                            .padding(.horizontal)
                    }
                }
            }
        }
        .padding(.top, 8)
    }

    // MARK: - Input bar

    private var inputBar: some View {
        HStack(spacing: 12) {
            TextField("Ask about your health…", text: $input, axis: .vertical)
                .lineLimit(1...4)
                .textFieldStyle(.plain)
                .padding(10)
                .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 12))

            Button {
                Task { await send() }
            } label: {
                Image(systemName: "arrow.up.circle.fill")
                    .font(.title2)
                    .foregroundStyle(input.trimmed.isEmpty || isSending ? .gray : .cyan)
            }
            .disabled(input.trimmed.isEmpty || isSending)
        }
        .padding(12)
        .background(Color.black)
    }

    // MARK: - Actions

    private func send() async {
        let text = input.trimmed
        guard !text.isEmpty else { return }
        input = ""
        isSending = true

        let userMsg = ChatHistoryItem(role: "user", content: text)
        messages.append(userMsg)

        do {
            let history = messages.dropLast().map { ChatHistoryItem(role: $0.role, content: $0.content) }
            let response: ChatResponse = try await APIClient.shared.chat(
                message: text,
                history: Array(history)
            )
            messages.append(ChatHistoryItem(role: "assistant", content: response.response))
        } catch {
            messages.append(ChatHistoryItem(role: "assistant", content: "Sorry, something went wrong: \(error.localizedDescription)"))
        }

        isSending = false
    }

    private func loadSuggestions() async {
        isLoadingSuggestions = true
        do { suggestedQuestions = try await APIClient.shared.suggestedQuestions() }
        catch {}
        isLoadingSuggestions = false
    }
}

// MARK: - Chat bubble

struct ChatBubbleView: View {
    let message: ChatHistoryItem

    private var isUser: Bool { message.role == "user" }

    var body: some View {
        HStack {
            if isUser { Spacer(minLength: 48) }
            Text(message.content)
                .font(.subheadline)
                .foregroundStyle(.white)
                .padding(12)
                .background(
                    isUser ? AnyShapeStyle(.cyan) : AnyShapeStyle(.ultraThinMaterial),
                    in: RoundedRectangle(cornerRadius: 16)
                )
            if !isUser { Spacer(minLength: 48) }
        }
        .padding(.horizontal)
    }
}
