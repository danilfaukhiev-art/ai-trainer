import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { workoutsAPI, profileAPI } from '../api/client'
import MuscleBodySVG from '../components/MuscleBodySVG'

const MUSCLE_LABELS_RU: Record<string, string> = {
  chest: 'Грудь', back: 'Спина', shoulders: 'Плечи',
  biceps: 'Бицепс', triceps: 'Трицепс', abs: 'Пресс',
  core: 'Кор', quadriceps: 'Квадрицепс', hamstrings: 'Бицепс бедра',
  glutes: 'Ягодицы', calves: 'Икры', forearms: 'Предплечья', cardio: 'Кардио',
}

interface Exercise {
  id: string
  name: string
  sets: number
  reps: string
  rest_sec: number
  notes: string
  weight_kg: number | null
  muscle_groups?: string[]
  gif_url?: string | null
}

interface RichExercise {
  name: string
  name_en?: string
  muscle_groups?: string[]
  is_main_lift?: boolean
  technique?: string
  warmup_str?: string
  top_set_weight?: number
  top_set_sets?: number
  top_set_reps?: number
  top_set_rpe?: string
  top_set_note?: string
  volume_weight?: number
  volume_sets?: number
  volume_reps?: number
  volume_note?: string
  sets?: number
  reps_min?: number
  reps_max?: number
  reps?: number
  weight_kg?: number
  coach_note?: string
  rest_sec?: number
  gif_url?: string | null
  instructions?: string[]
  steps_ru?: string[]
}

interface RichPlan {
  label: string
  week_focus?: string[]
  weekly_rules?: string[]
  weekly_goal?: string
  exercises: RichExercise[]
}

interface Workout {
  id: string
  exercises: Exercise[]
  status: string
  week: number
  day: number
  rich_plan?: RichPlan | null
}

interface WarmupExercise {
  name: string
  duration_sec: number | null
  reps: string | null
  notes: string
}

interface WarmupData {
  duration_min: number
  exercises: WarmupExercise[]
}

interface SetLog {
  workout_exercise_id: string
  set_number: number
  reps_done: number | null
  weight_kg: number | null
}

type Phase = 'warmup' | 'workout'

