import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { retrieveLaunchParams } from '@telegram-apps/sdk-react'

import { useAuthStore } from './store/authStore'
import { authAPI } from './api/client'

import DashboardPage from './pages/DashboardPage'
import WorkoutPage from './pages/WorkoutPage'
import ProgressPage from './pages/ProgressPage'
import NutritionPage from './pages/NutritionPage'
import ChatPage from './pages/ChatPage'
import SettingsPage from './pages/SettingsPage'
import SubscriptionPage from './pages/SubscriptionPage'
import OnboardingPage from './pages/OnboardingPage'
import ProgramPage from './pages/ProgramPage'
import BottomNav from './components/BottomNav'
import LoadingScreen from './components/LoadingScreen'
import { useState } from 'react'

export default function App() {
  const { token, setAuth, onboardingComplete } = useAuthStore()
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const authenticate = async () => {
      try {
        const { initDataRaw } = retrieveLaunchParams()

        if (!initDataRaw) {
          // Dev mode — use mock
          console.warn('No Telegram initData, using dev mode')
          setLoading(false)
          return
        }

        const response = await authAPI.telegramAuth(initDataRaw)
        const { access_token, is_new_user, onboarding_complete } = response.data

        setAuth(access_token, is_new_user, onboarding_complete)
      } catch (err) {
        console.error('Auth failed:', err)
      } finally {
        setLoading(false)
      }
    }

    authenticate()
  }, [])

  if (loading) return <LoadingScreen />

  if (!token) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-tg-bg">
        <p className="text-tg-hint">Открой в Telegram</p>
      </div>
    )
  }

  if (!onboardingComplete) {
    return (
      <BrowserRouter>
        <Routes>
          <Route path="*" element={<OnboardingPage />} />
        </Routes>
      </BrowserRouter>
    )
  }

  return (
    <BrowserRouter>
      <div className="flex flex-col min-h-screen bg-tg-bg text-tg-text">
        <main className="flex-1 overflow-y-auto pb-20">
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/workout/:id?" element={<WorkoutPage />} />
            <Route path="/program" element={<ProgramPage />} />
            <Route path="/progress" element={<ProgressPage />} />
            <Route path="/nutrition" element={<NutritionPage />} />
            <Route path="/chat" element={<ChatPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/subscription" element={<SubscriptionPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
        <BottomNav />
      </div>
    </BrowserRouter>
  )
}
