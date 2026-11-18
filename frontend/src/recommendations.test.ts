import { describe, expect, it } from 'vitest'
import { toRecommendations } from './recommendations'

describe('toRecommendations', () => {
  it('prefers structured items', () => {
    const items = [{ id: 'savings_rate.watch', severity: 'watch' as const, indicator: 'savings_rate', message: 'Save more' }]
    expect(toRecommendations({ recommendations: ['Save more'], recommendation_items: items })).toEqual(items)
  })

  it('wraps plain strings from older snapshots as info items', () => {
    expect(toRecommendations({ recommendations: ['Keep recording'] })).toEqual([
      { id: 'legacy-0', severity: 'info', indicator: null, message: 'Keep recording' },
    ])
  })

  it('handles missing data', () => {
    expect(toRecommendations(null)).toEqual([])
    expect(toRecommendations({ recommendation_items: [] })).toEqual([])
  })
})
