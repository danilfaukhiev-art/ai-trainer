import { useEffect, useRef, useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { profileAPI, nutritionAPI, foodAPI } from '../api/client'

interface Profile {
  weight_kg: number | null
  height_cm: number | null
  age: number | null
  gender: string | null
  fitness_level: string | null
  goal: string | null
}

interface Macros {
  calories: number
  protein: number
  fats: number
  carbs: number
}

interface MealItem {
  id: string
  name: string
  calories: number | null
  protein_g: number | null
  fats_g: number | null
  carbs_g: number | null
  portion_g: number | null
}

interface DailyData {
  meals: Record<string, MealItem[]>
  totals: { calories: number; protein_g: number; fats_g: number; carbs_g: number }
  water_ml: number
}

function calcMacros(profile: Profile): Macros | null {
  if (!profile.weight_kg || !profile.height_cm || !profile.age) return null
  const w = profile.weight_kg
  const h = profile.height_cm
  const a = profile.age
  const bmr = profile.gender === 'female'
    ? 10 * w + 6.25 * h - 5 * a - 161
    : 10 * w + 6.25 * h - 5 * a + 5
  const activityMap: Record<string, number> = {
    beginner: 1.375, intermediate: 1.55, advanced: 1.725,
  }
  const tdee = bmr * (activityMap[profile.fitness_level || 'beginner'] || 1.375)
  let calories = Math.round(tdee)
  if (profile.goal === 'fat_loss') calories = Math.round(tdee * 0.85)
  if (profile.goal === 'muscle_gain') calories = Math.round(tdee * 1.1)
  const protein = Math.round(w * (profile.goal === 'muscle_gain' ? 2.2 : 1.8))
  const fats = Math.round((calories * 0.25) / 9)
  const carbs = Math.round((calories - protein * 4 - fats * 9) / 4)
  return { calories, protein, fats, carbs }
}

const MEAL_TYPES = [
  { key: 'breakfast', label: 'Завтрак', emoji: '🌅' },
  { key: 'lunch', label: 'Обед', emoji: '☀️' },
  { key: 'dinner', label: 'Ужин', emoji: '🌙' },
  { key: 'snack', label: 'Перекус', emoji: '🍎' },
]

const WATER_AMOUNTS = [200, 250, 330, 500]

const GOAL_LABELS: Record<string, string> = {
  fat_loss: 'Похудение', muscle_gain: 'Набор массы',
  health: 'Здоровье', endurance: 'Выносливость',
}

interface FoodResult {
  name: string
  calories: number
  protein_g: number
  fats_g: number
  carbs_g: number
}

export default function NutritionPage() {
  const [profile, setProfile] = useState<Profile | null>(null)
  const [daily, setDaily] = useState<DailyData | null>(null)
  const [loading, setLoading] = useState(true)
  const [addingMealType, setAddingMealType] = useState<string | null>(null)
  const [mealForm, setMealForm] = useState({ name: '', calories: '', protein_g: '', fats_g: '', carbs_g: '', portion_g: '' })
  const [savingMeal, setSavingMeal] = useState(false)
  const [savingWater, setSavingWater] = useState(false)
  const [photoAnalyzing, setPhotoAnalyzing] = useState(false)
  const [photoPreFilled, setPhotoPreFilled] = useState(false)
  const photoInputRefs = useRef<Record<string, HTMLInputElement | null>>({})
  // Food search
  const [foodQuery, setFoodQuery] = useState('')
  const [foodResults, setFoodResults] = useState<FoodResult[]>([])
  const [foodSearching, setFoodSearching] = useState(false)
  const searchTimeout = useRef<ReturnType<typeof setTimeout> | null>(null)

  const today = new Date().toISOString().split('T')[0]

  useEffect(() => {
    loadAll()
  }, [])

  const loadAll = async () => {
    try {
      const [profileRes, nutritionRes] = await Promise.all([
        profileAPI.getProfile(),
        nutritionAPI.getDaily(today),
      ])
      setProfile(profileRes.data)
      setDaily(nutritionRes.data)
    } catch {
      // fallback
      try {
        const profileRes = await profileAPI.getProfile()
        setProfile(profileRes.data)
      } catch {}
    } finally {
      setLoading(false)
    }
  }

  const searchFood = useCallback((q: string) => {
    if (searchTimeout.current) clearTimeout(searchTimeout.current)
    setFoodQuery(q)
    if (!q.trim()) { setFoodResults([]); return }
    searchTimeout.current = setTimeout(async () => {
      setFoodSearching(true)
      try {
        const res = await foodAPI.search(q)
        setFoodResults(res.data.results || [])
      } catch { setFoodResults([]) }
      finally { setFoodSearching(false) }
    }, 350)
  }, [])

  const selectFoodResult = (food: FoodResult) => {
    setMealForm({
      name: food.name,
      calories: String(food.calories),
      protein_g: String(food.protein_g),
      fats_g: String(food.fats_g),
      carbs_g: String(food.carbs_g),
      portion_g: '100',
    })
    setFoodQuery('')
    setFoodResults([])
  }

  const handleFoodPhoto = async (file: File, mealType: string) => {
    setPhotoAnalyzing(true)
    try {
      const fd = new FormData()
      fd.append('file', file)
      const res = await nutritionAPI.analyzePhoto(fd)
      const d = res.data
      setAddingMealType(mealType)
      setMealForm({
        name: d.name || '',
        calories: d.calories != null ? String(d.calories) : '',
        protein_g: d.protein_g != null ? String(d.protein_g) : '',
        fats_g: d.fats_g != null ? String(d.fats_g) : '',
        carbs_g: d.carbs_g != null ? String(d.carbs_g) : '',
        portion_g: d.portion_g != null ? String(d.portion_g) : '',
      })
      setPhotoPreFilled(true)
    } catch { /* silent */ }
    finally { setPhotoAnalyzing(false) }
  }

  const addMeal = async () => {
    if (!addingMealType || !mealForm.name.trim()) return
    setSavingMeal(true)
    try {
      const data: Record<string, unknown> = {
        meal_date: today,
        meal_type: addingMealType,
        name: mealForm.name.trim(),
      }
      if (mealForm.calories) data.calories = parseInt(mealForm.calories)
      if (mealForm.protein_g) data.protein_g = parseFloat(mealForm.protein_g)
      if (mealForm.fats_g) data.fats_g = parseFloat(mealForm.fats_g)
      if (mealForm.carbs_g) data.carbs_g = parseFloat(mealForm.carbs_g)
      if (mealForm.portion_g) data.portion_g = parseInt(mealForm.portion_g)

      await nutritionAPI.addMeal(data)
      setAddingMealType(null)
      setPhotoPreFilled(false)
      setMealForm({ name: '', calories: '', protein_g: '', fats_g: '', carbs_g: '', portion_g: '' })
      const res = await nutritionAPI.getDaily(today)
      setDaily(res.data)
    } catch {}
    finally { setSavingMeal(false) }
  }

  const deleteMeal = async (id: string) => {
    try {
      await nutritionAPI.deleteMeal(id)
      const res = await nutritionAPI.getDaily(today)
      setDaily(res.data)
    } catch {}
  }

  const addWater = async (ml: number) => {
    setSavingWater(true)
    try {
      const res = await nutritionAPI.addWater({ log_date: today, amount_ml: ml })
      if (daily) {
        setDaily({ ...daily, water_ml: res.data.water_ml })
      }
    } catch {}
    finally { setSavingWater(false) }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="w-8 h-8 border-4 border-tg-button border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  const macros = profile ? calcMacros(profile) : null
  const goalLabel = profile?.goal ? (GOAL_LABELS[profile.goal] || profile.goal) : 'не указана'
  const totals = daily?.totals || { calories: 0, protein_g: 0, fats_g: 0, carbs_g: 0 }
  const waterGoal = profile?.weight_kg ? Math.round(profile.weight_kg * 33) : 2000

  return (
    <div className="min-h-screen bg-tg-bg pb-24">
      <div className="px-5 pt-6 pb-2">
        <h1 className="text-2xl font-bold tracking-tight">Питание</h1>
        <p className="text-sm text-tg-hint mt-0.5">Цель: {goalLabel}</p>
      </div>

      {macros && (
        <>
          {/* Calorie progress */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="mx-5 mt-4 rounded-2xl p-5 text-white relative overflow-hidden"
            style={{ background: 'linear-gradient(135deg, var(--tg-theme-button-color, #2481cc), #7c3aed)' }}
          >
            <div className="absolute top-0 right-0 w-32 h-32 rounded-full opacity-10"
              style={{ background: 'white', transform: 'translate(30%, -30%)' }} />
            <div className="flex justify-between items-end mb-2">
              <div>
                <p className="text-sm opacity-80 font-medium">Калории сегодня</p>
                <p className="text-4xl font-extrabold tracking-tight">{totals.calories}</p>
              </div>
              <div className="text-right">
                <p className="text-sm opacity-60">из {macros.calories}</p>
                <p className="text-lg font-bold">{Math.round((totals.calories / macros.calories) * 100)}%</p>
              </div>
            </div>
            <div className="h-2 bg-white/20 rounded-full overflow-hidden">
              <motion.div
                className="h-full rounded-full bg-white/80"
                initial={{ width: 0 }}
                animate={{ width: `${Math.min((totals.calories / macros.calories) * 100, 100)}%` }}
                transition={{ duration: 0.8, ease: 'easeOut' }}
              />
            </div>
          </motion.div>

          {/* Macros consumed */}
          <div className="mx-5 mt-3 grid grid-cols-3 gap-2">
            {[
              { label: 'Белки', consumed: totals.protein_g, target: macros.protein, emoji: '🥩' },
              { label: 'Жиры', consumed: totals.fats_g, target: macros.fats, emoji: '🥑' },
              { label: 'Углеводы', consumed: totals.carbs_g, target: macros.carbs, emoji: '🍞' },
            ].map((m, i) => (
              <motion.div
                key={m.label}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 + i * 0.05 }}
                className="stat-card rounded-2xl p-3 text-center"
              >
                <div className="text-lg mb-0.5">{m.emoji}</div>
                <div className="font-extrabold text-base">{Math.round(m.consumed)}<span className="text-[10px] text-tg-hint font-semibold">/{m.target}г</span></div>
                <div className="text-[10px] font-semibold text-tg-hint uppercase tracking-wide">{m.label}</div>
              </motion.div>
            ))}
          </div>
        </>
      )}

      {/* Water tracker */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="mx-5 mt-4 glass-card rounded-2xl p-4"
      >
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <span className="text-2xl">💧</span>
            <div>
              <div className="font-bold text-sm">Вода</div>
              <div className="text-xs text-tg-hint">{daily?.water_ml || 0} / {waterGoal} мл</div>
            </div>
          </div>
          <div className="text-sm font-bold" style={{ color: 'var(--tg-theme-button-color)' }}>
            {Math.round(((daily?.water_ml || 0) / waterGoal) * 100)}%
          </div>
        </div>
        <div className="h-1.5 bg-tg-bg rounded-full overflow-hidden mb-3">
          <motion.div
            className="h-full rounded-full"
            style={{ background: 'linear-gradient(90deg, #3b82f6, #06b6d4)' }}
            animate={{ width: `${Math.min(((daily?.water_ml || 0) / waterGoal) * 100, 100)}%` }}
          />
        </div>
        <div className="flex gap-2">
          {WATER_AMOUNTS.map(ml => (
            <motion.button
              key={ml}
              whileTap={{ scale: 0.95 }}
              onClick={() => addWater(ml)}
              disabled={savingWater}
              className="flex-1 bg-tg-bg rounded-xl py-2 text-xs font-bold disabled:opacity-50"
            >
              +{ml}мл
            </motion.button>
          ))}
        </div>
      </motion.div>

      {/* Meal log */}
      <div className="mx-5 mt-4">
        <h2 className="text-xs font-bold text-tg-hint mb-2.5 px-1 uppercase tracking-wider">Дневник питания</h2>

        {MEAL_TYPES.map((mt, i) => {
          const meals = daily?.meals?.[mt.key] || []
          return (
            <motion.div
              key={mt.key}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 + i * 0.05 }}
              className="glass-card rounded-2xl p-4 mb-3"
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="text-lg">{mt.emoji}</span>
                  <span className="font-bold text-sm">{mt.label}</span>
                  {meals.length > 0 && (
                    <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-full bg-tg-bg text-tg-hint">
                      {meals.reduce((s, m) => s + (m.calories || 0), 0)} ккал
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-1.5">
                  <label
                    className="w-7 h-7 rounded-lg flex items-center justify-center text-sm cursor-pointer"
                    style={{ background: 'rgba(249,115,22,0.12)', color: '#f97316' }}
                  >
                    📷
                    <input
                      type="file"
                      accept="image/*"
                      capture="environment"
                      className="hidden"
                      ref={el => { photoInputRefs.current[mt.key] = el }}
                      onChange={e => {
                        const f = e.target.files?.[0]
                        if (f) handleFoodPhoto(f, mt.key)
                        if (e.target) e.target.value = ''
                      }}
                    />
                  </label>
                  <motion.button
                    whileTap={{ scale: 0.9 }}
                    onClick={() => { setAddingMealType(addingMealType === mt.key ? null : mt.key); setPhotoPreFilled(false) }}
                    className="w-7 h-7 rounded-lg flex items-center justify-center text-sm font-bold"
                    style={{ background: 'var(--tg-theme-button-color, #2481cc)15', color: 'var(--tg-theme-button-color)' }}
                  >
                    +
                  </motion.button>
                </div>
              </div>

              {meals.map(meal => (
                <div key={meal.id} className="flex items-center justify-between py-1.5 border-t" style={{ borderColor: 'var(--tg-theme-bg-color)' }}>
                  <div className="flex-1 min-w-0">
                    <span className="text-sm font-medium">{meal.name}</span>
                    {meal.portion_g && <span className="text-xs text-tg-hint ml-1">{meal.portion_g}г</span>}
                  </div>
                  <div className="flex items-center gap-2">
                    {meal.calories && <span className="text-xs font-semibold text-tg-hint">{meal.calories} ккал</span>}
                    <button onClick={() => deleteMeal(meal.id)} className="text-tg-hint text-xs px-1">✕</button>
                  </div>
                </div>
              ))}

              {meals.length === 0 && addingMealType !== mt.key && (
                <p className="text-xs text-tg-hint py-1">Пока пусто</p>
              )}

              {/* Add meal form */}
              <AnimatePresence>
                {addingMealType === mt.key && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className="mt-2 space-y-2 overflow-hidden"
                  >
                    {photoPreFilled && (
                      <div className="text-xs font-semibold rounded-xl px-3 py-2"
                        style={{ background: 'rgba(249,115,22,0.1)', color: '#f97316' }}>
                        ✨ AI определил блюдо — проверьте данные
                      </div>
                    )}
                    {/* Food search */}
                    <div className="relative">
                      <input
                        type="text"
                        value={foodQuery}
                        onChange={e => searchFood(e.target.value)}
                        placeholder="🔍 Поиск продукта..."
                        className="w-full bg-tg-bg rounded-xl px-3 py-2.5 text-sm outline-none font-medium"
                        autoFocus
                      />
                      {foodSearching && (
                        <div className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 border-2 border-t-transparent rounded-full animate-spin"
                          style={{ borderColor: 'var(--tg-theme-button-color)', borderTopColor: 'transparent' }} />
                      )}
                      <AnimatePresence>
                        {foodResults.length > 0 && (
                          <motion.div
                            initial={{ opacity: 0, y: -4 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -4 }}
                            className="absolute left-0 right-0 top-full mt-1 z-20 rounded-xl overflow-hidden shadow-lg"
                            style={{ background: 'var(--tg-theme-bg-color, #fff)' }}
                          >
                            {foodResults.map(food => (
                              <button
                                key={food.name}
                                onClick={() => selectFoodResult(food)}
                                className="w-full flex items-center justify-between px-3 py-2.5 text-left hover:bg-tg-secondary-bg border-b last:border-b-0"
                                style={{ borderColor: 'var(--tg-theme-secondary-bg-color)' }}
                              >
                                <span className="text-sm font-medium">{food.name}</span>
                                <span className="text-xs text-tg-hint ml-2 shrink-0">{food.calories} ккал/100г</span>
                              </button>
                            ))}
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>
                    <input
                      type="text"
                      value={mealForm.name}
                      onChange={e => setMealForm(p => ({ ...p, name: e.target.value }))}
                      placeholder="Название блюда"
                      className="w-full bg-tg-bg rounded-xl px-3 py-2.5 text-sm outline-none font-medium"
                    />
                    <div className="grid grid-cols-2 gap-2">
                      <input type="number" value={mealForm.calories} onChange={e => setMealForm(p => ({ ...p, calories: e.target.value }))}
                        placeholder="Ккал" className="bg-tg-bg rounded-xl px-3 py-2 text-sm outline-none" />
                      <input type="number" value={mealForm.portion_g} onChange={e => setMealForm(p => ({ ...p, portion_g: e.target.value }))}
                        placeholder="Порция (г)" className="bg-tg-bg rounded-xl px-3 py-2 text-sm outline-none" />
                      <input type="number" value={mealForm.protein_g} onChange={e => setMealForm(p => ({ ...p, protein_g: e.target.value }))}
                        placeholder="Белки (г)" className="bg-tg-bg rounded-xl px-3 py-2 text-sm outline-none" />
                      <input type="number" value={mealForm.fats_g} onChange={e => setMealForm(p => ({ ...p, fats_g: e.target.value }))}
                        placeholder="Жиры (г)" className="bg-tg-bg rounded-xl px-3 py-2 text-sm outline-none" />
                      <input type="number" value={mealForm.carbs_g} onChange={e => setMealForm(p => ({ ...p, carbs_g: e.target.value }))}
                        placeholder="Углеводы (г)" className="bg-tg-bg rounded-xl px-3 py-2 text-sm outline-none" />
                    </div>
                    <div className="flex gap-2">
                      <button onClick={() => { setAddingMealType(null); setPhotoPreFilled(false) }} className="flex-1 bg-tg-bg rounded-xl py-2.5 text-sm font-semibold">
                        Отмена
                      </button>
                      <motion.button
                        whileTap={{ scale: 0.97 }}
                        onClick={addMeal}
                        disabled={!mealForm.name.trim() || savingMeal}
                        className="flex-1 btn-premium py-2.5 rounded-xl text-sm font-bold disabled:opacity-40"
                      >
                        {savingMeal ? '...' : 'Добавить'}
                      </motion.button>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          )
        })}
      </div>

      {/* AI Photo analyzing overlay */}
      <AnimatePresence>
        {photoAnalyzing && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 flex items-center justify-center z-50"
            style={{ background: 'rgba(0,0,0,0.7)' }}
          >
            <motion.div
              initial={{ scale: 0.85 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0.85 }}
              className="glass-card rounded-2xl p-8 text-center mx-8"
            >
              <div className="text-5xl mb-4">🤖</div>
              <div className="font-bold text-lg">Анализирую фото...</div>
              <div className="text-sm text-tg-hint mt-1">AI определяет калории и БЖУ</div>
              <div className="mt-4 w-8 h-8 border-2 border-t-transparent rounded-full animate-spin mx-auto"
                style={{ borderColor: '#f97316', borderTopColor: 'transparent' }} />
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Tips */}
      <div className="mx-5 mt-2">
        <h2 className="text-xs font-bold text-tg-hint mb-2 px-1 uppercase tracking-wider">Советы</h2>
        <div className="space-y-2">
          {[
            { emoji: '🕐', title: 'Режим питания', text: '3-4 приёма пищи равномерно в течение дня' },
            { emoji: '🥦', title: 'Овощи', text: '50% тарелки — некрахмалистые овощи' },
            { emoji: '💪', title: 'Белок', text: 'Мясо, рыба, яйца, творог, бобовые' },
          ].map((tip, i) => (
            <motion.div
              key={tip.title}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.5 + i * 0.05 }}
              className="glass-card rounded-2xl p-4 flex gap-3"
            >
              <span className="text-xl flex-shrink-0">{tip.emoji}</span>
              <div>
                <div className="font-bold text-sm">{tip.title}</div>
                <div className="text-xs text-tg-hint mt-0.5">{tip.text}</div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  )
}
