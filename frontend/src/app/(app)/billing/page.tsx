'use client'

import { useCallback, useEffect, useState } from 'react'
import { getUsage } from '@/lib/api'
import { listSessions, removeSessionById, resolveSessionToken } from '@/lib/session'
import type { ActiveSession, UsageStats } from '@/types'

const DEVICE_LIMITS: Record<string, number> = {
  free: 1,
  starter: 1,
  enterprise: 5,
}

function lastSeenLabel(iso: string): string {
  const minsAgo = Math.round((Date.now() - new Date(iso).getTime()) / 60000)
  if (minsAgo < 2) return 'Active now'
  if (minsAgo < 60) return `${minsAgo} mins ago`
  const hours = Math.round(minsAgo / 60)
  if (hours < 24) return `${hours} hours ago`
  return `${Math.round(hours / 24)} days ago`
}

export default function BillingPage() {
  const [usage, setUsage] = useState<UsageStats | null>(null)
  const [sessions, setSessions] = useState<ActiveSession[]>([])
  const [currentToken, setCurrentToken] = useState<string | null>(null)

  const fetchSessions = useCallback(async () => {
    try {
      setSessions(await listSessions())
    } catch {
      setSessions([])
    }
  }, [])

  useEffect(() => {
    // All async: avoids a synchronous setState in the effect body, and lets a
    // fresh tab (empty sessionStorage) still resolve its own fingerprint so the
    // "This device" badge is correct.
    void (async () => {
      setCurrentToken(await resolveSessionToken())
      try {
        setUsage(await getUsage())
      } catch {
        setUsage(null)
      }
      await fetchSessions()
    })()
  }, [fetchSessions])

  const plan = usage?.plan ?? 'free'
  const isSingleDevicePlan = plan === 'free' || plan === 'starter'
  const deviceLimit = DEVICE_LIMITS[plan] ?? 1
  const atLimit = usage != null && usage.used_today >= usage.limit

  return (
    <div className="mx-auto max-w-3xl p-8">
      <h1 className="text-2xl font-semibold tracking-tight">Billing &amp; plan</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Manage your plan, usage and active devices.
      </p>

      {/* ---------------------------------------------------------- USAGE */}
      <div
        style={{
          background: '#FFFFFF',
          border: '1px solid #E8E2D0',
          borderRadius: '8px',
          padding: '32px',
          margin: '24px 0',
        }}
      >
        <p
          style={{
            fontFamily: 'Inter',
            fontSize: '11px',
            fontWeight: 500,
            color: 'rgba(45,58,31,0.4)',
            letterSpacing: '0.12em',
            textTransform: 'uppercase',
            marginBottom: '16px',
          }}
        >
          USAGE
        </p>
        {usage ? (
          <>
            <p style={{ fontFamily: 'Inter', fontSize: '14px', color: '#2D3A1F' }}>
              <strong style={{ fontWeight: 500 }}>
                {usage.used_today} / {usage.limit}
              </strong>{' '}
              AI actions used today
            </p>
            <p
              style={{
                fontFamily: 'Inter',
                fontSize: '12px',
                color: 'rgba(45,58,31,0.4)',
                marginTop: '4px',
                textTransform: 'capitalize',
              }}
            >
              {plan} plan
            </p>

            {atLimit && (
              <div
                role="status"
                style={{
                  background: '#FEF3C7',
                  borderLeft: '3px solid #B8A678',
                  borderRadius: '0 6px 6px 0',
                  padding: '14px 16px',
                  marginTop: '16px',
                }}
              >
                <p
                  style={{
                    fontFamily: 'Inter',
                    fontSize: '14px',
                    color: '#2D3A1F',
                    fontWeight: 500,
                    marginBottom: '6px',
                  }}
                >
                  Daily limit reached
                </p>
                <p
                  style={{
                    fontFamily: 'Inter',
                    fontSize: '13px',
                    color: '#2D3A1F',
                    opacity: 0.7,
                    lineHeight: 1.6,
                  }}
                >
                  You&apos;ve used all {usage.limit} AI actions for today. Your limit
                  resets at midnight UTC.
                  {isSingleDevicePlan && (
                    <>
                      {' '}
                      <a
                        href="mailto:hello@counselai.in?subject=Plan Upgrade"
                        style={{ color: '#B8A678', textDecoration: 'underline' }}
                      >
                        Upgrade for a higher limit →
                      </a>
                    </>
                  )}
                </p>
              </div>
            )}
          </>
        ) : (
          <p style={{ fontFamily: 'Inter', fontSize: '14px', color: 'rgba(45,58,31,0.4)' }}>
            Loading usage…
          </p>
        )}
      </div>

      {/* -------------------------------------------------- ACTIVE DEVICES */}
      <div
        style={{
          background: '#FFFFFF',
          border: '1px solid #E8E2D0',
          borderRadius: '8px',
          padding: '32px',
          marginBottom: '24px',
        }}
      >
        <p
          style={{
            fontFamily: 'Inter',
            fontSize: '11px',
            fontWeight: 500,
            color: 'rgba(45,58,31,0.4)',
            letterSpacing: '0.12em',
            textTransform: 'uppercase',
            marginBottom: '16px',
          }}
        >
          ACTIVE DEVICES
        </p>

        {sessions.length === 0 && (
          <p
            style={{
              fontFamily: 'Gloock',
              fontStyle: 'italic',
              fontSize: '16px',
              color: 'rgba(45,58,31,0.4)',
            }}
          >
            No active sessions found.
          </p>
        )}

        {sessions.map((s, i) => {
          const isCurrentDevice = currentToken !== null && s.session_token === currentToken
          return (
            <div
              key={s.id}
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '14px 0',
                borderBottom: i < sessions.length - 1 ? '1px solid #E8E2D0' : 'none',
              }}
            >
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span
                    style={{
                      fontFamily: 'Inter',
                      fontSize: '14px',
                      color: '#2D3A1F',
                      fontWeight: 500,
                    }}
                  >
                    {s.device_info ?? 'Unknown device'}
                  </span>
                  {isCurrentDevice && (
                    <span
                      style={{
                        fontFamily: 'Inter',
                        fontSize: '10px',
                        background: '#E8E2D0',
                        color: '#2D3A1F',
                        padding: '2px 8px',
                        borderRadius: '100px',
                        letterSpacing: '0.08em',
                        textTransform: 'uppercase',
                      }}
                    >
                      This device
                    </span>
                  )}
                </div>
                <p
                  style={{
                    fontFamily: 'Inter',
                    fontSize: '12px',
                    color: 'rgba(45,58,31,0.4)',
                    marginTop: '2px',
                  }}
                >
                  {lastSeenLabel(s.last_seen_at)}
                </p>
              </div>
              {!isCurrentDevice && (
                <button
                  onClick={async () => {
                    await removeSessionById(s.id)
                    void fetchSessions()
                  }}
                  style={{
                    fontFamily: 'Inter',
                    fontSize: '12px',
                    color: 'rgba(45,58,31,0.4)',
                    background: 'none',
                    border: 'none',
                    cursor: 'pointer',
                    textDecoration: 'underline',
                  }}
                >
                  Sign out
                </button>
              )}
            </div>
          )
        })}

        <p
          style={{
            fontFamily: 'Inter',
            fontSize: '12px',
            color: 'rgba(45,58,31,0.35)',
            marginTop: '16px',
          }}
        >
          {isSingleDevicePlan
            ? `Your plan allows ${deviceLimit} active device. Need more? `
            : `Your Enterprise plan allows ${deviceLimit} active devices. `}
          {isSingleDevicePlan && (
            <a
              href="mailto:hello@counselai.in?subject=Enterprise Plan"
              style={{ color: '#B8A678', textDecoration: 'underline' }}
            >
              Contact us for Enterprise →
            </a>
          )}
        </p>
      </div>
    </div>
  )
}
