import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  LineChart, Line, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid
} from 'recharts'
import { progressAPI, reportsAPI } from '../api/client'

interface ProgressEntry {
  id: string
  recorded_date: string
  weight_kg: number | null
  chest_cm: number | null
  waist_cm: number | null
  hips_cm: number | null
  bicep_cm: number | null
  forearm_cm: number | null
  thigh_cm: number | null
  calf_cm: number | null
  body_fat_pct: number | null
}

interface Streak {
  current: number
  max: number
}

interface WeeklyReport {
  week_start: string
  week_end: string
  workouts: { completed: number; scheduled: number; completion_rate: number; avg_rpe: number | null }
  weight: { start: number | null; end: number | null; change: number | null }
  nutrition: { avg_calories: number | null; avg_protein: number | null; days_logged: number }
  streak: { current: number; max: number }
  ai_summary: string | null
}

type Tab = 'progress' | 'report'

export default function ProgressPage() {
  const [tab, setTab] = useState<Tab>('progress')
  const [report, setReport] = useState<WeeklyReport | null>(null)
  const [reportLoading, setReportLoading] = useState(false)
  const [entries, setEntries] = useState<ProgressEntry[]>([])
  const [streak, setStreak] = useState<Streak>({ current: 0, max: 0 })
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({
    weight_kg: '', body_fat_pct: '', chest_cm: '', waist_cm: '', hips_cm: '',
    bicep_cm: '', forearm_cm: '', thigh_cm: '', calf_cm: '',
  })
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    load()
  }, [])

  const load = async () => {
    try {
      const res = await progressAPI.getProgress()
      setEntries(res.data.entries || [])
      setStreak(res.data.streak || { current: 0, max: 0 })
    } catch {
      //
    } finally {
      setLoading(false)
    }
  }

  const saveEntry = async () => {
    setSaving(true)
    try {
      const data: Record<string, unknown> = {
        recorded_date: new Date().toISOString().split('T')[0],
      }
      if (form.weight_kg) data.weight_kg = parseFloat(form.weight_kg)
      if (form.body_fat_pct) data.body_fat_pct = parseFloat(form.body_fat_pct)
      if (form.chest_cm) data.chest_cm = parseInt(form.chest_cm)
      if (form.waist_cm) data.waist_cm = parseInt(form.waist_cm)
      if (form.hips_cm) data.hips_cm = parseInt(form.hips_cm)
      if (form.bicep_cm) data.bicep_cm = parseInt(form.bicep_cm)
      if (form.forearm_cm) data.forearm_cm = parseInt(form.forearm_cm)
      if (form.thigh_cm) data.thigh_cm = parseInt(form.thigh_cm)
      if (form.calf_cm) data.calf_cm = parseInt(form.calf_cm)

      await progressAPI.addEntry(data)
      setShowForm(false)
      setForm({
        weight_kg: '', body_fat_pct: '', chest_cm: '', waist_cm: '', hips_cm: '',
        bicep_cm: '', forearm_cm: '', thigh_cm: '', calf_cm: '',
      })
      await load()
    } catch {
      //
    } finally {
      setSaving(false)
    }
  }

  const chartData = [...entries]
    .reverse()
    .filter(e => e.weight_kg)
    .map(e => ({
      date: new Date(e.recorded_date).toLocaleDateString('ru', { day: 'numeric', month: 'short' }),
      weight: e.weight_kg,
    }))

  const loadReport = async () => {
    if (report) return
    setReportLoading(true)
    try {
      const res = await reportsAPI.getWeekly()
      setReport(res.data)
    } catch { /* ignore */ }
    finally { setReportLoading(false) }
  }

  const handleTabChange = (t: Tab) => {
    setTab(t)
    if (t === 'report') loadReport()
  }

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="w-8 h-8 border-4 border-tg-button border-t-transparent rounded-full animate-spin" /></div>
  }

  return (
    <div className="min-h-screen bg-tg-bg pb-24">
      <div className="px-5 pt-6 pb-2 flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Прогресс</h1>
          <p className="text-sm text-tg-hint mt-0.5">Отслеживай свои результаты</p>
        </div>
        {tab === 'progress' && (
          <motion.button
            whileTap={{ scale: 0.95 }}
            onClick={() => setShowForm(!showForm)}
            className="btn-premium px-4 py-2.5 rounded-xl text-sm font-bold"
          >
            + Добавить
          </motion.button>
        )}
      </div>

      {/* Tabs */}
      <div className="px-5 mt-2 mb-1">
        <div className="flex gap-2 bg-tg-secondary-bg p-1 rounded-xl">
          {([['progress', '📊 Замеры'], ['report', '📋 Отчёт недели']] as const).map(([t, label]) => (
            <button
              key={t}
              onClick={() => handleTabChange(t)}
              className={`flex-1 py-2 rounded-lg text-sm font-semibold transition-all ${
                tab === t ? 'bg-tg-bg shadow text-tg-text' : 'text-tg-hint'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Weekly Report Tab */}
      {tab === 'report' && (
        <div className="px-5 mt-3 space-y-3">
          {reportLoading ? (
            <div className="flex flex-col items-center justify-center py-12 gap-3">
              <div className="w-8 h-8 border-4 border-tg-button border-t-transparent rounded-full animate-spin" />
              <p className="text-sm text-tg-hint">AI анализирует твою неделю...</p>
            </div>
          ) : report ? (
            <>
              <div className="text-xs text-tg-hint px-1">
                {new Date(report.week_start).toLocaleDateString('ru', { day: 'numeric', month: 'long' })} — {new Date(report.week_end).toLocaleDateString('ru', { day: 'numeric', month: 'long' })}
              </div>

              {/* Workouts card */}
              <div className="glass-card rounded-2xl p-4">
                <p className="text-xs font-bold text-tg-hint uppercase tracking-wider mb-3">Тренировки</p>
                <div className="flex gap-3">
                  <div className="flex-1 text-center">
                    <p className="text-3xl font-extrabold">{report.workouts.completed}</p>
                    <p className="text-xs text-tg-hint mt-0.5">выполнено</p>
                  </div>
                  <div className="flex-1 text-center">
                    <p className="text-3xl font-extrabold">{report.workouts.scheduled}</p>
                    <p className="text-xs text-tg-hint mt-0.5">запланировано</p>
                  </div>
                  <div className="flex-1 text-center">
                    <p className="text-3xl font-extrabold">{report.workouts.completion_rate}%</p>
                    <p className="text-xs text-tg-hint mt-0.5">выполнение</p>
                  </div>
                </div>
                {report.workouts.avg_rpe && (
                  <div className="mt-3 pt-3 border-t border-tg-secondary-bg flex items-center justify-between">
                    <span className="text-sm text-tg-hint">Средний RPE</span>
                    <span className="font-bold">{report.workouts.avg_rpe} / 10</span>
                  </div>
                )}
              </div>

              {/* Weight + Nutrition */}
              <div className="flex gap-3">
                {(report.weight.start || report.weight.end) && (
                  <div className="flex-1 glass-card rounded-2xl p-4">
                    <p className="text-xs font-bold text-tg-hint uppercase tracking-wider mb-2">Вес</p>
                    {report.weight.change !== null && (
                      <p className={`text-2xl font-extrabold ${report.weight.change <= 0 ? 'text-green-500' : 'text-orange-500'}`}>
                        {report.weight.change > 0 ? '+' : ''}{report.weight.change} кг
                      </p>
                    )}
                    <p className="text-xs text-tg-hint mt-1">
                      {report.weight.start} → {report.weight.end} кг
                    </p>
                  </div>
                )}
                {report.nutrition.avg_calories && (
                  <div className="flex-1 glass-card rounded-2xl p-4">
                    <p className="text-xs font-bold text-tg-hint uppercase tracking-wider mb-2">Питание</p>
                    <p className="text-2xl font-extrabold">{report.nutrition.avg_calories}</p>
                    <p className="text-xs text-tg-hint mt-1">ккал/день · {report.nutrition.days_logged} дн.</p>
                  </div>
                )}
              </div>

              {/* Streak */}
              <div className="flex gap-3">
                <div className="flex-1 stat-card rounded-2xl p-4 text-center">
                  <p className="text-3xl font-extrabold">🔥 {report.streak.current}</p>
                  <p className="text-xs font-medium text-tg-hint mt-1">Текущий стрик</p>
                </div>
                <div className="flex-1 stat-card rounded-2xl p-4 text-center">
                  <p className="text-3xl font-extrabold">⭐ {report.streak.max}</p>
                  <p className="text-xs font-medium text-tg-hint mt-1">Рекорд</p>
                </div>
              </div>

              {/* AI Summary */}
              {report.ai_summary && (
                <div className="glass-card rounded-2xl p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-lg">🤖</span>
                    <p className="text-xs font-bold text-tg-hint uppercase tracking-wider">Тренер Константин говорит:</p>
                  </div>
                  <p className="text-sm leading-relaxed">{report.ai_summary}</p>
                </div>
              )}

              <motion.button
                whileTap={{ scale: 0.97 }}
                onClick={() => { setReport(null); loadReport() }}
                className="w-full glass-card py-3 rounded-xl text-sm font-semibold text-tg-hint"
              >
                Обновить отчёт
              </motion.button>
            </>
          ) : (
            <div className="text-center py-12">
              <p className="text-4xl mb-3">📋</p>
              <p className="text-tg-hint text-sm">Нет данных для отчёта</p>
              <p className="text-tg-hint text-xs mt-1">Заверши несколько тренировок</p>
            </div>
          )}
        </div>
      )}

      {tab === 'progress' && (<>

      {/* Streak */}
      <div className="px-5 mt-3">
        <div className="flex gap-3">
          <div className="flex-1 stat-card rounded-2xl p-4 text-center">
            <p className="text-3xl font-extrabold">🔥 {streak.current}</p>
            <p className="text-xs font-medium text-tg-hint mt-1">Текущий стрик</p>
          </div>
          <div className="flex-1 stat-card rounded-2xl p-4 text-center">
            <p className="text-3xl font-extrabold">⭐ {streak.max}</p>
            <p className="text-xs font-medium text-tg-hint mt-1">Рекорд</p>
          </div>
        </div>
      </div>

      {/* Add form */}
      <AnimatePresence>
        {showForm && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="px-5 mt-4"
          >
            <div className="glass-card rounded-2xl p-4 space-y-3">
              <h3 className="font-bold">Сегодняшние данные</h3>
              <div className="grid grid-cols-2 gap-3">
                {[
                  { key: 'weight_kg', label: 'Вес (кг)', placeholder: '70.5' },
                  { key: 'body_fat_pct', label: '% жира', placeholder: '15' },
                  { key: 'chest_cm', label: 'Грудь (см)', placeholder: '100' },
                  { key: 'waist_cm', label: 'Талия (см)', placeholder: '80' },
                  { key: 'hips_cm', label: 'Бёдра (см)', placeholder: '95' },
                  { key: 'bicep_cm', label: 'Бицепс (см)', placeholder: '35' },
                  { key: 'forearm_cm', label: 'Предплечье (см)', placeholder: '28' },
                  { key: 'thigh_cm', label: 'Бедро (см)', placeholder: '55' },
                  { key: 'calf_cm', label: 'Голень (см)', placeholder: '37' },
                ].map(field => (
                  <div key={field.key}>
                    <label className="text-[11px] font-semibold text-tg-hint uppercase tracking-wide">{field.label}</label>
                    <input
                      type="number"
                      step="0.1"
                      value={form[field.key as keyof typeof form]}
                      onChange={e => setForm(prev => ({ ...prev, [field.key]: e.target.value }))}
                      placeholder={field.placeholder}
                      className="w-full bg-tg-bg rounded-xl px-3 py-2.5 mt-1 outline-none text-sm font-medium"
                    />
                  </div>
                ))}
              </div>
              <motion.button
                whileTap={{ scale: 0.97 }}
                onClick={saveEntry}
                disabled={saving}
                className="w-full btn-premium py-3.5 rounded-xl font-bold disabled:opacity-50"
              >
                {saving ? 'Сохраняем...' : 'Сохранить'}
              </motion.button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Weight Chart */}
      {chartData.length > 1 && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mx-5 mt-4 glass-card rounded-2xl p-4"
        >
          <h3 className="font-bold mb-3">Динамика веса</h3>
          <ResponsiveContainer width="100%" height={160}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.05)" />
              <XAxis dataKey="date" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} domain={['auto', 'auto']} />
              <Tooltip />
              <Line
                type="monotone"
                dataKey="weight"
                stroke="var(--tg-theme-button-color, #2563eb)"
                strokeWidth={2.5}
                dot={{ r: 3, fill: 'var(--tg-theme-button-color, #2563eb)' }}
                activeDot={{ r: 5 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </motion.div>
      )}

      {/* History */}
      <div className="px-5 mt-4 space-y-2">
        <h3 className="text-xs font-bold text-tg-hint uppercase tracking-wider px-1">История</h3>
        {entries.length === 0 ? (
          <p className="text-tg-hint text-center py-8 text-sm">Пока нет записей</p>
        ) : (
          entries.map((entry, i) => (
            <motion.div
              key={entry.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.03 }}
              className="glass-card rounded-2xl p-4"
            >
              <p className="font-bold text-sm mb-1.5">{new Date(entry.recorded_date).toLocaleDateString('ru')}</p>
              <div className="grid grid-cols-2 gap-x-4 gap-y-0.5 text-sm text-tg-hint">
                {entry.weight_kg && <p>Вес: <span className="font-semibold text-tg-text">{entry.weight_kg} кг</span></p>}
                {entry.body_fat_pct && <p>Жир: <span className="font-semibold text-tg-text">{entry.body_fat_pct}%</span></p>}
                {entry.chest_cm && <p>Грудь: <span className="font-semibold text-tg-text">{entry.chest_cm} см</span></p>}
                {entry.waist_cm && <p>Талия: <span className="font-semibold text-tg-text">{entry.waist_cm} см</span></p>}
                {entry.hips_cm && <p>Бёдра: <span className="font-semibold text-tg-text">{entry.hips_cm} см</span></p>}
                {entry.bicep_cm && <p>Бицепс: <span className="font-semibold text-tg-text">{entry.bicep_cm} см</span></p>}
                {entry.forearm_cm && <p>Предплечье: <span className="font-semibold text-tg-text">{entry.forearm_cm} см</span></p>}
                {entry.thigh_cm && <p>Бедро: <span className="font-semibold text-tg-text">{entry.thigh_cm} см</span></p>}
                {entry.calf_cm && <p>Голень: <span className="font-semibold text-tg-text">{entry.calf_cm} см</span></p>}
              </div>
            </motion.div>
          ))
        )}
      </div>
      </>)}
    </div>
  )
}
