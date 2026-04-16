import React from 'react';
import { View, Text, StyleSheet, Dimensions } from 'react-native';
import { VictoryChart, VictoryLine, VictoryArea, VictoryAxis, VictoryTheme } from 'victory-native';

interface DataPoint {
  date: string;
  value: number;
}

interface Props {
  title: string;
  data: DataPoint[];
  color?: string;
  unit?: string;
  area?: boolean;
}

const WIDTH = Dimensions.get('window').width - 48;

export function TrendChart({ title, data, color = '#0ea5e9', unit = '', area = false }: Props) {
  if (!data || data.length === 0) {
    return (
      <View style={styles.empty}>
        <Text style={styles.emptyText}>No data for {title}</Text>
      </View>
    );
  }

  const chartData = data.map((d, i) => ({ x: i + 1, y: d.value }));
  const ChartComponent = area ? VictoryArea : VictoryLine;

  return (
    <View style={styles.container}>
      <Text style={styles.title}>{title}</Text>
      <VictoryChart
        width={WIDTH}
        height={180}
        theme={VictoryTheme.material}
        padding={{ top: 10, bottom: 30, left: 40, right: 10 }}
      >
        <VictoryAxis
          tickFormat={(t) => {
            const item = data[Math.round(t) - 1];
            if (!item) return '';
            return new Date(item.date).toLocaleDateString('en', { month: 'short', day: 'numeric' });
          }}
          tickCount={4}
          style={{
            axis: { stroke: '#334155' },
            tickLabels: { fill: '#64748b', fontSize: 10 },
            grid: { stroke: 'transparent' },
          }}
        />
        <VictoryAxis
          dependentAxis
          tickFormat={(t) => `${t}${unit}`}
          style={{
            axis: { stroke: '#334155' },
            tickLabels: { fill: '#64748b', fontSize: 10 },
            grid: { stroke: '#1e293b' },
          }}
        />
        <ChartComponent
          data={chartData}
          style={{
            data: {
              stroke: color,
              strokeWidth: 2,
              fill: area ? `${color}33` : undefined,
            },
          }}
          interpolation="monotoneX"
        />
      </VictoryChart>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: '#1e293b',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
  },
  title: {
    color: '#e2e8f0',
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 4,
  },
  empty: {
    backgroundColor: '#1e293b',
    borderRadius: 12,
    padding: 24,
    alignItems: 'center',
    marginBottom: 16,
  },
  emptyText: {
    color: '#64748b',
    fontSize: 13,
  },
});
