import React, { useEffect, useState, useRef } from 'react'
import { Upload, FlaskConical, Trash2, ChevronDown, ChevronUp, AlertTriangle, CheckCircle, Clock } from 'lucide-react'
import { labTestsApi } from '../services/api'
import type { LabTest } from '../types'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import { format } from 'date-fns'
import clsx from 'clsx'

const STATUS_COLORS: Record<string, string> = {
  normal: 'badge-green',
  low: 'badge-yellow',
  high: 'badge-yellow',
  critical_low: 'badge-red',
  critical_high: 'badge-red',
}

const CATEGORY_LABELS: Record<string, string> = {
  metabolic: 'Metabolic',
  lipid: 'Lipid Panel',
  thyroid: 'Thyroid',
  cbc: 'CBC',
  hormone: 'Hormones',
  vitamin: 'Vitamins',
  other: 'Other',
}

export default function LabTests() {
  const [tests, setTests] = useState<LabTest[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [expanded, setExpanded] = useState<number | null>(null)
  const [showUploadForm, setShowUploadForm] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)

  const [formData, setFormData] = useState({
    test_name: '',
    lab_name: '',
    ordered_by: '',
    test_date: '',
    notes: '',
  })
  const [selectedFile, setSelectedFile] = useState<File | null>(null)

  useEffect(() => {
    loadTests()
  }, [])

  const loadTests = async () => {
    try {
      const res = await labTestsApi.list()
      setTests(res.data)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedFile || !formData.test_name) return

    setUploading(true)
    try {
      await labTestsApi.upload({
        file: selectedFile,
        ...formData,
      })
      setShowUploadForm(false)
      setSelectedFile(null)
      setFormData({ test_name: '', lab_name: '', ordered_by: '', test_date: '', notes: '' })
      await loadTests()
    } catch (e) {
      console.error(e)
    } finally {
      setUploading(false)
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this lab test?')) return
    try {
      await labTestsApi.delete(id)
      setTests(t => t.filter(test => test.id !== id))
    } catch (e) {
      console.error(e)
    }
  }

  if (loading) return <LoadingSpinner className="h-64" />

  const abnormalCount = tests.reduce((count, test) =>
    count + test.results.filter(r => r.status && r.status !== 'normal').length, 0
  )

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Lab Tests</h1>
          <p className="text-slate-500 text-sm">
            {tests.length} test{tests.length !== 1 ? 's' : ''}
            {abnormalCount > 0 && ` · ${abnormalCount} abnormal value${abnormalCount !== 1 ? 's' : ''}`}
          </p>
        </div>
        <button
          onClick={() => setShowUploadForm(!showUploadForm)}
          className="btn-primary flex items-center gap-2 text-sm"
        >
          <Upload className="w-4 h-4" />
          Upload Lab Test
        </button>
      </div>

      {/* Upload form */}
      {showUploadForm && (
        <div className="card">
          <h3 className="font-semibold text-white mb-4">Upload Lab Test</h3>
          <form onSubmit={handleUpload} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="label">Test Name *</label>
                <input
                  className="input"
                  placeholder="e.g., Complete Blood Count"
                  value={formData.test_name}
                  onChange={e => setFormData(f => ({ ...f, test_name: e.target.value }))}
                  required
                />
              </div>
              <div>
                <label className="label">Laboratory</label>
                <input
                  className="input"
                  placeholder="e.g., LabCorp"
                  value={formData.lab_name}
                  onChange={e => setFormData(f => ({ ...f, lab_name: e.target.value }))}
                />
              </div>
              <div>
                <label className="label">Ordered By</label>
                <input
                  className="input"
                  placeholder="Doctor's name"
                  value={formData.ordered_by}
                  onChange={e => setFormData(f => ({ ...f, ordered_by: e.target.value }))}
                />
              </div>
              <div>
                <label className="label">Test Date</label>
                <input
                  className="input"
                  type="date"
                  value={formData.test_date}
                  onChange={e => setFormData(f => ({ ...f, test_date: e.target.value }))}
                />
              </div>
            </div>

            <div>
              <label className="label">Notes</label>
              <textarea
                className="input"
                rows={2}
                placeholder="Any notes about this test..."
                value={formData.notes}
                onChange={e => setFormData(f => ({ ...f, notes: e.target.value }))}
              />
            </div>

            {/* File upload */}
            <div>
              <label className="label">File (PDF, JPG, PNG) *</label>
              <div
                className="border-2 border-dashed border-surface-700 rounded-lg p-6 text-center cursor-pointer hover:border-brand-500/50 transition-colors"
                onClick={() => fileRef.current?.click()}
              >
                <input
                  type="file"
                  ref={fileRef}
                  className="hidden"
                  accept=".pdf,.jpg,.jpeg,.png,.txt"
                  onChange={e => setSelectedFile(e.target.files?.[0] || null)}
                />
                {selectedFile ? (
                  <div>
                    <p className="text-brand-400 font-medium">{selectedFile.name}</p>
                    <p className="text-slate-500 text-xs mt-1">{(selectedFile.size / 1024).toFixed(1)} KB</p>
                  </div>
                ) : (
                  <div>
                    <Upload className="w-8 h-8 text-slate-600 mx-auto mb-2" />
                    <p className="text-slate-400 text-sm">Click to upload or drag & drop</p>
                    <p className="text-slate-600 text-xs mt-1">PDF, JPG, PNG up to 10MB</p>
                  </div>
                )}
              </div>
            </div>

            <div className="flex gap-3">
              <button
                type="submit"
                disabled={uploading || !selectedFile || !formData.test_name}
                className="btn-primary flex items-center gap-2"
              >
                {uploading && <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />}
                {uploading ? 'Processing with AI...' : 'Upload & Analyze'}
              </button>
              <button type="button" onClick={() => setShowUploadForm(false)} className="btn-secondary">
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Tests list */}
      {tests.length === 0 ? (
        <div className="text-center py-20">
          <FlaskConical className="w-12 h-12 text-slate-600 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-slate-400">No lab tests uploaded yet</h3>
          <p className="text-slate-600 text-sm mt-1">Upload PDFs or images of your lab results for AI analysis.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {tests.map(test => {
            const isExpanded = expanded === test.id
            const abnormal = test.results.filter(r => r.status && r.status !== 'normal')

            return (
              <div key={test.id} className="card">
                <div className="flex items-start gap-4">
                  <div className="w-10 h-10 rounded-lg bg-surface-800 flex items-center justify-center flex-shrink-0">
                    <FlaskConical className="w-5 h-5 text-slate-400" />
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="font-semibold text-white text-sm">{test.test_name}</h3>
                      <span className={clsx(
                        'px-2 py-0.5 rounded-full text-xs font-medium',
                        test.status === 'processed' ? 'bg-brand-500/20 text-brand-400' :
                        test.status === 'pending' ? 'bg-yellow-500/20 text-yellow-400' :
                        'bg-red-500/20 text-red-400'
                      )}>
                        {test.status === 'processed' ? 'Analyzed' : test.status === 'pending' ? 'Processing...' : 'Error'}
                      </span>
                      {abnormal.length > 0 && (
                        <span className="badge-yellow flex items-center gap-1">
                          <AlertTriangle className="w-3 h-3" />
                          {abnormal.length} abnormal
                        </span>
                      )}
                    </div>
                    <div className="flex flex-wrap gap-3 mt-1 text-xs text-slate-500">
                      {test.lab_name && <span>{test.lab_name}</span>}
                      {test.ordered_by && <span>Dr. {test.ordered_by}</span>}
                      {test.test_date && <span className="flex items-center gap-1"><Clock className="w-3 h-3" />{format(new Date(test.test_date), 'MMM d, yyyy')}</span>}
                      {test.file_name && <span>{test.file_name}</span>}
                    </div>
                    {test.parsed_summary && (
                      <p className="text-xs text-slate-400 mt-1.5 leading-relaxed">{test.parsed_summary}</p>
                    )}
                  </div>

                  <div className="flex items-center gap-2 flex-shrink-0">
                    <button
                      onClick={() => setExpanded(isExpanded ? null : test.id)}
                      className="btn-ghost py-1.5 px-2 text-xs"
                      disabled={test.results.length === 0}
                    >
                      {test.results.length} results
                      {isExpanded ? <ChevronUp className="w-3.5 h-3.5 inline ml-1" /> : <ChevronDown className="w-3.5 h-3.5 inline ml-1" />}
                    </button>
                    <button
                      onClick={() => handleDelete(test.id)}
                      className="text-slate-600 hover:text-red-400 transition-colors p-1"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {isExpanded && test.results.length > 0 && (
                  <div className="mt-4 pt-4 border-t border-surface-700/50">
                    {/* Group by category */}
                    {Object.entries(
                      test.results.reduce((acc, r) => {
                        const cat = r.category || 'other'
                        if (!acc[cat]) acc[cat] = []
                        acc[cat].push(r)
                        return acc
                      }, {} as Record<string, typeof test.results>)
                    ).map(([category, results]) => (
                      <div key={category} className="mb-4">
                        <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                          {CATEGORY_LABELS[category] || category}
                        </h4>
                        <div className="space-y-2">
                          {results.map(result => (
                            <div key={result.id} className="flex items-center gap-3 text-sm">
                              <div className="w-4 flex-shrink-0">
                                {result.status === 'normal' ? (
                                  <CheckCircle className="w-4 h-4 text-brand-500" />
                                ) : result.status?.includes('critical') ? (
                                  <AlertTriangle className="w-4 h-4 text-red-400" />
                                ) : (
                                  <AlertTriangle className="w-4 h-4 text-yellow-400" />
                                )}
                              </div>
                              <span className="text-slate-300 flex-1 min-w-0 truncate">{result.biomarker_name}</span>
                              <div className="flex items-center gap-2 flex-shrink-0">
                                <span className="font-medium text-white">
                                  {result.value !== null ? result.value?.toFixed(2) : '—'}
                                  {result.unit && <span className="text-slate-500 text-xs ml-0.5">{result.unit}</span>}
                                </span>
                                <span className="text-slate-600 text-xs">{result.reference_text || `${result.reference_min}–${result.reference_max}`}</span>
                                {result.status && (
                                  <span className={STATUS_COLORS[result.status] || 'badge-blue'}>
                                    {result.status.replace('_', ' ')}
                                  </span>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
