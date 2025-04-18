import React, { useState } from 'react'
import { Send, Loader } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import rehypeHighlight from 'rehype-highlight'

export default function AIAssistant() {
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(false)
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: "Hello! I'm your AI recruitment assistant. I can help you with:\n\n- Screening resumes\n- Writing job descriptions\n- Generating interview questions\n- Evaluating candidate responses"
    }
  ])
  const [sessionId] = useState(() => Date.now().toString(36) + Math.random().toString(36).substr(2))
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!message.trim()) return

    const userMessage = { role: 'user', content: message }
    setMessages((prev) => [...prev, userMessage])
    setLoading(true)

    try {
      const response = await fetch('http://127.0.0.1:8080/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: message, session_id: sessionId })
      })
      const data = await response.json()
      const aiMessage = { role: 'assistant', content: data.answer }
      setMessages((prev) => [...prev, aiMessage])
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: '**Error:** Could not connect to AI service' }
      ])
    } finally {
      setLoading(false)
      setMessage('')
    }
  }

  return (
    <div className="bg-white rounded-lg shadow-lg h-[calc(100vh-24rem)] flex flex-col overflow-hidden border border-gray-200">
      <div className="p-4 border-b border-gray-200 bg-gray-50">
        <h2 className="text-xl font-semibold text-gray-900">AI Recruitment Assistant</h2>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {messages.map((msg, idx) => (
          <div key={idx} className={`flex items-start space-x-3 ${msg.role === 'user' ? 'justify-end' : ''}`}>
            {msg.role === 'assistant' && (
              <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center font-semibold text-blue-600">AI</div>
            )}
            <div
              className={`rounded-lg px-4 py-3 text-sm max-w-[80%] whitespace-pre-wrap ${
                msg.role === 'user'
                  ? 'bg-blue-600 text-white ml-auto'
                  : 'bg-gray-100 text-gray-900'
              }`}
            >
              <div className="prose prose-sm max-w-none">
                <ReactMarkdown rehypePlugins={[rehypeHighlight]}>
                  {msg.content}
                </ReactMarkdown>
              </div>
            </div>
            {msg.role === 'user' && (
              <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center font-semibold text-gray-600">You</div>
            )}
          </div>
        ))}
        {loading && (
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center font-semibold text-blue-600">AI</div>
            <div className="bg-gray-100 rounded-lg px-4 py-3 text-sm text-gray-500">
              <div className="flex items-center space-x-2">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-200" />
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-400" />
                <span>Analyzing...</span>
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="p-4 border-t border-gray-200 bg-white">
        <form onSubmit={handleSubmit} className="flex items-center space-x-2">
          <input
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Ask me anything about recruitment..."
            className="flex-1 border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 focus:outline-none"
          />
          <button
            type="submit"
            disabled={loading}
            className="p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? (
              <Loader className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </form>
      </div>
    </div>
  )
}
