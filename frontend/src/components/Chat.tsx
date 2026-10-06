import { useEffect, useRef, useState } from 'react'
import { sendMessage } from '../api'
import type { ChatMessage } from '../types'
import Message from './Message'

export default function Chat() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  // keep the latest message in view
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    const question = input.trim()
    if (!question || loading) return

    const history = messages
    setMessages([...history, { role: 'user', content: question }])
    setInput('')
    setError(null)
    setLoading(true)
    try {
      const response = await sendMessage(question, history)
      setMessages([
        ...history,
        { role: 'user', content: question },
        {
          role: 'assistant',
          content: response.answer,
          toolCalls: response.tool_calls,
          sources: response.sources,
        },
      ])
    } catch (err) {
      // put the question back in the input so it can be sent again
      setMessages(history)
      setInput(question)
      setError(err instanceof Error ? err.message : 'Something went wrong')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 space-y-4 overflow-y-auto px-6 py-6">
        {messages.length === 0 && !loading && (
          <div className="mt-24 text-center text-slate-400">
            <p className="text-lg font-medium text-slate-500">Ask a question about your documents</p>
            <p className="mt-1 text-sm">
              For example: “Which documents do I have?” or “Summarise the meeting notes.”
            </p>
          </div>
        )}
        {messages.map((message, index) => (
          <Message key={index} message={message} />
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="animate-pulse rounded-2xl rounded-bl-sm border border-slate-200 bg-white px-4 py-2 text-sm text-slate-400">
              Searching your documents…
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {error && (
        <p className="mx-6 mb-2 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
      )}

      <form onSubmit={handleSubmit} className="flex gap-2 border-t border-slate-200 bg-white px-6 py-4">
        <input
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder="Type your question…"
          className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-slate-300"
        >
          Send
        </button>
      </form>
    </div>
  )
}
