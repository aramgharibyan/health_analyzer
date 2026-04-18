import Foundation

// MARK: - Auth

struct AuthResponse: Codable {
    let accessToken: String
    let tokenType: String
    let user: User
}

struct User: Codable, Identifiable {
    let id: Int
    let email: String
    let fullName: String?
    let age: Int?
    let heightCm: Double?
    let weightKg: Double?
    let gender: String?
    let isActive: Bool
    let createdAt: String
}

// MARK: - Health Data

struct SleepRecord: Codable, Identifiable {
    let id: Int
    let source: String
    let startTime: String
    let endTime: String
    let totalDurationMinutes: Double?
    let sleepEfficiency: Double?
    let deepSleepMinutes: Double?
    let lightSleepMinutes: Double?
    let remSleepMinutes: Double?
    let awakeMins: Double?
    let sleepScore: Double?
    let recoveryScore: Double?
    let avgHeartRate: Double?
    let hrv: Double?
    let avgSpo2: Double?
    let respiratoryRate: Double?
    let createdAt: String

    enum CodingKeys: String, CodingKey {
        case id, source
        case startTime = "start_time"
        case endTime = "end_time"
        case totalDurationMinutes = "total_duration_minutes"
        case sleepEfficiency = "sleep_efficiency"
        case deepSleepMinutes = "deep_sleep_minutes"
        case lightSleepMinutes = "light_sleep_minutes"
        case remSleepMinutes = "rem_sleep_minutes"
        case awakeMins = "awake_minutes"
        case sleepScore = "sleep_score"
        case recoveryScore = "recovery_score"
        case avgHeartRate = "avg_heart_rate"
        case hrv
        case avgSpo2 = "avg_spo2"
        case respiratoryRate = "respiratory_rate"
        case createdAt = "created_at"
    }
}

struct ActivityRecord: Codable, Identifiable {
    let id: Int
    let source: String
    let activityType: String?
    let startTime: String
    let durationMinutes: Double?
    let caloriesBurned: Double?
    let avgHeartRate: Double?
    let strainScore: Double?
    let steps: Int?
    let distanceKm: Double?
    let workoutName: String?
    let createdAt: String

    enum CodingKeys: String, CodingKey {
        case id, source
        case activityType = "activity_type"
        case startTime = "start_time"
        case durationMinutes = "duration_minutes"
        case caloriesBurned = "calories_burned"
        case avgHeartRate = "avg_heart_rate"
        case strainScore = "strain_score"
        case steps
        case distanceKm = "distance_km"
        case workoutName = "workout_name"
        case createdAt = "created_at"
    }
}

struct NutritionRecord: Codable, Identifiable {
    let id: Int
    let source: String
    let recordedDate: String
    let mealType: String?
    let calories: Double?
    let proteinG: Double?
    let carbsG: Double?
    let fatG: Double?
    let fiberG: Double?
    let createdAt: String

    enum CodingKeys: String, CodingKey {
        case id, source
        case recordedDate = "recorded_date"
        case mealType = "meal_type"
        case calories
        case proteinG = "protein_g"
        case carbsG = "carbs_g"
        case fatG = "fat_g"
        case fiberG = "fiber_g"
        case createdAt = "created_at"
    }
}

struct BodyMetric: Codable, Identifiable {
    let id: Int
    let source: String
    let measuredAt: String
    let weightKg: Double?
    let bmi: Double?
    let bodyFatPercent: Double?
    let muscleMassKg: Double?
    let systolicBp: Int?
    let diastolicBp: Int?
    let pulse: Int?
    let createdAt: String

    enum CodingKeys: String, CodingKey {
        case id, source
        case measuredAt = "measured_at"
        case weightKg = "weight_kg"
        case bmi
        case bodyFatPercent = "body_fat_percent"
        case muscleMassKg = "muscle_mass_kg"
        case systolicBp = "systolic_bp"
        case diastolicBp = "diastolic_bp"
        case pulse
        case createdAt = "created_at"
    }
}

struct HydrationRecord: Codable, Identifiable {
    let id: Int
    let source: String
    let recordedAt: String
    let amountMl: Double?
    let dailyTotalMl: Double?
    let dailyGoalMl: Double?

    enum CodingKeys: String, CodingKey {
        case id, source
        case recordedAt = "recorded_at"
        case amountMl = "amount_ml"
        case dailyTotalMl = "daily_total_ml"
        case dailyGoalMl = "daily_goal_ml"
    }
}

// MARK: - Dashboard

