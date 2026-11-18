import { errorMessage } from './errors'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1'

export type AuthUser = { id: string; email: string; role: 'borrower' | 'lender' | 'admin'; created_at: string; is_demo?: boolean }
export type AuthResponse = { access_token: string; token_type: string; user: AuthUser }
export type RecordKind = 'income' | 'expense' | 'savings' | 'debt' | 'reserve'
export type FinancialRecord = {
  id: string; kind: RecordKind; period_start: string; period_end: string; amount: number; currency: string
  category: string; source_label?: string | null; required_payment?: number | null; is_sample?: boolean
}
export type Indicator = { name: string; label: string; value: number | null; unit: string; status: string; explanation: string }
export type Severity = 'attention' | 'watch' | 'info' | 'positive'
export type Recommendation = { id: string; severity: Severity; indicator: string | null; message: string }
export type Assessment = {
  id: string; created_at: string; methodology_version: string; overall_category: string | null
  summary: string | null; indicators: Indicator[]; recommendations: string[]
  recommendation_items?: Recommendation[]; is_synthetic?: boolean
}
export type DashboardData = {
  analysis: {
    overall_category: string; summary: string; indicators: Indicator[]; recommendations: string[]
    recommendation_items: Recommendation[]; methodology_version: string
    monthly: Array<{ month: string; income: number | null; expenses: number | null; savings: number | null; debt_balance: number | null; debt_payment: number | null; reserve: number | null }>
    reporting_months: number; is_synthetic: boolean
  }
  record_count: number; recent_records: FinancialRecord[]; latest_assessment: Assessment | null
}
export type PersonaKey = 'steady' | 'freelancer' | 'stretched'
export type Persona = { key: PersonaKey; label: string; description: string }
export type PersonaInfo = { demo_logins: boolean; personas: Persona[] }

/** Thrown when the saved login is no longer accepted, so the app can sign out and say why. */
export class SessionExpiredError extends Error {
  constructor() {
    super('Your session has expired. Please sign in again.')
    this.name = 'SessionExpiredError'
  }
}

async function post<T>(path: string, body: unknown, fallback: string): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  const data = await response.json().catch(() => ({}))
  if (response.status === 429) throw new Error('Too many attempts. Please wait a minute and try again.')
  if (!response.ok) throw new Error(errorMessage(data.detail, fallback))
  return data as T
}

export const authenticate = (path: 'login' | 'register', email: string, password: string) =>
  post<AuthResponse>(`/auth/${path}`, { email, password }, 'Could not authenticate. Please try again.')

export const demoLogin = (persona: PersonaKey) =>
  post<AuthResponse>(`/auth/demo/${persona}`, undefined, 'The demo account is not available right now.')

export async function getPersonas(): Promise<PersonaInfo> {
  const response = await fetch(`${API_URL}/demo/personas`)
  if (!response.ok) throw new Error('Could not load demo options.')
  return response.json() as Promise<PersonaInfo>
}

export async function getCurrentUser(token: string): Promise<AuthUser> {
  const response = await fetch(`${API_URL}/auth/me`, { headers: { Authorization: `Bearer ${token}` } })
  if (response.status === 401) throw new SessionExpiredError()
  if (!response.ok) throw new Error('Could not load your account.')
  return response.json() as Promise<AuthUser>
}

async function request<T>(token: string, path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}`, ...options.headers },
  })
  if (response.status === 401) throw new SessionExpiredError()
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
export const loadSampleData = (token: string, persona: PersonaKey) =>
  request<{ run_id: string; persona: PersonaKey }>(token, '/demo/sample-data', { method: 'POST', body: JSON.stringify({ persona }) })
export const clearSampleData = (token: string) => request<void>(token, '/demo/sample-data', { method: 'DELETE' })
