const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1'

export type AuthUser = { id: string; email: string; role: 'borrower' | 'lender' | 'admin'; created_at: string }
export type AuthResponse = { access_token: string; token_type: string; user: AuthUser }
export type RecordKind = 'income' | 'expense' | 'savings' | 'debt' | 'reserve'
export type FinancialRecord = {
  id: string; kind: RecordKind; period_start: string; period_end: string; amount: number; currency: string
  category: string; source_label?: string | null; required_payment?: number | null
}
export type Indicator = { name: string; label: string; value: number | null; unit: string; status: string; explanation: string }
export type Assessment = {
  id: string; created_at: string; methodology_version: string; overall_category: string | null
  summary: string | null; indicators: Indicator[]; recommendations: string[]
}
export type DashboardData = {
  analysis: {
    overall_category: string; summary: string; indicators: Indicator[]; recommendations: string[]
    monthly: Array<{ month: string; income: number | null; expenses: number | null; savings: number | null; debt_balance: number | null; debt_payment: number | null; reserve: number | null }>
    reporting_months: number; is_synthetic: boolean
  }
  record_count: number; recent_records: FinancialRecord[]; latest_assessment: Assessment | null
}

type ValidationIssue = { loc?: Array<string | number>; msg?: string }

// FastAPI returns `detail` as a string for HTTP errors, but as a list of
// issues for request-validation (422) errors. Turn either into readable text.
function errorMessage(detail: unknown, fallback: string): string {
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

export async function authenticate(path: 'login' | 'register', email: string, password: string): Promise<AuthResponse> {
  const response = await fetch(`${API_URL}/auth/${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  const body = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(errorMessage(body.detail, 'Could not authenticate. Please try again.'))
  return body as AuthResponse
}

export async function getCurrentUser(token: string): Promise<AuthUser> {
  const response = await fetch(`${API_URL}/auth/me`, { headers: { Authorization: `Bearer ${token}` } })
  if (!response.ok) throw new Error('Session expired')
  return response.json() as Promise<AuthUser>
}

async function request<T>(token: string, path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}`, ...options.headers },
  })
  if (response.status === 204) return undefined as T
  const body = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(errorMessage(body.detail, 'The request could not be completed.'))
  return body as T
}

export const getDashboard = (token: string) => request<DashboardData>(token, '/dashboard')
export const listRecords = (token: string) => request<FinancialRecord[]>(token, '/financial-records')
export const addRecord = (token: string, kind: RecordKind, record: {
  period_start: string; period_end: string; amount: number; currency: 'INR'; category: string
  source_label: string; required_payment?: number | null
}) => request<FinancialRecord>(token, `/financial-records/${kind}`, { method: 'POST', body: JSON.stringify(record) })
export const deleteRecord = (token: string, kind: RecordKind, id: string) => request<void>(token, `/financial-records/${kind}/${id}`, { method: 'DELETE' })
export const createAssessment = (token: string) => request<Assessment>(token, '/assessments', { method: 'POST' })
