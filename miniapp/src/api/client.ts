import axios from 'axios'
import { useAuthStore } from '../store/authStore'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

export const apiClient = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
})

// Attach JWT token to every request
apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Handle 401 — token expired
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout()
    }
    return Promise.reject(error)
  }
)

// Auth
export const authAPI = {
  telegramAuth: (initData: string) =>
    apiClient.post('/auth/telegram', { init_data: initData }),
}

// Onboarding
export const onboardingAPI = {
  getStatus: () => apiClient.get('/onboarding/status'),
  submitStep: (step: string, answer: unknown) =>
    apiClient.post('/onboarding/step', { step, answer }),
}

// Workouts
export const workoutsAPI = {
  getToday: () => apiClient.get('/workouts/today'),
  getWorkout: (id: string) => apiClient.get(`/workouts/${id}`),
  completeWorkout: (id: string, data: object) =>
    apiClient.post(`/workouts/${id}/complete`, data),
  skipWorkout: (id: string) => apiClient.post(`/workouts/${id}/skip`),
  getWarmup: (id: string) => apiClient.get(`/workouts/${id}/warmup`),
  getSchedule: () => apiClient.get('/workouts/schedule'),
}

// Progress
export const progressAPI = {
  getProgress: () => apiClient.get('/progress'),
  addEntry: (data: object) => apiClient.post('/progress', data),
  uploadPhoto: (formData: FormData) =>
    apiClient.post('/progress/photos', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
}

// AI Chat
export const aiAPI = {
  sendMessage: (message: string) => apiClient.post('/ai/chat', { message }),
  getHistory: () => apiClient.get('/ai/history'),
}

// Profile
export const profileAPI = {
  getProfile: () => apiClient.get('/profile'),
  updateProfile: (data: object) => apiClient.put('/profile', data),
  deleteAccount: () => apiClient.delete('/profile/account'),
}

// Nutrition
export const nutritionAPI = {
  getDaily: (date?: string) => apiClient.get('/nutrition', { params: date ? { target_date: date } : {} }),
  addMeal: (data: object) => apiClient.post('/nutrition/meal', data),
  deleteMeal: (id: string) => apiClient.delete(`/nutrition/meal/${id}`),
  addWater: (data: object) => apiClient.post('/nutrition/water', data),
  analyzePhoto: (formData: FormData) =>
    apiClient.post('/nutrition/analyze-photo', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
}

// Reports
export const reportsAPI = {
  getWeekly: () => apiClient.get('/reports/weekly'),
}

// Subscriptions
export const subscriptionAPI = {
  getInfo: () => apiClient.get('/subscriptions/info'),
  activate: (tier: string, externalId?: string) =>
    apiClient.post('/subscriptions/activate', { tier, external_id: externalId }),
}

// Food search
export const foodAPI = {
  search: (q: string) => apiClient.get('/nutrition/search', { params: { q } }),
}
