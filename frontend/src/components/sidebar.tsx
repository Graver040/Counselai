'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import { FileText, LayoutDashboard, PenLine, LogOut } from 'lucide-react'
import { createClient } from '@/lib/supabase/client'
import { removeSession } from '@/lib/session'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

const NAV = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/draft', label: 'Draft', icon: PenLine },
  { href: '/billing', label: 'Billing', icon: FileText },
]

export function Sidebar() {
  const pathname = usePathname()
  const router = useRouter()
  const [email, setEmail] = useState<string | null>(null)

  useEffect(() => {
    const supabase = createClient()
    supabase.auth.getUser().then(({ data }) => setEmail(data.user?.email ?? null))
  }, [])

  const logout = async () => {
    const supabase = createClient()
    // Release this device's slot before the token is invalidated, otherwise it
    // stays claimed until it goes stale 24h later.
    const { data } = await supabase.auth.getSession()
    if (data.session?.access_token) {
      await removeSession(data.session.access_token)
    }
    await supabase.auth.signOut()
    router.push('/login')
  }

  return (
    <aside className="flex h-screen w-60 flex-col border-r bg-muted/30">
      <div className="px-6 py-5 text-lg font-semibold tracking-tight">CounselAI</div>

      <nav className="flex-1 space-y-1 px-3">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = pathname.startsWith(href)
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                active
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:bg-muted hover:text-foreground'
              )}
            >
              <Icon className="h-4 w-4" />
              {label}
            </Link>
          )
        })}
      </nav>

      <div className="border-t p-3">
        {email && (
          <div className="mb-2 truncate px-3 text-xs text-muted-foreground" title={email}>
            {email}
          </div>
        )}
        <Button variant="ghost" size="sm" className="w-full justify-start" onClick={logout}>
          <LogOut className="mr-2 h-4 w-4" />
          Logout
        </Button>
      </div>
    </aside>
  )
}
