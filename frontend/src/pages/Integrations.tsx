import React, { useEffect, useState, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  CheckCircle, XCircle, RefreshCw, Link2, Link2Off, Upload,
  ChevronDown, ChevronUp, Clock, ExternalLink
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
}

const AUTH_TYPE_LABELS: Record<string, string> = {
  oauth2: 'OAuth2 (Secure)',
  credentials: 'Email & Password',
  api_key: 'API Key',
}

interface SyncState {
  loading: boolean
  result: string | null
}

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
    if (connected) {
      setTimeout(loadIntegrations, 1000)
    }
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
    try {
      setSyncStates(s => ({ ...s, [platform]: { loading: true, result: null } }))

      if (authType === 'oauth2') {
        let res
        if (platform === 'whoop') res = await integrationsApi.whoopConnect()
        else if (platform === 'withings') res = await integrationsApi.withingsConnect()
        else if (platform === 'fitbod') res = await integrationsApi.fitbodConnect()
        else if (platform === 'yazio') res = await integrationsApi.yazioConnect()
        else if (platform === 'larq') res = await integrationsApi.larqConnect()

        if (res?.data?.auth_url) {
          window.location.href = res.data.auth_url
        }
      } else {
        setConnectForms(f => ({ ...f, [platform]: true }))
      }
    } catch (e) {
      setSyncStates(s => ({ ...s, [platform]: { loading: false, result: 'Connection failed' } }))
    } finally {
      setSyncStates(s => ({ ...s, [platform]: { ...s[platform], loading: false } }))
    }
  }

  const handleCredentialConnect = async (platform: string) => {
    const data = formData[platform] || {}
    try {
      setSyncStates(s => ({ ...s, [platform]: { loading: true, result: null } }))
      if (platform === 'renpho') {
        await integrationsApi.renphoConnect(data.email, data.password)
      } else if (platform === 'braun') {
        await integrationsApi.braunConnect(data.api_key)
      }
      setConnectForms(f => ({ ...f, [platform]: false }))
      await loadIntegrations()
      setSyncStates(s => ({ ...s, [platform]: { loading: false, result: 'Connected!' } }))
    } catch (e) {
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

      const count = res?.data?.records_synced || 0
      setSyncStates(s => ({ ...s, [platform]: { loading: false, result: `Synced ${count} records` } }))
      await loadIntegrations()
    } catch (e) {
      setSyncStates(s => ({ ...s, [platform]: { loading: false, result: 'Sync failed' } }))
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
    } catch (e) {
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
        <button onClick={() => integrationsApi.syncAll().then(loadIntegrations)} className="btn-secondary flex items-center gap-2 text-sm">
          <RefreshCw className="w-4 h-4" />
          Sync All
        </button>
      </div>

      <div className="space-y-3">
        {integrations.map((integration) => {
          const syncState = syncStates[integration.platform] || { loading: false, result: null }
          const isExpanded = expanded === integration.platform
          const showForm = connectForms[integration.platform]

          return (
            <div key={integration.platform} className="card">
              <div className="flex items-center gap-4">
                <div className="text-2xl w-10 flex-shrink-0 flex items-center justify-center">
                  {PLATFORM_ICONS[integration.platform]}
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
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
                  </div>
                  <p className="text-xs text-slate-500 mt-0.5">{integration.description}</p>
                  <div className="flex flex-wrap gap-1 mt-1.5">
                    {integration.data_types.map(t => (
                      <span key={t} className="px-1.5 py-0.5 rounded text-xs bg-surface-800 text-slate-500">{t}</span>
                    ))}
                  </div>
                </div>

                <div className="flex items-center gap-2 flex-shrink-0">
                  {integration.is_connected ? (
                    <>
                      <button
                        onClick={() => handleSync(integration.platform)}
                        disabled={syncState.loading}
                        className="btn-secondary flex items-center gap-1.5 text-xs py-1.5"
                      >
                        <RefreshCw className={clsx('w-3.5 h-3.5', syncState.loading && 'animate-spin')} />
                        Sync
                      </button>
                      <button
                        onClick={() => handleDisconnect(integration.platform)}
                        className="btn-ghost flex items-center gap-1.5 text-xs py-1.5 text-red-400 hover:text-red-300"
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
                      Connect
                    </button>
                  )}
                  <button
                    onClick={() => setExpanded(isExpanded ? null : integration.platform)}
                    className="btn-ghost py-1.5 px-2"
                  >
                    {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {/* Sync result */}
              {syncState.result && (
                <div className={clsx(
                  'mt-3 px-3 py-2 rounded-lg text-xs',
                  syncState.result.includes('failed') ? 'bg-red-500/10 text-red-400' : 'bg-brand-500/10 text-brand-400'
                )}>
                  {syncState.result}
                </div>
              )}

              {/* Expanded details */}
              {isExpanded && (
                <div className="mt-4 pt-4 border-t border-surface-700/50 space-y-3">
                  <div className="grid grid-cols-2 gap-4 text-xs">
                    <div>
                      <span className="text-slate-500">Auth type: </span>
                      <span className="text-slate-300">{AUTH_TYPE_LABELS[integration.auth_type]}</span>
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

                  {/* Credential connect form */}
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

                  {/* Import section */}
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
