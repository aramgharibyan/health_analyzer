export interface User {
  id: number
  email: string
  full_name: string | null
  age: number | null
  height_cm: number | null
  weight_kg: number | null
  gender: string | null
  is_active: boolean
  created_at: string
}

export interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
}

export interface SleepRecord {
  id: number
  source: string
  start_time: string
  end_time: string
  total_duration_minutes: number | null
  sleep_efficiency: number | null
  deep_sleep_minutes: number | null
  light_sleep_minutes: number | null
  rem_sleep_minutes: number | null
  awake_minutes: number | null
  sleep_score: number | null
  recovery_score: number | null
  avg_heart_rate: number | null
  hrv: number | null
  avg_spo2: number | null
  respiratory_rate: number | null
  created_at: string
}

export interface ActivityRecord {
  id: number
  source: string
  activity_type: string | null
  start_time: string
  end_time: string | null
  duration_minutes: number | null
  calories_burned: number | null
  avg_heart_rate: number | null
  max_heart_rate: number | null
  strain_score: number | null
  steps: number | null
  distance_km: number | null
  workout_name: string | null
  total_volume_kg: number | null
  created_at: string
}

export interface NutritionRecord {
  id: number
  source: string
  recorded_date: string
  meal_type: string | null
  calories: number | null
  protein_g: number | null
  carbs_g: number | null
  fat_g: number | null
  fiber_g: number | null
  sugar_g: number | null
  sodium_mg: number | null
  food_items: unknown[] | null
  created_at: string
}

export interface BodyMetric {
  id: number
  source: string
  measured_at: string
  weight_kg: number | null
  bmi: number | null
  body_fat_percent: number | null
  muscle_mass_kg: number | null
  bone_mass_kg: number | null
  water_percent: number | null
  visceral_fat: number | null
  metabolic_age: number | null
  systolic_bp: number | null
  diastolic_bp: number | null
  pulse: number | null
  created_at: string
}

export interface HydrationRecord {
  id: number
  source: string
  recorded_at: string
  amount_ml: number | null
  daily_total_ml: number | null
  daily_goal_ml: number | null
  created_at: string
}

export interface DashboardSummary {
  latest_sleep: SleepRecord | null
  latest_body_metric: BodyMetric | null
  latest_activity: ActivityRecord | null
  avg_sleep_duration_7d: number | null
  avg_sleep_score_7d: number | null
  avg_hrv_7d: number | null
  avg_recovery_score_7d: number | null
  total_calories_7d: number | null
  avg_daily_calories_7d: number | null
  total_steps_7d: number | null
  avg_hydration_7d: number | null
  weight_trend: { date: string; value: number }[]
  sleep_trend: { date: string; duration: number; score: number; hrv: number; recovery: number }[]
  activity_trend: { date: string; calories: number; strain: number; type: string }[]
  hrv_trend: { date: string; hrv: number }[]
  connected_integrations: number
}

export interface LabTestResult {
  id: number
  biomarker_name: string
  value: number | null
  unit: string | null
  reference_min: number | null
  reference_max: number | null
  reference_text: string | null
  status: string | null
  category: string | null
  interpretation: string | null
}

export interface LabTest {
  id: number
  test_name: string
  lab_name: string | null
  ordered_by: string | null
  test_date: string | null
  file_name: string | null
  notes: string | null
  parsed_summary: string | null
  status: string
  results: LabTestResult[]
  created_at: string
}

export interface Integration {
  platform: string
  name: string
  description: string
  auth_type: string
  data_types: string[]
  is_connected: boolean
  is_active: boolean
  platform_username: string | null
  last_synced_at: string | null
  auto_sync: boolean
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp?: string
}
