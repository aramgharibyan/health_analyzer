import SwiftUI
import PhotosUI

struct LabTestsView: View {
    @State private var tests: [LabTest] = []
    @State private var isLoading = true
    @State private var showFilePicker = false
    @State private var selectedPhoto: PhotosPickerItem?
    @State private var pendingFileData: Data?
    @State private var pendingFileName = ""
    @State private var pendingMimeType = ""
    @State private var showUploadSheet = false
    @State private var testName = ""
    @State private var isUploading = false
    @State private var uploadError: String?
    @State private var expandedId: Int?

    var body: some View {
        NavigationStack {
            ZStack {
                Color.black.ignoresSafeArea()
                if isLoading {
                    ProgressView().tint(.cyan)
                } else {
                    list
                }
            }
            .navigationTitle("Lab Tests")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Menu {
                        PhotosPicker(selection: $selectedPhoto, matching: .images) {
                            Label("Take / Choose Photo", systemImage: "camera")
                        }
                        Button {
                            showFilePicker = true
                        } label: {
                            Label("Import PDF / File", systemImage: "doc")
                        }
                    } label: {
                        Image(systemName: "plus")
                    }
                }
            }
            .fileImporter(
                isPresented: $showFilePicker,
                allowedContentTypes: [.pdf, .plainText, .json],
                allowsMultipleSelection: false
            ) { result in
                if let url = try? result.get().first,
                   url.startAccessingSecurityScopedResource(),
                   let data = try? Data(contentsOf: url) {
                    pendingFileData = data
                    pendingFileName = url.lastPathComponent
                    pendingMimeType = url.pathExtension == "pdf" ? "application/pdf" : "text/plain"
                    url.stopAccessingSecurityScopedResource()
                    showUploadSheet = true
                }
            }
            .onChange(of: selectedPhoto) { _, item in
                Task {
                    if let data = try? await item?.loadTransferable(type: Data.self) {
                        pendingFileData = data
                        pendingFileName = "lab-test.jpg"
                        pendingMimeType = "image/jpeg"
                        showUploadSheet = true
                    }
                }
            }
            .sheet(isPresented: $showUploadSheet) { uploadSheet }
        }
        .task { await load() }
    }

    // MARK: - List

    private var list: some View {
        Group {
            if tests.isEmpty {
                ContentUnavailableView(
                    "No Lab Tests",
                    systemImage: "flask",
                    description: Text("Tap + to upload a PDF or photo of your lab results.")
                )
            } else {
                List {
                    ForEach(tests) { test in
                        LabTestRow(test: test, isExpanded: expandedId == test.id) {
                            expandedId = expandedId == test.id ? nil : test.id
                        }
                        .listRowBackground(Color.clear)
                        .listRowSeparator(.hidden)
                    }
                    .onDelete { offsets in
                        Task { await deleteTests(at: offsets) }
                    }
                }
                .listStyle(.plain)
                .refreshable { await load() }
            }
        }
    }

    // MARK: - Upload sheet

    private var uploadSheet: some View {
        NavigationStack {
            ZStack {
                Color.black.ignoresSafeArea()
                VStack(spacing: 20) {
                    if let name = pendingFileName.nilIfEmpty {
                        Label(name, systemImage: "doc.fill")
                            .foregroundStyle(.cyan)
                    }
                    TextField("Test name (e.g. Complete Blood Count)", text: $testName)
                        .textFieldStyle(.plain)
                        .padding()
                        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 12))

                    if let err = uploadError {
                        Text(err).foregroundStyle(.red).font(.footnote)
                    }

                    Button {
                        Task { await uploadFile() }
                    } label: {
                        Group {
                            if isUploading { ProgressView().tint(.white) }
                            else { Text("Upload & Analyse").fontWeight(.semibold) }
                        }
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(.cyan, in: RoundedRectangle(cornerRadius: 12))
                        .foregroundStyle(.white)
                    }
                    .disabled(isUploading || testName.trimmed.isEmpty)
                    Spacer()
                }
                .padding(24)
            }
            .navigationTitle("Upload Lab Test")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("Cancel") {
                        showUploadSheet = false
                        testName = ""
                        uploadError = nil
                    }
                }
            }
        }
    }

    // MARK: - Actions

    private func load() async {
        isLoading = tests.isEmpty
        do { tests = try await APIClient.shared.labTests() }
        catch {}
        isLoading = false
    }

    private func uploadFile() async {
        guard let data = pendingFileData else { return }
        isUploading = true
        uploadError = nil
        do {
            let test = try await APIClient.shared.uploadLabTest(
                fileName: pendingFileName,
                mimeType: pendingMimeType,
                fileData: data,
                testName: testName.trimmed
            )
            tests.insert(test, at: 0)
            showUploadSheet = false
            testName = ""
        } catch {
            uploadError = error.localizedDescription
        }
        isUploading = false
    }

    private func deleteTests(at offsets: IndexSet) async {
        for i in offsets {
            let id = tests[i].id
            try? await APIClient.shared.deleteLabTest(id: id)
        }
        tests.remove(atOffsets: offsets)
    }
}

