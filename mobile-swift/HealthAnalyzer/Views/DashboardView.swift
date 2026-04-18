import SwiftUI
import Charts

struct DashboardView: View {
    @State private var summary: DashboardSummary?
    @State private var isLoading = true
    @State private var error: String?

    var body: some View {
        NavigationStack {
            ZStack {
                Color.black.ignoresSafeArea()
                if isLoading {
                    ProgressView().tint(.cyan)
                } else if let error {
                    ContentUnavailableView(error, systemImage: "exclamationmark.triangle")
                } else if let s = summary {
                    ScrollView {
                        LazyVStack(spacing: 20, pinnedViews: []) {
                            metricsGrid(s)
                            if !s.sleepTrend.isEmpty { sleepChart(s.sleepTrend) }
                            if !s.hrvTrend.isEmpty   { hrvChart(s.hrvTrend) }
                            if !s.weightTrend.isEmpty { weightChart(s.weightTrend) }
                            if !s.activityTrend.isEmpty { activityChart(s.activityTrend) }
                        }
                        .padding()
                    }
                    .refreshable { await load() }
                }
            }
            .navigationTitle("Dashboard")
        }
        .task { await load() }
    }

    // MARK: - Metric Cards

    @ViewBuilder
    private func metricsGrid(_ s: DashboardSummary) -> some View {
        let sleepHrs = s.avgSleepDuration7d.map { String(format: "%.1f", $0 / 60) } ?? "—"
        LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 12) {
            MetricTile(label: "Avg Sleep", value: sleepHrs, unit: "hrs", color: .purple)
            MetricTile(label: "Avg HRV", value: s.avgHrv7d.fmt(0), unit: "ms", color: .green)
            MetricTile(label: "Avg Calories", value: s.avgDailyCalories7d.fmt(0), unit: "kcal", color: .orange)
            MetricTile(label: "Total Steps", value: s.totalSteps7d.map { ($0 / 7).formatted() } ?? "—", color: .cyan)
            MetricTile(label: "Recovery", value: s.avgRecoveryScore7d.fmt(0), unit: "%", color: .red)
            MetricTile(label: "Hydration", value: s.avgHydration7d.fmt(0), unit: "mL", color: .blue)
        }
    }

    // MARK: - Charts

    @ViewBuilder
    private func sleepChart(_ data: [SleepTrendPoint]) -> some View {
        ChartCard(title: "Sleep Duration (hours)") {
            Chart(data) { p in
                AreaMark(x: .value("Date", p.shortDate), y: .value("Hours", p.duration / 60))
                    .foregroundStyle(.purple.opacity(0.3))
                LineMark(x: .value("Date", p.shortDate), y: .value("Hours", p.duration / 60))
                    .foregroundStyle(.purple)
            }
        }
    }

    @ViewBuilder
    private func hrvChart(_ data: [HrvTrendPoint]) -> some View {
        ChartCard(title: "HRV (ms)") {
            Chart(data) { p in
                LineMark(x: .value("Date", p.shortDate), y: .value("HRV", p.hrv))
                    .foregroundStyle(.green)
                PointMark(x: .value("Date", p.shortDate), y: .value("HRV", p.hrv))
                    .foregroundStyle(.green)
            }
        }
    }

    @ViewBuilder
    private func weightChart(_ data: [TrendPoint]) -> some View {
        ChartCard(title: "Weight (kg)") {
            Chart(data) { p in
                LineMark(x: .value("Date", p.shortDate), y: .value("kg", p.value))
                    .foregroundStyle(.orange)
                AreaMark(x: .value("Date", p.shortDate), y: .value("kg", p.value))
                    .foregroundStyle(.orange.opacity(0.15))
            }
        }
    }

    @ViewBuilder
    private func activityChart(_ data: [ActivityTrendPoint]) -> some View {
        ChartCard(title: "Active Calories") {
            Chart(data) { p in
                BarMark(x: .value("Date", p.shortDate), y: .value("kcal", p.calories))
                    .foregroundStyle(.yellow)
            }
        }
    }

    // MARK: - Load

    private func load() async {
        isLoading = summary == nil
        error = nil
        do { summary = try await APIClient.shared.dashboard() }
        catch { self.error = error.localizedDescription }
        isLoading = false
    }
}

// MARK: - Reusable subviews

struct MetricTile: View {
    let label: String
    let value: String
    var unit: String = ""
    let color: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(label)
                .font(.caption.weight(.semibold))
                .foregroundStyle(.secondary)
                .textCase(.uppercase)
            HStack(alignment: .firstTextBaseline, spacing: 2) {
                Text(value)
                    .font(.title.bold())
                    .foregroundStyle(color)
                if !unit.isEmpty {
                    Text(unit).font(.caption).foregroundStyle(.secondary)
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding()
        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 14))
        .overlay(alignment: .leading) {
            RoundedRectangle(cornerRadius: 3).fill(color).frame(width: 4).padding(.vertical, 12)
        }
    }
}

struct ChartCard<Content: View>: View {
    let title: String
    @ViewBuilder let content: Content

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(title)
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(.secondary)
            content
                .frame(height: 160)
                .chartXAxis {
                    AxisMarks(values: .stride(by: .day, count: 7)) {
                        AxisValueLabel(format: .dateTime.month(.abbreviated).day())
                            .foregroundStyle(.secondary)
                    }
                }
                .chartYAxis {
                    AxisMarks { AxisValueLabel().foregroundStyle(.secondary) }
                }
        }
        .padding()
        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 14))
    }
}

// MARK: - Trend shortDate helpers

private extension TrendPoint {
    var shortDate: Date { ISO8601DateFormatter().date(from: date) ?? Date() }
}
private extension SleepTrendPoint {
    var shortDate: Date { ISO8601DateFormatter().date(from: date) ?? Date() }
}
private extension HrvTrendPoint {
    var shortDate: Date { ISO8601DateFormatter().date(from: date) ?? Date() }
}
private extension ActivityTrendPoint {
    var shortDate: Date { ISO8601DateFormatter().date(from: date) ?? Date() }
}
private extension Optional where Wrapped == Double {
    func fmt(_ decimals: Int) -> String {
        guard let v = self else { return "—" }
        return String(format: "%.\(decimals)f", v)
    }
}
