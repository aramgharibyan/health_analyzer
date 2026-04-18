import Foundation
import HealthKit

@MainActor
final class HealthKitManager: ObservableObject {
    static let shared = HealthKitManager()
    private let store = HKHealthStore()

    static var isAvailable: Bool { HKHealthStore.isHealthDataAvailable() }

    // MARK: - Permission request

    func requestAuthorization() async throws {
        guard Self.isAvailable else { throw HKError(.errorHealthDataUnavailable) }

        let readTypes: Set<HKObjectType> = [
            .quantityType(forIdentifier: .stepCount)!,
            .quantityType(forIdentifier: .heartRate)!,
            .quantityType(forIdentifier: .restingHeartRate)!,
            .quantityType(forIdentifier: .heartRateVariabilitySDNN)!,
            .quantityType(forIdentifier: .oxygenSaturation)!,
            .quantityType(forIdentifier: .respiratoryRate)!,
            .quantityType(forIdentifier: .activeEnergyBurned)!,
            .quantityType(forIdentifier: .basalEnergyBurned)!,
            .quantityType(forIdentifier: .distanceWalkingRunning)!,
            .quantityType(forIdentifier: .bodyMass)!,
            .quantityType(forIdentifier: .bodyFatPercentage)!,
            .quantityType(forIdentifier: .bodyMassIndex)!,
            .quantityType(forIdentifier: .bloodPressureSystolic)!,
            .quantityType(forIdentifier: .bloodPressureDiastolic)!,
            .quantityType(forIdentifier: .vo2Max)!,
            .quantityType(forIdentifier: .dietaryEnergyConsumed)!,
            .quantityType(forIdentifier: .dietaryProtein)!,
            .quantityType(forIdentifier: .dietaryCarbohydrates)!,
            .quantityType(forIdentifier: .dietaryFatTotal)!,
            .quantityType(forIdentifier: .dietaryFiber)!,
            .quantityType(forIdentifier: .dietaryWater)!,
            .categoryType(forIdentifier: .sleepAnalysis)!,
            HKObjectType.workoutType(),
        ]
        try await store.requestAuthorization(toShare: [], read: readTypes)
    }

    // MARK: - Sync to backend

    func syncToBackend(days: Int = 30) async throws -> SyncNativeResponse {
        try await requestAuthorization()

        let start = Calendar.current.date(byAdding: .day, value: -days, to: Date())!

        // Fetch all data concurrently
        async let steps       = fetchQuantity(.stepCount,              start: start, unit: .count())
        async let heartRate   = fetchQuantity(.heartRate,              start: start, unit: HKUnit(from: "count/min"))
        async let restingHR   = fetchQuantity(.restingHeartRate,       start: start, unit: HKUnit(from: "count/min"))
        async let hrv         = fetchQuantity(.heartRateVariabilitySDNN, start: start, unit: .secondUnit(with: .milli))
        async let spo2        = fetchQuantity(.oxygenSaturation,       start: start, unit: .percent())
        async let respRate    = fetchQuantity(.respiratoryRate,        start: start, unit: HKUnit(from: "count/min"))
        async let activeCals  = fetchQuantity(.activeEnergyBurned,     start: start, unit: .kilocalorie())
        async let basalCals   = fetchQuantity(.basalEnergyBurned,      start: start, unit: .kilocalorie())
        async let distance    = fetchQuantity(.distanceWalkingRunning, start: start, unit: .meterUnit(with: .kilo))
        async let weight      = fetchQuantity(.bodyMass,               start: start, unit: .gramUnit(with: .kilo))
        async let bodyFat     = fetchQuantity(.bodyFatPercentage,      start: start, unit: .percent())
        async let bmi         = fetchQuantity(.bodyMassIndex,          start: start, unit: .count())
        async let calories    = fetchQuantity(.dietaryEnergyConsumed,  start: start, unit: .kilocalorie())
        async let protein     = fetchQuantity(.dietaryProtein,         start: start, unit: .gramUnit(with: .none))
        async let carbs       = fetchQuantity(.dietaryCarbohydrates,   start: start, unit: .gramUnit(with: .none))
        async let fat         = fetchQuantity(.dietaryFatTotal,        start: start, unit: .gramUnit(with: .none))
        async let fiber       = fetchQuantity(.dietaryFiber,           start: start, unit: .gramUnit(with: .none))
        async let water       = fetchQuantity(.dietaryWater,           start: start, unit: .literUnit(with: .milli))
        async let sleep       = fetchSleep(start: start)
        async let workouts    = fetchWorkouts(start: start)

        // Build Health Auto Export-compatible JSON payload
        let metrics: [[String: Any]] = [
            metric("step_count",              "count",  try await steps),
            metric("heart_rate",              "bpm",    try await heartRate),
            metric("resting_heart_rate",      "bpm",    try await restingHR),
            metric("heart_rate_variability",  "ms",     try await hrv),
            metric("oxygen_saturation",       "%",      try await spo2),
            metric("respiratory_rate",        "breaths/min", try await respRate),
            metric("active_energy",           "kcal",   try await activeCals),
            metric("basal_body_temperature",  "kcal",   try await basalCals),
            metric("walking_running_distance","km",     try await distance),
            metric("weight_body_mass",        "kg",     try await weight),
            metric("body_fat_percentage",     "%",      try await bodyFat),
            metric("bmi",                     "count",  try await bmi),
            metric("dietary_energy",          "kcal",   try await calories),
            metric("protein",                 "g",      try await protein),
            metric("carbohydrates",           "g",      try await carbs),
            metric("total_fat",               "g",      try await fat),
            metric("fiber",                   "g",      try await fiber),
            metric("water",                   "mL",     try await water),
        ]

        let sleepData = try await sleep
        let workoutData = try await workouts

        let payload: [String: Any] = [
            "data": [
                "metrics": metrics,
                "sleep": sleepData,
                "workouts": workoutData,
            ]
        ]

        let data = try JSONSerialization.data(withJSONObject: payload)
        return try await APIClient.shared.syncNativeAppleHealth(payload: data)
    }

