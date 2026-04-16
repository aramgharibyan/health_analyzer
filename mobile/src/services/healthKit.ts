/**
 * Apple HealthKit integration for iOS.
 * Uses react-native-health to request permissions and read data,
 * then posts to the backend /api/integrations/apple-health/sync-native endpoint.
 *
 * On Android this module exports no-op stubs so the rest of the app compiles fine.
 */
import { Platform } from 'react-native';
import { integrationApi } from './api';

// ── iOS-only block ─────────────────────────────────────────────────────────────

let AppleHealthKit: any = null;
let Permissions: any = {};

if (Platform.OS === 'ios') {
  const rnh = require('react-native-health');
  AppleHealthKit = rnh.default;
  Permissions = rnh.HealthKitPermissions ?? AppleHealthKit.Constants?.Permissions ?? {};
}

// ── Permission set ─────────────────────────────────────────────────────────────

const READ_PERMISSIONS = [
  'Steps',
  'FlightsClimbed',
  'DistanceWalkingRunning',
  'HeartRate',
  'RestingHeartRate',
  'HeartRateVariability',
  'OxygenSaturation',
  'RespiratoryRate',
  'ActiveEnergyBurned',
  'BasalEnergyBurned',
  'SleepAnalysis',
  'Weight',
  'BodyFatPercentage',
  'BodyMassIndex',
  'LeanBodyMass',
  'BloodPressureSystolic',
  'BloodPressureDiastolic',
  'VO2Max',
  'DietaryEnergyConsumed',
  'DietaryProtein',
  'DietaryCarbohydrates',
  'DietaryFatTotal',
  'DietaryFiber',
  'DietaryWater',
  'Workout',
];

// ── Init / permission request ──────────────────────────────────────────────────

export function isHealthKitAvailable(): boolean {
  return Platform.OS === 'ios' && AppleHealthKit !== null;
}

