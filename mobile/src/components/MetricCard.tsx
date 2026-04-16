import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

interface Props {
  label: string;
  value: string | number | null | undefined;
  unit?: string;
  color?: string;
  subtitle?: string;
}

export function MetricCard({ label, value, unit, color = '#0ea5e9', subtitle }: Props) {
  const display = value === null || value === undefined ? '—' : String(value);

  return (
    <View style={[styles.card, { borderLeftColor: color }]}>
      <Text style={styles.label}>{label}</Text>
      <View style={styles.row}>
        <Text style={[styles.value, { color }]}>{display}</Text>
        {unit ? <Text style={styles.unit}> {unit}</Text> : null}
      </View>
      {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#1e293b',
    borderRadius: 12,
    padding: 16,
    borderLeftWidth: 4,
    marginBottom: 12,
    flex: 1,
    marginHorizontal: 6,
  },
  label: {
    color: '#94a3b8',
    fontSize: 12,
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: 6,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'baseline',
  },
  value: {
    fontSize: 28,
    fontWeight: '700',
  },
  unit: {
    color: '#94a3b8',
    fontSize: 14,
  },
  subtitle: {
    color: '#64748b',
    fontSize: 11,
    marginTop: 4,
  },
});
