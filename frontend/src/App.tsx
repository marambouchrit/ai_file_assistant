import { useEffect, useState } from 'react'
import { listDocuments } from './api'
import Chat from './components/Chat'
import DocumentList from './components/DocumentList'
import UploadPanel from './components/UploadPanel'
import type { DocumentInfo } from './types'

export default function App() {
  const [documents, setDocuments] = useState<DocumentInfo[]>([])
  const [error, setError] = useState<string | null>(null)

  function refreshDocuments() {
    listDocuments()
      .then((docs) => {
        setDocuments(docs)
        setError(null)
      })
      .catch((err: Error) => setError(err.message))
  }

  // load the list once when the page opens
  useEffect(refreshDocuments, [])

  return (
    <div className="flex h-full bg-slate-50 text-slate-900">
      <aside className="flex w-80 shrink-0 flex-col gap-5 overflow-y-auto border-r border-slate-200 bg-slate-100 p-5">
        <div>
          <h1 className="text-lg font-semibold">AI File Assistant</h1>
          <p className="text-xs text-slate-500">Chat with your documents</p>
        </div>
        <UploadPanel onUploaded={refreshDocuments} />
        <div>
          <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
            Documents ({documents.length})
          </h2>
          <DocumentList documents={documents} error={error} />
        </div>
      </aside>
      <main className="min-w-0 flex-1">
        <Chat />
      </main>
    </div>
  )
}
