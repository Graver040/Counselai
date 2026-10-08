'use client'

import { useSessionHeartbeat } from '@/hooks/useSessionHeartbeat'

/**
 * Renders nothing — exists so the app layout can stay a Server Component while
 * still running the client-side session heartbeat.
 */
export function SessionHeartbeat() {
  useSessionHeartbeat()
  return null
}
