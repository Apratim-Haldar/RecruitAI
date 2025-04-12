"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Bot, Send, User, Sparkles, ChevronDown, ChevronUp } from "lucide-react"

export function AiAssistant() {
  const [isExpanded, setIsExpanded] = useState(false)
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content: "Hello! I'm your AI recruiting assistant. How can I help you with the hiring process today?",
    },
  ])
  const [inputValue, setInputValue] = useState("")

  const handleSendMessage = () => {
    if (!inputValue.trim()) return

    // Add user message
    setMessages([...messages, { role: "user", content: inputValue }])

    // Simulate AI response
    setTimeout(() => {
      const aiResponses = [
        "I can help analyze this candidate's profile. Their skills in React and TypeScript are a strong match for the position.",
        "Based on their experience, this candidate would be a good fit for the Senior Frontend Developer role. Would you like me to suggest some interview questions?",
        "I've analyzed their resume and found they have 5 years of relevant experience, which meets our requirements.",
        "Their technical assessment scores are above average compared to other candidates for this position.",
      ]

      const randomResponse = aiResponses[Math.floor(Math.random() * aiResponses.length)]
      setMessages((prev) => [...prev, { role: "assistant", content: randomResponse }])
    }, 1000)

    setInputValue("")
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
                  {message.content}
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
          </div>

          <div className="flex gap-2">
            <Input
              placeholder="Ask about candidates or hiring..."
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              className="flex-1"
            />
            <Button size="icon" onClick={handleSendMessage} className="bg-purple-600 hover:bg-purple-700">
              <Send className="h-4 w-4" />
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
              Analyze this candidate's profile
            </Button>
            <Button variant="outline" size="sm" className="justify-start text-left" onClick={() => setIsExpanded(true)}>
              <Sparkles className="h-4 w-4 mr-2 text-purple-500" />
              Suggest interview questions
            </Button>
            <Button variant="outline" size="sm" className="justify-start text-left" onClick={() => setIsExpanded(true)}>
              <Sparkles className="h-4 w-4 mr-2 text-purple-500" />
              Compare with other candidates
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}

