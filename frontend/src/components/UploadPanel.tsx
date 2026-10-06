import { useRef, useState } from 'react'
import { uploadFile } from '../api'

interface Props {
  onUploaded: () => void
}

export default function UploadPanel({ onUploaded }: Props) {
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  async function handleChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    if (!file) return
    setUploading(true)
    setError(null)
    try {
      await uploadFile(file)
      onUploaded()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setUploading(false)
      // reset so the same file can be selected again
      if (inputRef.current) inputRef.current.value = ''
    }
  }

  return (
    <div>
      <label
        className={`block rounded-lg border-2 border-dashed px-4 py-5 text-center text-sm transition ${
          uploading
            ? 'cursor-wait border-slate-200 text-slate-400'
            : 'cursor-pointer border-slate-300 text-slate-600 hover:border-indigo-400 hover:bg-indigo-50'
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.docx,.txt"
          className="hidden"
          disabled={uploading}
          onChange={handleChange}
        />
        <span className="font-medium">{uploading ? 'Indexing…' : 'Upload a document'}</span>
        <span className="mt-1 block text-xs text-slate-400">PDF, DOCX or TXT</span>
      </label>
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
    </div>
  )
}
