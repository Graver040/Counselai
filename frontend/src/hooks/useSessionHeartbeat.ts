'use client'

import { useEffect } from 'react'
import { api } from '@/lib/api'
import { getDeviceInfo, resolveSessionToken } from '@/lib/session'

const V1 = '/api/v1'
const INTERVAL_MS = 5 * 60 * 1000 // 5 minutes

/**
 * Keeps this device's session slot alive while the app is open.
 * A session with no heartbeat for 24h is treated as stale and freed.
 */
export function useSessionHeartbeat() {
  useEffect(() => {
    let cancelled = false
    let interval: ReturnType<typeof setInterval> | undefined

    const ping = async (token: string) => {
      try {
        await api.post(`${V1}/sessions/heartbeat`, {
          session_token: token,
          device_info: getDeviceInfo(),
        })
      } catch {
        // A missed heartbeat is not fatal — the next tick retries.
      }
    }

    void (async () => {
      const token = await resolveSessionToken()
      if (!token || cancelled) return
      await ping(token)
      if (cancelled) return
      interval = setInterval(() => void ping(token), INTERVAL_MS)
    })()

    return () => {
      cancelled = true
      if (interval) clearInterval(interval)
    }
  }, [])
}
