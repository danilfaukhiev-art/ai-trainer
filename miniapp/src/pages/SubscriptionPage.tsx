import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { subscriptionAPI } from '../api/client'

interface TierInfo {
  tier: string
  stars: number
  days: number
  is_current: boolean
  is_upgrade: boolean
  features: Record<string, boolean | number>
}

interface SubInfo {
  current_tier: string
  expires_at: string | null
  tiers: TierInfo[]
}

const TIER_META: Record<string, { emoji: string; name: string; gradient: string }> = {
  basic: { emoji: '⭐', name: 'Basic', gradient: 'linear-gradient(135deg, #f59e0b, #d97706)' },
  pro: { emoji: '🚀', name: 'Pro', gradient: 'linear-gradient(135deg, #2563eb, #7c3aed)' },
  premium: { emoji: '💎', name: 'Premium', gradient: 'linear-gradient(135deg, #8b5cf6, #ec4899)' },
}

const FEATURE_LABELS: Record<string, string> = {
  workouts_per_week: 'Тренировок в неделю',
  ai_messages_per_day: 'AI-сообщений в день',
  nutrition_pro: 'Питание Pro',
  video_analysis: 'Видео-анализ техники',
  progress_photos: 'Фото прогресса',
  pdf_export: 'PDF-экспорт',
}

export default function SubscriptionPage() {
  const [info, setInfo] = useState<SubInfo | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    subscriptionAPI.getInfo()
      .then(r => setInfo(r.data))
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const openPayBot = (tier: string) => {
    // Open Telegram bot for Stars payment
    const tg = (window as any).Telegram?.WebApp
    if (tg) {
      tg.openTelegramLink(`https://t.me/${import.meta.env.VITE_BOT_USERNAME}?start=subscribe_${tier}`)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="w-8 h-8 border-4 border-tg-button border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  const currentTier = info?.current_tier || 'free'

  return (
    <div className="min-h-screen bg-tg-bg pb-24">
      {/* Header */}
      <div className="px-5 pt-6 pb-2">
        <h1 className="text-2xl font-bold tracking-tight">Подписка</h1>
        <p className="text-sm text-tg-hint mt-0.5">Оплата через Telegram Stars</p>
      </div>

      {/* Current plan badge */}
      <div className="mx-5 mb-5">
        <div className="glass-card rounded-2xl p-4 flex items-center gap-3">
          <span className="text-2xl">
            {TIER_META[currentTier]?.emoji || '🆓'}
          </span>
          <div>
            <div className="font-bold text-sm">
              Текущий план: {TIER_META[currentTier]?.name || 'Бесплатный'}
            </div>
            {info?.expires_at && (
              <div className="text-xs text-tg-hint mt-0.5">
                До {new Date(info.expires_at).toLocaleDateString('ru-RU')}
              </div>
            )}
            {!info?.expires_at && currentTier === 'free' && (
              <div className="text-xs text-tg-hint mt-0.5">
                3 тренировки · 3 AI-сообщения в день
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Tier cards */}
      <div className="px-5 space-y-4">
        {info?.tiers.map((tier, i) => {
          const meta = TIER_META[tier.tier]
          if (!meta) return null
          const isPro = tier.tier === 'pro'

          return (
            <motion.div
              key={tier.tier}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.08 }}
              className={`rounded-2xl overflow-hidden border-2 ${
                isPro ? 'border-blue-500' : 'border-transparent'
              }`}
            >
              {/* Tier header */}
              <div
                className="px-4 py-3 flex items-center justify-between"
                style={{ background: meta.gradient }}
              >
                <div className="flex items-center gap-2">
                  <span className="text-2xl">{meta.emoji}</span>
                  <span className="text-white font-bold text-lg">{meta.name}</span>
                  {isPro && (
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-white/20 text-white">
                      Популярный
                    </span>
                  )}
                </div>
                <div className="text-right">
                  <div className="text-white font-extrabold">{tier.stars} ⭐</div>
                  <div className="text-white/70 text-xs">{tier.days} дней</div>
                </div>
              </div>

              {/* Features */}
              <div className="glass-card rounded-b-2xl p-4 space-y-2.5">
                {Object.entries(tier.features).map(([key, val]) => {
                  const label = FEATURE_LABELS[key]
                  if (!label) return null
                  const isUnlimited = val === -1
                  const isEnabled = val === true || (typeof val === 'number' && val > 0) || isUnlimited

                  return (
                    <div key={key} className="flex items-center justify-between">
                      <span className="text-sm text-tg-hint">{label}</span>
                      <span className={`text-sm font-bold ${isEnabled ? '' : 'text-tg-hint opacity-40'}`}>
                        {typeof val === 'boolean'
                          ? (val ? '✅' : '❌')
                          : isUnlimited
                            ? '∞'
                            : `${val}`
                        }
                      </span>
                    </div>
                  )
                })}

                {/* CTA button */}
                {tier.is_current ? (
                  <div className="mt-3 py-3 rounded-xl text-center text-sm font-bold text-tg-hint bg-tg-bg">
                    Текущий план
                  </div>
                ) : (
                  <motion.button
                    whileTap={{ scale: 0.97 }}
                    onClick={() => openPayBot(tier.tier)}
                    className="mt-3 w-full py-3 rounded-xl font-bold text-sm text-white"
                    style={{ background: meta.gradient }}
                  >
                    {tier.is_upgrade ? `Улучшить до ${meta.name}` : `Перейти на ${meta.name}`}
                  </motion.button>
                )}
              </div>
            </motion.div>
          )
        })}
      </div>

      {/* Stars info */}
      <div className="mx-5 mt-6 glass-card rounded-2xl p-4">
        <p className="text-xs text-tg-hint leading-relaxed">
          💫 <strong>Telegram Stars</strong> — внутренняя валюта Telegram. Купить Stars можно прямо в приложении.
          Оплата безопасна и защищена Telegram. Подписка активируется мгновенно.
        </p>
      </div>
    </div>
  )
}
