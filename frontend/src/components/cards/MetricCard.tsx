import React from 'react'
import clsx from 'clsx'
import type { LucideIcon } from 'lucide-react'

interface MetricCardProps {
  title: string
  value: string | number | null | undefined
  unit?: string
  icon: LucideIcon
  trend?: number | null
  subtitle?: string
  color?: 'green' | 'blue' | 'purple' | 'orange' | 'red' | 'teal'
  size?: 'sm' | 'md'
}

const colorMap = {
  green: { bg: 'bg-brand-500/15', text: 'text-brand-400', icon: 'text-brand-400' },
  blue: { bg: 'bg-blue-500/15', text: 'text-blue-400', icon: 'text-blue-400' },
  purple: { bg: 'bg-purple-500/15', text: 'text-purple-400', icon: 'text-purple-400' },
  orange: { bg: 'bg-orange-500/15', text: 'text-orange-400', icon: 'text-orange-400' },
  red: { bg: 'bg-red-500/15', text: 'text-red-400', icon: 'text-red-400' },
  teal: { bg: 'bg-teal-500/15', text: 'text-teal-400', icon: 'text-teal-400' },
}

export default function MetricCard({
  title, value, unit, icon: Icon, trend, subtitle, color = 'green', size = 'md'
}: MetricCardProps) {
  const colors = colorMap[color]
  const hasValue = value !== null && value !== undefined

  return (
    <div className="card flex flex-col gap-3">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">{title}</p>
          <div className="mt-1 flex items-baseline gap-1.5">
            {hasValue ? (
              <>
                <span className={clsx('font-bold', size === 'md' ? 'text-2xl' : 'text-xl', 'text-white')}>
                  {typeof value === 'number' ? value.toLocaleString(undefined, { maximumFractionDigits: 1 }) : value}
                </span>
                {unit && <span className="text-sm text-slate-500">{unit}</span>}
              </>
            ) : (
              <span className="text-slate-600 text-lg">—</span>
            )}
          </div>
          {subtitle && <p className="text-xs text-slate-500 mt-0.5">{subtitle}</p>}
        </div>
        <div className={clsx('p-2.5 rounded-lg', colors.bg)}>
          <Icon className={clsx('w-5 h-5', colors.icon)} />
        </div>
      </div>

      {trend !== null && trend !== undefined && (
        <div className="flex items-center gap-1">
          <span className={clsx(
            'text-xs font-medium',
            trend > 0 ? 'text-brand-400' : trend < 0 ? 'text-red-400' : 'text-slate-500'
          )}>
            {trend > 0 ? '↑' : trend < 0 ? '↓' : '→'} {Math.abs(trend).toFixed(1)}%
          </span>
          <span className="text-xs text-slate-600">vs last week</span>
        </div>
      )}
    </div>
  )
}