    // MARK: - Quantity samples

    private func fetchQuantity(
        _ identifier: HKQuantityTypeIdentifier,
        start: Date,
        unit: HKUnit
    ) async -> [[String: Any]] {
        guard let type = HKQuantityType.quantityType(forIdentifier: identifier) else { return [] }
        let predicate = HKQuery.predicateForSamples(withStart: start, end: Date())
        let descriptor = HKSampleQueryDescriptor(
            predicates: [.quantitySample(type: type, predicate: predicate)],
            sortDescriptors: [SortDescriptor(\.startDate)]
        )
        guard let samples = try? await descriptor.result(for: store) else { return [] }
        return samples.map { s in
            ["date": ISO8601DateFormatter().string(from: s.startDate),
             "qty": s.quantity.doubleValue(for: unit)]
        }
    }

    // MARK: - Sleep

    private func fetchSleep(start: Date) async -> [[String: Any]] {
        guard let type = HKCategoryType.categoryType(forIdentifier: .sleepAnalysis) else { return [] }
        let predicate = HKQuery.predicateForSamples(withStart: start, end: Date())
        let descriptor = HKSampleQueryDescriptor(
            predicates: [.categorySample(type: type, predicate: predicate)],
            sortDescriptors: [SortDescriptor(\.startDate)]
        )
        guard let samples = try? await descriptor.result(for: store) else { return [] }
        let fmt = ISO8601DateFormatter()
        return samples.map { s in
            let stage: String
            switch s.value {
            case HKCategoryValueSleepAnalysis.inBed.rawValue:        stage = "HKCategoryValueSleepAnalysisInBed"
            case HKCategoryValueSleepAnalysis.awake.rawValue:         stage = "HKCategoryValueSleepAnalysisAwake"
            case HKCategoryValueSleepAnalysis.asleepCore.rawValue:    stage = "HKCategoryValueSleepAnalysisAsleepCore"
            case HKCategoryValueSleepAnalysis.asleepDeep.rawValue:    stage = "HKCategoryValueSleepAnalysisAsleepDeep"
            case HKCategoryValueSleepAnalysis.asleepREM.rawValue:     stage = "HKCategoryValueSleepAnalysisAsleepREM"
            default:                                                   stage = "HKCategoryValueSleepAnalysisInBed"
            }
            return [
                "startDate": fmt.string(from: s.startDate),
                "endDate":   fmt.string(from: s.endDate),
                "value":     stage,
            ]
        }
    }

    // MARK: - Workouts

    private func fetchWorkouts(start: Date) async -> [[String: Any]] {
        let predicate = HKQuery.predicateForSamples(withStart: start, end: Date())
        let descriptor = HKSampleQueryDescriptor(
            predicates: [.workout(predicate: predicate)],
            sortDescriptors: [SortDescriptor(\.startDate)]
        )
        guard let workouts = try? await descriptor.result(for: store) else { return [] }
        let fmt = ISO8601DateFormatter()
        return workouts.map { w in
            var dict: [String: Any] = [
                "name":  w.workoutActivityType.name,
                "start": fmt.string(from: w.startDate),
                "end":   fmt.string(from: w.endDate),
                "duration": w.duration / 60,
            ]
            if let cals = w.statistics(for: .init(.activeEnergyBurned))?
                .sumQuantity()?.doubleValue(for: .kilocalorie()) {
                dict["activeEnergy"] = cals
            }
            if let dist = w.statistics(for: .init(.distanceWalkingRunning))?
                .sumQuantity()?.doubleValue(for: .meterUnit(with: .kilo)) {
                dict["distance"] = dist
            }
            return dict
        }
    }

    // MARK: - Helpers

    private func metric(_ name: String, _ units: String, _ data: [[String: Any]]) -> [String: Any] {
        ["name": name, "units": units, "data": data]
    }
}

// MARK: - Workout name mapping

extension HKWorkoutActivityType {
    var name: String {
        switch self {
        case .running:     return "Running"
        case .cycling:     return "Cycling"
        case .walking:     return "Walking"
        case .swimming:    return "Swimming"
        case .yoga:        return "Yoga"
        case .hiking:      return "Hiking"
        case .rowing:      return "Rowing"
        case .elliptical:  return "Elliptical"
        case .traditionalStrengthTraining: return "Strength Training"
        case .highIntensityIntervalTraining: return "HIIT"
        case .pilates:     return "Pilates"
        case .crossTraining: return "Cross Training"
        default:           return "Workout"
        }
    }
}
