import React, { useEffect, useState, useCallback } from 'react';
import {
  ScrollView, View, Text, StyleSheet,
  RefreshControl, ActivityIndicator,
} from 'react-native';
import { healthApi } from '../services/api';
import { DashboardSummary } from '../types';
import { MetricCard } from '../components/MetricCard';
import { TrendChart } from '../components/TrendChart';

function fmt(val: number | null | undefined, decimals = 0): string {
  if (val === null || val === undefined) return '—';
  return val.toFixed(decimals);
}

export function DashboardScreen() {
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    try {
      const res = await healthApi.dashboard();
      setData(res.data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#0ea5e9" />
      </View>
    );
  }

  const sleepHours = data?.avg_sleep_duration_7d
    ? (data.avg_sleep_duration_7d / 60).toFixed(1)
    : null;

  return (
    <ScrollView
      style={styles.screen}
      contentContainerStyle={styles.content}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={() => load(true)}
          tintColor="#0ea5e9"
        />
      }
    >
      <Text style={styles.sectionTitle}>7-Day Averages</Text>
      <View style={styles.cardRow}>
        <MetricCard label="Sleep" value={sleepHours} unit="hrs" color="#8b5cf6" />
        <MetricCard label="HRV" value={fmt(data?.avg_hrv_7d, 0)} unit="ms" color="#10b981" />
      </View>
      <View style={styles.cardRow}>
        <MetricCard label="Calories" value={fmt(data?.avg_daily_calories_7d, 0)} unit="kcal" color="#f59e0b" />
        <MetricCard label="Steps" value={data?.total_steps_7d ? Math.round(data.total_steps_7d / 7).toLocaleString() : null} color="#0ea5e9" />
      </View>
      <View style={styles.cardRow}>
        <MetricCard label="Recovery" value={fmt(data?.avg_recovery_score_7d, 0)} unit="%" color="#ef4444" />
        <MetricCard label="Hydration" value={fmt(data?.avg_hydration_7d, 0)} unit="mL" color="#06b6d4" />
      </View>

      {(data?.latest_body_metric?.weight_kg) && (
        <>
          <Text style={styles.sectionTitle}>Body</Text>
          <View style={styles.cardRow}>
            <MetricCard
              label="Weight"
              value={fmt(data.latest_body_metric.weight_kg, 1)}
              unit="kg"
              color="#f97316"
            />
            <MetricCard
              label="Body Fat"
              value={fmt(data.latest_body_metric.body_fat_percent, 1)}
              unit="%"
              color="#ec4899"
            />
          </View>
        </>
      )}

      <Text style={styles.sectionTitle}>Trends</Text>

      <TrendChart
        title="Sleep Duration"
        data={data?.sleep_trend?.map((d) => ({ date: d.date, value: +(d.duration / 60).toFixed(1) })) ?? []}
        color="#8b5cf6"
        unit="h"
        area
      />
      <TrendChart
        title="HRV"
        data={data?.hrv_trend?.map((d) => ({ date: d.date, value: d.hrv })) ?? []}
        color="#10b981"
        unit="ms"
      />
      <TrendChart
        title="Weight"
        data={data?.weight_trend?.map((d) => ({ date: d.date, value: d.value })) ?? []}
        color="#f97316"
        unit="kg"
      />
      <TrendChart
        title="Activity Calories"
        data={data?.activity_trend?.map((d) => ({ date: d.date, value: d.calories })) ?? []}
        color="#f59e0b"
        unit="kcal"
        area
      />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: '#0f172a' },
  content: { padding: 16 },
  center: { flex: 1, backgroundColor: '#0f172a', alignItems: 'center', justifyContent: 'center' },
  sectionTitle: {
    color: '#94a3b8',
    fontSize: 12,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 1,
    marginTop: 8,
    marginBottom: 8,
  },
  cardRow: { flexDirection: 'row', marginHorizontal: -6, marginBottom: 0 },
});
