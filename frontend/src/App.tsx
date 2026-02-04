import { useState } from 'react'
import Header from './components/Header'
import Chat from './components/Chat'
import ReportViewer from './components/ReportViewer'

interface Report {
  scenarioId: string
  content: string
}

function App() {
  const [currentReport, setCurrentReport] = useState<Report | null>(null)
  const [showReport, setShowReport] = useState(false)

  const handleReportGenerated = (scenarioId: string, content: string) => {
    setCurrentReport({ scenarioId, content })
    setShowReport(true)
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-500 to-secondary-500">
      <Header />

      <main className="container mx-auto px-4 py-6">
        <div className="flex gap-6 h-[calc(100vh-120px)]">
          {/* 聊天区域 */}
          <div className={`transition-all duration-300 ${showReport ? 'w-1/2' : 'w-full max-w-4xl mx-auto'}`}>
            <Chat onReportGenerated={handleReportGenerated} />
          </div>

          {/* 报告查看区域 */}
          {showReport && currentReport && (
            <div className="w-1/2 animate-fade-in">
              <ReportViewer
                scenarioId={currentReport.scenarioId}
                content={currentReport.content}
                onClose={() => setShowReport(false)}
              />
            </div>
          )}
        </div>
      </main>
    </div>
  )
}

export default App