struct DashboardSummary: Codable {
    let latestSleep: SleepRecord?
    let latestBodyMetric: BodyMetric?
    let latestActivity: ActivityRecord?
    let avgSleepDuration7d: Double?
    let avgSleepScore7d: Double?
    let avgHrv7d: Double?
    let avgRecoveryScore7d: Double?
    let totalCalories7d: Double?
    let avgDailyCalories7d: Double?
    let totalSteps7d: Int?
    let avgHydration7d: Double?
    let weightTrend: [TrendPoint]
    let sleepTrend: [SleepTrendPoint]
    let activityTrend: [ActivityTrendPoint]
    let hrvTrend: [HrvTrendPoint]
    let connectedIntegrations: Int

    enum CodingKeys: String, CodingKey {
        case latestSleep = "latest_sleep"
        case latestBodyMetric = "latest_body_metric"
        case latestActivity = "latest_activity"
        case avgSleepDuration7d = "avg_sleep_duration_7d"
        case avgSleepScore7d = "avg_sleep_score_7d"
        case avgHrv7d = "avg_hrv_7d"
        case avgRecoveryScore7d = "avg_recovery_score_7d"
        case totalCalories7d = "total_calories_7d"
        case avgDailyCalories7d = "avg_daily_calories_7d"
        case totalSteps7d = "total_steps_7d"
        case avgHydration7d = "avg_hydration_7d"
        case weightTrend = "weight_trend"
        case sleepTrend = "sleep_trend"
        case activityTrend = "activity_trend"
        case hrvTrend = "hrv_trend"
        case connectedIntegrations = "connected_integrations"
    }
}

struct TrendPoint: Codable, Identifiable {
    var id: String { date }
    let date: String
    let value: Double
}

struct SleepTrendPoint: Codable, Identifiable {
    var id: String { date }
    let date: String
    let duration: Double
    let score: Double
    let hrv: Double
    let recovery: Double
}

struct ActivityTrendPoint: Codable, Identifiable {
    var id: String { date }
    let date: String
    let calories: Double
    let strain: Double
    let type: String
}

struct HrvTrendPoint: Codable, Identifiable {
    var id: String { date }
    let date: String
    let hrv: Double
}

// MARK: - Lab Tests

struct LabTest: Codable, Identifiable {
    let id: Int
    let testName: String
    let labName: String?
    let orderedBy: String?
    let testDate: String?
    let fileName: String?
    let notes: String?
    let parsedSummary: String?
    let status: String
    let results: [LabTestResult]
    let createdAt: String

    enum CodingKeys: String, CodingKey {
        case id
        case testName = "test_name"
        case labName = "lab_name"
        case orderedBy = "ordered_by"
        case testDate = "test_date"
        case fileName = "file_name"
        case notes
        case parsedSummary = "parsed_summary"
        case status, results
        case createdAt = "created_at"
    }
}

struct LabTestResult: Codable, Identifiable {
    let id: Int
    let biomarkerName: String
    let value: Double?
    let unit: String?
    let referenceMin: Double?
    let referenceMax: Double?
    let referenceText: String?
    let status: String?
    let category: String?
    let interpretation: String?

    enum CodingKeys: String, CodingKey {
        case id
        case biomarkerName = "biomarker_name"
        case value, unit
        case referenceMin = "reference_min"
        case referenceMax = "reference_max"
        case referenceText = "reference_text"
        case status, category, interpretation
    }
}

// MARK: - Integrations

struct Integration: Codable, Identifiable {
    var id: String { platform }
    let platform: String
    let name: String
    let description: String
    let authType: String
    let dataTypes: [String]
    let isConnected: Bool
    let isActive: Bool
    let platformUsername: String?
    let lastSyncedAt: String?
    let autoSync: Bool

    enum CodingKeys: String, CodingKey {
        case platform, name, description
        case authType = "auth_type"
        case dataTypes = "data_types"
        case isConnected = "is_connected"
        case isActive = "is_active"
        case platformUsername = "platform_username"
        case lastSyncedAt = "last_synced_at"
        case autoSync = "auto_sync"
    }
}

struct ConnectResponse: Codable {
    let authUrl: String
    enum CodingKeys: String, CodingKey { case authUrl = "auth_url" }
}

// MARK: - AI

struct ChatMessage: Identifiable {
    let id = UUID()
    let role: String   // "user" | "assistant"
    let content: String
}

struct ChatRequest: Codable {
    let message: String
    let conversationHistory: [ChatHistoryItem]
    enum CodingKeys: String, CodingKey {
        case message
        case conversationHistory = "conversation_history"
    }
}

struct ChatHistoryItem: Codable {
    let role: String
    let content: String
}

struct ChatResponse: Codable {
    let message: String
    let role: String
}

struct InsightsResponse: Codable {
    let insights: String
}
