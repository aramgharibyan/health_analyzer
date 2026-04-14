import axios from 'axios'
import { useAuthStore } from '../store/authStore'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

// Attach token to all requests
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Handle 401 by logging out
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      useAuthStore.getState().logout()
    }
    return Promise.reject(err)
  }
)

// Auth
export const authApi = {
  register: (data: { email: string; password: string; full_name?: string }) =>
    api.post('/auth/register', data),
  login: (email: string, password: string) => {
    const form = new FormData()
    form.append('username', email)
    form.append('password', password)
    return api.post('/auth/login', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  me: () => api.get('/auth/me'),
  updateMe: (data: Partial<{ full_name: string; age: number; height_cm: number; weight_kg: number; gender: string }>) =>
    api.put('/auth/me', data),
}

// Health Data
export const healthApi = {
  dashboard: () => api.get('/health/dashboard'),
  sleep: (days = 30) => api.get(`/health/sleep?days=${days}`),
  activity: (days = 30) => api.get(`/health/activity?days=${days}`),
  nutrition: (days = 30) => api.get(`/health/nutrition?days=${days}`),
  body: (days = 90) => api.get(`/health/body?days=${days}`),
  hydration: (days = 30) => api.get(`/health/hydration?days=${days}`),
}

// Integrations
export const integrationsApi = {
  status: () => api.get('/integrations/status'),
  syncAll: () => api.post('/integrations/sync-all'),
  toggleAutoSync: (platform: string) => api.post(`/integrations/${platform}/toggle-auto-sync`),

  // Whoop
  whoopConnect: () => api.get('/integrations/whoop/connect'),
  whoopSync: (days = 30) => api.post(`/integrations/whoop/sync?days=${days}`),
  whoopDisconnect: () => api.post('/integrations/whoop/disconnect'),

  // Withings
  withingsConnect: () => api.get('/integrations/withings/connect'),
  withingsSync: (days = 30) => api.post(`/integrations/withings/sync?days=${days}`),
  withingsDisconnect: () => api.post('/integrations/withings/disconnect'),

  // Fitbod
  fitbodConnect: () => api.get('/integrations/fitbod/connect'),
  fitbodSync: (days = 30) => api.post(`/integrations/fitbod/sync?days=${days}`),
  fitbodDisconnect: () => api.post('/integrations/fitbod/disconnect'),
  fitbodImport: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return api.post('/integrations/fitbod/import', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  // Yazio
  yazioConnect: () => api.get('/integrations/yazio/connect'),
  yazioSync: (days = 30) => api.post(`/integrations/yazio/sync?days=${days}`),
  yazioDisconnect: () => api.post('/integrations/yazio/disconnect'),
  yazioImport: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return api.post('/integrations/yazio/import', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  // Renpho
  renphoConnect: (email: string, password: string) =>
    api.post('/integrations/renpho/connect', null, { params: { email, password } }),
  renphoSync: (days = 30) => api.post(`/integrations/renpho/sync?days=${days}`),
  renphoDisconnect: () => api.post('/integrations/renpho/disconnect'),
  renphoImport: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return api.post('/integrations/renpho/import', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  // Braun
  braunConnect: (apiKey: string) => api.post('/integrations/braun/connect', { api_key: apiKey }),
  braunDisconnect: () => api.post('/integrations/braun/disconnect'),
  braunManualEntry: (data: { systolic: number; diastolic: number; pulse?: number }) =>
    api.post('/integrations/braun/manual-entry', data),
  braunImport: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return api.post('/integrations/braun/import', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  // Larq
  larqConnect: () => api.get('/integrations/larq/connect'),
  larqSync: (days = 30) => api.post(`/integrations/larq/sync?days=${days}`),
  larqDisconnect: () => api.post('/integrations/larq/disconnect'),
  larqLog: (amount_ml: number) => api.post('/integrations/larq/log', { amount_ml }),

  // Apple Health
  appleHealthImport: (file: File, onUploadProgress?: (pct: number) => void) => {
    const form = new FormData()
    form.append('file', file)
    return api.post('/integrations/apple-health/import', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (evt) => {
        if (onUploadProgress && evt.total) {
          onUploadProgress(Math.round((evt.loaded * 100) / evt.total))
        }
      },
      // exports can be large — give it 10 minutes
      timeout: 600_000,
    })
  },
  appleHealthDisconnect: () => api.post('/integrations/apple-health/disconnect'),
  appleHealthWebhookToken: () => api.get('/integrations/apple-health/webhook-token'),
}

// Lab Tests
export const labTestsApi = {
  list: () => api.get('/lab-tests/'),
  get: (id: number) => api.get(`/lab-tests/${id}`),
  upload: (data: {
    file: File
    test_name: string
    lab_name?: string
    ordered_by?: string
    test_date?: string
    notes?: string
  }) => {
    const form = new FormData()
    form.append('file', data.file)
    form.append('test_name', data.test_name)
    if (data.lab_name) form.append('lab_name', data.lab_name)
    if (data.ordered_by) form.append('ordered_by', data.ordered_by)
    if (data.test_date) form.append('test_date', data.test_date)
    if (data.notes) form.append('notes', data.notes)
    return api.post('/lab-tests/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  delete: (id: number) => api.delete(`/lab-tests/${id}`),
}

// AI Assistant
export const aiApi = {
  chat: (message: string, history: { role: string; content: string }[]) =>
    api.post('/ai/chat', { message, conversation_history: history }),
  insights: () => api.get('/ai/insights'),
  correlate: (metric1: string, metric2: string) =>
    api.post('/ai/correlate', { metric1, metric2 }),
  suggestedQuestions: () => api.get('/ai/suggested-questions'),
}

export default api
