import React, { useEffect, useState } from 'react'
import {
  Moon, Zap, Dumbbell, Droplets, Scale, Heart, RefreshCw, TrendingUp, Activity
} from 'lucide-react'
import {
  LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, BarChart, Bar, Legend
} from 'recharts'
import MetricCard from '../components/cards/MetricCard'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import { healthApi, aiApi } from '../services/api'
import type { DashboardSummary } from '../types'
import { format } from 'date-fns'

const CustomTooltip = ({ active, payload, label }: { active?: boolean; payload?: { color: string; name: string; value: number }[]; label?: string }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-surface-800 border border-surface-700 rounded-lg p-3 text-xs">
        <p className="text-slate-400 mb-1">{label}</p>
        {payload.map((p, i) => (
          <p key={i} style={{ color: p.color }}>{p.name}: {typeof p.value === 'number' ? p.value.toFixed(1) : p.value}</p>
        ))}
      </div>
    )
  }
  return null
}

export default function Dashboard() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null)
  const [insights, setInsights] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [insightsLoading, setInsightsLoading] = useState(false)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    setLoading(true)
    try {
      const res = await healthApi.dashboard()
      setSummary(res.data)
    } catch (e) {
      console.error('Dashboard load error:', e)
    } finally {
      setLoading(false)
    }
  }

  const loadInsights = async () => {
    setInsightsLoading(true)
    try {
      const res = await aiApi.insights()
      setInsights(res.data.insights)
    } catch (e) {
      console.error('Insights error:', e)
    } finally {
      setInsightsLoading(false)
    }
  }

  if (loading) return <LoadingSpinner className="h-64" />

  if (!summary) return (
    <div className="text-center py-20">
      <Activity className="w-12 h-12 text-slate-600 mx-auto mb-4" />
      <h3 className="text-lg font-medium text-slate-400">No health data yet</h3>
      <p className="text-slate-600 mt-1 text-sm">Connect your health devices in Integrations to get started.</p>
    </div>
  )

  const formatDate = (d: string) => {
    try { return format(new Date(d), 'MMM d') } catch { return d }
  }
  const formatMinutes = (m: number | null | undefined) => {
    if (!m) return '—'
    const h = Math.floor(m / 60), min = m % 60
    return `${h}h ${min}m`
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Dashboard</h1>
          <p className="text-slate-500 text-sm">Your health overview</p>
        </div>
        <div className="flex gap-2">
          <button onClick={loadInsights} disabled={insightsLoading} className="btn-secondary flex items-center gap-2 text-sm">
            <TrendingUp className="w-4 h-4" />
            {insightsLoading ? 'Analyzing...' : 'AI Insights'}
          </button>
          <button onClick={loadData} className="btn-ghost">
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* AI Insights */}
      {insights && (
        <div className="card border-brand-500/30 bg-brand-500/5">
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-lg bg-brand-500/20 flex items-center justify-center flex-shrink-0">
              <TrendingUp className="w-4 h-4 text-brand-400" />
            </div>
            <div>
              <p className="text-sm font-medium text-brand-400 mb-2">AI Health Brief</p>
              <p className="text-sm text-slate-300 whitespace-pre-wrap leading-relaxed">{insights}</p>
            </div>
          </div>
        </div>
      )}

      {/* Metric cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Sleep Duration"
          value={summary.avg_sleep_duration_7d ? Math.round(summary.avg_sleep_duration_7d) : null}
          unit="min avg"
          subtitle={summary.avg_sleep_duration_7d ? formatMinutes(Math.round(summary.avg_sleep_duration_7d)) : '7-day avg'}
          icon={Moon}
          color="blue"
        />
        <MetricCard
          title="Recovery Score"
          value={summary.avg_recovery_score_7d ? Math.round(summary.avg_recovery_score_7d) : null}
          unit="%"
          subtitle="7-day average"
          icon={Zap}
          color="green"
        />
        <MetricCard
          title="HRV"
          value={summary.avg_hrv_7d ? Math.round(summary.avg_hrv_7d) : null}
          unit="ms"
          subtitle="7-day average"
          icon={Heart}
          color="purple"
        />
        <MetricCard
          title="Daily Calories"
          value={summary.avg_daily_calories_7d ? Math.round(summary.avg_daily_calories_7d) : null}
          unit="kcal"
          subtitle="7-day average"
          icon={Dumbbell}
          color="orange"
        />
        <MetricCard
          title="Weight"
          value={summary.latest_body_metric?.weight_kg}
          unit="kg"
          subtitle={summary.latest_body_metric?.measured_at ? `As of ${formatDate(summary.latest_body_metric.measured_at)}` : 'Latest'}
          icon={Scale}
          color="teal"
        />
        <MetricCard
          title="Body Fat"
          value={summary.latest_body_metric?.body_fat_percent}
          unit="%"
          subtitle="Latest measurement"
          icon={Activity}
          color="red"
        />
        <MetricCard
          title="Hydration"
          value={summary.avg_hydration_7d ? Math.round(summary.avg_hydration_7d) : null}
          unit="ml/day"
          subtitle="7-day average"
          icon={Droplets}
          color="blue"
        />
        <MetricCard
          title="Steps"
          value={summary.total_steps_7d ? Math.round(summary.total_steps_7d / 7) : null}
          unit="steps/day"
          subtitle="7-day average"
          icon={Activity}
          color="green"
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Sleep Chart */}
        {summary.sleep_trend.length > 0 && (
          <div className="card">
            <h3 className="text-sm font-semibold text-slate-200 mb-4">Sleep Quality (30 days)</h3>
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={summary.sleep_trend.map(d => ({ ...d, date: formatDate(d.date) }))}>
                <defs>
                  <linearGradient id="sleepGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#60a5fa" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#60a5fa" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="recoveryGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#4ade80" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#4ade80" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 11 }} tickLine={false} />
                <YAxis tick={{ fill: '#64748b', fontSize: 11 }} tickLine={false} axisLine={false} />
                <Tooltip content={<CustomTooltip />} />
                <Legend wrapperStyle={{ fontSize: '11px', color: '#94a3b8' }} />
                <Area type="monotone" dataKey="score" stroke="#60a5fa" fill="url(#sleepGrad)" name="Sleep Score" strokeWidth={2} dot={false} />
                <Area type="monotone" dataKey="recovery" stroke="#4ade80" fill="url(#recoveryGrad)" name="Recovery" strokeWidth={2} dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* HRV Chart */}
        {summary.hrv_trend.length > 0 && (
          <div className="card">
            <h3 className="text-sm font-semibold text-slate-200 mb-4">HRV Trend (30 days)</h3>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={summary.hrv_trend.map(d => ({ ...d, date: formatDate(d.date) }))}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 11 }} tickLine={false} />
                <YAxis tick={{ fill: '#64748b', fontSize: 11 }} tickLine={false} axisLine={false} />
                <Tooltip content={<CustomTooltip />} />
                <Line type="monotone" dataKey="hrv" stroke="#c084fc" strokeWidth={2} dot={false} name="HRV (ms)" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Weight Chart */}
        {summary.weight_trend.length > 0 && (
          <div className="card">
            <h3 className="text-sm font-semibold text-slate-200 mb-4">Weight Trend (30 days)</h3>
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={summary.weight_trend.map(d => ({ ...d, date: formatDate(d.date) }))}>
                <defs>
                  <linearGradient id="weightGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#2dd4bf" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#2dd4bf" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 11 }} tickLine={false} />
                <YAxis tick={{ fill: '#64748b', fontSize: 11 }} tickLine={false} axisLine={false} domain={['auto', 'auto']} />
                <Tooltip content={<CustomTooltip />} />
                <Area type="monotone" dataKey="value" stroke="#2dd4bf" fill="url(#weightGrad)" name="Weight (kg)" strokeWidth={2} dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Activity Chart */}
        {summary.activity_trend.length > 0 && (
          <div className="card">
            <h3 className="text-sm font-semibold text-slate-200 mb-4">Activity (30 days)</h3>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={summary.activity_trend.map(d => ({ ...d, date: formatDate(d.date) }))}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 11 }} tickLine={false} />
                <YAxis tick={{ fill: '#64748b', fontSize: 11 }} tickLine={false} axisLine={false} />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="calories" fill="#fb923c" name="Calories" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Latest sleep breakdown */}
      {summary.latest_sleep && (
        <div className="card">
          <h3 className="text-sm font-semibold text-slate-200 mb-4">Last Night's Sleep Breakdown</h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {[
              { label: 'Deep', value: summary.latest_sleep.deep_sleep_minutes, color: 'bg-blue-600' },
              { label: 'REM', value: summary.latest_sleep.rem_sleep_minutes, color: 'bg-purple-500' },
              { label: 'Light', value: summary.latest_sleep.light_sleep_minutes, color: 'bg-blue-400' },
              { label: 'Awake', value: summary.latest_sleep.awake_minutes, color: 'bg-slate-600' },
            ].map(({ label, value, color }) => (
              <div key={label} className="flex flex-col gap-2">
                <div className="flex items-center gap-2">
                  <div className={`w-2.5 h-2.5 rounded-full ${color}`} />
                  <span className="text-xs text-slate-500">{label}</span>
                </div>
                <span className="text-lg font-semibold text-white">{formatMinutes(value)}</span>
                <div className="w-full h-1 bg-surface-700 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${color}`}
                    style={{ width: `${Math.min(100, ((value || 0) / (summary.latest_sleep!.total_duration_minutes || 1)) * 100)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
          <div className="mt-4 grid grid-cols-3 gap-4 pt-4 border-t border-surface-700/50">
            <div>
              <p className="text-xs text-slate-500">HRV</p>
              <p className="text-base font-semibold text-white">{summary.latest_sleep.hrv?.toFixed(1) || '—'} ms</p>
            </div>
            <div>
              <p className="text-xs text-slate-500">SpO2</p>
              <p className="text-base font-semibold text-white">{summary.latest_sleep.avg_spo2?.toFixed(1) || '—'} %</p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Resp Rate</p>
              <p className="text-base font-semibold text-white">{summary.latest_sleep.respiratory_rate?.toFixed(1) || '—'} brpm</p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
