import axios from 'axios';
import * as SecureStore from 'expo-secure-store';
import Constants from 'expo-constants';
import { DashboardSummary, Integration, LabTest, ChatMessage } from '../types';

const BASE_URL = (Constants.expoConfig?.extra?.apiUrl as string) ?? 'http://localhost:8000';

const api = axios.create({
  baseURL: `${BASE_URL}/api`,
  timeout: 30_000,
});

// Attach JWT to every request
api.interceptors.request.use(async (config) => {
  const token = await SecureStore.getItemAsync('health_analyzer_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// On 401, clear token (logout handled by consuming code via authStore)
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      SecureStore.deleteItemAsync('health_analyzer_token');
      SecureStore.deleteItemAsync('health_analyzer_user');
    }
    return Promise.reject(err);
  }
);

// ── Auth ──────────────────────────────────────────────────────────────────────

export const authApi = {
  register: (data: {
    email: string;
    password: string;
    full_name?: string;
    age?: number;
    height_cm?: number;
    weight_kg?: number;
    gender?: string;
  }) => api.post('/auth/register', data),

  login: (email: string, password: string) => {
    const form = new FormData();
    form.append('username', email);
    form.append('password', password);
    return api.post('/auth/login', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  me: () => api.get('/auth/me'),

  updateMe: (data: Partial<{
    full_name: string;
    age: number;
    height_cm: number;
    weight_kg: number;
    gender: string;
  }>) => api.put('/auth/me', data),
};

// ── Health data ───────────────────────────────────────────────────────────────

export const healthApi = {
  dashboard: () => api.get<DashboardSummary>('/health/dashboard'),
  sleep: (days = 30) => api.get(`/health/sleep?days=${days}`),
  activity: (days = 30) => api.get(`/health/activity?days=${days}`),
  nutrition: (days = 30) => api.get(`/health/nutrition?days=${days}`),
  body: (days = 90) => api.get(`/health/body?days=${days}`),
  hydration: (days = 30) => api.get(`/health/hydration?days=${days}`),
};

// ── Integrations ──────────────────────────────────────────────────────────────

export const integrationApi = {
  status: () => api.get<Integration[]>('/integrations/status'),
  syncAll: () => api.post('/integrations/sync-all'),
  toggleAutoSync: (platform: string) =>
    api.post(`/integrations/${platform}/toggle-auto-sync`),

  // OAuth-based platforms — mobile=true switches to mobile redirect URI
  connect: (platform: string) =>
    api.get<{ auth_url: string }>(`/integrations/${platform}/connect?mobile=true`),
  callback: (platform: string, code: string, state: string) =>
    api.get(`/integrations/${platform}/callback?code=${code}&state=${state}`),
  disconnect: (platform: string) =>
    api.post(`/integrations/${platform}/disconnect`),
  sync: (platform: string, days = 30) =>
    api.post(`/integrations/${platform}/sync?days=${days}`),

  // Renpho (credentials)
  renphoConnect: (email: string, password: string) =>
    api.post(`/integrations/renpho/connect?email=${encodeURIComponent(email)}&password=${encodeURIComponent(password)}`),

  // Braun (API key)
  braunConnect: (apiKey: string) =>
    api.post('/integrations/braun/connect', { api_key: apiKey }),
  braunManualEntry: (data: { systolic: number; diastolic: number; pulse?: number }) =>
    api.post('/integrations/braun/manual-entry', data),

  // Larq (water log)
  larqLog: (amount_ml: number) =>
    api.post('/integrations/larq/log', { amount_ml }),

  // Apple Health — native sync (JWT-authenticated, no webhook token needed)
  appleHealthSyncNative: (payload: object) =>
    api.post('/integrations/apple-health/sync-native', payload),
  appleHealthDisconnect: () =>
    api.post('/integrations/apple-health/disconnect'),
};

// ── Lab tests ─────────────────────────────────────────────────────────────────

export const labApi = {
  list: () => api.get<LabTest[]>('/lab-tests/'),

  upload: (
    file: { uri: string; name: string; type: string },
    meta: { test_name: string; lab_name?: string; notes?: string },
    onProgress?: (pct: number) => void
  ) => {
    const form = new FormData();
    form.append('file', file as unknown as Blob);
    form.append('test_name', meta.test_name);
    if (meta.lab_name) form.append('lab_name', meta.lab_name);
    if (meta.notes) form.append('notes', meta.notes);
    return api.post('/lab-tests/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120_000,
      onUploadProgress: (e) => {
        if (onProgress && e.total) {
          onProgress(Math.round((e.loaded / e.total) * 100));
        }
      },
    });
  },

  get: (id: number) => api.get<LabTest>(`/lab-tests/${id}`),
  delete: (id: number) => api.delete(`/lab-tests/${id}`),
};

// ── AI ────────────────────────────────────────────────────────────────────────

export const aiApi = {
  chat: (message: string, history: ChatMessage[]) =>
    api.post('/ai/chat', { message, conversation_history: history }),
  insights: () => api.get('/ai/insights'),
  suggestedQuestions: () => api.get<string[]>('/ai/suggested-questions'),
};

export default api;
