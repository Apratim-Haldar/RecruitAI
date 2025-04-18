import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Bot, Send, User, Sparkles, ChevronDown, ChevronUp } from "lucide-react"
import ReactMarkdown from 'react-markdown'
import rehypeHighlight from 'rehype-highlight'

export function AiAssistant() {
  const [isExpanded, setIsExpanded] = useState(false)
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content: "Hello! I'm your AI recruiting assistant. How can I help you with the hiring process today?",
    },
  ])
  const [inputValue, setInputValue] = useState("")
  const [isTyping, setIsTyping] = useState(false)
  const [sessionId] = useState(() => Date.now().toString(36) + Math.random().toString(36).substr(2))


  const handleSendMessage = async () => {
    if (!inputValue.trim()) return

    setMessages(prev => [...prev, { role: "user", content: inputValue }])
    setInputValue("")
    setIsTyping(true)

    try {
      const response = await fetch('http://127.0.0.1:8080/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: inputValue, session_id: sessionId })
      })

      const data = await response.json()
      setMessages(prev => [
        ...prev,
        { role: "assistant", content: data.answer }
      ])
    } catch (error) {
      setMessages(prev => [
        ...prev,
        { role: "assistant", content: "**Error:** Could not connect to AI service" }
      ])
    } finally {
      setIsTyping(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === "Enter") {
      handleSendMessage()
    }
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex justify-between items-center mb-4">
        <div className="flex items-center gap-2">
          <Avatar className="h-8 w-8 bg-purple-100">
            <AvatarFallback className="bg-purple-100 text-purple-600">
              <Bot className="h-4 w-4" />
            </AvatarFallback>
          </Avatar>
          <h3 className="font-medium">Recruiting Assistant</h3>
        </div>
        <Button variant="ghost" size="sm" className="h-8 w-8 p-0" onClick={() => setIsExpanded(!isExpanded)}>
          {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
        </Button>
      </div>

      {isExpanded && (
        <>
          <div className="flex-1 overflow-y-auto mb-4 space-y-4 max-h-[300px]">
            {messages.map((message, index) => (
              <div key={index} className={`flex gap-2 ${message.role === "user" ? "justify-end" : "justify-start"}`}>
                {message.role === "assistant" && (
                  <Avatar className="h-8 w-8 mt-1">
                    <AvatarFallback className="bg-purple-100 text-purple-600">
                      <Bot className="h-4 w-4" />
                    </AvatarFallback>
                  </Avatar>
                )}
                <div
                  className={`p-3 rounded-lg max-w-[80%] ${
                    message.role === "user" ? "bg-purple-600 text-white" : "bg-gray-100 text-gray-800"
                  }`}
                >
                  <div className="prose prose-sm max-w-none">
                    <ReactMarkdown rehypePlugins={[rehypeHighlight]}>
                      {message.content}
                    </ReactMarkdown>
                  </div>
                </div>
                {message.role === "user" && (
                  <Avatar className="h-8 w-8 mt-1">
                    <AvatarFallback className="bg-gray-100">
                      <User className="h-4 w-4" />
                    </AvatarFallback>
                  </Avatar>
                )}
              </div>
            ))}
            {isTyping && (
              <div className="flex items-center gap-2 justify-start">
                <Avatar className="h-8 w-8 mt-1">
                  <AvatarFallback className="bg-purple-100 text-purple-600">
                    <Bot className="h-4 w-4" />
                  </AvatarFallback>
                </Avatar>
                <div className="flex items-center gap-2 text-sm text-gray-500 px-4">
                  <div className="flex space-x-2">
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
                  </div>
                  <span>Analyzing...</span>
                </div>
              </div>
            )}
          </div>

          <div className="flex gap-2">
            <Input
              placeholder="Ask about candidates or hiring..."
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              className="flex-1"
            />
            <Button
              size="icon"
              onClick={handleSendMessage}
              className="bg-purple-600 hover:bg-purple-700"
              disabled={isTyping}
            >
              {isTyping ? (
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </Button>
          </div>
        </>
      )}

      {!isExpanded && (
        <div className="space-y-2">
          <p className="text-sm text-gray-500">
            I can help you analyze candidates, suggest interview questions, and provide hiring insights.
          </p>
          <div className="grid grid-cols-1 gap-2">
            <Button variant="outline" size="sm" className="justify-start text-left" onClick={() => setIsExpanded(true)}>
              <Sparkles className="h-4 w-4 mr-2 text-purple-500" />
              Analyze a candidate's profile
            </Button>
            <Button variant="outline" size="sm" className="justify-start text-left" onClick={() => setIsExpanded(true)}>
              <Sparkles className="h-4 w-4 mr-2 text-purple-500" />
              Suggest interview questions
            </Button>
            <Button variant="outline" size="sm" className="justify-start text-left" onClick={() => setIsExpanded(true)}>
              <Sparkles className="h-4 w-4 mr-2 text-purple-500" />
              Compare multiple candidates
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
