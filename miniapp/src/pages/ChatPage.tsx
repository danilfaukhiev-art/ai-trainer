import { useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import { aiAPI } from '../api/client'

interface Message {
  role: 'user' | 'assistant'
  content: string
  id: string
  time?: string
}

const SUGGESTED = [
  'Как правильно делать планку?',
  'Что съесть перед тренировкой?',
  'Болят мышцы — тренироваться?',
  'Как восстановиться быстрее?',
]

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [remaining, setRemaining] = useState<number>(-1)
  const [historyLoading, setHistoryLoading] = useState(true)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    loadHistory()
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const loadHistory = async () => {
    try {
      const res = await aiAPI.getHistory()
      const msgs = res.data.map((m: { id: string; role: string; content: string; created_at: string }) => ({
        id: m.id,
        role: m.role as 'user' | 'assistant',
        content: m.content,
        time: new Date(m.created_at).toLocaleTimeString('ru', { hour: '2-digit', minute: '2-digit' }),
      }))
      setMessages(msgs)
    } catch {
      // no history yet
    } finally {
      setHistoryLoading(false)
    }
  }

  const sendMessage = async (text?: string) => {
    const msg = (text || input).trim()
    if (!msg || loading) return

    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: msg,
      time: new Date().toLocaleTimeString('ru', { hour: '2-digit', minute: '2-digit' }),
    }

    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      const res = await aiAPI.sendMessage(msg)
      const { reply, remaining_messages } = res.data
      setMessages(prev => [
        ...prev,
        {
          id: Date.now().toString() + '_ai',
          role: 'assistant',
          content: reply,
          time: new Date().toLocaleTimeString('ru', { hour: '2-digit', minute: '2-digit' }),
        },
      ])
      setRemaining(remaining_messages)
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: { message?: string } } } }
      const errMsg = axiosErr.response?.data?.detail?.message || 'Ошибка. Попробуй снова.'
      setMessages(prev => [
        ...prev,
        { id: Date.now().toString() + '_err', role: 'assistant', content: errMsg },
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-[100dvh] bg-tg-bg">
      {/* Header */}
      <div className="px-4 py-3 flex items-center gap-3 flex-shrink-0" style={{
        background: 'var(--tg-theme-secondary-bg-color)',
        boxShadow: '0 1px 10px rgba(0,0,0,0.04)',
      }}>
        <div className="w-11 h-11 rounded-xl flex items-center justify-center text-xl flex-shrink-0"
          style={{ background: 'linear-gradient(135deg, var(--tg-theme-button-color, #2481cc), #7c3aed)' }}>
          🤖
        </div>
        <div className="flex-1 min-w-0">
          <div className="font-bold text-base">Константин — AI-тренер</div>
          <div className="text-xs text-tg-hint">
            {remaining === -1
              ? 'Отвечу на любой вопрос о тренировках'
              : remaining > 0
                ? `Осталось сегодня: ${remaining} сообщ.`
                : 'Лимит на сегодня исчерпан'}
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-2 h-2 rounded-full bg-green-500" />
          <span className="text-[10px] text-green-500 font-semibold">Online</span>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3 pb-2">
        {historyLoading ? (
          <div className="flex justify-center pt-10">
            <div className="w-6 h-6 border-2 border-tg-button border-t-transparent rounded-full animate-spin" />
          </div>
        ) : messages.length === 0 ? (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center py-8"
          >
            <motion.div
              animate={{ scale: [1, 1.05, 1] }}
              transition={{ duration: 2, repeat: Infinity }}
              className="text-5xl mb-3"
            >
              💬
            </motion.div>
            <p className="font-bold text-lg mb-1">Привет! Я Константин</p>
            <p className="text-tg-hint text-sm mb-6">Твой персональный AI-тренер. Задай любой вопрос!</p>
            <div className="space-y-2">
              {SUGGESTED.map((q, i) => (
                <motion.button
                  key={q}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.1 + i * 0.05 }}
                  whileTap={{ scale: 0.97 }}
                  onClick={() => sendMessage(q)}
                  className="w-full glass-card text-sm p-3.5 rounded-2xl text-left font-medium"
                >
                  {q}
                </motion.button>
              ))}
            </div>
          </motion.div>
        ) : (
          messages.map(msg => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} items-end gap-2`}
            >
              {msg.role === 'assistant' && (
                <div className="w-7 h-7 rounded-lg flex items-center justify-center text-sm flex-shrink-0 mb-0.5"
                  style={{ background: 'linear-gradient(135deg, var(--tg-theme-button-color, #2481cc), #7c3aed)' }}>
                  🤖
                </div>
              )}
              <div className="max-w-[78%]">
                <div
                  className={`px-4 py-3 text-sm whitespace-pre-wrap leading-relaxed ${
                    msg.role === 'user'
                      ? 'rounded-2xl rounded-br-sm text-white'
                      : 'glass-card rounded-2xl rounded-bl-sm'
                  }`}
                  style={msg.role === 'user'
                    ? { background: 'linear-gradient(135deg, var(--tg-theme-button-color, #2481cc), #7c3aed)' }
                    : {}}
                >
                  {msg.content}
                </div>
                {msg.time && (
                  <div className={`text-[10px] text-tg-hint mt-1 font-medium ${msg.role === 'user' ? 'text-right' : 'text-left'}`}>
                    {msg.time}
                  </div>
                )}
              </div>
            </motion.div>
          ))
        )}

        {loading && (
          <div className="flex justify-start items-end gap-2">
            <div className="w-7 h-7 rounded-lg flex items-center justify-center text-sm flex-shrink-0"
              style={{ background: 'linear-gradient(135deg, var(--tg-theme-button-color, #2481cc), #7c3aed)' }}>
              🤖
            </div>
            <div className="glass-card px-4 py-3 rounded-2xl rounded-bl-sm">
              <div className="flex gap-1.5 items-center h-4">
                {[0,1,2].map(i => (
                  <motion.div
                    key={i}
                    className="w-1.5 h-1.5 rounded-full bg-tg-hint"
                    animate={{ scale: [1, 1.5, 1] }}
                    transition={{ duration: 0.6, repeat: Infinity, delay: i * 0.15 }}
                  />
                ))}
              </div>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="px-3 pb-20 pt-2 border-t flex-shrink-0" style={{
        background: 'var(--tg-theme-bg-color)',
        borderColor: 'var(--tg-theme-secondary-bg-color)',
      }}>
        <div className="flex gap-2 items-end">
          <input
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && !e.shiftKey && sendMessage()}
            placeholder="Спроси Константина..."
            className="flex-1 bg-tg-secondary-bg rounded-2xl px-4 py-3 text-sm outline-none"
          />
          <motion.button
            whileTap={{ scale: 0.9 }}
            onClick={() => sendMessage()}
            disabled={!input.trim() || loading}
            className="w-11 h-11 rounded-xl flex items-center justify-center font-bold text-white disabled:opacity-30 flex-shrink-0"
            style={{ background: 'linear-gradient(135deg, var(--tg-theme-button-color, #2481cc), #7c3aed)' }}
          >
            ↑
          </motion.button>
        </div>
      </div>
    </div>
  )
}
