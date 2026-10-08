import { Sidebar } from '@/components/sidebar'
import { SessionHeartbeat } from '@/components/session-heartbeat'

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen">
      {/* Client-only: keeps this device's session slot alive. Renders nothing. */}
      <SessionHeartbeat />
      <Sidebar />
      <main className="flex-1 overflow-y-auto">{children}</main>
    </div>
  )
}
