import { createServerClient } from '@supabase/ssr'
import { cookies } from 'next/headers'

// Next 16: cookies() is async, so this factory is async too.
// Await it in server components / route handlers: `const supabase = await createClient()`.
export const createClient = async () => {
  const cookieStore = await cookies()
  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll: () => cookieStore.getAll(),
        setAll: (cookiesToSet) => {
          try {
            cookiesToSet.forEach(({ name, value, options }) =>
              cookieStore.set(name, value, options)
            )
          } catch {
            // called from a Server Component — safe to ignore; middleware refreshes the session
          }
        },
      },
    }
  )
}
