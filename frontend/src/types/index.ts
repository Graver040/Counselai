// Shared domain types for the CounselAI frontend.
// NOTE: some backend field names differ (filename↔name, ocr_page_count↔ocr_used);
// api.ts maps between them so components can use these shapes directly.

export interface Document {
  id: string
  name: string
  status: 'processing' | 'ready' | 'failed'
  page_count: number | null
  chunk_count: number | null
  ocr_used: boolean
  created_at: string
  workspace_id: string
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  citations?: number[]
  created_at: string
}

export type Plan = 'free' | 'starter' | 'enterprise'

export interface UsageStats {
  used_today: number
  limit: number
  plan: Plan
  plan_expires_at?: string
}

/** A signed-in device, from GET /sessions/list. */
export interface ActiveSession {
  id: string
  device_info: string | null
  last_seen_at: string
  session_token: string
}

export type DraftType = 'cbdt_notice' | 'gst_notice' | 'legal_letter' | 'client_memo'

export interface DraftResponse {
  draft: string
  citations: number[]
}

export interface AskResponse {
  answer: string
  citations: number[]
}
