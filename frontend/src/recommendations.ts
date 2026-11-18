import type { Recommendation, Severity } from './api'

export const severityLabels: Record<Severity, string> = {
  attention: 'Needs attention',
  watch: 'Worth watching',
  info: 'More data',
  positive: 'Going well',
}

/**
 * Suggestions to show. Snapshots saved before suggestion severities existed only
 * have plain strings, so those are shown as neutral "info" items.
 */
export function toRecommendations(source?: { recommendations?: string[]; recommendation_items?: Recommendation[] } | null): Recommendation[] {
  if (!source) return []
  if (source.recommendation_items?.length) return source.recommendation_items
  return (source.recommendations ?? []).map((message, index) => ({ id: `legacy-${index}`, severity: 'info', indicator: null, message }))
}
