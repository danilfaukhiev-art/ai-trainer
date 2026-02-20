import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface AuthState {
  token: string | null
  isNewUser: boolean
  onboardingComplete: boolean
  setAuth: (token: string, isNew: boolean, onboardingComplete: boolean) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      isNewUser: false,
      onboardingComplete: false,
      setAuth: (token, isNewUser, onboardingComplete) =>
        set({ token, isNewUser, onboardingComplete }),
      logout: () => set({ token: null, isNewUser: false, onboardingComplete: false }),
    }),
    { name: 'auth-storage' }
  )
)
