import axios from 'axios'
import { toast } from 'sonner'
import { createClient } from '@/lib/supabase/client'
import type { AskResponse, Document, DraftResponse, DraftType, UsageStats } from '@/types'

const API_URL = process.env.NEXT_PUBLIC_API_URL!
const V1 = '/api/v1'

export const api = axios.create({ baseURL: API_URL })

// Attach the current Supabase JWT to every request.
api.interceptors.request.use(async (config) => {
  const supabase = createClient()
  const { data } = await supabase.auth.getSession()
  const token = data.session?.access_token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Structured error payloads the backend returns as `detail` objects.
export type ApiErrorCode =
  | 'DAILY_LIMIT_REACHED'
  | 'RATE_LIMITED'
  | 'DEVICE_LIMIT_REACHED'

export interface ApiErrorDetail {
  code?: ApiErrorCode
  message?: string
  used_today?: number
  limit?: number
  plan?: string
}

/** Pull the backend's structured `detail` off a rejected request, if present. */
export function getApiErrorDetail(error: unknown): ApiErrorDetail | null {
  const detail = (error as { response?: { data?: { detail?: unknown } } })?.response
    ?.data?.detail
  return detail && typeof detail === 'object' ? (detail as ApiErrorDetail) : null
}

/** True when the request failed because the workspace is out of daily actions. */
export function isDailyLimitError(error: unknown): boolean {
  return getApiErrorDetail(error)?.code === 'DAILY_LIMIT_REACHED'
}

// On 401 bounce to login; on 429 surface why (quota vs. burst) instead of
// letting it fail as a generic network error.
api.interceptors.response.use(
  (res) => res,
  (error) => {
    const status = error?.response?.status
    if (typeof window !== 'undefined') {
      if (status === 401) {
        window.location.href = '/login'
      } else if (status === 429) {
        const detail = getApiErrorDetail(error)
        if (detail?.code === 'DAILY_LIMIT_REACHED') {
          toast.error('Daily limit reached', {
            description:
              detail.message ??
              `You've used all ${detail.limit ?? ''} AI actions for today.`,
          })
        } else {
          toast.error('Slow down a moment', {
            description:
              detail?.message ?? 'Too many requests in a short time. Try again shortly.',
          })
        }
      }
    }
    return Promise.reject(error)
  }
)

// The backend returns citations as objects ({document_id, filename, page}).
// The UI works with page numbers, so collapse to a de-duplicated number[].
type RawCitation = { document_id: string; filename: string; page: number }
const toPages = (citations: RawCitation[] = []): number[] =>
  Array.from(new Set(citations.map((c) => c.page))).sort((a, b) => a - b)

// Backend document shape -> frontend Document shape.
type RawDocument = {
  id: string
  filename: string
  status: Document['status']
  page_count: number | null
  chunk_count?: number | null
  ocr_page_count?: number | null
  created_at: string
  workspace_id?: string
}
const toDocument = (d: RawDocument): Document => ({
  id: d.id,
  name: d.filename,
  status: d.status,
  page_count: d.page_count,
  chunk_count: d.chunk_count ?? null,
  ocr_used: (d.ocr_page_count ?? 0) > 0,
  created_at: d.created_at,
  workspace_id: d.workspace_id ?? '',
})

// ---- typed helpers -------------------------------------------------------

export async function getDocuments(): Promise<Document[]> {
  const { data } = await api.get<RawDocument[]>(`${V1}/documents`)
  return data.map(toDocument)
}

export async function uploadDocument(file: File): Promise<{ id: string; status: string }> {
  const form = new FormData()
  form.append('file', file)
  const { data } = await api.post(`${V1}/documents`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function deleteDocument(id: string): Promise<void> {
  await api.delete(`${V1}/documents/${id}`)
}

export async function askQuestion(docId: string, question: string): Promise<AskResponse> {
  const { data } = await api.post(`${V1}/ask`, {
    question,
    document_ids: [docId],
  })
  return { answer: data.answer ?? '', citations: toPages(data.citations) }
}

export async function generateDraft(
  docId: string,
  instructions: string,
  draftType: DraftType
): Promise<DraftResponse> {
  const { data } = await api.post(`${V1}/draft`, {
    instruction: instructions,
    draft_type: draftType,
    document_ids: [docId],
  })
  return { draft: data.draft ?? '', citations: toPages(data.citations) }
}

// TODO(backend): no GET /usage endpoint exists yet — add one that reads usage_logs.
export async function getUsage(): Promise<UsageStats> {
  const { data } = await api.get<UsageStats>(`${V1}/usage`)
  return data
}

// ---- streaming -----------------------------------------------------------
// axios can't read a streaming body, so use native fetch + ReadableStream.
// TODO(backend): expects an SSE endpoint POST /api/v1/ask/stream emitting
// `event: token|citations|done` with `data:` payloads. Not built yet.
export async function streamAsk(
  docId: string,
  question: string,
  onChunk: (text: string) => void,
  onCitations: (citations: number[]) => void,
  onDone: () => void,
  onError: (err: unknown) => void
): Promise<void> {
  try {
    const supabase = createClient()
    const { data } = await supabase.auth.getSession()
    const token = data.session?.access_token

    const res = await fetch(`${API_URL}${V1}/ask/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ question, document_ids: [docId] }),
    })

    if (!res.ok || !res.body) {
      throw new Error(`stream failed: ${res.status}`)
    }

    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })

      // SSE frames are separated by a blank line.
      const frames = buffer.split('\n\n')
      buffer = frames.pop() ?? ''

      for (const frame of frames) {
        const eventMatch = frame.match(/^event:\s*(.+)$/m)
        const dataMatch = frame.match(/^data:\s*(.+)$/m)
        if (!dataMatch) continue
        const event = eventMatch?.[1]?.trim() ?? 'token'
        const payload = dataMatch[1].trim()

        if (event === 'token') {
          // tokens are JSON-encoded server-side so newlines stay SSE-safe
          try {
            onChunk(JSON.parse(payload) as string)
          } catch {
            onChunk(payload)
          }
        } else if (event === 'citations') {
          try {
            onCitations(JSON.parse(payload) as number[])
          } catch {
            /* ignore malformed citation frame */
          }
        } else if (event === 'done') {
          onDone()
          return
        }
      }
    }
    onDone()
  } catch (err) {
    onError(err)
  }
}
