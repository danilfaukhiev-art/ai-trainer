import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'

interface PaywallSheetProps {
  open: boolean
  onClose: () => void
  reason?: string  // e.g. "AI-сообщения исчерпаны на сегодня"
}

const TIERS = [
  {
    key: 'basic',
    emoji: '⭐',
    name: 'Basic',
    price: '99 Stars/мес',
    gradient: 'linear-gradient(135deg, #f59e0b, #d97706)',
    perks: ['7 тренировок/нед', '20 AI-сообщений/день', 'Фото прогресса'],
  },
  {
    key: 'pro',
    emoji: '🚀',
    name: 'Pro',
    price: '299 Stars/мес',
    gradient: 'linear-gradient(135deg, #2563eb, #7c3aed)',
    perks: ['Безлимитный AI-чат', 'Питание Pro', 'Всё из Basic'],
    highlight: true,
  },
  {
    key: 'premium',
    emoji: '💎',
    name: 'Premium',
    price: '599 Stars/мес',
    gradient: 'linear-gradient(135deg, #8b5cf6, #ec4899)',
    perks: ['Видео-анализ техники', 'PDF-экспорт', 'Всё из Pro'],
  },
]

export default function PaywallSheet({ open, onClose, reason }: PaywallSheetProps) {
  const navigate = useNavigate()

  const openSubscribePage = () => {
    onClose()
    navigate('/subscription')
  }

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-40 bg-black/50"
            onClick={onClose}
          />

          {/* Sheet */}
          <motion.div
            initial={{ y: '100%' }}
            animate={{ y: 0 }}
            exit={{ y: '100%' }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            className="fixed bottom-0 left-0 right-0 z-50 rounded-t-3xl p-5 pb-10 max-h-[85vh] overflow-y-auto"
            style={{ background: 'var(--tg-theme-bg-color, #ffffff)' }}
          >
            {/* Handle */}
            <div className="w-10 h-1 rounded-full bg-gray-300 mx-auto mb-4" />

            <div className="text-center mb-5">
              <div className="text-4xl mb-2">🔒</div>
              <h2 className="text-xl font-bold">Нужна подписка</h2>
              {reason && (
                <p className="text-sm text-tg-hint mt-1">{reason}</p>
              )}
            </div>

            {/* Tier cards */}
            <div className="space-y-3 mb-5">
              {TIERS.map(tier => (
                <motion.div
                  key={tier.key}
                  whileTap={{ scale: 0.98 }}
                  onClick={openSubscribePage}
                  className={`rounded-2xl p-4 cursor-pointer border-2 ${
                    tier.highlight ? 'border-blue-500' : 'border-transparent'
                  }`}
                  style={{
                    background: tier.highlight
                      ? 'rgba(37,99,235,0.06)'
                      : 'var(--tg-theme-secondary-bg-color, rgba(0,0,0,0.04))',
                  }}
                >
                  <div className="flex items-center gap-3">
                    <div
                      className="w-10 h-10 rounded-xl flex items-center justify-center text-xl shrink-0"
                      style={{ background: tier.gradient }}
                    >
                      {tier.emoji}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-sm">{tier.name}</span>
                        {tier.highlight && (
                          <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-full text-white"
                            style={{ background: '#2563eb' }}>
                            Популярный
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-tg-hint">{tier.price}</div>
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-1.5 mt-3">
                    {tier.perks.map(perk => (
                      <span
                        key={perk}
                        className="text-xs px-2 py-0.5 rounded-full font-medium"
                        style={{
                          background: tier.highlight
                            ? 'rgba(37,99,235,0.12)'
                            : 'rgba(0,0,0,0.06)',
                          color: tier.highlight ? '#2563eb' : undefined,
                        }}
                      >
                        {perk}
                      </span>
                    ))}
                  </div>
                </motion.div>
              ))}
            </div>

            <button
              onClick={openSubscribePage}
              className="w-full btn-premium py-3.5 rounded-xl font-bold text-sm"
            >
              Выбрать тариф →
            </button>

            <button
              onClick={onClose}
              className="w-full mt-2 py-3 rounded-xl text-sm text-tg-hint font-medium"
            >
              Не сейчас
            </button>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
