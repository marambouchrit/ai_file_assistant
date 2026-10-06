import type { ChatMessage, ChatResponse, DocumentInfo } from './types'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000'

// Sends a request and returns the JSON body, or throws an Error with the API's message.
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(API_URL + path, init)
  } catch {
    throw new Error('Cannot reach the server. Is the API running?')
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    const detail = typeof body?.detail === 'string' ? body.detail : null
    throw new Error(detail ?? `Request failed (${response.status})`)
  }
  return response.json()
}

export function listDocuments(): Promise<DocumentInfo[]> {
  return request('/documents')
}

export function uploadFile(file: File): Promise<DocumentInfo> {
  const form = new FormData()
  form.append('file', file)
  return request('/upload', { method: 'POST', body: form })
}

export function sendMessage(message: string, history: ChatMessage[]): Promise<ChatResponse> {
  return request('/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      history: history.map(({ role, content }) => ({ role, content })),
    }),
  })
}
