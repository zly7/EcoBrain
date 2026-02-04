import { useState, useRef, useEffect } from 'react'
import { Send, RotateCcw, Bot, User, Loader2 } from 'lucide-react'
import { useChat } from '../hooks/useChat'
import { cn } from '../lib/utils'

interface ChatProps {
  onReportGenerated?: (scenarioId: string, content: string) => void
}

const SUGGESTIONS = [
  '查询柳州市汽车产业园区',
  '生成天津武清开发区的报告',
  '上海电子信息产业园怎么样',
  '你能做什么',
]

export default function Chat({ onReportGenerated }: ChatProps) {
  const { messages, isLoading, sendMessage, resetChat } = useChat()
  const [input, setInput] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // 检测报告生成
  useEffect(() => {
    const lastMessage = messages[messages.length - 1]
    if (lastMessage?.role === 'assistant' && lastMessage.content.includes('报告生成完成')) {
      // 提取 scenario_id
      const match = lastMessage.content.match(/PDF 报告：`outputs\/([^/]+)\/report\.pdf`/)
      if (match && onReportGenerated) {
        onReportGenerated(match[1], lastMessage.content)
      }
    }
  }, [messages, onReportGenerated])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isLoading) return

    const message = input
    setInput('')
    await sendMessage(message)
  }

  const handleSuggestionClick = (suggestion: string) => {
    setInput(suggestion)
    inputRef.current?.focus()
  }

  const handleReset = async () => {
    if (window.confirm('确定要重置对话吗？')) {
      await resetChat()
    }
  }

  return (
    <div className="bg-white rounded-2xl shadow-2xl flex flex-col h-full overflow-hidden">
      {/* 头部 */}
      <div className="bg-gradient-to-r from-primary-500 to-secondary-500 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-white/20 rounded-full flex items-center justify-center">
            <Bot className="w-6 h-6 text-white" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-white">EcoBrain 对话助手</h2>
            <p className="text-xs text-white/80">多能源园区低碳规划智能顾问</p>
          </div>
        </div>
        <button
          onClick={handleReset}
          className="flex items-center gap-2 px-3 py-1.5 bg-white/20 hover:bg-white/30 rounded-lg text-white text-sm transition-colors"
        >
          <RotateCcw className="w-4 h-4" />
          重置对话
        </button>
      </div>

      {/* 快捷建议 */}
      <div className="px-4 py-3 bg-gray-50 border-b flex gap-2 flex-wrap">
        {SUGGESTIONS.map((suggestion, index) => (
          <button
            key={index}
            onClick={() => handleSuggestionClick(suggestion)}
            className="px-3 py-1.5 bg-white border border-primary-200 text-primary-600 rounded-full text-sm hover:bg-primary-50 hover:border-primary-300 transition-colors"
          >
            {suggestion}
          </button>
        ))}
      </div>

      {/* 消息列表 */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {messages.map((message) => (
          <div
            key={message.id}
            className={cn(
              'flex gap-3 animate-fade-in',
              message.role === 'user' ? 'flex-row-reverse' : ''
            )}
          >
            {/* 头像 */}
            <div
              className={cn(
                'w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0',
                message.role === 'user'
                  ? 'bg-primary-500'
                  : 'bg-secondary-500'
              )}
            >
              {message.role === 'user' ? (
                <User className="w-5 h-5 text-white" />
              ) : (
                <Bot className="w-5 h-5 text-white" />
              )}
            </div>

            {/* 消息内容 */}
            <div
              className={cn(
                'max-w-[75%] px-4 py-3 rounded-2xl whitespace-pre-wrap',
                message.role === 'user'
                  ? 'bg-primary-500 text-white rounded-br-sm'
                  : 'bg-gray-100 text-gray-800 rounded-bl-sm'
              )}
            >
              {message.content}
            </div>
          </div>
        ))}

        {/* 加载状态 */}
        {isLoading && (
          <div className="flex gap-3 animate-fade-in">
            <div className="w-9 h-9 rounded-full bg-secondary-500 flex items-center justify-center flex-shrink-0">
              <Bot className="w-5 h-5 text-white" />
            </div>
            <div className="bg-gray-100 px-4 py-3 rounded-2xl rounded-bl-sm flex items-center gap-2 text-gray-500">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span className="loading-dots">正在思考</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* 输入区域 */}
      <form onSubmit={handleSubmit} className="px-4 py-4 bg-white border-t">
        <div className="flex gap-3">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="输入您的问题..."
            disabled={isLoading}
            className="flex-1 px-4 py-3 border-2 border-gray-200 rounded-full focus:border-primary-400 focus:outline-none transition-colors disabled:bg-gray-50 disabled:cursor-not-allowed"
          />
          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            className="px-6 py-3 bg-gradient-to-r from-primary-500 to-secondary-500 text-white rounded-full font-medium hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            <Send className="w-4 h-4" />
            发送
          </button>
        </div>
      </form>
    </div>
  )
}
