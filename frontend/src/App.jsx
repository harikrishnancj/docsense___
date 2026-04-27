import { useState } from 'react'
import Header from './components/Header'
import Sidebar from './components/Sidebar'
import InsightDashboard from './components/InsightDashboard'
import IntelligenceContext from './components/IntelligenceContext'
import StatusBar from './components/StatusBar'
import './App.css'

function App() {
  const [files, setFiles] = useState([])
  const [lastResults, setLastResults] = useState(null)
  const [isProcessing, setIsProcessing] = useState(false)

  const handleFileUpload = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      setFiles(Array.from(e.target.files))
    }
  }

  const handleReset = () => {
    setFiles([])
    setLastResults(null)
    setIsProcessing(false)
  }

  return (
    <div className="app-container">
      <Sidebar
        onFileUpload={handleFileUpload}
        onReset={handleReset}
        uploadedFiles={files}
      />
      <Header />

      <main className="main-area">
        <IntelligenceContext
          files={files}
          onNewResults={setLastResults}
          onProcessing={setIsProcessing}
        />
        <InsightDashboard lastResults={lastResults} />
      </main>

      <StatusBar />
    </div>
  )
}

export default App
