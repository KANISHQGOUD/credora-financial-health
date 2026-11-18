type ValidationIssue = { loc?: Array<string | number>; msg?: string }

// FastAPI returns `detail` as a string for HTTP errors, but as a list of
// issues for request-validation (422) errors. Turn either into readable text.
export function errorMessage(detail: unknown, fallback: string): string {
  if (typeof detail === 'string' && detail.trim()) return detail
  if (Array.isArray(detail)) {
    const messages = detail
      .map((issue: ValidationIssue) => {
        const msg = (issue?.msg ?? '').replace(/^Value error, /, '')
        if (!msg) return ''
        const field = issue.loc?.filter((part) => part !== 'body').at(-1)
        if (typeof field !== 'string') return msg
        const label = field.replace(/_/g, ' ')
        return `${label.charAt(0).toUpperCase()}${label.slice(1)}: ${msg}`
      })
      .filter(Boolean)
    if (messages.length) return messages.join(' ')
  }
  return fallback
}
