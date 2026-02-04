import { useState, useCallback, useRef, useEffect } from 'react'
import { sendChatMessage, resetChat as apiResetChat } from '../lib/api'

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content: `您好！我是 EcoBrain 多能源园区低碳规划助手。

我可以帮您：
1. 📊 查询全国 10 万+ 园区信息
2. 📝 生成专业的低碳规划报告
3. 💡 提供减排措施建议
4. 📋 匹配相关政策支持

请告诉我您想查询哪个园区？例如：
- 柳州市汽车产业园区
- 天津武清开发区
- 上海电子信息产业园`,
      timestamp: new Date(),
    },
  ])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const messageIdRef = useRef(0)

  const generateId = useCallback(() => {
    messageIdRef.current += 1
    return `msg-${Date.now()}-${messageIdRef.current}`
  }, [])

  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim() || isLoading) return

    setError(null)

    // 添加用户消息
    const userMessage: Message = {
      id: generateId(),
      role: 'user',
      content: content.trim(),
      timestamp: new Date(),
    }
    setMessages(prev => [...prev, userMessage])
    setIsLoading(true)

    try {
      const response = await sendChatMessage(content)

      // 添加助手回复
      const assistantMessage: Message = {
        id: generateId(),
        role: 'assistant',
        content: response.response,
        timestamp: new Date(),
      }
      setMessages(prev => [...prev, assistantMessage])

      return response
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '发送消息失败'
      setError(errorMessage)

      // 添加错误消息
      const errorAssistantMessage: Message = {
        id: generateId(),
        role: 'assistant',
        content: `❌ 错误: ${errorMessage}\n\n请确保 API 服务已启动。`,
        timestamp: new Date(),
      }
      setMessages(prev => [...prev, errorAssistantMessage])
    } finally {
      setIsLoading(false)
    }
  }, [isLoading, generateId])

  const resetChat = useCallback(async () => {
    try {
      await apiResetChat()
      setMessages([
        {
          id: 'welcome',
          role: 'assistant',
          content: `您好！我是 EcoBrain 多能源园区低碳规划助手。

我可以帮您：
1. 📊 查询全国 10 万+ 园区信息
2. 📝 生成专业的低碳规划报告
3. 💡 提供减排措施建议
4. 📋 匹配相关政策支持

请告诉我您想查询哪个园区？`,
          timestamp: new Date(),
        },
      ])
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : '重置失败')
    }
  }, [])

  return {
    messages,
    isLoading,
    error,
    sendMessage,
    resetChat,
  }
}
