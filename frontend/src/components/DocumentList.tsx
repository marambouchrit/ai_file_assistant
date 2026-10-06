import type { DocumentInfo } from '../types'

interface Props {
  documents: DocumentInfo[]
  error: string | null
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export default function DocumentList({ documents, error }: Props) {
  if (error) return <p className="text-sm text-red-600">{error}</p>
  if (documents.length === 0) {
    return <p className="text-sm text-slate-400">No documents yet.</p>
  }

  return (
    <ul className="space-y-2">
      {documents.map((doc) => (
        <li key={doc.doc_id} className="rounded-lg border border-slate-200 bg-white px-3 py-2">
          <div className="flex items-center gap-2">
            <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-slate-500">
              {doc.type}
            </span>
            <span className="truncate text-sm font-medium text-slate-800" title={doc.filename}>
              {doc.filename}
            </span>
          </div>
          <p className="mt-1 text-xs text-slate-400">
            {formatSize(doc.size_bytes)}
            {doc.pages !== null && ` · ${doc.pages} ${doc.pages === 1 ? 'page' : 'pages'}`}
            {` · ${doc.chunk_count} ${doc.chunk_count === 1 ? 'chunk' : 'chunks'}`}
          </p>
        </li>
      ))}
    </ul>
  )
}
