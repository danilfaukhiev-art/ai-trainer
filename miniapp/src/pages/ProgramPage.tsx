import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { workoutsAPI } from '../api/client'

const MUSCLE_RU: Record<string, string> = {
  chest: 'Грудь', back: 'Спина', shoulders: 'Плечи',
  biceps: 'Бицепс', triceps: 'Трицепс', abs: 'Пресс',
  core: 'Кор', quadriceps: 'Квадрицепс', hamstrings: 'Бицепс бедра',
  glutes: 'Ягодицы', calves: 'Икры', forearms: 'Предплечья', cardio: 'Кардио',
}

interface ExPreview {
  name: string
  muscle_groups: string[]
  weight?: number | null
  sets?: number | null
  reps?: string | number | null
}

interface WorkoutCard {
  id: string
  day: number
  week: number
  scheduled_date: string
  status: string
  is_today: boolean
  label: string
  week_focus: string[]
  exercises: ExPreview[]
}

export default function ProgramPage() {
  const navigate = useNavigate()
  const [workouts, setWorkouts] = useState<WorkoutCard[]>([])
  const [planName, setPlanName] = useState('')
  const [coachIntro, setCoachIntro] = useState('')
  const [loading, setLoading] = useState(true)
  const [expandedIntro, setExpandedIntro] = useState(false)
  const [expandedDay, setExpandedDay] = useState<string | null>(null)

  useEffect(() => {
    workoutsAPI.getSchedule().then(r => {
      setWorkouts(r.data.workouts || [])
      setPlanName(r.data.plan_name || '')
      setCoachIntro(r.data.coach_intro || '')
      // Auto-expand today
      const today = r.data.workouts?.find((w: WorkoutCard) => w.is_today)
      if (today) setExpandedDay(today.id)
    }).catch(console.error).finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full pt-24">
        <div className="w-8 h-8 border-4 border-tg-button border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (!workouts.length) {
    return (
      <div className="flex flex-col items-center justify-center h-full pt-24 p-6 text-center">
        <span className="text-5xl mb-4">📋</span>
        <h2 className="text-xl font-bold mb-2">Программы нет</h2>
        <p className="text-tg-hint text-sm">Пройди онбординг чтобы получить персональный план</p>
      </div>
    )
  }

  const uniqueMuscles = (exercises: ExPreview[]) => {
    const set = new Set<string>()
    exercises.forEach(e => (e.muscle_groups || []).forEach(m => set.add(m)))
    return Array.from(set).slice(0, 4)
  }

  const statusColor = (status: string, isToday: boolean) => {
    if (status === 'completed') return { bg: 'rgba(16,185,129,0.1)', border: 'rgba(16,185,129,0.3)', dot: '#10b981' }
    if (isToday) return { bg: 'rgba(59,130,246,0.08)', border: 'rgba(59,130,246,0.35)', dot: '#3b82f6' }
    return { bg: 'rgba(255,255,255,0.03)', border: 'rgba(255,255,255,0.08)', dot: 'rgba(255,255,255,0.2)' }
  }

  return (
    <div className="min-h-screen bg-tg-bg pb-24">
      {/* Header */}
      <div className="px-5 pt-6 pb-3">
        <h1 className="text-2xl font-bold tracking-tight">Моя программа</h1>
        {planName && <p className="text-sm text-tg-hint mt-0.5">{planName}</p>}
      </div>

      {/* Coach intro */}
      {coachIntro && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="mx-5 mb-4 glass-card rounded-2xl overflow-hidden"
        >
          <button
            onClick={() => setExpandedIntro(v => !v)}
            className="w-full p-4 flex items-start gap-3 text-left"
          >
            <div className="w-10 h-10 rounded-xl flex items-center justify-center text-base font-black shrink-0 text-white"
              style={{ background: 'linear-gradient(135deg, #7c3aed, #4f46e5)' }}>
              К
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-2">
                <p className="font-bold text-sm">Тренер Константин — разбор плана</p>
                <span className="text-tg-hint text-xs shrink-0">{expandedIntro ? '▲' : '▼'}</span>
              </div>
              {!expandedIntro && (
                <p className="text-xs text-tg-hint mt-0.5 line-clamp-2 leading-relaxed">
                  {coachIntro.split('\n')[0]}
                </p>
              )}
            </div>
          </button>
          <AnimatePresence>
            {expandedIntro && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="overflow-hidden"
              >
                <div className="px-4 pb-4 space-y-3">
                  {coachIntro.split('\n\n').filter(Boolean).map((para, i) => (
                    <p key={i} className="text-sm leading-relaxed text-tg-hint">{para}</p>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      )}

      {/* Weekly schedule */}
      <div className="px-5 space-y-3">
        {workouts.map((w, idx) => {
          const colors = statusColor(w.status, w.is_today)
          const isExpanded = expandedDay === w.id
          const muscles = uniqueMuscles(w.exercises)
          const dateStr = w.scheduled_date
            ? new Date(w.scheduled_date).toLocaleDateString('ru', { weekday: 'short', day: 'numeric', month: 'short' })
            : ''

          return (
            <motion.div
              key={w.id}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.04 }}
              className="rounded-2xl overflow-hidden"
              style={{ background: colors.bg, border: `1px solid ${colors.border}` }}
            >
              {/* Day header */}
              <button
                className="w-full p-4 flex items-start gap-3 text-left"
                onClick={() => setExpandedDay(isExpanded ? null : w.id)}
              >
                {/* Day number badge */}
                <div className="w-9 h-9 rounded-xl flex flex-col items-center justify-center shrink-0"
                  style={{ background: w.status === 'completed' ? '#10b981' : w.is_today ? '#3b82f6' : 'rgba(255,255,255,0.06)' }}>
                  <span className="text-[10px] font-bold text-white opacity-80">Д</span>
                  <span className="text-sm font-black text-white leading-none">{w.day}</span>
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <p className="font-bold text-sm leading-tight">{w.label}</p>
                    {w.is_today && (
                      <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-full text-white"
                        style={{ background: '#3b82f6' }}>сегодня</span>
                    )}
                    {w.status === 'completed' && (
                      <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-full text-white"
                        style={{ background: '#10b981' }}>✓ готово</span>
                    )}
                  </div>
                  <p className="text-xs text-tg-hint mt-0.5">{dateStr} · {w.exercises.length} упр.</p>
                  {/* Muscle chips */}
                  {muscles.length > 0 && (
                    <div className="flex gap-1 mt-1.5 flex-wrap">
                      {muscles.map(m => (
                        <span key={m} className="text-[10px] px-1.5 py-0.5 rounded-full font-semibold"
                          style={{ background: 'rgba(249,115,22,0.12)', color: '#f97316' }}>
                          {MUSCLE_RU[m] || m}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                <span className="text-tg-hint text-xs pt-1 shrink-0">{isExpanded ? '▲' : '▼'}</span>
              </button>

              {/* Expanded exercises list */}
              <AnimatePresence>
                {isExpanded && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="overflow-hidden"
                  >
                    <div className="px-4 pb-4 space-y-2">
                      {/* Week focus */}
                      {w.week_focus && w.week_focus.length > 0 && (
                        <div className="rounded-xl p-3 mb-3" style={{ background: 'rgba(124,58,237,0.08)', border: '1px solid rgba(124,58,237,0.15)' }}>
                          <p className="text-[10px] font-bold uppercase tracking-wider mb-1.5" style={{ color: '#7c3aed' }}>Фокус дня</p>
                          <ul className="space-y-0.5">
                            {w.week_focus.slice(0, 3).map((f, i) => (
                              <li key={i} className="text-xs text-tg-hint flex gap-1.5">
                                <span style={{ color: '#7c3aed' }}>•</span>{f}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Exercises */}
                      {w.exercises.map((ex, i) => (
                        <div key={i} className="flex items-center justify-between py-2 border-b last:border-0"
                          style={{ borderColor: 'rgba(255,255,255,0.05)' }}>
                          <div className="flex-1 min-w-0 mr-3">
                            <p className="text-sm font-semibold truncate">{ex.name}</p>
                            {ex.muscle_groups?.length > 0 && (
                              <p className="text-[10px] text-tg-hint mt-0.5">
                                {ex.muscle_groups.map(m => MUSCLE_RU[m] || m).join(', ')}
                              </p>
                            )}
                          </div>
                          <div className="text-right shrink-0">
                            {ex.sets && ex.reps && (
                              <p className="text-sm font-bold tabular-nums">{ex.sets}×{ex.reps}</p>
                            )}
                            {ex.weight && (
                              <p className="text-[11px] text-tg-hint">{ex.weight} кг</p>
                            )}
                          </div>
                        </div>
                      ))}

                      {/* Start button */}
                      {w.status === 'pending' && (
                        <motion.button
                          whileTap={{ scale: 0.97 }}
                          onClick={() => navigate(`/workout/${w.id}`)}
                          className="w-full mt-3 py-3 rounded-xl font-bold text-sm text-white"
                          style={{
                            background: w.is_today
                              ? 'linear-gradient(135deg, #3b82f6, #2563eb)'
                              : 'rgba(255,255,255,0.06)',
                            color: w.is_today ? '#fff' : 'var(--tg-theme-hint-color)',
                          }}
                        >
                          {w.is_today ? 'Начать тренировку' : 'Открыть тренировку'}
                        </motion.button>
                      )}
                      {w.status === 'completed' && (
                        <button
                          onClick={() => navigate(`/workout/${w.id}`)}
                          className="w-full mt-3 py-2.5 rounded-xl text-sm font-semibold"
                          style={{ background: 'rgba(16,185,129,0.1)', color: '#10b981' }}
                        >
                          Посмотреть результаты
                        </button>
                      )}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}
