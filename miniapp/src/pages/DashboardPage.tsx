import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { workoutsAPI, progressAPI } from '../api/client'

interface TodayWorkout {
  id: string
  exercises: Array<{ name: string; sets: number; reps: string }>
  status: string
}

const GREETINGS = [
  'Готов покорять цели?',
  'Сегодня — ещё один шаг вперёд!',
  'Твой тренер уже ждёт!',
  'Движение — это жизнь',
  'Ты становишься лучше каждый день',
]

export default function DashboardPage() {
  const navigate = useNavigate()
  const [todayWorkout, setTodayWorkout] = useState<TodayWorkout | null>(null)
  const [streak, setStreak] = useState(0)
  const [loading, setLoading] = useState(true)
  const [message, setMessage] = useState('')
  const [coachIntro, setCoachIntro] = useState('')
  const [introExpanded, setIntroExpanded] = useState(false)
  const greeting = GREETINGS[new Date().getDay() % GREETINGS.length]

  useEffect(() => {
    const load = async () => {
      try {
        const [workoutRes, progressRes] = await Promise.all([
          workoutsAPI.getToday(),
          progressAPI.getProgress(),
        ])
        setTodayWorkout(workoutRes.data.today)
        setMessage(workoutRes.data.message)
        if (workoutRes.data.coach_intro) setCoachIntro(workoutRes.data.coach_intro)
        setStreak(progressRes.data.streak?.current || 0)
      } catch (err) {
        console.error(err)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full pt-20">
        <div className="w-8 h-8 border-4 border-tg-button border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-tg-bg pb-24">
      {/* Hero Header */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="relative overflow-hidden"
      >
        <div className="absolute inset-0 opacity-[0.04]"
          style={{ background: 'radial-gradient(circle at 30% 20%, var(--tg-theme-button-color), transparent 70%)' }} />
        <div className="px-5 pt-6 pb-4 flex justify-between items-start relative">
          <div>
            <motion.h1
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="text-2xl font-bold tracking-tight"
            >
              Привет!
            </motion.h1>
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.1 }}
              className="text-tg-hint text-sm mt-0.5"
            >
              {new Date().toLocaleDateString('ru', { weekday: 'long', day: 'numeric', month: 'long' })}
            </motion.p>
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.15 }}
              className="text-sm font-semibold mt-1"
              style={{ color: 'var(--tg-theme-button-color, #2481cc)' }}
            >
              {greeting}
            </motion.p>
          </div>
          {streak > 0 && (
            <motion.div
              initial={{ scale: 0, rotate: -20 }}
              animate={{ scale: 1, rotate: 0 }}
              transition={{ type: 'spring', stiffness: 200, delay: 0.2 }}
              className="glass-card rounded-2xl px-4 py-3 flex flex-col items-center min-w-[64px]"
            >
              <span className="text-2xl">🔥</span>
              <span className="text-lg font-extrabold mt-0.5">{streak}</span>
              <span className="text-[10px] font-medium text-tg-hint">дней</span>
            </motion.div>
          )}
        </div>
      </motion.div>

      {/* AI Trainer Banner */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.05 }}
        onClick={() => navigate('/chat')}
        className="mx-5 mb-4 rounded-2xl p-4 flex items-center gap-3 cursor-pointer active:scale-[0.98] transition-transform"
        style={{
          background: 'linear-gradient(135deg, var(--tg-theme-button-color, #2481cc)15, var(--tg-theme-button-color, #2481cc)08)',
          boxShadow: 'var(--card-shadow)',
        }}
      >
        <div className="w-11 h-11 rounded-xl flex items-center justify-center text-xl glass-card flex-shrink-0">
          🤖
        </div>
        <div className="flex-1 min-w-0">
          <div className="font-bold text-sm">AI-тренер Константин</div>
          <div className="text-xs text-tg-hint truncate">Спроси совет или разбери технику</div>
        </div>
        <div className="btn-premium text-xs font-bold px-3.5 py-2 rounded-xl flex-shrink-0">
          Чат
        </div>
      </motion.div>

      {/* Coach Intro Card */}
      {coachIntro && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.08 }}
          className="mx-5 mb-4 glass-card rounded-2xl overflow-hidden"
        >
          <button
            onClick={() => setIntroExpanded(v => !v)}
            className="w-full p-4 flex items-start gap-3 text-left"
          >
            <div className="w-10 h-10 rounded-xl flex items-center justify-center text-lg flex-shrink-0 font-bold"
              style={{ background: 'linear-gradient(135deg, #7c3aed, #4f46e5)', color: '#fff' }}>
              М
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between">
                <p className="font-bold text-sm">Тренер Константин — твой план</p>
                <span className="text-tg-hint text-xs ml-2">{introExpanded ? '▲' : '▼'}</span>
              </div>
              {!introExpanded && (
                <p className="text-xs text-tg-hint mt-0.5 line-clamp-2 leading-relaxed">
                  {coachIntro.split('\n')[0]}
                </p>
              )}
            </div>
          </button>
          {introExpanded && (
            <div className="px-4 pb-4 space-y-3">
              {coachIntro.split('\n\n').filter(Boolean).map((para, i) => (
                <p key={i} className="text-sm leading-relaxed text-tg-hint">{para}</p>
              ))}
            </div>
          )}
        </motion.div>
      )}

      {/* Today Workout Card */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="mx-5 mb-4 glass-card rounded-2xl p-5"
      >
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-bold tracking-tight">Тренировка сегодня</h2>
          {todayWorkout && (
            <span className="text-[11px] font-semibold px-2.5 py-1 rounded-full"
              style={{ background: 'var(--tg-theme-button-color, #2481cc)12', color: 'var(--tg-theme-button-color, #2481cc)' }}>
              {todayWorkout.exercises.length} упр.
            </span>
          )}
        </div>

        {todayWorkout ? (
          <>
            <div className="space-y-1 mb-4">
              {todayWorkout.exercises.slice(0, 4).map((ex, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.15 + i * 0.05 }}
                  className="flex justify-between items-center py-2.5 border-b last:border-0"
                  style={{ borderColor: 'var(--tg-theme-bg-color)' }}
                >
                  <span className="font-medium text-sm">{ex.name}</span>
                  <span className="text-tg-hint text-sm font-semibold tabular-nums">{ex.sets}x{ex.reps}</span>
                </motion.div>
              ))}
              {todayWorkout.exercises.length > 4 && (
                <p className="text-tg-hint text-xs pt-1">+{todayWorkout.exercises.length - 4} упражнений</p>
              )}
            </div>
            <motion.button
              whileTap={{ scale: 0.97 }}
              onClick={() => navigate(`/workout/${todayWorkout.id}`)}
              className="w-full py-3.5 rounded-xl font-bold text-base btn-premium"
            >
              Начать тренировку
            </motion.button>
          </>
        ) : (
          <div className="text-center py-8">
            <motion.span
              animate={{ y: [0, -5, 0] }}
              transition={{ duration: 2, repeat: Infinity }}
              className="text-5xl inline-block"
            >
              🛋️
            </motion.span>
            <p className="mt-3 font-bold text-lg">День отдыха</p>
            <p className="mt-1 text-tg-hint text-sm">{message || 'Восстановление — часть прогресса'}</p>
          </div>
        )}
      </motion.div>

      {/* Quick Actions */}
      <div className="mx-5">
        <h2 className="text-xs font-bold text-tg-hint mb-2.5 px-1 uppercase tracking-wider">Разделы</h2>
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
          className="grid grid-cols-2 gap-3"
        >
          {[
            { emoji: '📊', label: 'Прогресс', sub: 'Замеры и графики', path: '/progress' },
            { emoji: '🥗', label: 'Питание', sub: 'Калории и БЖУ', path: '/nutrition' },
            { emoji: '🤖', label: 'AI-тренер', sub: 'Чат с Константином', path: '/chat' },
            { emoji: '⚙️', label: 'Настройки', sub: 'Профиль и данные', path: '/settings' },
          ].map((item, i) => (
            <motion.button
              key={item.path}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.25 + i * 0.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => navigate(item.path)}
              className="glass-card rounded-2xl p-4 flex flex-col items-start gap-1 text-left"
            >
              <span className="text-2xl">{item.emoji}</span>
              <span className="font-bold text-sm mt-1">{item.label}</span>
              <span className="text-[11px] text-tg-hint">{item.sub}</span>
            </motion.button>
          ))}
        </motion.div>
      </div>
    </div>
  )
}