// MARK: - Lab Test Row

struct LabTestRow: View {
    let test: LabTest
    let isExpanded: Bool
    let onTap: () -> Void

    private let statusColor: [String: Color] = [
        "normal": .green, "high": .orange, "low": .blue,
        "critical_high": .red, "critical_low": .red,
    ]

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            // Header
            Button(action: onTap) {
                HStack {
                    VStack(alignment: .leading, spacing: 4) {
                        Text(test.testName).font(.headline).foregroundStyle(.white)
                        if let lab = test.labName { Text(lab).font(.caption).foregroundStyle(.secondary) }
                        if let date = test.testDate?.prefix(10) { Text(date).font(.caption2).foregroundStyle(.tertiary) }
                    }
                    Spacer()
                    Capsule()
                        .fill(test.status == "processed" ? Color.green.opacity(0.2) : Color.gray.opacity(0.2))
                        .frame(width: 72, height: 24)
                        .overlay(Text(test.status).font(.caption2.bold())
                            .foregroundStyle(test.status == "processed" ? .green : .gray))
                    Image(systemName: isExpanded ? "chevron.up" : "chevron.down")
                        .foregroundStyle(.secondary).font(.caption)
                }
            }
            .padding()

            if isExpanded {
                Divider().background(.ultraThinMaterial)
                VStack(alignment: .leading, spacing: 8) {
                    if let summary = test.parsedSummary {
                        Text(summary)
                            .font(.footnote).foregroundStyle(.secondary)
                            .padding(.bottom, 4)
                    }
                    ForEach(test.results) { r in
                        HStack {
                            VStack(alignment: .leading, spacing: 2) {
                                Text(r.biomarkerName).font(.subheadline).foregroundStyle(.white)
                                if let interp = r.interpretation {
                                    Text(interp).font(.caption2).foregroundStyle(.secondary)
                                }
                            }
                            Spacer()
                            VStack(alignment: .trailing, spacing: 2) {
                                HStack(alignment: .firstTextBaseline, spacing: 2) {
                                    Text(r.value.map { String(format: "%.1f", $0) } ?? "—")
                                        .font(.subheadline.bold())
                                        .foregroundStyle(statusColor[r.status ?? ""] ?? .white)
                                    if let u = r.unit { Text(u).font(.caption2).foregroundStyle(.secondary) }
                                }
                                if let ref = r.referenceText { Text(ref).font(.caption2).foregroundStyle(.tertiary) }
                            }
                        }
                        .padding(.vertical, 4)
                        Divider().opacity(0.3)
                    }
                }
                .padding([.horizontal, .bottom])
            }
        }
        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 14))
        .padding(.vertical, 4)
    }
}
