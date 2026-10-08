'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { createClient } from '@/lib/supabase/client'
import { registerSession } from '@/lib/session'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

export default function LoginPage() {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  // Kept separate from `error`: this one is an upsell, not a failure.
  const [deviceError, setDeviceError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    setDeviceError('')

    const supabase = createClient()
    const { data, error: signInError } = await supabase.auth.signInWithPassword({
      email,
      password,
    })

    if (signInError) {
      setError(signInError.message)
      setLoading(false)
      return
    }

    const accessToken = data.session?.access_token
    if (!accessToken) {
      setError('Could not start a session. Please try again.')
      setLoading(false)
      return
    }

    // Claim a device slot — this is what enforces the plan's device limit.
    const sessionError = await registerSession(accessToken)

    if (sessionError) {
      // Undo the sign-in so this device is not left authenticated.
      await supabase.auth.signOut()
      setDeviceError(sessionError)
      setLoading(false)
      return
    }

    router.push('/dashboard')
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-6">
      <div className="w-full max-w-sm">
        <h1 className="text-2xl font-semibold tracking-tight">Sign in to CounselAI</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Answer tax &amp; legal notices from your own documents.
        </p>

        <form onSubmit={handleSubmit} className="mt-8 space-y-4">
          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@firm.com"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
            />
          </div>

          {error && (
            <p className="text-sm text-destructive" role="alert">
              {error}
            </p>
          )}

          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? 'Signing in…' : 'Sign in'}
          </Button>
        </form>

        {deviceError && (
          <div
            role="alert"
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
              Account active on another device
            </p>
            <p
              style={{
                fontFamily: 'Inter',
                fontSize: '13px',
                color: '#2D3A1F',
                opacity: 0.7,
                lineHeight: 1.6,
                marginBottom: '10px',
              }}
            >
              {deviceError} Sign out on your other device first, or upgrade to
              Enterprise for 5 simultaneous users.
            </p>
            <a
              href="mailto:hello@counselai.in?subject=Enterprise Plan Enquiry"
              style={{
                fontFamily: 'Gloock',
                fontStyle: 'italic',
                fontSize: '14px',
                color: '#B8A678',
              }}
            >
              Contact us about Enterprise →
            </a>
          </div>
        )}

        <p className="mt-6 text-sm text-muted-foreground">
          Don&apos;t have an account?{' '}
          <Link href="/signup" className="font-medium underline">
            Sign up
          </Link>
        </p>
      </div>
    </div>
  )
}
