import { useState } from 'react'
import { X, Download, FileText, Loader2, CheckCircle } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { downloadPdf } from '../lib/api'

interface ReportViewerProps {
  scenarioId: string
  content: string
  onClose: () => void
}

export default function ReportViewer({ scenarioId, content, onClose }: ReportViewerProps) {
  const [isDownloading, setIsDownloading] = useState(false)
  const [downloadSuccess, setDownloadSuccess] = useState(false)

  const handleDownloadPdf = async () => {
    setIsDownloading(true)
    setDownloadSuccess(false)

    try {
      await downloadPdf(scenarioId)
      setDownloadSuccess(true)
      setTimeout(() => setDownloadSuccess(false), 3000)
    } catch (error) {
      alert(`下载失败: ${error instanceof Error ? error.message : '未知错误'}`)
    } finally {
      setIsDownloading(false)
    }
  }

  return (
    <div className="bg-white rounded-2xl shadow-2xl flex flex-col h-full overflow-hidden">
      {/* 头部 */}
      <div className="bg-gradient-to-r from-accent-500 to-primary-500 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-white/20 rounded-full flex items-center justify-center">
            <FileText className="w-6 h-6 text-white" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-white">报告预览</h2>
            <p className="text-xs text-white/80">{scenarioId}</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleDownloadPdf}
            disabled={isDownloading}
            className="flex items-center gap-2 px-4 py-2 bg-white text-primary-600 rounded-lg font-medium hover:bg-white/90 transition-colors disabled:opacity-50"
          >
            {isDownloading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                下载中...
              </>
            ) : downloadSuccess ? (
              <>
                <CheckCircle className="w-4 h-4 text-green-500" />
                下载成功
              </>
            ) : (
              <>
                <Download className="w-4 h-4" />
                下载 PDF
              </>
            )}
          </button>

          <button
            onClick={onClose}
            className="w-10 h-10 flex items-center justify-center bg-white/20 hover:bg-white/30 rounded-lg text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* 报告内容 */}
      <div className="flex-1 overflow-y-auto px-6 py-6">
        <div className="markdown-content prose prose-sm max-w-none">
          <ReactMarkdown>{content}</ReactMarkdown>
        </div>
      </div>

      {/* 底部操作栏 */}
      <div className="px-6 py-4 bg-gray-50 border-t flex items-center justify-between">
        <p className="text-sm text-gray-500">
          报告 ID: <span className="font-mono text-gray-700">{scenarioId}</span>
        </p>
        <div className="flex items-center gap-3">
          <button
            onClick={handleDownloadPdf}
            disabled={isDownloading}
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-primary-500 to-secondary-500 text-white rounded-lg font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            {isDownloading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                下载中...
              </>
            ) : (
              <>
                <Download className="w-4 h-4" />
                下载完整 PDF 报告
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
