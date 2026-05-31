import React, { useEffect, useState, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  CheckCircle, XCircle, RefreshCw, Link2, Link2Off, Upload,
  ChevronDown, ChevronUp, Clock, Copy, Check, Info, Webhook, AlertTriangle
} from 'lucide-react'
import { integrationsApi } from '../services/api'
import type { Integration } from '../types'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import { format } from 'date-fns'
import clsx from 'clsx'

const PLATFORM_ICONS: Record<string, string> = {
  whoop: '🔴',
  withings: '⚖️',
  fitbod: '💪',
  yazio: '🥗',
  renpho: '📊',
  braun: '🩺',
  larq: '💧',
  apple_health: '🍎',
}

const AUTH_TYPE_LABELS: Record<string, string> = {
  oauth2: 'OAuth2 (Secure)',
  credentials: 'Email & Password',
  api_key: 'API Key',
  export: 'File Export / Webhook',
}

interface SyncEndpointError {
  status?: number
  body?: string
  error?: string
}

interface SyncDetails {
  counts?: Record<string, number>
  errors?: Record<string, SyncEndpointError>
  granted_scope?: string | null
}

interface SyncState {
  loading: boolean
  result: string | null
  ok?: boolean
  details?: SyncDetails
  uploadPct?: number
}

// Whoop OAuth scope required to read each resource — used to explain failures.
const WHOOP_RESOURCE_SCOPE: Record<string, string> = {
  recovery: 'read:recovery',
  sleep: 'read:sleep',
  workout: 'read:workout',
  cycle: 'read:cycles',
  body: 'read:body_measurement',
}

const RESOURCE_LABELS: Record<string, string> = {
  recovery: 'Recovery (HRV)',
  sleep: 'Sleep',
  workout: 'Workouts',
  cycle: 'Daily strain',
  body: 'Body / weight',
}

// ── Apple Health panel ────────────────────────────────────────────────────────

