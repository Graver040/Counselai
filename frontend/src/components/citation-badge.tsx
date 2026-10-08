'use client'

import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

interface CitationBadgeProps {
  page: number
  onPageJump?: (page: number) => void
}

export function CitationBadge({ page, onPageJump }: CitationBadgeProps) {
  if (onPageJump) {
    return (
      <Badge
        role="button"
        tabIndex={0}
        onClick={() => onPageJump(page)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') onPageJump(page)
        }}
        className={cn(
          'cursor-pointer bg-blue-600 text-white hover:bg-blue-700',
          'focus-visible:ring-2 focus-visible:ring-blue-400'
        )}
      >
        Page {page}
      </Badge>
    )
  }

  return (
    <Badge variant="secondary" className="bg-muted text-muted-foreground">
      Page {page}
    </Badge>
  )
}
