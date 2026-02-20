import { useLocation, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'

const NAV_ITEMS = [
  { path: '/', emoji: '🏠', label: 'Главная' },
  { path: '/program', emoji: '📋', label: 'Программа' },
  { path: '/progress', emoji: '📊', label: 'Прогресс' },
  { path: '/chat', emoji: '🤖', label: 'Тренер' },
  { path: '/settings', emoji: '⚙️', label: 'Настройки' },
]

export default function BottomNav() {
  const location = useLocation()
  const navigate = useNavigate()

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50" style={{
      background: 'var(--tg-theme-secondary-bg-color)',
      boxShadow: '0 -1px 20px rgba(0, 0, 0, 0.06)',
      backdropFilter: 'blur(20px)',
      WebkitBackdropFilter: 'blur(20px)',
    }}>
      <div className="flex items-center justify-around px-1 pt-2 pb-6">
        {NAV_ITEMS.map(item => {
          const isActive = location.pathname === item.path ||
            (item.path !== '/' && location.pathname.startsWith(item.path))
          return (
            <button
              key={item.path}
              onClick={() => navigate(item.path)}
              className="flex flex-col items-center gap-0.5 px-3 py-1 rounded-xl transition-all relative"
            >
              <span className={`text-xl transition-transform ${isActive ? 'scale-110' : ''}`}>{item.emoji}</span>
              <span className={`text-[10px] font-semibold transition-colors ${
                isActive ? 'text-tg-button' : 'text-tg-hint'
              }`}>{item.label}</span>
              {isActive && (
                <motion.div
                  layoutId="nav-indicator"
                  className="absolute -bottom-1 w-1 h-1 rounded-full"
                  style={{ background: 'var(--tg-theme-button-color)' }}
                  transition={{ type: 'spring', stiffness: 350, damping: 30 }}
                />
              )}
            </button>
          )
        })}
      </div>
    </nav>
  )
}
