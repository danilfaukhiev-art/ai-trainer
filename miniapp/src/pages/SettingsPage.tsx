import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { profileAPI } from '../api/client'
import { useAuthStore } from '../store/authStore'

interface Profile {
  telegram_username: string | null
  goal: string | null
  gender: string | null
  age: number | null
  height_cm: number | null
  weight_kg: number | null
  fitness_level: string | null
  equipment: string | null
  available_days: number | null
  session_minutes: number | null
  medical_notes: string | null
  subscription_tier: string
}

const TIER_LABELS: Record<string, { label: string; emoji: string; gradient: string }> = {
  free: { label: 'Бесплатный', emoji: '🆓', gradient: 'linear-gradient(135deg, #9ca3af, #6b7280)' },
  basic: { label: 'Basic', emoji: '⭐', gradient: 'linear-gradient(135deg, #f59e0b, #d97706)' },
  pro: { label: 'Pro', emoji: '🚀', gradient: 'linear-gradient(135deg, #2563eb, #7c3aed)' },
  premium: { label: 'Premium', emoji: '💎', gradient: 'linear-gradient(135deg, #8b5cf6, #ec4899)' },
}

const GOAL_LABELS: Record<string, string> = {
  fat_loss: 'Похудеть',
  muscle_gain: 'Набрать мышцы',
  health: 'Здоровье и тонус',
  endurance: 'Выносливость',
}

const FITNESS_LABELS: Record<string, string> = {
  beginner: 'Новичок',
  intermediate: 'Средний',
  advanced: 'Продвинутый',
}

const EQUIPMENT_LABELS: Record<string, string> = {
  gym: 'Тренажёрный зал',
  home: 'Дома',
  minimal: 'Минимум оборудования',
}

