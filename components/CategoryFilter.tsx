'use client'

import { PinCategory, CATEGORIES } from '@/lib/types'

type Props = {
  activeCategories: Set<PinCategory>
  onToggle: (category: PinCategory) => void
}

export default function CategoryFilter({ activeCategories, onToggle }: Props) {
  return (
    <div className="absolute top-4 left-4 z-[1000] flex flex-col gap-2">
      {(Object.entries(CATEGORIES) as [PinCategory, typeof CATEGORIES[PinCategory]][]).map(([key, cat]) => {
        const isActive = activeCategories.has(key)
        return (
          <button
            key={key}
            onClick={() => onToggle(key)}
            className="flex items-center gap-2 px-3 py-2 rounded-lg shadow-md text-sm font-bold transition-all"
            style={{
              backgroundColor: isActive ? cat.color : '#e5e7eb',
              color: isActive ? '#fff' : '#6b7280',
              border: `2px solid ${isActive ? cat.color : '#d1d5db'}`,
            }}
          >
            <span>{cat.icon}</span>
            <span>{cat.label}</span>
          </button>
        )
      })}
    </div>
  )
}