export function requestPermissions(): Promise<void> {
  if (!isHealthKitAvailable()) return Promise.resolve();

  return new Promise((resolve, reject) => {
    const options = {
      permissions: {
        read: READ_PERMISSIONS.map((p) => Permissions[p]).filter(Boolean),
        write: [],
      },
    };
    AppleHealthKit.initHealthKit(options, (err: Error | null) => {
      if (err) reject(err);
      else resolve();
    });
  });
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function startOf(daysAgo: number): string {
  const d = new Date();
  d.setDate(d.getDate() - daysAgo);
  d.setHours(0, 0, 0, 0);
  return d.toISOString();
}

function promisify<T>(fn: (opts: object, cb: (err: Error | null, result: T) => void) => void, opts: object): Promise<T> {
  return new Promise((resolve, reject) =>
    fn(opts, (err, result) => (err ? reject(err) : resolve(result)))
  );
}

// ── Per-metric fetch helpers ───────────────────────────────────────────────────

async function fetchSamples(method: string, startDate: string): Promise<any[]> {
  if (!isHealthKitAvailable()) return [];
  try {
    return await promisify<any[]>(
      AppleHealthKit[method].bind(AppleHealthKit),
      { startDate, limit: 5000, ascending: true }
    );
  } catch {
    return [];
  }
}

async function fetchDailySamples(method: string, startDate: string): Promise<any[]> {
  return fetchSamples(method, startDate);
}

// ── Main sync function ─────────────────────────────────────────────────────────

export async function syncToBackend(days = 30): Promise<{ records_synced: number }> {
  if (!isHealthKitAvailable()) {
    throw new Error('Apple Health is only available on iOS.');
  }

  await requestPermissions();
  const startDate = startOf(days);

  // Fetch all metrics in parallel
  const [
    steps,
    heartRate,
    restingHR,
    hrv,
    spo2,
    respiratoryRate,
    activeCalories,
    basalCalories,
    distanceWalking,
    weight,
    bodyFat,
    bmi,
    systolic,
    diastolic,
    dietaryCalories,
    protein,
    carbs,
    fat,
    fiber,
    water,
    sleepSamples,
    workouts,
  ] = await Promise.all([
    fetchDailySamples('getDailyStepCountSamples', startDate),
    fetchSamples('getHeartRateSamples', startDate),
    fetchSamples('getRestingHeartRate', startDate),
    fetchSamples('getHeartRateVariabilitySamples', startDate),
    fetchSamples('getOxygenSaturationSamples', startDate),
    fetchSamples('getRespiratoryRateSamples', startDate),
    fetchDailySamples('getActiveEnergyBurned', startDate),
    fetchDailySamples('getBasalEnergyBurned', startDate),
    fetchDailySamples('getDailyDistanceWalkingRunningSamples', startDate),
    fetchSamples('getWeightSamples', startDate),
    fetchSamples('getBodyFatPercentageSamples', startDate),
    fetchSamples('getBMISamples', startDate),
    fetchSamples('getBloodPressureSamples', startDate),  // returns systolic
    fetchSamples('getBloodPressureSamples', startDate),  // returns diastolic (same call)
    fetchDailySamples('getDailyCalorieSamples', startDate),
    fetchSamples('getProteinSamples', startDate),
    fetchSamples('getCarbsSamples', startDate),
    fetchSamples('getFatSamples', startDate),
    fetchSamples('getFiberSamples', startDate),
    fetchDailySamples('getDailyWaterSamples', startDate),
    fetchSamples('getSleepSamples', startDate),
    promisify<any[]>(AppleHealthKit.getSamples.bind(AppleHealthKit), {
      type: 'Workout',
      startDate,
      limit: 500,
    }).catch(() => []),
  ]);

  // Shape into Health Auto Export JSON format (same as webhook handler)
  const toMetric = (name: string, units: string, samples: any[], valueKey = 'value') => ({
    name,
    units,
    data: samples.map((s) => ({ date: s.startDate ?? s.end_date, qty: s[valueKey] })),
  });

  const metrics = [
    toMetric('step_count', 'count', steps),
    toMetric('heart_rate', 'bpm', heartRate),
    toMetric('resting_heart_rate', 'bpm', restingHR),
    toMetric('heart_rate_variability', 'ms', hrv),
    toMetric('oxygen_saturation', '%', spo2),
    toMetric('respiratory_rate', 'breaths/min', respiratoryRate),
    toMetric('active_energy', 'kcal', activeCalories),
    toMetric('basal_body_temperature', 'kcal', basalCalories),
    toMetric('walking_running_distance', 'km', distanceWalking),
    toMetric('weight_body_mass', 'kg', weight),
    toMetric('body_fat_percentage', '%', bodyFat),
    toMetric('bmi', 'count', bmi),
    toMetric('dietary_energy', 'kcal', dietaryCalories),
    toMetric('protein', 'g', protein),
    toMetric('carbohydrates', 'g', carbs),
    toMetric('total_fat', 'g', fat),
    toMetric('fiber', 'g', fiber),
    toMetric('water', 'mL', water),
    // Sleep: shape differently — backend _process_health_auto_export handles arrays
    {
      name: 'sleep_analysis',
      units: 'min',
      data: sleepSamples.map((s) => ({
        date: s.startDate,
        qty: s.value,
        endDate: s.endDate,
      })),
    },
    // Blood pressure: combine systolic/diastolic pairs
    ...systolic.map((s: any) => ({
      name: 'blood_pressure_systolic',
      units: 'mmHg',
      data: [{ date: s.startDate, qty: s.bloodPressureSystolicValue ?? s.value }],
    })),
  ];

  // Workouts
  const formattedWorkouts = workouts.map((w: any) => ({
    name: w.activityName ?? w.type ?? 'Workout',
    start: w.startDate,
    end: w.endDate,
    duration: w.duration,
    activeEnergy: w.calories,
    distance: w.distance,
  }));

  const payload = { data: { metrics, workouts: formattedWorkouts } };
  const response = await integrationApi.appleHealthSyncNative(payload);
  return response.data;
}