export default function WorkoutPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [workout, setWorkout] = useState<Workout | null>(null)
  const [warmup, setWarmup] = useState<WarmupData | null>(null)
  const [phase, setPhase] = useState<Phase>('warmup')
  const [warmupIdx, setWarmupIdx] = useState(0)
  const [loading, setLoading] = useState(true)
  const [currentExIdx, setCurrentExIdx] = useState(0)
  const [rpe, setRpe] = useState<number | null>(null)
  const [completing, setCompleting] = useState(false)
  const [completed, setCompleted] = useState(false)
  const [aiFeedback, setAiFeedback] = useState('')
  const [showAnatomy, setShowAnatomy] = useState(false)
  const [gender, setGender] = useState<'male' | 'female'>('male')
  // Per-set tracking: exId -> array of {reps_done, weight_kg} per set
  const [setsData, setSetsData] = useState<Record<string, { reps: string; weight: string }[]>>({})
  const [completedSets, setCompletedSets] = useState<Record<string, boolean[]>>({})

  useEffect(() => {
    profileAPI.getProfile().then(r => {
      if (r.data?.gender === 'female') setGender('female')
    }).catch(() => {})
  }, [])

  useEffect(() => {
    const load = async () => {
      try {
        let workoutData: Workout
        if (id) {
          const res = await workoutsAPI.getWorkout(id)
          workoutData = res.data
        } else {
          const res = await workoutsAPI.getToday()
          if (!res.data.today) { setLoading(false); return }
          const wRes = await workoutsAPI.getWorkout(res.data.today.id)
          workoutData = wRes.data
        }
        setWorkout(workoutData)
        // Init per-set state for all exercises
        const initSets: Record<string, { reps: string; weight: string }[]> = {}
        const initCompleted: Record<string, boolean[]> = {}
        for (const ex of workoutData.exercises) {
          initSets[ex.id] = Array.from({ length: ex.sets }, () => ({
            reps: '',
            weight: ex.weight_kg ? String(ex.weight_kg) : '',
          }))
          initCompleted[ex.id] = Array(ex.sets).fill(false)
        }
        setSetsData(initSets)
        setCompletedSets(initCompleted)
        try {
          const wRes = await workoutsAPI.getWarmup(workoutData.id)
          setWarmup(wRes.data)
        } catch { /* warmup optional */ }
      } catch (err) {
        console.error(err)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [id])

  const updateSetField = (exId: string, setIdx: number, field: 'reps' | 'weight', value: string) => {
    setSetsData(prev => {
      const updated = [...(prev[exId] || [])]
      updated[setIdx] = { ...updated[setIdx], [field]: value }
      return { ...prev, [exId]: updated }
    })
  }

  const toggleSetDone = (exId: string, setIdx: number) => {
    setCompletedSets(prev => {
      const updated = [...(prev[exId] || [])]
      updated[setIdx] = !updated[setIdx]
      return { ...prev, [exId]: updated }
    })
  }

  const buildSetsLog = (): SetLog[] => {
    if (!workout) return []
    const log: SetLog[] = []
    for (const ex of workout.exercises) {
      const sets = setsData[ex.id] || []
      sets.forEach((s, idx) => {
        if (completedSets[ex.id]?.[idx]) {
          log.push({
            workout_exercise_id: ex.id,
            set_number: idx + 1,
            reps_done: s.reps ? parseInt(s.reps) : null,
            weight_kg: s.weight ? parseFloat(s.weight) : null,
          })
        }
      })
    }
    return log
  }

  const handleComplete = async () => {
    if (!workout || !rpe) return
    setCompleting(true)
    try {
      const res = await workoutsAPI.completeWorkout(workout.id, {
        rpe_score: rpe,
        sets_log: buildSetsLog(),
      })
      setAiFeedback(res.data.ai_feedback)
      setCompleted(true)
    } catch (err) {
      console.error(err)
    } finally {
      setCompleting(false)
    }
  }

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-full pt-20 gap-4">
        <div className="w-8 h-8 border-4 border-tg-button border-t-transparent rounded-full animate-spin" />
        <p className="text-tg-hint text-sm">Загружаем разминку...</p>
      </div>
    )
  }

  if (!workout) {
    return (
      <div className="flex flex-col items-center justify-center h-full pt-20 p-4 text-center">
        <motion.span
          animate={{ y: [0, -5, 0] }}
          transition={{ duration: 2, repeat: Infinity }}
          className="text-5xl mb-4 inline-block"
        >
          🛋️
        </motion.span>
        <h2 className="text-xl font-bold mb-2">Тренировок нет</h2>
        <p className="text-tg-hint">Сегодня день отдыха!</p>
        <button onClick={() => navigate('/')} className="mt-6 btn-premium px-6 py-3 rounded-xl font-semibold">
          На главную
        </button>
      </div>
    )
  }

  if (completed) {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="flex flex-col items-center justify-center min-h-screen p-6 text-center"
      >
        <motion.span
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: 'spring', stiffness: 200, delay: 0.1 }}
          className="text-7xl mb-4"
        >
          🎉
        </motion.span>
        <motion.h2
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="text-2xl font-bold mb-2"
        >
          Тренировка завершена!
        </motion.h2>
        {aiFeedback && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="glass-card rounded-2xl p-4 mt-4 text-left w-full max-w-sm"
          >
            <p className="text-sm text-tg-hint mb-1 font-semibold">🤖 Тренер говорит:</p>
            <p className="text-sm leading-relaxed">{aiFeedback}</p>
          </motion.div>
        )}
        <motion.button
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4 }}
          onClick={() => navigate('/')}
          className="mt-6 w-full max-w-sm btn-premium py-3.5 rounded-xl font-bold"
        >
          На главную
        </motion.button>
      </motion.div>
    )
  }

  // ── WARMUP PHASE ───────────────────────────────────────────
  if (phase === 'warmup' && warmup) {
    const wEx = warmup.exercises[warmupIdx]
    const wProgress = ((warmupIdx + 1) / warmup.exercises.length) * 100

    return (
      <div className="min-h-screen bg-tg-bg p-4 pb-24 space-y-4">
        {/* Header */}
        <div className="pt-2 flex items-center justify-between">
          <div>
            <span className="text-xs font-bold uppercase tracking-wider px-2.5 py-1 rounded-full"
              style={{ background: 'rgba(16, 185, 129, 0.15)', color: '#10b981' }}>
              🔥 Разминка
            </span>
            <p className="text-xs text-tg-hint mt-1.5">{warmup.duration_min} мин · профессиональный разогрев</p>
          </div>
          <button
            onClick={() => setPhase('workout')}
            className="text-xs text-tg-hint font-medium px-3 py-1.5 rounded-lg bg-tg-secondary-bg"
          >
            Пропустить →
          </button>
        </div>

        {/* Progress */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-tg-hint">
              {warmupIdx + 1} из {warmup.exercises.length}
            </span>
            <span className="text-xs font-bold" style={{ color: '#10b981' }}>
              {Math.round(wProgress)}%
            </span>
          </div>
          <div className="h-1.5 bg-tg-secondary-bg rounded-full overflow-hidden">
            <motion.div
              className="h-full rounded-full"
              style={{ background: 'linear-gradient(90deg, #10b981, #059669)' }}
              animate={{ width: `${wProgress}%` }}
              transition={{ duration: 0.4, ease: 'easeOut' }}
            />
          </div>
        </div>

        {/* Warmup Exercise Card */}
        <AnimatePresence mode="wait">
          <motion.div
            key={warmupIdx}
            initial={{ opacity: 0, x: 30 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -30 }}
            className="rounded-2xl p-5 border"
            style={{ background: 'rgba(16, 185, 129, 0.06)', borderColor: 'rgba(16, 185, 129, 0.2)' }}
          >
            <h2 className="text-2xl font-bold mb-3 tracking-tight">{wEx.name}</h2>
            <div className="flex gap-3 mb-3">
              {wEx.duration_sec && (
                <div className="flex-1 rounded-xl px-3 py-2.5 text-center" style={{ background: 'rgba(16, 185, 129, 0.12)' }}>
                  <p className="text-lg font-extrabold">{wEx.duration_sec}с</p>
                  <p className="text-[11px] text-tg-hint font-medium">Время</p>
                </div>
              )}
              {wEx.reps && (
                <div className="flex-1 rounded-xl px-3 py-2.5 text-center" style={{ background: 'rgba(16, 185, 129, 0.12)' }}>
                  <p className="text-lg font-extrabold">{wEx.reps}</p>
                  <p className="text-[11px] text-tg-hint font-medium">Повторения</p>
                </div>
              )}
            </div>
            {wEx.notes && (
              <div className="rounded-xl p-3" style={{ background: 'rgba(0,0,0,0.03)' }}>
                <p className="text-sm text-tg-hint leading-relaxed">{wEx.notes}</p>
              </div>
            )}
          </motion.div>
        </AnimatePresence>

        {/* Navigation */}
        <div className="flex gap-3">
          {warmupIdx > 0 && (
            <motion.button
              whileTap={{ scale: 0.97 }}
              onClick={() => setWarmupIdx(i => i - 1)}
              className="flex-1 glass-card py-3.5 rounded-xl font-semibold text-sm"
            >
              ← Назад
            </motion.button>
          )}
          {warmupIdx < warmup.exercises.length - 1 ? (
            <motion.button
              whileTap={{ scale: 0.97 }}
              onClick={() => setWarmupIdx(i => i + 1)}
              className="flex-1 py-3.5 rounded-xl font-bold text-sm text-white"
              style={{ background: 'linear-gradient(135deg, #10b981, #059669)' }}
            >
              Следующее →
            </motion.button>
          ) : (
            <motion.button
              whileTap={{ scale: 0.97 }}
              onClick={() => setPhase('workout')}
              className="flex-1 py-3.5 rounded-xl font-bold text-sm text-white"
              style={{ background: 'linear-gradient(135deg, #10b981, #059669)' }}
            >
              Начать тренировку 💪
            </motion.button>
          )}
        </div>
      </div>
    )
  }

  // ── No warmup — skip to workout ────────────────────────────────
  if (phase === 'warmup' && !warmup) {
    setPhase('workout')
  }

  // ── MAIN WORKOUT PHASE ────────────────────────────────────
  const currentEx = workout.exercises[currentExIdx]
  const progress = ((currentExIdx + 1) / workout.exercises.length) * 100
  const exSets = setsData[currentEx.id] || []
  const exCompleted = completedSets[currentEx.id] || []
  const allSetsLogged = exSets.length > 0 && exCompleted.every(Boolean)

  return (
    <div className="min-h-screen bg-tg-bg p-4 pb-24 space-y-4">
      {/* Progress bar */}
      <div className="pt-2">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-semibold text-tg-hint">
            Упражнение {currentExIdx + 1} из {workout.exercises.length}
          </span>
          <span className="text-xs font-bold" style={{ color: 'var(--tg-theme-button-color)' }}>
            {Math.round(progress)}%
          </span>
        </div>
        <div className="h-1.5 bg-tg-secondary-bg rounded-full overflow-hidden">
          <motion.div
            className="h-full rounded-full"
            style={{ background: 'linear-gradient(90deg, var(--tg-theme-button-color, #2563eb), #7c3aed)' }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.4, ease: 'easeOut' }}
          />
        </div>
      </div>

      {/* Week focus banner (shown on first exercise) */}
      {currentExIdx === 0 && workout.rich_plan?.week_focus && workout.rich_plan.week_focus.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-2xl p-4"
          style={{ background: 'rgba(124,58,237,0.08)', border: '1px solid rgba(124,58,237,0.2)' }}
        >
          <p className="text-xs font-bold uppercase tracking-wider mb-2" style={{ color: '#7c3aed' }}>
            📅 Фокус недели
          </p>
          <ul className="space-y-1">
            {workout.rich_plan.week_focus.map((f, i) => (
              <li key={i} className="text-sm flex gap-2">
                <span style={{ color: '#7c3aed' }}>•</span>
                <span>{f}</span>
              </li>
            ))}
          </ul>
        </motion.div>
      )}

      {/* Current exercise */}
      <AnimatePresence mode="wait">
        <motion.div
          key={currentExIdx}
          initial={{ opacity: 0, x: 30 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -30 }}
          className="glass-card rounded-2xl p-5"
        >
          {/* Exercise name + technique */}
          <h2 className="text-2xl font-bold tracking-tight">{currentEx.name}</h2>
          {(() => {
            const rich = workout.rich_plan?.exercises[currentExIdx]
            if (rich?.technique) {
              return <p className="text-xs text-tg-hint mt-1 italic">{rich.technique}</p>
            }
          })()}

          {/* GIF + Instructions */}
          {(() => {
            const rich = workout.rich_plan?.exercises[currentExIdx]
            const gifUrl = currentEx.gif_url || rich?.gif_url
            const instructions = rich?.steps_ru?.length ? rich.steps_ru : (rich?.instructions?.length ? rich.instructions : [])
            if (!gifUrl && instructions.length === 0) return null
            return (
              <div className="mt-3 mb-1 rounded-2xl overflow-hidden" style={{ border: '1px solid rgba(255,255,255,0.06)' }}>
                {gifUrl && (
                  <div className="flex justify-center bg-tg-secondary-bg">
                    <img
                      src={gifUrl}
                      alt={currentEx.name}
                      className="h-52 w-auto object-contain"
                      loading="lazy"
                    />
                  </div>
                )}
                {instructions && instructions.length > 0 && (
                  <div className="p-3 space-y-2" style={{ background: 'rgba(255,255,255,0.03)' }}>
                    <p className="text-[10px] font-bold uppercase tracking-wider text-tg-hint">Техника выполнения</p>
                    <ol className="space-y-1.5">
                      {instructions.map((step, i) => (
                        <li key={i} className="flex gap-2 text-sm leading-snug">
                          <span className="shrink-0 w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold mt-0.5"
                            style={{ background: 'rgba(59,130,246,0.15)', color: '#3b82f6' }}>
                            {i + 1}
                          </span>
                          <span className="text-tg-hint">{step}</span>
                        </li>
                      ))}
                    </ol>
                  </div>
                )}
              </div>
            )
          })()}

          {/* Rich plan card */}
          {(() => {
            const rich = workout.rich_plan?.exercises[currentExIdx]
            if (!rich) {
              // Fallback: legacy display
              return (
                <>
                  <div className="flex gap-3 my-4">
                    <StatCard label="Подходы" value={String(currentEx.sets)} />
                    <StatCard label="Повторения" value={currentEx.reps} />
                    {currentEx.rest_sec > 0 && <StatCard label="Отдых" value={`${currentEx.rest_sec}с`} />}
                  </div>
                  {currentEx.notes && (
                    <div className="bg-tg-bg rounded-xl p-3">
                      <p className="text-sm text-tg-hint leading-relaxed">{currentEx.notes}</p>
                    </div>
                  )}
                </>
              )
            }

            return (
              <div className="mt-4 space-y-3">
                {/* Warmup sets */}
                {rich.warmup_str && (
                  <div className="rounded-xl p-3" style={{ background: 'rgba(16,185,129,0.06)', border: '1px solid rgba(16,185,129,0.15)' }}>
                    <p className="text-[10px] font-bold uppercase tracking-wider mb-1.5" style={{ color: '#10b981' }}>
                      🔄 Разминочные подходы
                    </p>
                    <p className="text-sm font-mono">{rich.warmup_str}</p>
                  </div>
                )}

                {/* Top set */}
                {rich.is_main_lift && rich.top_set_weight && (
                  <div className="rounded-xl p-3" style={{ background: 'rgba(239,68,68,0.07)', border: '1px solid rgba(239,68,68,0.2)' }}>
                    <p className="text-[10px] font-bold uppercase tracking-wider mb-1.5" style={{ color: '#ef4444' }}>
                      🔥 Топ-сет
                    </p>
                    <div className="flex items-center gap-3">
                      <span className="text-2xl font-black">{rich.top_set_weight} кг</span>
                      <span className="text-lg font-bold text-tg-hint">×</span>
                      <span className="text-xl font-bold">{rich.top_set_sets} × {rich.top_set_reps}</span>
                      {rich.top_set_rpe && (
                        <span className="text-xs font-semibold px-2 py-0.5 rounded-full ml-auto" style={{ background: 'rgba(239,68,68,0.12)', color: '#ef4444' }}>
                          {rich.top_set_rpe}
                        </span>
                      )}
                    </div>
                    {rich.top_set_note && (
                      <p className="text-xs text-tg-hint mt-1.5 leading-relaxed">{rich.top_set_note}</p>
                    )}
                  </div>
                )}

                {/* Volume */}
                {rich.is_main_lift && rich.volume_sets && (
                  <div className="rounded-xl p-3" style={{ background: 'rgba(59,130,246,0.06)', border: '1px solid rgba(59,130,246,0.15)' }}>
                    <p className="text-[10px] font-bold uppercase tracking-wider mb-1.5" style={{ color: '#3b82f6' }}>
                      📊 Объём
                    </p>
                    <div className="flex items-center gap-3">
                      <span className="text-xl font-black">{rich.volume_weight} кг</span>
                      <span className="text-lg font-bold text-tg-hint">×</span>
                      <span className="text-lg font-bold">{rich.volume_sets} × {rich.volume_reps}</span>
                    </div>
                    {rich.volume_note && (
                      <p className="text-xs text-tg-hint mt-1.5 leading-relaxed">{rich.volume_note}</p>
                    )}
                  </div>
                )}

                {/* Simple exercise (accessory) */}
                {!rich.is_main_lift && (
                  <div className="flex gap-3">
                    {rich.weight_kg && <StatCard label="Вес" value={`${rich.weight_kg} кг`} />}
                    <StatCard label="Подходы" value={String(rich.sets || currentEx.sets)} />
                    <StatCard label="Повторения" value={rich.reps_min && rich.reps_max ? `${rich.reps_min}–${rich.reps_max}` : String(rich.reps || currentEx.reps)} />
                    {rich.rest_sec && <StatCard label="Отдых" value={`${rich.rest_sec}с`} />}
                  </div>
                )}

                {/* Coach note */}
                {(rich.coach_note) && (
                  <div className="rounded-xl p-3 bg-tg-bg">
                    <p className="text-sm text-tg-hint leading-relaxed">{rich.coach_note}</p>
                  </div>
                )}
              </div>
            )
          })()}
        </motion.div>
      </AnimatePresence>

      {/* ── Per-set tracker ───────────────────────────────────── */}
      <div className="glass-card rounded-2xl p-4 space-y-3">
        <p className="text-sm font-bold text-tg-hint uppercase tracking-wider">Запись подходов</p>
        {exSets.map((s, idx) => (
          <motion.div
            key={idx}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.05 }}
            className={`flex items-center gap-2 rounded-xl px-3 py-2.5 transition-all ${
              exCompleted[idx]
                ? 'opacity-60'
                : ''
            }`}
            style={{
              background: exCompleted[idx]
                ? 'rgba(16,185,129,0.08)'
                : 'var(--tg-theme-secondary-bg-color, rgba(0,0,0,0.04))',
            }}
          >
            {/* Set number */}
            <span className="text-xs font-bold text-tg-hint w-5 shrink-0">{idx + 1}</span>

            {/* Weight input */}
            <div className="flex-1">
              <p className="text-[10px] text-tg-hint mb-0.5">Вес (кг)</p>
              <input
                type="number"
                inputMode="decimal"
                placeholder={currentEx.weight_kg ? String(currentEx.weight_kg) : '0'}
                value={s.weight}
                onChange={e => updateSetField(currentEx.id, idx, 'weight', e.target.value)}
                disabled={exCompleted[idx]}
                className="w-full bg-transparent outline-none text-sm font-semibold"
              />
            </div>

            {/* Reps input */}
            <div className="flex-1">
              <p className="text-[10px] text-tg-hint mb-0.5">Повторения</p>
              <input
                type="number"
                inputMode="numeric"
                placeholder={currentEx.reps?.split('–')[0] || '—'}
                value={s.reps}
                onChange={e => updateSetField(currentEx.id, idx, 'reps', e.target.value)}
                disabled={exCompleted[idx]}
                className="w-full bg-transparent outline-none text-sm font-semibold"
              />
            </div>

            {/* Done button */}
            <motion.button
              whileTap={{ scale: 0.85 }}
              onClick={() => toggleSetDone(currentEx.id, idx)}
              className="w-8 h-8 rounded-xl flex items-center justify-center shrink-0 font-bold text-sm transition-all"
              style={{
                background: exCompleted[idx]
                  ? 'linear-gradient(135deg, #10b981, #059669)'
                  : 'rgba(0,0,0,0.06)',
                color: exCompleted[idx] ? '#fff' : 'var(--tg-theme-hint-color)',
              }}
            >
              {exCompleted[idx] ? '✓' : '○'}
            </motion.button>
          </motion.div>
        ))}
      </div>

      {/* Anatomy block */}
      {currentEx.muscle_groups && currentEx.muscle_groups.length > 0 && (
        <div>
          <button
            onClick={() => setShowAnatomy(v => !v)}
            className="w-full glass-card rounded-2xl p-3 flex items-center justify-between text-sm font-semibold"
          >
            <span>🫀 Анатомия мышц</span>
            <span className="text-tg-hint text-xs">{showAnatomy ? '▲' : '▼'}</span>
          </button>
          <AnimatePresence>
            {showAnatomy && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="glass-card rounded-2xl p-4 mt-1 overflow-hidden"
              >
                <MuscleBodySVG muscles={currentEx.muscle_groups} gender={gender} />
                <div className="flex gap-1.5 mt-3 flex-wrap">
                  {currentEx.muscle_groups.map(m => (
                    <span
                      key={m}
                      className="text-xs px-2 py-0.5 rounded-full font-bold"
                      style={{ background: 'rgba(249,115,22,0.15)', color: '#f97316' }}
                    >
                      {MUSCLE_LABELS_RU[m] || m}
                    </span>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}

      {/* Navigation */}
      <div className="flex gap-3">
        {currentExIdx > 0 && (
          <motion.button
            whileTap={{ scale: 0.97 }}
            onClick={() => { setCurrentExIdx(i => i - 1); setShowAnatomy(false) }}
            className="flex-1 glass-card py-3.5 rounded-xl font-semibold text-sm"
          >
            ← Назад
          </motion.button>
        )}
        {currentExIdx < workout.exercises.length - 1 ? (
          <motion.button
            whileTap={{ scale: 0.97 }}
            onClick={() => { setCurrentExIdx(i => i + 1); setShowAnatomy(false) }}
            className={`flex-1 py-3.5 rounded-xl font-bold text-sm ${allSetsLogged ? 'btn-premium' : 'glass-card'}`}
          >
            {allSetsLogged ? 'Следующее →' : 'Следующее →'}
          </motion.button>
        ) : (
          <motion.button
            whileTap={{ scale: 0.97 }}
            onClick={() => {
              const el = document.getElementById('rpe-section')
              el?.scrollIntoView({ behavior: 'smooth' })
            }}
            className="flex-1 py-3.5 rounded-xl font-bold text-sm text-white"
            style={{ background: 'linear-gradient(135deg, #10b981, #059669)' }}
          >
            Завершить
          </motion.button>
        )}
      </div>

      {/* RPE Section */}
      {currentExIdx === workout.exercises.length - 1 && (
        <motion.div
          id="rpe-section"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-card rounded-2xl p-5"
        >
          <h3 className="font-bold mb-3">Насколько было тяжело?</h3>
          <div className="grid grid-cols-5 gap-2 mb-4">
            {[1,2,3,4,5,6,7,8,9,10].map(n => (
              <motion.button
                key={n}
                whileTap={{ scale: 0.9 }}
                onClick={() => setRpe(n)}
                className={`py-2.5 rounded-xl font-bold text-sm transition-all ${
                  rpe === n
                    ? 'text-white shadow-lg'
                    : 'bg-tg-bg text-tg-hint'
                }`}
                style={rpe === n ? {
                  background: n <= 3 ? '#10b981' : n <= 6 ? 'var(--tg-theme-button-color)' : n <= 8 ? '#f59e0b' : '#ef4444',
                } : {}}
              >
                {n}
              </motion.button>
            ))}
          </div>
          <motion.button
            whileTap={{ scale: 0.97 }}
            onClick={handleComplete}
            disabled={!rpe || completing}
            className="w-full btn-premium py-3.5 rounded-xl font-bold disabled:opacity-40"
          >
            {completing ? 'Сохраняем...' : 'Завершить тренировку'}
          </motion.button>
        </motion.div>
      )}
    </div>
  )
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="stat-card flex-1 flex flex-col items-center rounded-xl px-3 py-3">
      <span className="text-lg font-extrabold">{value}</span>
      <span className="text-[11px] text-tg-hint font-medium mt-0.5">{label}</span>
    </div>
  )
}