function AppleHealthPanel({
  integration,
  onImported,
}: {
  integration: Integration
  onImported: () => void
}) {
  const [uploadPct, setUploadPct] = useState<number | null>(null)
  const [result, setResult] = useState<{ ok: boolean; text: string } | null>(null)
  const [webhookToken, setWebhookToken] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)

  const handleFile = async (file: File) => {
    setResult(null)
    setUploadPct(0)
    try {
      const res = await integrationsApi.appleHealthImport(file, (pct) => setUploadPct(pct))
      const d = res.data
      setResult({
        ok: true,
        text: `Imported ${d.records_imported.toLocaleString()} records — `
          + `${d.breakdown.sleep_sessions} sleep sessions, `
          + `${d.breakdown.workouts} workouts, `
          + `${d.breakdown.nutrition_days} nutrition days, `
          + `${d.breakdown.metrics.toLocaleString()} metrics.`,
      })
      onImported()
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Import failed — make sure you uploaded the Apple Health ZIP or export.xml.'
      setResult({ ok: false, text: msg })
    } finally {
      setUploadPct(null)
    }
  }

  const fetchToken = async () => {
    try {
      const res = await integrationsApi.appleHealthWebhookToken()
      setWebhookToken(res.data.token)
    } catch {
      setWebhookToken('error')
    }
  }

  const copyToken = () => {
    if (webhookToken) {
      navigator.clipboard.writeText(
        `${window.location.origin}/api/integrations/apple-health/webhook?token=${webhookToken}`
      )
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  return (
    <div className="mt-4 pt-4 border-t border-surface-700/50 space-y-5">

      {/* ── Method 1: Export ZIP ─────────────────────────────────── */}
      <div>
        <p className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-3">
          Method 1 — Export from the Health app
        </p>
        <ol className="space-y-1.5 text-xs text-slate-400 mb-4 list-decimal list-inside">
          <li>Open the <strong className="text-slate-300">Health</strong> app on your iPhone</li>
          <li>Tap your <strong className="text-slate-300">profile picture</strong> (top-right)</li>
          <li>Scroll down and tap <strong className="text-slate-300">Export All Health Data</strong></li>
          <li>Tap <strong className="text-slate-300">Export</strong> in the confirmation dialog</li>
          <li>Share the <code className="text-brand-400 bg-surface-800 px-1 rounded">export.zip</code> to your computer and upload it below</li>
        </ol>

        <div
          className={clsx(
            'border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-colors',
            uploadPct !== null
              ? 'border-brand-500/50 bg-brand-500/5 cursor-default'
              : 'border-surface-700 hover:border-brand-500/40 hover:bg-surface-800/50'
          )}
          onClick={() => uploadPct === null && fileRef.current?.click()}
        >
          <input
            type="file"
            accept=".zip,.xml"
            className="hidden"
            ref={fileRef}
            onChange={e => {
              const file = e.target.files?.[0]
              if (file) handleFile(file)
              e.target.value = ''
            }}
          />

          {uploadPct !== null ? (
            <div className="space-y-3">
              <div className="text-sm text-slate-300 font-medium">
                {uploadPct < 100 ? `Uploading… ${uploadPct}%` : 'Parsing health data…'}
              </div>
              <div className="w-full bg-surface-700 rounded-full h-2 overflow-hidden">
                <div
                  className="h-full bg-brand-500 rounded-full transition-all duration-300"
                  style={{ width: `${uploadPct < 100 ? uploadPct : 100}%` }}
                />
              </div>
              {uploadPct === 100 && (
                <p className="text-xs text-slate-500">
                  Processing export.xml — this can take a minute for large exports…
                </p>
              )}
            </div>
          ) : (
            <>
              <Upload className="w-8 h-8 text-slate-600 mx-auto mb-2" />
              <p className="text-sm text-slate-400">
                Drop <code className="text-brand-400">export.zip</code> or{' '}
                <code className="text-brand-400">export.xml</code> here, or click to browse
              </p>
              <p className="text-xs text-slate-600 mt-1">
                Large exports (100–500 MB) are supported
              </p>
            </>
          )}
        </div>

        {result && (
          <div className={clsx(
            'mt-3 px-3 py-2.5 rounded-lg text-xs leading-relaxed',
            result.ok
              ? 'bg-brand-500/10 border border-brand-500/20 text-brand-400'
              : 'bg-red-500/10 border border-red-500/20 text-red-400'
          )}>
            {result.ok ? <CheckCircle className="inline w-3.5 h-3.5 mr-1.5 mb-0.5" /> : null}
            {result.text}
          </div>
        )}
      </div>

      {/* ── Divider ──────────────────────────────────────────────── */}
      <div className="flex items-center gap-3">
        <div className="flex-1 h-px bg-surface-700" />
        <span className="text-xs text-slate-600">or</span>
        <div className="flex-1 h-px bg-surface-700" />
      </div>

      {/* ── Method 2: Health Auto Export webhook ─────────────────── */}
      <div>
        <p className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-3">
          Method 2 — Real-time sync via Health Auto Export
        </p>
        <div className="bg-surface-800 rounded-lg p-4 space-y-3">
          <div className="flex gap-2">
            <Info className="w-4 h-4 text-blue-400 flex-shrink-0 mt-0.5" />
            <p className="text-xs text-slate-400 leading-relaxed">
              Install <strong className="text-slate-300">Health Auto Export</strong> (free on the App Store).
              It reads HealthKit data on a schedule and POSTs it directly to this app —
              no manual exports needed.
            </p>
          </div>
          <ol className="space-y-1.5 text-xs text-slate-400 list-decimal list-inside">
            <li>Download <strong className="text-slate-300">Health Auto Export — JSON+CSV</strong> from the App Store</li>
            <li>Open the app → <strong className="text-slate-300">REST API</strong> tab</li>
            <li>Toggle <strong className="text-slate-300">REST API</strong> on</li>
            <li>Paste the webhook URL below into the <strong className="text-slate-300">URL</strong> field</li>
            <li>Set your preferred sync interval (hourly recommended)</li>
          </ol>

          {!webhookToken ? (
            <button
              onClick={fetchToken}
              className="btn-secondary text-xs flex items-center gap-2"
            >
              <Webhook className="w-3.5 h-3.5" />
              Generate webhook URL
            </button>
          ) : webhookToken === 'error' ? (
            <p className="text-xs text-red-400">Failed to generate token — try again</p>
          ) : (
            <div className="space-y-2">
              <p className="text-xs text-slate-500">Your webhook URL (contains your auth token — keep it private):</p>
              <div className="flex items-center gap-2">
                <code className="flex-1 text-xs bg-surface-900 border border-surface-700 rounded-lg px-3 py-2 text-brand-400 break-all">
                  {window.location.origin}/api/integrations/apple-health/webhook?token={webhookToken.slice(0, 24)}…
                </code>
                <button
                  onClick={copyToken}
                  className="btn-secondary flex items-center gap-1.5 text-xs flex-shrink-0"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-brand-400" /> : <Copy className="w-3.5 h-3.5" />}
                  {copied ? 'Copied!' : 'Copy'}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Meta row ─────────────────────────────────────────────── */}
      {integration.last_synced_at && (
        <div className="flex items-center gap-1.5 text-xs text-slate-500">
          <Clock className="w-3 h-3" />
          Last import: {format(new Date(integration.last_synced_at), 'MMM d, yyyy HH:mm')}
        </div>
      )}
    </div>
  )
}

// ── Sync result + diagnostics ─────────────────────────────────────────────────

function SyncResult({ platform, state }: { platform: string; state: SyncState }) {
  const details = state.details
  const errors = details?.errors ?? {}
  const counts = details?.counts ?? {}
  const errorKeys = Object.keys(errors)
  const hasErrors = errorKeys.length > 0
  const grantedScope = details?.granted_scope ?? null

  // Whoop: flag endpoints that failed because the OAuth grant lacks the scope.
  const missingScopeResources =
    platform === 'whoop' && grantedScope !== null
      ? errorKeys.filter(r => {
          const needed = WHOOP_RESOURCE_SCOPE[r]
          return needed && !grantedScope.split(/\s+/).includes(needed)
        })
      : []

  const tone = state.ok ? 'ok' : hasErrors ? 'warn' : 'error'

  return (
    <div className="mt-3 space-y-2">
      {/* Headline banner */}
      <div className={clsx(
        'px-3 py-2 rounded-lg text-xs flex items-center gap-2',
        tone === 'ok' && 'bg-brand-500/10 text-brand-400',
        tone === 'warn' && 'bg-amber-500/10 text-amber-400',
        tone === 'error' && 'bg-red-500/10 text-red-400',
      )}>
        {tone === 'ok'
          ? <CheckCircle className="w-3.5 h-3.5 flex-shrink-0" />
          : <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" />}
        {state.result}
      </div>

      {/* Per-endpoint record counts */}
      {Object.keys(counts).length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {Object.entries(counts).map(([k, n]) => (
            <span key={k} className="px-2 py-0.5 rounded text-xs bg-surface-800 text-slate-400">
              {RESOURCE_LABELS[k] ?? k}: <span className="text-slate-200">{n}</span>
            </span>
          ))}
        </div>
      )}

      {/* Per-endpoint errors + remediation */}
      {hasErrors && (
        <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-3 space-y-2">
          <p className="text-xs font-semibold text-amber-400">Some data couldn&apos;t be fetched:</p>
          <ul className="space-y-1">
            {errorKeys.map(r => (
              <li key={r} className="text-xs text-slate-400">
                <span className="text-slate-300">{RESOURCE_LABELS[r] ?? r}</span>
                {errors[r].status ? ` — HTTP ${errors[r].status}` : ''}
                {errors[r].error ? ` — ${errors[r].error}` : ''}
              </li>
            ))}
          </ul>

          {missingScopeResources.length > 0 && (
            <div className="mt-2 pt-2 border-t border-amber-500/20 space-y-2 text-xs text-slate-400">
              <p className="text-amber-400 font-medium">
                Your Whoop authorization is missing permission(s):{' '}
                <code className="text-amber-300">{missingScopeResources.map(r => WHOOP_RESOURCE_SCOPE[r]).join(', ')}</code>
              </p>
              <ol className="list-decimal list-inside space-y-0.5">
                <li>
                  Open <a className="text-brand-400 underline" href="https://developer.whoop.com" target="_blank" rel="noreferrer">developer.whoop.com</a>
                  {' '}→ your app → enable the missing scopes
                </li>
                <li>Back here, click <strong className="text-slate-300">Disconnect</strong>, then <strong className="text-slate-300">Connect</strong> again to re-authorize</li>
                <li>Click <strong className="text-slate-300">Sync</strong></li>
              </ol>
            </div>
          )}

          {grantedScope && (
            <p className="text-xs text-slate-500 pt-1">
              Granted scopes: <code className="text-slate-400 break-all">{grantedScope}</code>
            </p>
          )}
        </div>
      )}
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export default function Integrations() {
  const [integrations, setIntegrations] = useState<Integration[]>([])
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState<string | null>(null)
  const [syncStates, setSyncStates] = useState<Record<string, SyncState>>({})
  const [connectForms, setConnectForms] = useState<Record<string, boolean>>({})
  const [formData, setFormData] = useState<Record<string, Record<string, string>>>({})
  const [searchParams] = useSearchParams()
  const fileRefs = useRef<Record<string, HTMLInputElement | null>>({})

  useEffect(() => {
    loadIntegrations()
    const connected = searchParams.get('connected')
    if (connected) setTimeout(loadIntegrations, 1000)
  }, [])

  const loadIntegrations = async () => {
    try {
      const res = await integrationsApi.status()
      setIntegrations(res.data)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const handleConnect = async (platform: string, authType: string) => {
    // Export-based platforms: just open the expanded panel with instructions
    if (authType === 'export') {
      setExpanded(platform)
      return
    }

    try {
      setSyncStates(s => ({ ...s, [platform]: { loading: true, result: null } }))

      if (authType === 'oauth2') {
        let res
        if (platform === 'whoop') res = await integrationsApi.whoopConnect()
        else if (platform === 'withings') res = await integrationsApi.withingsConnect()
        else if (platform === 'fitbod') res = await integrationsApi.fitbodConnect()
        else if (platform === 'yazio') res = await integrationsApi.yazioConnect()
        else if (platform === 'larq') res = await integrationsApi.larqConnect()

        if (res?.data?.auth_url) window.location.href = res.data.auth_url
      } else {
        setConnectForms(f => ({ ...f, [platform]: true }))
      }
    } catch {
      setSyncStates(s => ({ ...s, [platform]: { loading: false, result: 'Connection failed' } }))
    } finally {
      setSyncStates(s => ({ ...s, [platform]: { ...s[platform], loading: false } }))
    }
  }

  const handleCredentialConnect = async (platform: string) => {
    const data = formData[platform] || {}
    try {
      setSyncStates(s => ({ ...s, [platform]: { loading: true, result: null } }))
      if (platform === 'renpho') await integrationsApi.renphoConnect(data.email, data.password)
      else if (platform === 'braun') await integrationsApi.braunConnect(data.api_key)
      setConnectForms(f => ({ ...f, [platform]: false }))
      await loadIntegrations()
      setSyncStates(s => ({ ...s, [platform]: { loading: false, result: 'Connected!' } }))
    } catch {
      setSyncStates(s => ({ ...s, [platform]: { loading: false, result: 'Connection failed' } }))
    }
  }

  const handleDisconnect = async (platform: string) => {
    try {
      if (platform === 'whoop') await integrationsApi.whoopDisconnect()
      else if (platform === 'withings') await integrationsApi.withingsDisconnect()
      else if (platform === 'fitbod') await integrationsApi.fitbodDisconnect()
      else if (platform === 'yazio') await integrationsApi.yazioDisconnect()
      else if (platform === 'renpho') await integrationsApi.renphoDisconnect()
      else if (platform === 'braun') await integrationsApi.braunDisconnect()
      else if (platform === 'larq') await integrationsApi.larqDisconnect()
      else if (platform === 'apple_health') await integrationsApi.appleHealthDisconnect()
      await loadIntegrations()
    } catch (e) {
      console.error(e)
    }
  }

  const handleSync = async (platform: string) => {
    setSyncStates(s => ({ ...s, [platform]: { loading: true, result: null } }))
    try {
      let res
      if (platform === 'whoop') res = await integrationsApi.whoopSync()
      else if (platform === 'withings') res = await integrationsApi.withingsSync()
      else if (platform === 'fitbod') res = await integrationsApi.fitbodSync()
      else if (platform === 'yazio') res = await integrationsApi.yazioSync()
      else if (platform === 'renpho') res = await integrationsApi.renphoSync()
      else if (platform === 'larq') res = await integrationsApi.larqSync()
      // apple_health has no "sync" button — re-import instead

      const data = res?.data ?? {}
      const count = data.records_synced || 0
      const errors: Record<string, SyncEndpointError> = data.errors ?? {}
      const hasErrors = Object.keys(errors).length > 0
      setSyncStates(s => ({
        ...s,
        [platform]: {
          loading: false,
          ok: !hasErrors,
          result: hasErrors
            ? `Synced ${count} records — some data couldn't be fetched`
            : `Synced ${count} records`,
          details: {
            counts: data.counts,
            errors,
            granted_scope: data.granted_scope,
          },
        },
      }))
      await loadIntegrations()
    } catch {
      setSyncStates(s => ({ ...s, [platform]: { loading: false, ok: false, result: 'Sync failed' } }))
    }
  }

  const handleImport = async (platform: string, file: File) => {
    setSyncStates(s => ({ ...s, [platform]: { loading: true, result: null } }))
    try {
      let res
      if (platform === 'fitbod') res = await integrationsApi.fitbodImport(file)
      else if (platform === 'yazio') res = await integrationsApi.yazioImport(file)
      else if (platform === 'renpho') res = await integrationsApi.renphoImport(file)
      else if (platform === 'braun') res = await integrationsApi.braunImport(file)

      const count = res?.data?.records_imported || 0
      setSyncStates(s => ({ ...s, [platform]: { loading: false, result: `Imported ${count} records` } }))
    } catch {
      setSyncStates(s => ({ ...s, [platform]: { loading: false, result: 'Import failed' } }))
    }
  }

  if (loading) return <LoadingSpinner className="h-64" />

  const connectedCount = integrations.filter(i => i.is_connected).length

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Integrations</h1>
          <p className="text-slate-500 text-sm">{connectedCount} of {integrations.length} connected</p>
        </div>
        <button
          onClick={() => integrationsApi.syncAll().then(loadIntegrations)}
          className="btn-secondary flex items-center gap-2 text-sm"
        >
          <RefreshCw className="w-4 h-4" />
          Sync All
        </button>
      </div>

      <div className="space-y-3">
        {integrations.map((integration) => {
          const syncState = syncStates[integration.platform] || { loading: false, result: null }
          const isExpanded = expanded === integration.platform
          const showForm = connectForms[integration.platform]
          const isAppleHealth = integration.platform === 'apple_health'
          const isExportType = integration.auth_type === 'export'

          return (
            <div key={integration.platform} className="card">
              <div className="flex items-center gap-4">
                {/* Icon */}
                <div className="text-2xl w-10 flex-shrink-0 flex items-center justify-center">
                  {PLATFORM_ICONS[integration.platform] ?? '🔗'}
                </div>

                {/* Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3 className="font-semibold text-white text-sm">{integration.name}</h3>
                    {integration.is_connected ? (
                      <span className="badge-green flex items-center gap-1">
                        <CheckCircle className="w-3 h-3" /> Connected
                      </span>
                    ) : (
                      <span className="badge-red flex items-center gap-1">
                        <XCircle className="w-3 h-3" /> Not connected
                      </span>
                    )}
                    {isExportType && (
                      <span className="badge-blue">Export / Webhook</span>
                    )}
                  </div>
                  <p className="text-xs text-slate-500 mt-0.5">{integration.description}</p>
                  <div className="flex flex-wrap gap-1 mt-1.5">
                    {integration.data_types.map(t => (
                      <span key={t} className="px-1.5 py-0.5 rounded text-xs bg-surface-800 text-slate-500">{t}</span>
                    ))}
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2 flex-shrink-0">
                  {integration.is_connected ? (
                    <>
                      {/* Apple Health: Re-import button instead of Sync */}
                      {isAppleHealth ? (
                        <button
                          onClick={() => setExpanded(isExpanded ? null : integration.platform)}
                          className="btn-secondary flex items-center gap-1.5 text-xs py-1.5"
                        >
                          <Upload className="w-3.5 h-3.5" />
                          Re-import
                        </button>
                      ) : (
                        <button
                          onClick={() => handleSync(integration.platform)}
                          disabled={syncState.loading}
                          className="btn-secondary flex items-center gap-1.5 text-xs py-1.5"
                        >
                          <RefreshCw className={clsx('w-3.5 h-3.5', syncState.loading && 'animate-spin')} />
                          Sync
                        </button>
                      )}
                      <button
                        onClick={() => handleDisconnect(integration.platform)}
                        className="btn-ghost flex items-center gap-1.5 text-xs py-1.5 text-red-400 hover:text-red-300"
                        title="Disconnect"
                      >
                        <Link2Off className="w-3.5 h-3.5" />
                      </button>
                    </>
                  ) : (
                    <button
                      onClick={() => handleConnect(integration.platform, integration.auth_type)}
                      disabled={syncState.loading}
                      className="btn-primary flex items-center gap-1.5 text-xs py-1.5"
                    >
                      <Link2 className="w-3.5 h-3.5" />
                      {isExportType ? 'Import' : 'Connect'}
                    </button>
                  )}
                  {/* Expand toggle — skip for Apple Health (always shown in connect flow) */}
                  {!isAppleHealth && (
                    <button
                      onClick={() => setExpanded(isExpanded ? null : integration.platform)}
                      className="btn-ghost py-1.5 px-2"
                    >
                      {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                    </button>
                  )}
                </div>
              </div>

              {/* Non-Apple sync result banner + diagnostics */}
              {syncState.result && !isAppleHealth && (
                <SyncResult platform={integration.platform} state={syncState} />
              )}

              {/* ── Apple Health dedicated panel ── */}
              {isAppleHealth && isExpanded && (
                <AppleHealthPanel
                  integration={integration}
                  onImported={loadIntegrations}
                />
              )}

              {/* ── Standard expanded panel (non-Apple) ── */}
              {!isAppleHealth && isExpanded && (
                <div className="mt-4 pt-4 border-t border-surface-700/50 space-y-3">
                  <div className="grid grid-cols-2 gap-4 text-xs">
                    <div>
                      <span className="text-slate-500">Auth type: </span>
                      <span className="text-slate-300">{AUTH_TYPE_LABELS[integration.auth_type] ?? integration.auth_type}</span>
                    </div>
                    {integration.platform_username && (
                      <div>
                        <span className="text-slate-500">Account: </span>
                        <span className="text-slate-300">{integration.platform_username}</span>
                      </div>
                    )}
                    {integration.last_synced_at && (
                      <div className="flex items-center gap-1">
                        <Clock className="w-3 h-3 text-slate-500" />
                        <span className="text-slate-500">Last sync: </span>
                        <span className="text-slate-300">
                          {format(new Date(integration.last_synced_at), 'MMM d, HH:mm')}
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Credential / API key form */}
                  {showForm && !integration.is_connected && (
                    <div className="bg-surface-800 rounded-lg p-4 space-y-3">
                      {integration.auth_type === 'credentials' && (
                        <>
                          <div>
                            <label className="label">Email</label>
                            <input
                              className="input"
                              type="email"
                              placeholder="your@email.com"
                              value={formData[integration.platform]?.email || ''}
                              onChange={e => setFormData(f => ({
                                ...f, [integration.platform]: { ...f[integration.platform], email: e.target.value }
                              }))}
                            />
                          </div>
                          <div>
                            <label className="label">Password</label>
                            <input
                              className="input"
                              type="password"
                              placeholder="••••••••"
                              value={formData[integration.platform]?.password || ''}
                              onChange={e => setFormData(f => ({
                                ...f, [integration.platform]: { ...f[integration.platform], password: e.target.value }
                              }))}
                            />
                          </div>
                        </>
                      )}
                      {integration.auth_type === 'api_key' && (
                        <div>
                          <label className="label">API Key</label>
                          <input
                            className="input"
                            type="text"
                            placeholder="Your API key"
                            value={formData[integration.platform]?.api_key || ''}
                            onChange={e => setFormData(f => ({
                              ...f, [integration.platform]: { ...f[integration.platform], api_key: e.target.value }
                            }))}
                          />
                        </div>
                      )}
                      <button
                        onClick={() => handleCredentialConnect(integration.platform)}
                        className="btn-primary text-sm w-full"
                      >
                        Connect
                      </button>
                    </div>
                  )}

                  {/* CSV import section */}
                  {['fitbod', 'yazio', 'renpho', 'braun'].includes(integration.platform) && (
                    <div>
                      <p className="text-xs text-slate-500 mb-2">Or import data from CSV export:</p>
                      <div className="flex items-center gap-2">
                        <input
                          type="file"
                          accept=".csv,.json"
                          className="hidden"
                          ref={el => { fileRefs.current[integration.platform] = el }}
                          onChange={e => {
                            const file = e.target.files?.[0]
                            if (file) handleImport(integration.platform, file)
                          }}
                        />
                        <button
                          onClick={() => fileRefs.current[integration.platform]?.click()}
                          className="btn-secondary flex items-center gap-2 text-xs"
                        >
                          <Upload className="w-3.5 h-3.5" />
                          Import CSV
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
