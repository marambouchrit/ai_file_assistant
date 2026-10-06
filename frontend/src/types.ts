// These interfaces mirror the Pydantic response models in app/api.py.

export interface DocumentInfo {
  doc_id: string
  filename: string
  type: string
  size_bytes: number
  pages: number | null
  uploaded_at: string
  chunk_count: number
}

export interface ToolCall {
  name: string
  arguments: Record<string, unknown>
}

export interface Source {
  doc_id: string
  filename: string
  chunk_index: number | null
  score: number | null
  text: string
}

export interface ChatResponse {
  answer: string
  tool_calls: ToolCall[]
  sources: Source[]
}

// One message shown in the chat. Tool calls and sources only exist on assistant messages.
export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  toolCalls?: ToolCall[]
  sources?: Source[]
}
