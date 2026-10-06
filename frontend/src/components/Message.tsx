import type { ChatMessage } from '../types'

interface Props {
  message: ChatMessage
}

export default function Message({ message }: Props) {
  if (message.role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] whitespace-pre-wrap rounded-2xl rounded-br-sm bg-indigo-600 px-4 py-2 text-sm text-white">
          {message.content}
        </div>
      </div>
    )
  }

  const toolCalls = message.toolCalls ?? []
  const sources = message.sources ?? []

  return (
    <div className="flex justify-start">
      <div className="max-w-[80%] rounded-2xl rounded-bl-sm border border-slate-200 bg-white px-4 py-2 text-sm text-slate-800">
        <p className="whitespace-pre-wrap leading-relaxed">{message.content}</p>

        {(toolCalls.length > 0 || sources.length > 0) && (
          <details className="mt-3 border-t border-slate-100 pt-2 text-xs text-slate-500">
            <summary className="cursor-pointer select-none font-medium hover:text-slate-700">
              Tools used ({toolCalls.length}) · Sources ({sources.length})
            </summary>

            {toolCalls.length > 0 && (
              <ul className="mt-2 space-y-1">
                {toolCalls.map((call, index) => (
                  <li key={index} className="break-all rounded bg-slate-50 px-2 py-1 font-mono">
                    {call.name}({JSON.stringify(call.arguments)})
                  </li>
                ))}
              </ul>
            )}

            {sources.length > 0 && (
              <ul className="mt-2 space-y-2">
                {sources.map((source, index) => (
                  <li key={index} className="rounded border border-slate-100 px-2 py-1">
                    <p className="font-medium text-slate-700">
                      {source.filename}
                      {source.chunk_index !== null && ` · passage ${source.chunk_index}`}
                      {source.score !== null && ` · score ${source.score.toFixed(2)}`}
                    </p>
                    <p className="mt-0.5 line-clamp-3 whitespace-pre-wrap">{source.text}</p>
                  </li>
                ))}
              </ul>
            )}
          </details>
        )}
      </div>
    </div>
  )
}