export default function SettingsPage() {
  const { logout } = useAuthStore()
  const navigate = useNavigate()
  const [profile, setProfile] = useState<Profile | null>(null)
  const [loading, setLoading] = useState(true)
  const [editField, setEditField] = useState<string | null>(null)
  const [editValue, setEditValue] = useState('')
  const [saving, setSaving] = useState(false)
  const [deleteStep, setDeleteStep] = useState(0)
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    loadProfile()
  }, [])

  const loadProfile = async () => {
    try {
      const res = await profileAPI.getProfile()
      setProfile(res.data)
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }

  const startEdit = (field: string, current: string | number | null) => {
    setEditField(field)
    setEditValue(String(current ?? ''))
  }

  const saveEdit = async () => {
    if (!editField || !profile) return
    setSaving(true)
    try {
      const data: Record<string, number | string> = {}
      if (editField === 'weight_kg') data.weight_kg = parseFloat(editValue)
      if (editField === 'available_days') data.available_days = parseInt(editValue)
      if (editField === 'session_minutes') data.session_minutes = parseInt(editValue)
      await profileAPI.updateProfile(data)
      setProfile({ ...profile, ...data } as Profile)
      setEditField(null)
    } catch {
      // ignore
    } finally {
      setSaving(false)
    }
  }

  const handleDeleteAccount = async () => {
    if (deleteStep === 0) { setDeleteStep(1); return }
    setDeleting(true)
    try {
      await profileAPI.deleteAccount()
      setDeleteStep(2)
      setTimeout(() => logout(), 2000)
    } catch {
      setDeleting(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="w-8 h-8 border-4 border-tg-button border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (deleteStep === 2) {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="flex flex-col items-center justify-center h-screen p-8 text-center"
      >
        <div className="text-6xl mb-4">👋</div>
        <h2 className="text-2xl font-bold mb-2">Аккаунт удалён</h2>
        <p className="text-tg-hint text-sm">Возвращайся, когда будешь готов</p>
      </motion.div>
    )
  }

  const tier = profile ? TIER_LABELS[profile.subscription_tier] || TIER_LABELS.free : TIER_LABELS.free

  return (
    <div className="min-h-screen bg-tg-bg pb-24">
      {/* Header */}
      <div className="px-5 pt-6 pb-4">
        <h1 className="text-2xl font-bold tracking-tight">Настройки</h1>
        <p className="text-sm text-tg-hint mt-0.5">Управляй своим профилем</p>
      </div>

      {/* Profile card */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="mx-5 mb-4 glass-card rounded-2xl p-5"
      >
        <div className="flex items-center gap-4 mb-4">
          <div className="w-14 h-14 rounded-2xl flex items-center justify-center text-3xl"
            style={{ background: tier.gradient, boxShadow: '0 4px 12px rgba(0,0,0,0.15)' }}>
            👤
          </div>
          <div>
            <div className="font-bold text-lg">
              {profile?.telegram_username ? `@${profile.telegram_username}` : 'Мой профиль'}
            </div>
            <div className="flex items-center gap-1.5 mt-0.5">
              <span className="text-sm font-bold px-2 py-0.5 rounded-md text-white"
                style={{ background: tier.gradient, fontSize: '11px' }}>
                {tier.emoji} {tier.label}
              </span>
            </div>
          </div>
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-3 gap-2">
          {[
            { label: 'Возраст', value: profile?.age ? `${profile.age}` : '—' },
            { label: 'Рост', value: profile?.height_cm ? `${profile.height_cm} см` : '—' },
            { label: 'Уровень', value: profile?.fitness_level ? FITNESS_LABELS[profile.fitness_level] : '—' },
          ].map(stat => (
            <div key={stat.label} className="bg-tg-bg rounded-xl p-3 text-center">
              <div className="font-extrabold text-base">{stat.value}</div>
              <div className="text-[10px] font-medium text-tg-hint mt-0.5 uppercase tracking-wide">{stat.label}</div>
            </div>
          ))}
        </div>
      </motion.div>

      {/* Editable params */}
      <div className="mx-5 mb-4">
        <h2 className="text-xs font-bold text-tg-hint mb-2 px-1 uppercase tracking-wider">Параметры</h2>
        <div className="glass-card rounded-2xl overflow-hidden">
          {[
            { key: 'weight_kg', label: 'Вес', value: profile?.weight_kg, suffix: 'кг', type: 'number' },
            { key: 'available_days', label: 'Дней в неделю', value: profile?.available_days, suffix: 'дн', type: 'number' },
            { key: 'session_minutes', label: 'Длина тренировки', value: profile?.session_minutes, suffix: 'мин', type: 'number' },
          ].map((item, idx, arr) => (
            <div key={item.key}>
              <div className="flex items-center px-4 py-3.5">
                <span className="text-sm font-medium flex-1">{item.label}</span>
                {editField === item.key ? (
                  <div className="flex items-center gap-2">
                    <input
                      type="number"
                      value={editValue}
                      onChange={e => setEditValue(e.target.value)}
                      className="bg-tg-bg rounded-xl px-3 py-1.5 text-sm w-20 text-center outline-none font-semibold"
                      autoFocus
                    />
                    <button
                      onClick={saveEdit}
                      disabled={saving}
                      className="text-sm font-bold px-3 py-1.5 rounded-xl btn-premium"
                    >
                      {saving ? '...' : 'OK'}
                    </button>
                    <button onClick={() => setEditField(null)} className="text-tg-hint text-sm px-2">✕</button>
                  </div>
                ) : (
                  <button
                    onClick={() => startEdit(item.key, item.value ?? null)}
                    className="flex items-center gap-1 text-tg-hint"
                  >
                    <span className="text-sm font-semibold">{item.value ? `${item.value} ${item.suffix}` : 'Не указано'}</span>
                    <span className="text-lg ml-1">›</span>
                  </button>
                )}
              </div>
              {idx < arr.length - 1 && <div className="h-px bg-tg-bg mx-4" />}
            </div>
          ))}
        </div>
      </div>

      {/* Info params */}
      <div className="mx-5 mb-4">
        <h2 className="text-xs font-bold text-tg-hint mb-2 px-1 uppercase tracking-wider">Программа</h2>
        <div className="glass-card rounded-2xl overflow-hidden">
          {[
            { label: 'Цель', value: profile?.goal ? (GOAL_LABELS[profile.goal] || profile.goal) : '—' },
            { label: 'Место тренировок', value: profile?.equipment ? EQUIPMENT_LABELS[profile.equipment] : '—' },
            ...(profile?.medical_notes ? [{ label: 'Мед. особенности', value: profile.medical_notes }] : []),
          ].map((item, idx, arr) => (
            <div key={item.label}>
              <div className="flex items-center px-4 py-3.5">
                <span className="text-sm font-medium flex-1">{item.label}</span>
                <span className="text-sm text-tg-hint font-medium max-w-[50%] text-right">{item.value}</span>
              </div>
              {idx < arr.length - 1 && <div className="h-px bg-tg-bg mx-4" />}
            </div>
          ))}
        </div>
      </div>

      {/* Subscription */}
      <div className="mx-5 mb-4">
        <div className="glass-card rounded-2xl p-4 flex items-center gap-3">
          <span className="text-2xl">{tier.emoji}</span>
          <div className="flex-1">
            <div className="font-bold text-sm">Подписка: {tier.label}</div>
            <div className="text-xs text-tg-hint mt-0.5">
              {profile?.subscription_tier === 'free'
                ? 'Перейди на Pro для безлимитного AI-чата'
                : 'Активная подписка'}
            </div>
          </div>
          {profile?.subscription_tier === 'free' && (
            <motion.button
              whileTap={{ scale: 0.95 }}
              onClick={() => navigate('/subscription')}
              className="px-3 py-2 rounded-xl text-xs font-bold text-white shrink-0"
              style={{ background: 'linear-gradient(135deg, #2563eb, #7c3aed)' }}
            >
              Улучшить
            </motion.button>
          )}
        </div>
      </div>

      {/* Delete account */}
      <div className="mx-5 mb-4">
        <AnimatePresence>
          {deleteStep === 1 ? (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="bg-red-500/10 border border-red-500/30 rounded-2xl p-4"
            >
              <p className="text-sm font-bold text-red-500 mb-1">Удалить аккаунт?</p>
              <p className="text-xs text-tg-hint mb-4">Все данные будут удалены безвозвратно.</p>
              <div className="flex gap-3">
                <button
                  onClick={() => setDeleteStep(0)}
                  className="flex-1 py-3 rounded-xl glass-card text-sm font-semibold"
                >
                  Отмена
                </button>
                <button
                  onClick={handleDeleteAccount}
                  disabled={deleting}
                  className="flex-1 py-3 rounded-xl bg-red-500 text-white text-sm font-bold"
                >
                  {deleting ? 'Удаляем...' : 'Да, удалить'}
                </button>
              </div>
            </motion.div>
          ) : (
            <motion.button
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              onClick={handleDeleteAccount}
              className="w-full glass-card rounded-2xl p-4 flex items-center gap-3 text-red-500"
            >
              <span className="text-xl">🗑️</span>
              <span className="font-medium text-sm">Удалить аккаунт и все данные</span>
            </motion.button>
          )}
        </AnimatePresence>
      </div>

      <p className="text-center text-[10px] text-tg-hint pb-4 uppercase tracking-wider font-medium">AI Personal Trainer v1.0</p>
    </div>
  )
}
