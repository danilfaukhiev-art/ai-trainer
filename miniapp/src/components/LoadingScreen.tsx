import { motion } from 'framer-motion'

export default function LoadingScreen() {
  return (
    <div className="flex flex-col items-center justify-center h-screen bg-tg-bg gap-6">
      <motion.div
        initial={{ scale: 0.8, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ duration: 0.5, ease: 'easeOut' }}
        className="relative"
      >
        <motion.div
          animate={{ scale: [1, 1.15, 1] }}
          transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
          className="text-6xl"
        >
          💪
        </motion.div>
        <motion.div
          className="absolute -inset-4 rounded-full"
          style={{ border: '2px solid var(--tg-theme-button-color)', opacity: 0.15 }}
          animate={{ scale: [1, 1.3, 1], opacity: [0.15, 0, 0.15] }}
          transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
        />
      </motion.div>
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="flex flex-col items-center gap-2"
      >
        <div className="flex gap-1">
          {[0, 1, 2].map(i => (
            <motion.div
              key={i}
              className="w-1.5 h-1.5 rounded-full"
              style={{ background: 'var(--tg-theme-button-color)' }}
              animate={{ scale: [1, 1.5, 1], opacity: [0.4, 1, 0.4] }}
              transition={{ duration: 0.8, repeat: Infinity, delay: i * 0.15 }}
            />
          ))}
        </div>
        <p className="text-tg-hint text-sm font-medium">AI Personal Trainer</p>
      </motion.div>
    </div>
  )
}
