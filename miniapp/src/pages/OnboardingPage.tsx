import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { onboardingAPI } from '../api/client'
import { useAuthStore } from '../store/authStore'

interface StepOption {
  value: string | number
  label: string
  sub?: string
  emoji?: string
}

interface StepQuestion {
  question: string
  type?: string
  options?: StepOption[]
  min?: number
  max?: number
}

interface OnboardingStatus {
  step: string
  is_complete: boolean
  question: StepQuestion | null
  answers: Record<string, unknown>
  progress_pct: number
}

const STEP_ICONS: Record<string, string> = {
  consent: '📋',
  name: '👋',
  goal: '🎯',
  gender: '👤',
  sport_background: '🏅',
  age: '🎂',
  height: '📏',
  weight: '⚖️',
  fitness_level: '📊',
  equipment: '🏋️',
  injuries: '🩺',
  medical_notes: '🏥',
  available_days: '📅',
  session_minutes: '⏱',
  motivation_type: '🔥',
  training_style: '🎨',
}

const STEP_SUBTITLES: Record<string, string> = {
  name: 'Твой личный AI-тренер Константин будет обращаться к тебе по имени',
  goal: 'Мы создадим программу именно под тебя',
  gender: 'Это влияет на подбор упражнений и нагрузки',
  sport_background: 'Честно — это только улучшит твой план',
  age: 'Учитываем для правильного восстановления',
  height: 'Для расчёта идеальных параметров',
  weight: 'Отправная точка твоей трансформации',
  fitness_level: 'Будь честным — план подстроится под тебя',
  equipment: 'Подберём лучшие упражнения для твоих условий',
  injuries: 'Обойдём проблемные зоны в программе',
  medical_notes: 'Учтём все особенности для безопасных тренировок',
  available_days: 'Стабильность важнее частоты',
  session_minutes: 'Каждая минута будет использована на 100%',
  motivation_type: 'Константин подстроит стиль общения под твою мотивацию',
  training_style: 'Программа адаптируется под твой подход к тренировкам',
}

const TOTAL_STEPS = 16

interface ConsentScreenProps {
  onAccept: () => void
  loading: boolean
}

function ConsentScreen({ onAccept, loading }: ConsentScreenProps) {
  const [checked, setChecked] = useState({ medical: false, data: false, age: false })
  const allChecked = checked.medical && checked.data && checked.age

  const toggle = (key: keyof typeof checked) =>
    setChecked(prev => ({ ...prev, [key]: !prev[key] }))

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-col min-h-screen bg-tg-bg px-5 py-6"
    >
      <div className="mb-6">
        <div className="text-5xl mb-4">📋</div>
        <h1 className="text-2xl font-bold leading-tight mb-2">Условия использования</h1>
        <p className="text-sm text-tg-hint leading-relaxed">
          Для продолжения необходимо ознакомиться и принять условия
        </p>
      </div>

      {/* Medical disclaimer */}
      <div className="rounded-2xl p-4 mb-4 border border-red-400/30" style={{ background: 'rgba(239, 68, 68, 0.08)' }}>
        <div className="flex items-start gap-2 mb-2">
          <span className="text-lg">⚠️</span>
          <span className="font-bold text-sm" style={{ color: '#f87171' }}>Медицинский дисклеймер</span>
        </div>
        <p className="text-xs text-tg-hint leading-relaxed">
          Приложение предоставляет общие рекомендации и <strong>не является медицинской консультацией</strong>.
          Перед началом тренировок проконсультируйтесь с врачом, особенно при наличии хронических заболеваний или травм.
          Разработчик не несёт ответственности за травмы, возникшие при выполнении упражнений.
        </p>
      </div>

      {/* Privacy */}
      <div className="rounded-2xl p-4 mb-6 border border-blue-400/30" style={{ background: 'rgba(37, 99, 235, 0.08)' }}>
        <div className="flex items-start gap-2 mb-2">
          <span className="text-lg">🔒</span>
          <span className="font-bold text-sm" style={{ color: '#60a5fa' }}>Обработка данных (152-ФЗ)</span>
        </div>
        <p className="text-xs text-tg-hint leading-relaxed">
          Мы собираем данные о физических параметрах и активности для формирования персонального плана.
          Данные хранятся в защищённом виде, не передаются третьим лицам и используются только для работы сервиса.
        </p>
      </div>

      {/* Checkboxes */}
      <div className="space-y-3 mb-6">
        {([
          { key: 'medical' as const, text: 'Ознакомлен(а) с медицинским дисклеймером и принимаю его' },
          { key: 'data' as const, text: 'Согласен(на) на обработку персональных данных согласно 152-ФЗ' },
          { key: 'age' as const, text: 'Мне 18+ лет и я беру ответственность за своё здоровье' },
        ] as const).map(({ key, text }) => (
          <button
            key={key}
            onClick={() => toggle(key)}
            className="w-full flex items-center gap-3 p-4 rounded-2xl text-left transition-all"
            style={{ background: checked[key] ? 'rgba(37, 99, 235, 0.12)' : 'var(--tg-theme-secondary-bg-color)' }}
          >
            <div className={`w-6 h-6 rounded-lg border-2 flex items-center justify-center flex-shrink-0 transition-all ${
              checked[key] ? 'bg-blue-500 border-blue-500' : 'border-tg-hint'
            }`}>
              {checked[key] && <span className="text-white text-xs font-bold">✓</span>}
            </div>
            <span className="text-sm leading-snug">{text}</span>
          </button>
        ))}
      </div>

      <p className="text-xs text-tg-hint text-center mb-4">
        Дата и время принятия условий фиксируются для вашей защиты
      </p>

      <motion.button
        whileTap={{ scale: 0.97 }}
        onClick={onAccept}
        disabled={!allChecked || loading}
        className="w-full py-4 rounded-2xl font-bold text-base disabled:opacity-40 transition-all"
        style={{ background: 'var(--tg-theme-button-color, #2481cc)', color: 'var(--tg-theme-button-text-color, #fff)' }}
      >
        {loading ? '⏳ Сохраняем...' : 'Принять и начать →'}
      </motion.button>
    </motion.div>
  )
}

