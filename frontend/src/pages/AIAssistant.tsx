import React, { useState, useRef, useEffect } from 'react'
import { Send, Sparkles, RefreshCw, MessageSquare } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { aiApi } from '../services/api'
import type { ChatMessage } from '../types'
import { format } from 'date-fns'
import clsx from 'clsx'
import LoadingSpinner from '../components/ui/LoadingSpinner'

const QUICK_PROMPTS = [
  "Why was my sleep bad recently?",
  "What's the relationship between my diet and recovery?",
  "Am I overtraining based on my data?",
  "What nutrients might I be deficient in?",
  "When should I work out today?",
  "Analyze my HRV trend",
]

export default function AIAssistant() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [suggestedQuestions, setSuggestedQuestions] = useState<string[]>(QUICK_PROMPTS)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  useEffect(() => {
    aiApi.suggestedQuestions().then(res => {
      setSuggestedQuestions(res.data.questions?.slice(0, 6) || QUICK_PROMPTS)
    }).catch(() => {})
  }, [])

  const sendMessage = async (text?: string) => {
    const messageText = text || input.trim()
    if (!messageText || loading) return

    setInput('')
    const userMsg: ChatMessage = {
      role: 'user',
      content: messageText,
      timestamp: new Date().toISOString(),
    }
    setMessages(prev => [...prev, userMsg])
    setLoading(true)

    try {
      const history = messages.map(m => ({ role: m.role, content: m.content }))
      const res = await aiApi.chat(messageText, history)
      const assistantMsg: ChatMessage = {
        role: 'assistant',
        content: res.data.message,
        timestamp: new Date().toISOString(),
      }
      setMessages(prev => [...prev, assistantMsg])
    } catch (e: unknown) {
      const errorMsg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Failed to get response. Please check your API key configuration.'
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Sorry, I encountered an error: ${errorMsg}`,
        timestamp: new Date().toISOString(),
      }])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const clearConversation = () => {
    setMessages([])
  }

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)]">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-brand-400" />
            AI Health Assistant
          </h1>
          <p className="text-slate-500 text-sm">Powered by Claude — analyzes all your health data</p>
        </div>
        {messages.length > 0 && (
          <button onClick={clearConversation} className="btn-ghost text-sm flex items-center gap-1.5">
            <RefreshCw className="w-4 h-4" />
            New chat
          </button>
        )}
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto space-y-4 pb-4">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center gap-6">
            <div className="w-16 h-16 rounded-2xl bg-brand-500/15 border border-brand-500/20 flex items-center justify-center">
              <MessageSquare className="w-8 h-8 text-brand-400" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-white mb-1">Ask me anything about your health</h3>
              <p className="text-slate-500 text-sm max-w-sm">
                I have access to all your health data from connected devices — sleep, nutrition, workouts, body metrics, and lab tests.
              </p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-xl">
              {suggestedQuestions.map((q, i) => (
                <button
                  key={i}
                  onClick={() => sendMessage(q)}
                  className="text-left px-4 py-3 rounded-xl bg-surface-800 border border-surface-700/50 hover:border-brand-500/40 hover:bg-surface-700 text-sm text-slate-300 transition-all"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((msg, i) => (
            <div
              key={i}
              className={clsx('flex gap-3', msg.role === 'user' ? 'justify-end' : 'justify-start')}
            >
              {msg.role === 'assistant' && (
                <div className="w-7 h-7 rounded-lg bg-brand-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <Sparkles className="w-3.5 h-3.5 text-brand-400" />
                </div>
              )}
              <div className={clsx(
                'max-w-2xl rounded-2xl px-4 py-3 text-sm',
                msg.role === 'user'
                  ? 'bg-brand-500/20 text-slate-100 rounded-tr-sm'
                  : 'bg-surface-800 text-slate-200 rounded-tl-sm border border-surface-700/50'
              )}>
                {msg.role === 'assistant' ? (
                  <div className="prose prose-invert prose-sm max-w-none prose-p:leading-relaxed prose-headings:text-white prose-strong:text-white prose-ul:mt-1 prose-li:mt-0.5">
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                  </div>
                ) : (
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                )}
                {msg.timestamp && (
                  <p className={clsx('text-xs mt-1.5', msg.role === 'user' ? 'text-brand-300/60' : 'text-slate-600')}>
                    {format(new Date(msg.timestamp), 'HH:mm')}
                  </p>
                )}
              </div>
              {msg.role === 'user' && (
                <div className="w-7 h-7 rounded-lg bg-surface-700 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <span className="text-xs font-medium text-slate-400">You</span>
                </div>
              )}
            </div>
          ))
        )}

        {loading && (
          <div className="flex gap-3 justify-start">
            <div className="w-7 h-7 rounded-lg bg-brand-500/20 flex items-center justify-center flex-shrink-0">
              <Sparkles className="w-3.5 h-3.5 text-brand-400" />
            </div>
            <div className="bg-surface-800 rounded-2xl rounded-tl-sm border border-surface-700/50 px-4 py-3">
              <div className="flex gap-1.5 items-center">
                <div className="w-1.5 h-1.5 bg-brand-400 rounded-full animate-bounce" />
                <div className="w-1.5 h-1.5 bg-brand-400 rounded-full animate-bounce delay-75" />
                <div className="w-1.5 h-1.5 bg-brand-400 rounded-full animate-bounce delay-150" />
              </div>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="bg-surface-900 border border-surface-700/50 rounded-2xl p-3 flex items-end gap-3">
        <textarea
          ref={inputRef}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about your health data..."
          rows={1}
          className="flex-1 bg-transparent text-slate-100 placeholder-slate-600 resize-none focus:outline-none text-sm leading-relaxed max-h-32 overflow-y-auto"
          style={{ minHeight: '1.5rem' }}
        />
        <button
          onClick={() => sendMessage()}
          disabled={!input.trim() || loading}
          className={clsx(
            'w-8 h-8 rounded-xl flex items-center justify-center transition-all flex-shrink-0',
            input.trim() && !loading
              ? 'bg-brand-500 hover:bg-brand-600 text-white'
              : 'bg-surface-700 text-slate-600 cursor-not-allowed'
          )}
        >
          <Send className="w-4 h-4" />
        </button>
      </div>
      <p className="text-xs text-slate-600 text-center mt-2">
        AI may make mistakes. Always consult healthcare providers for medical decisions.
      </p>
    </div>
  )
}
