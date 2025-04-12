import React, { useState } from 'react';
import { Send, Loader } from 'lucide-react';

export default function AIAssistant() {
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim()) return;
    
    setLoading(true);
    // Simulate AI response
    setTimeout(() => {
      setLoading(false);
      setMessage('');
    }, 1000);
  };

  return (
    <div className="bg-white rounded-lg shadow h-[calc(100vh-24rem)]">
      <div className="p-6 border-b border-gray-200">
        <h2 className="text-xl font-semibold text-gray-900">AI Recruitment Assistant</h2>
      </div>
      <div className="flex flex-col h-full">
        <div className="flex-1 p-6 overflow-y-auto">
          <div className="space-y-4">
            <div className="flex items-start">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center">
                  <span className="text-blue-600 font-medium">AI</span>
                </div>
              </div>
              <div className="ml-3 bg-gray-100 rounded-lg p-4 max-w-[80%]">
                <p className="text-sm text-gray-900">
                  Hello! I'm your AI recruitment assistant. I can help you with:
                  <ul className="list-disc ml-4 mt-2">
                    <li>Screening resumes</li>
                    <li>Writing job descriptions</li>
                    <li>Generating interview questions</li>
                    <li>Evaluating candidate responses</li>
                  </ul>
                </p>
              </div>
            </div>
          </div>
        </div>
        <div className="p-4 border-t border-gray-200">
          <form onSubmit={handleSubmit} className="flex items-center space-x-2">
            <input
              type="text"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Ask me anything about recruitment..."
              className="flex-1 border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
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
    </div>
  );
}