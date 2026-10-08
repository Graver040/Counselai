// Device/session limiting: claim and release a device slot on the backend.
//
// The backend identifies a device by a fingerprint — the last 32 chars of the
// Supabase JWT — never the whole token.

import { createClient } from '@/lib/supabase/client'
import { api } from '@/lib/api'
import type { ActiveSession } from '@/types'

const V1 = '/api/v1'
const STORAGE_KEY = 'session_token'

/** Stable per-session fingerprint derived from the access token. */
export function getTokenFingerprint(accessToken: string): string {
  return accessToken.slice(-32)
}

/** Best-effort device label from the user agent, shown in the device list. */
export function getDeviceInfo(): string {
  if (typeof window === 'undefined') return 'Server'
  const ua = navigator.userAgent
  if (/iPhone/.test(ua)) return 'Safari on iPhone'
  if (/iPad/.test(ua)) return 'Safari on iPad'
  if (/Android.*Chrome/.test(ua)) return 'Chrome on Android'
  if (/Android/.test(ua)) return 'Browser on Android'
  if (/Mac.*Chrome/.test(ua)) return 'Chrome on Mac'
  if (/Mac.*Safari/.test(ua)) return 'Safari on Mac'
  if (/Windows.*Chrome/.test(ua)) return 'Chrome on Windows'
  if (/Windows.*Firefox/.test(ua)) return 'Firefox on Windows'
  if (/Windows/.test(ua)) return 'Browser on Windows'
  if (/Linux/.test(ua)) return 'Browser on Linux'
  return 'Unknown device'
}

export function getStoredSessionToken(): string | null {
  if (typeof window === 'undefined') return null
  return sessionStorage.getItem(STORAGE_KEY)
}

/**
 * Resolve this tab's fingerprint, re-deriving it from the live Supabase session
 * when sessionStorage is empty (new tab, or the app reopened after a close).
 * Without this the heartbeat would silently stop in those cases.
 */
export async function resolveSessionToken(): Promise<string | null> {
  const stored = getStoredSessionToken()
  if (stored) return stored

  const supabase = createClient()
  const { data } = await supabase.auth.getSession()
  const accessToken = data.session?.access_token
  if (!accessToken) return null

  const fingerprint = getTokenFingerprint(accessToken)
  sessionStorage.setItem(STORAGE_KEY, fingerprint)
  return fingerprint
}

/**
 * Claim a device slot after sign-in.
 * Returns null on success, or a user-facing message when the plan's device
 * limit is already reached (the caller should sign the user back out).
 */
export async function registerSession(accessToken: string): Promise<string | null> {
  const fingerprint = getTokenFingerprint(accessToken)
  try {
    await api.post(`${V1}/sessions/register`, {
      session_token: fingerprint,
      device_info: getDeviceInfo(),
    })
    sessionStorage.setItem(STORAGE_KEY, fingerprint)
    return null
  } catch (err: unknown) {
    const detail = (
      err as { response?: { data?: { detail?: { code?: string; message?: string } } } }
    )?.response?.data?.detail
    if (detail?.code === 'DEVICE_LIMIT_REACHED') {
      return detail.message ?? 'This account is already active on another device.'
    }
    return 'Could not register session. Please try again.'
  }
}

/** Devices currently holding a session slot for this user. */
export async function listSessions(): Promise<ActiveSession[]> {
  const { data } = await api.get<ActiveSession[]>(`${V1}/sessions/list`)
  return data
}

/** Sign a specific device out remotely (from the billing page). */
export async function removeSessionById(sessionId: string): Promise<void> {
  await api.delete(`${V1}/sessions/remove/${sessionId}`)
}

/** Release this device's slot on explicit sign-out. */
export async function removeSession(accessToken: string): Promise<void> {
  try {
    await api.delete(`${V1}/sessions/logout`, {
      data: {
        session_token: getTokenFingerprint(accessToken),
        device_info: getDeviceInfo(),
      },
    })
  } catch {
    // Sign-out must never be blocked by a failed cleanup call.
  }
  if (typeof window !== 'undefined') sessionStorage.removeItem(STORAGE_KEY)
}