export default function OnboardingPage() {
  const { setAuth, token } = useAuthStore()
  const [status, setStatus] = useState<OnboardingStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [numValue, setNumValue] = useState('')
  const [selectedMulti, setSelectedMulti] = useState<string[]>([])
  const [done, setDone] = useState(false)
  const [stepIndex, setStepIndex] = useState(0)
  const [customGoal, setCustomGoal] = useState('')
  const [showCustomInput, setShowCustomInput] = useState(false)
  const [textValue, setTextValue] = useState('')

  useEffect(() => {
    loadStatus()
  }, [])

  const loadStatus = async () => {
    try {
      const res = await onboardingAPI.getStatus()
      setStatus(res.data)
      const steps = Object.keys(STEP_ICONS)
      const idx = steps.indexOf(res.data.step)
      setStepIndex(idx >= 0 ? idx : 0)
    } catch {
      // handle
    } finally {
      setLoading(false)
    }
  }

  const isLastStep = status?.step === 'training_style'

  const submitStep = async (answer: unknown) => {
    if (!status) return
    setSubmitting(true)
    try {
      const res = await onboardingAPI.submitStep(status.step, answer)
      if (res.data.status === 'complete') {
        setDone(true)
        if (token) setAuth(token, false, true)
      } else {
        await loadStatus()
        setNumValue('')
        setTextValue('')
        setSelectedMulti([])
        setShowCustomInput(false)
        setCustomGoal('')
      }
    } catch (err) {
      console.error(err)
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="w-10 h-10 border-4 border-tg-button border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (submitting && isLastStep) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="flex flex-col items-center justify-center h-screen p-8 text-center"
      >
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
          className="text-6xl mb-6"
        >
          ⚙️
        </motion.div>
        <h2 className="text-2xl font-bold mb-3">AI создаёт твой план</h2>
        <p className="text-tg-hint text-sm leading-relaxed mb-6">
          Анализируем твои данные<br />и составляем персональную программу...
        </p>
        <div className="flex gap-1.5">
          {[0, 1, 2].map(i => (
            <motion.div
              key={i}
              className="w-2.5 h-2.5 rounded-full bg-tg-button"
              animate={{ scale: [1, 1.5, 1] }}
              transition={{ duration: 0.8, repeat: Infinity, delay: i * 0.2 }}
            />
          ))}
        </div>
      </motion.div>
    )
  }

  if (done) {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.85 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ type: 'spring', duration: 0.6 }}
        className="flex flex-col items-center justify-center h-screen p-8 text-center"
      >
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ delay: 0.2, type: 'spring', stiffness: 200 }}
          className="text-8xl mb-6"
        >
          🚀
        </motion.div>
        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="text-3xl font-bold mb-3"
        >
          Твой план готов!
        </motion.h1>
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="text-tg-hint text-base mb-8 leading-relaxed"
        >
          AI-тренер Константин уже составил<br />персональную программу для тебя
        </motion.p>
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.7 }}
          className="w-8 h-8 border-4 border-tg-button border-t-transparent rounded-full animate-spin"
        />
      </motion.div>
    )
  }

  // Consent step — special full-screen UI bypasses regular question renderer
  if (status?.step === 'consent' && !done) {
    return <ConsentScreen onAccept={() => submitStep(true)} loading={submitting} />
  }

  if (!status?.question) return null

  const { question, step } = status
  const icon = STEP_ICONS[step] || '✨'
  const subtitle = STEP_SUBTITLES[step] || ''

  return (
    <div className="flex flex-col min-h-screen bg-tg-bg">
      {/* Header with progress */}
      <div className="px-5 pt-6 pb-4">
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm font-medium text-tg-hint">
            {stepIndex + 1} / {TOTAL_STEPS}
          </span>
          <span className="text-sm font-semibold text-tg-button">
            {Math.round(((stepIndex + 1) / TOTAL_STEPS) * 100)}%
          </span>
        </div>
        <div className="h-2 bg-tg-secondary-bg rounded-full overflow-hidden">
          <motion.div
            className="h-full rounded-full"
            style={{ background: 'var(--tg-theme-button-color, #2481cc)' }}
            animate={{ width: `${((stepIndex + 1) / TOTAL_STEPS) * 100}%` }}
            transition={{ duration: 0.5, ease: 'easeOut' }}
          />
        </div>
      </div>

      <AnimatePresence mode="wait">
        <motion.div
          key={step}
          initial={{ opacity: 0, x: 50 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -50 }}
          transition={{ duration: 0.25 }}
          className="flex-1 px-5 pb-8"
        >
          {/* Question block */}
          <div className="mb-8 mt-4">
            <motion.div
              initial={{ scale: 0.5, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ delay: 0.1 }}
              className="text-5xl mb-4"
            >
              {icon}
            </motion.div>
            <h2 className="text-2xl font-bold leading-tight mb-2">
              {question.question}
            </h2>
            {subtitle && (
              <p className="text-sm text-tg-hint leading-relaxed">{subtitle}</p>
            )}
          </div>

          {/* Single select */}
          {question.options && question.type !== 'multiselect' && !showCustomInput && (
            <div className="space-y-3">
              {question.options.map((opt, i) => (
                <motion.button
                  key={String(opt.value)}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.06 }}
                  whileTap={{ scale: 0.97 }}
                  onClick={() => {
                    if (submitting) return
                    if (opt.value === 'custom') {
                      setShowCustomInput(true)
                    } else {
                      submitStep(opt.value)
                    }
                  }}
                  disabled={submitting}
                  className="w-full bg-tg-secondary-bg p-4 rounded-2xl text-left transition-all active:scale-95 disabled:opacity-50 flex items-center gap-4"
                >
                  {opt.emoji && (
                    <span className="text-2xl flex-shrink-0">{opt.emoji}</span>
                  )}
                  <div className="flex-1 min-w-0">
                    <div className="font-semibold text-base">{opt.label}</div>
                    {opt.sub && (
                      <div className="text-xs text-tg-hint mt-0.5">{opt.sub}</div>
                    )}
                  </div>
                  <span className="text-tg-hint text-lg flex-shrink-0">›</span>
                </motion.button>
              ))}
            </div>
          )}

          {/* Custom goal input */}
          {showCustomInput && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="space-y-4"
            >
              <div className="bg-tg-secondary-bg rounded-2xl p-2">
                <textarea
                  value={customGoal}
                  onChange={e => setCustomGoal(e.target.value)}
                  placeholder="Например: хочу пробежать марафон, подтянуться 20 раз, влезть в старые джинсы..."
                  className="w-full bg-transparent text-base p-3 outline-none resize-none min-h-[120px] leading-relaxed"
                  autoFocus
                />
              </div>
              <div className="flex gap-3">
                <button
                  onClick={() => { setShowCustomInput(false); setCustomGoal('') }}
                  className="flex-1 py-4 rounded-2xl font-semibold bg-tg-secondary-bg text-tg-text"
                >
                  ← Назад
                </button>
                <motion.button
                  whileTap={{ scale: 0.97 }}
                  onClick={() => submitStep(customGoal.trim())}
                  disabled={!customGoal.trim() || submitting}
                  className="flex-2 flex-1 py-4 rounded-2xl font-bold disabled:opacity-40"
                  style={{ background: 'var(--tg-theme-button-color, #2481cc)', color: 'var(--tg-theme-button-text-color, #fff)' }}
                >
                  {submitting ? '⏳...' : 'Продолжить →'}
                </motion.button>
              </div>
            </motion.div>
          )}

          {/* Multi select */}
          {question.options && question.type === 'multiselect' && (
            <div className="space-y-3">
              {question.options.map((opt, i) => {
                const val = String(opt.value)
                const selected = selectedMulti.includes(val)
                return (
                  <motion.button
                    key={val}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.06 }}
                    whileTap={{ scale: 0.97 }}
                    onClick={() => {
                      if (val === 'none') {
                        setSelectedMulti(['none'])
                      } else {
                        setSelectedMulti(prev =>
                          prev.includes(val)
                            ? prev.filter(v => v !== val)
                            : [...prev.filter(v => v !== 'none'), val]
                        )
                      }
                    }}
                    className={`w-full p-4 rounded-2xl text-left transition-all flex items-center gap-4 ${
                      selected
                        ? 'bg-tg-button text-tg-button-text'
                        : 'bg-tg-secondary-bg'
                    }`}
                  >
                    {opt.emoji && (
                      <span className="text-2xl flex-shrink-0">{opt.emoji}</span>
                    )}
                    <div className="flex-1">
                      <div className="font-semibold text-base">{opt.label}</div>
                    </div>
                    <div className={`w-6 h-6 rounded-full border-2 flex items-center justify-center flex-shrink-0 ${
                      selected ? 'border-tg-button-text bg-tg-button-text/20' : 'border-tg-hint'
                    }`}>
                      {selected && <div className="w-3 h-3 rounded-full bg-tg-button-text" />}
                    </div>
                  </motion.button>
                )
              })}
              <motion.button
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
                onClick={() => submitStep(selectedMulti)}
                disabled={selectedMulti.length === 0 || submitting}
                className="w-full py-4 rounded-2xl font-bold text-base mt-4 disabled:opacity-40 transition-all"
                style={{ background: 'var(--tg-theme-button-color, #2481cc)', color: 'var(--tg-theme-button-text-color, #fff)' }}
              >
                {submitting ? '⏳ Загрузка...' : 'Продолжить →'}
              </motion.button>
            </div>
          )}

          {/* Text input */}
          {question.type === 'text' && (
            <div className="space-y-4">
              <div className="bg-tg-secondary-bg rounded-2xl p-2">
                {step === 'name' ? (
                  <input
                    type="text"
                    value={textValue}
                    onChange={e => setTextValue(e.target.value)}
                    placeholder={(question as any).placeholder || 'Напиши здесь...'}
                    className="w-full bg-transparent text-2xl font-bold text-center p-4 outline-none"
                    autoFocus
                    onKeyDown={e => { if (e.key === 'Enter' && textValue.trim()) submitStep(textValue.trim()) }}
                  />
                ) : (
                  <textarea
                    value={textValue}
                    onChange={e => setTextValue(e.target.value)}
                    placeholder={(question as any).placeholder || 'Напиши здесь...'}
                    className="w-full bg-transparent text-base p-3 outline-none resize-none min-h-[120px] leading-relaxed"
                    autoFocus
                  />
                )}
              </div>
              <div className="flex gap-3">
                <motion.button
                  whileTap={{ scale: 0.97 }}
                  onClick={() => submitStep(textValue.trim() || '')}
                  disabled={submitting || (step === 'name' && !textValue.trim())}
                  className="flex-1 py-4 rounded-2xl font-bold text-base disabled:opacity-40 transition-all"
                  style={{ background: 'var(--tg-theme-button-color, #2481cc)', color: 'var(--tg-theme-button-text-color, #fff)' }}
                >
                  {submitting ? '⏳...' : (step !== 'name' && !textValue.trim()) ? 'Пропустить →' : 'Продолжить →'}
                </motion.button>
              </div>
            </div>
          )}

          {/* Number input */}
          {question.type === 'number' && (
            <div className="space-y-4">
              <div className="bg-tg-secondary-bg rounded-2xl p-2">
                <input
                  type="number"
                  value={numValue}
                  onChange={e => setNumValue(e.target.value)}
                  className="w-full bg-transparent text-4xl font-bold text-center p-4 outline-none"
                  placeholder="—"
                  autoFocus
                />
              </div>
              <motion.button
                whileTap={{ scale: 0.97 }}
                onClick={() => submitStep(Number(numValue))}
                disabled={!numValue || submitting}
                className="w-full py-4 rounded-2xl font-bold text-base disabled:opacity-40 transition-all"
                style={{ background: 'var(--tg-theme-button-color, #2481cc)', color: 'var(--tg-theme-button-text-color, #fff)' }}
              >
                {submitting ? '⏳ Создаём план...' : 'Продолжить →'}
              </motion.button>
            </div>
          )}
        </motion.div>
      </AnimatePresence>
    </div>
  )
}
