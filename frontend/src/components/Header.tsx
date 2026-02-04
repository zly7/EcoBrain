import { Leaf, Github } from 'lucide-react'

export default function Header() {
  return (
    <header className="bg-white/10 backdrop-blur-sm border-b border-white/20">
      <div className="container mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-white rounded-xl flex items-center justify-center shadow-lg">
              <Leaf className="w-6 h-6 text-primary-500" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white">EcoBrain</h1>
              <p className="text-xs text-white/80">多能源园区低碳规划系统</p>
            </div>
          </div>

          <nav className="flex items-center gap-4">
            <a
              href="https://github.com"
              target="_blank"
              rel="noopener noreferrer"
              className="text-white/80 hover:text-white transition-colors"
            >
              <Github className="w-5 h-5" />
            </a>
          </nav>
        </div>
      </div>
    </header>
  )
}
