import React, { useState } from 'react'
import { Save, User } from 'lucide-react'
import { authApi } from '../services/api'
import { useAuthStore } from '../store/authStore'
import type { User as UserType } from '../types'

export default function Settings() {
  const { user, updateUser } = useAuthStore()
  const [formData, setFormData] = useState({
    full_name: user?.full_name || '',
    age: user?.age?.toString() || '',
    height_cm: user?.height_cm?.toString() || '',
    weight_kg: user?.weight_kg?.toString() || '',
    gender: user?.gender || '',
  })
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      const res = await authApi.updateMe({
        full_name: formData.full_name || undefined,
        age: formData.age ? parseInt(formData.age) : undefined,
        height_cm: formData.height_cm ? parseFloat(formData.height_cm) : undefined,
        weight_kg: formData.weight_kg ? parseFloat(formData.weight_kg) : undefined,
        gender: formData.gender || undefined,
      })
      updateUser(res.data as UserType)
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch (e) {
      console.error(e)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="max-w-xl space-y-6">
      <div>
        <h1 className="text-xl font-bold text-white">Settings</h1>
        <p className="text-slate-500 text-sm">Your profile and preferences</p>
      </div>

      <div className="card">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-12 h-12 rounded-full bg-brand-500/20 flex items-center justify-center">
            <User className="w-6 h-6 text-brand-400" />
          </div>
          <div>
            <p className="font-medium text-white">{user?.full_name || 'Your profile'}</p>
            <p className="text-sm text-slate-500">{user?.email}</p>
          </div>
        </div>

        <form onSubmit={handleSave} className="space-y-4">
          <div>
            <label className="label">Full Name</label>
            <input
              className="input"
              value={formData.full_name}
              onChange={e => setFormData(f => ({ ...f, full_name: e.target.value }))}
              placeholder="John Doe"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label">Age</label>
              <input
                className="input"
                type="number"
                value={formData.age}
                onChange={e => setFormData(f => ({ ...f, age: e.target.value }))}
                placeholder="30"
              />
            </div>
            <div>
              <label className="label">Gender</label>
              <select
                className="input"
                value={formData.gender}
                onChange={e => setFormData(f => ({ ...f, gender: e.target.value }))}
              >
                <option value="">Prefer not to say</option>
                <option value="male">Male</option>
                <option value="female">Female</option>
                <option value="other">Other</option>
              </select>
            </div>
            <div>
              <label className="label">Height (cm)</label>
              <input
                className="input"
                type="number"
                value={formData.height_cm}
                onChange={e => setFormData(f => ({ ...f, height_cm: e.target.value }))}
                placeholder="175"
              />
            </div>
            <div>
              <label className="label">Weight (kg)</label>
              <input
                className="input"
                type="number"
                step="0.1"
                value={formData.weight_kg}
                onChange={e => setFormData(f => ({ ...f, weight_kg: e.target.value }))}
                placeholder="75.0"
              />
            </div>
          </div>

          <button type="submit" disabled={saving} className="btn-primary flex items-center gap-2">
            <Save className="w-4 h-4" />
            {saving ? 'Saving...' : saved ? 'Saved!' : 'Save Changes'}
          </button>
        </form>
      </div>

      <div className="card">
        <h3 className="font-semibold text-white mb-3">Account</h3>
        <div className="text-sm text-slate-400 space-y-2">
          <p>Email: <span className="text-slate-200">{user?.email}</span></p>
          <p>Member since: <span className="text-slate-200">{user?.created_at ? new Date(user.created_at).toLocaleDateString() : '—'}</span></p>
        </div>
      </div>
    </div>
  )
}
