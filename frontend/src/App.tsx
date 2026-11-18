import { useEffect, useState, type FormEvent } from 'react'
import type { ReactNode } from 'react'
import {
  Activity, ArrowDownRight, ArrowRight, ArrowUpRight, BadgeCheck, Banknote, ChartNoAxesCombined,
  CircleHelp, Clock3, Eye, Fingerprint, Info, Landmark, Plus, ShieldCheck, Sparkles, ThumbsUp, Trash2, TriangleAlert, Wallet,
} from 'lucide-react'
import {
  addRecord, authenticate, createAssessment, deleteRecord, getCurrentUser, getDashboard,
  listRecords, type AuthUser, type DashboardData, type FinancialRecord,
  type Indicator, type Recommendation, type RecordKind, type Severity,
} from './api'
import { severityLabels, toRecommendations } from './recommendations'
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

type AuthMode = 'login' | 'register'
const TOKEN_KEY = 'credora_access_token'
const labels: Record<RecordKind, string> = { income: 'Income', expense: 'Expense', savings: 'Savings contribution', debt: 'Debt', reserve: 'Liquid reserves' }
const categories: Record<RecordKind, string[]> = {
  income: ['Salary', 'Freelance', 'Business', 'Other income'],
  expense: ['Housing', 'Food', 'Transport', 'Utilities', 'Healthcare', 'Education', 'Other expense'],
  savings: ['Emergency fund', 'Recurring deposit', 'Investment contribution', 'Other savings'],
  debt: ['Home loan', 'Personal loan', 'Credit card', 'Education loan', 'Other debt'],
  reserve: ['Liquid reserves'],
}

function localMonth() {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
}

function monthBounds(value: string) {
  const [year, month] = value.split('-').map(Number)
  const start = `${year}-${String(month).padStart(2, '0')}-01`
  const last = new Date(year, month, 0).getDate()
  return { period_start: start, period_end: `${year}-${String(month).padStart(2, '0')}-${String(last).padStart(2, '0')}` }
}

function inr(value: number | null | undefined) {
  if (value === null || value === undefined) return '—'
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(value)
}

function displayIndicator(indicator: Indicator) {
  if (indicator.value === null) return 'Not enough data'
  if (indicator.unit === 'ratio' || indicator.unit === 'coefficient of variation' || indicator.unit === 'heuristic ratio') return `${(indicator.value * 100).toFixed(1)}%`
  if (indicator.unit === 'months of reported expenses') return `${indicator.value.toFixed(1)} months`
  if (indicator.unit.startsWith('INR')) return inr(indicator.value)
  return indicator.value.toLocaleString('en-IN')
}

function App() {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [mode, setMode] = useState<AuthMode>('register')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [dashboard, setDashboard] = useState<DashboardData | null>(null)
  const [records, setRecords] = useState<FinancialRecord[]>([])
  const [loading, setLoading] = useState(false)
  const [actionError, setActionError] = useState('')
  const [actionBusy, setActionBusy] = useState(false)

  useEffect(() => {
    const token = localStorage.getItem(TOKEN_KEY)
    if (!token) return
    getCurrentUser(token).then(setUser).catch(() => localStorage.removeItem(TOKEN_KEY))
  }, [])

  useEffect(() => {
    if (!user) return
    let active = true
    setLoading(true)
    const token = localStorage.getItem(TOKEN_KEY)
    if (!token) return
    Promise.all([getDashboard(token), listRecords(token)])
      .then(([nextDashboard, nextRecords]) => {
        if (!active) return
        setDashboard(nextDashboard)
        setRecords(nextRecords)
      })
      .catch(problem => {
        if (active) setActionError(problem instanceof Error ? problem.message : 'Could not load your financial profile.')
      })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [user])

  async function refresh() {
    const token = localStorage.getItem(TOKEN_KEY)
    if (!token) return
    const [nextDashboard, nextRecords] = await Promise.all([getDashboard(token), listRecords(token)])
    setDashboard(nextDashboard)
    setRecords(nextRecords)
  }

  async function submitAuth(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      const result = await authenticate(mode, email, password)
      localStorage.setItem(TOKEN_KEY, result.access_token)
      setDashboard(null)
      setRecords([])
      setUser(result.user)
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : 'Something went wrong.')
    } finally {
      setBusy(false)
    }
  }

  function signOut() {
    localStorage.removeItem(TOKEN_KEY)
    setUser(null)
    setDashboard(null)
    setRecords([])
    setPassword('')
    setActionError('')
  }

  async function generateAssessment() {
    const token = localStorage.getItem(TOKEN_KEY)
    if (!token) return
    setActionBusy(true)
    setActionError('')
    try {
      await createAssessment(token)
      await refresh()
    } catch (problem) {
      setActionError(problem instanceof Error ? problem.message : 'Could not save the assessment.')
    } finally {
      setActionBusy(false)
    }
  }

  async function saveRecord(kind: RecordKind, value: { month: string; amount: number; category: string; source: string; payment: number | null }) {
    const token = localStorage.getItem(TOKEN_KEY)
    if (!token) return
    setActionBusy(true)
    setActionError('')
    try {
      await addRecord(token, kind, {
        ...monthBounds(value.month), amount: value.amount, currency: 'INR', category: value.category,
        source_label: value.source, ...(kind === 'debt' ? { required_payment: value.payment } : {}),
      })
      await refresh()
    } catch (problem) {
      setActionError(problem instanceof Error ? problem.message : 'Could not save this record.')
      throw problem
    } finally {
      setActionBusy(false)
    }
  }

  async function removeRecord(record: FinancialRecord) {
    const token = localStorage.getItem(TOKEN_KEY)
    if (!token) return
    setActionBusy(true)
    setActionError('')
    try {
      await deleteRecord(token, record.kind, record.id)
      await refresh()
    } catch (problem) {
      setActionError(problem instanceof Error ? problem.message : 'Could not delete this record.')
    } finally {
      setActionBusy(false)
    }
  }

  return (
    <main className="shell">
      <header className="topbar">
        <a className="brand" href="#home" aria-label="Credora home"><span className="brand-mark">c</span><span>credora</span></a>
        <div className="topbar-note"><span className="status-dot" /> Research prototype <span className="topbar-divider">·</span> Financial clarity for everyone</div>
        {user ? <button className="text-button" onClick={signOut}>Sign out</button> : <a className="top-link" href="#access">Sign in <ArrowRight size={14} /></a>}
      </header>

      {user ? <Dashboard user={user} dashboard={dashboard} records={records} loading={loading} busy={actionBusy} error={actionError}
        onSave={saveRecord} onDelete={removeRecord} onAssess={generateAssessment} /> : <section className="hero" id="home">
        <div className="hero-copy">
          <div className="hero-label"><Sparkles size={14} /> A clearer picture of your finances</div>
          <h1>More than a credit history.<br /><em>A fuller financial story.</em></h1>
          <p className="hero-description">Understand the patterns behind your financial health. Credora brings income, spending, savings and obligations together in one thoughtful view.</p>
          <div className="feature-list">
            <div className="feature"><span className="feature-icon mint"><ChartNoAxesCombined size={18} /></span><span><strong>See the whole picture</strong><small>Understand how your money moves month to month.</small></span></div>
            <div className="feature"><span className="feature-icon lavender"><Fingerprint size={18} /></span><span><strong>Built around your context</strong><small>Financial patterns matter, even without a long credit file.</small></span></div>
            <div className="feature"><span className="feature-icon peach"><ShieldCheck size={18} /></span><span><strong>Your information stays yours</strong><small>Institutional access will require your explicit permission.</small></span></div>
          </div>
          <p className="trust-note"><ShieldCheck size={15} /> Your data is private and under your control.</p>
        </div>
        <section className="auth-card" id="access">
          <div className="auth-heading"><div><p className="eyebrow">BORROWER PORTAL</p><h2>{mode === 'register' ? 'Create your account' : 'Welcome back'}</h2></div><div className="help-icon" title="Your account data is private"><CircleHelp size={18} /></div></div>
          <p className="auth-subtitle">{mode === 'register' ? 'Start building a clearer picture of your financial health.' : 'Sign in to continue to your financial profile.'}</p>
          <form onSubmit={submitAuth}>
            <label htmlFor="email">Email address</label>
            <input id="email" type="email" value={email} onChange={event => setEmail(event.target.value)} placeholder="you@example.com" autoComplete="email" required />
            <div className="password-label"><label htmlFor="password">Password</label></div>
            <input id="password" type="password" value={password} onChange={event => setPassword(event.target.value)} placeholder={mode === 'register' ? 'At least 12 characters' : 'Enter your password'} autoComplete={mode === 'register' ? 'new-password' : 'current-password'} minLength={mode === 'register' ? 12 : 1} maxLength={128} required />
            {error && <p className="error-message" role="alert">{error}</p>}
            <button className="submit-button" type="submit" disabled={busy}>{busy ? 'Please wait…' : mode === 'register' ? 'Create account' : 'Sign in'} <ArrowRight size={16} /></button>
          </form>
          <div className="switch-mode">{mode === 'register' ? 'Already have an account?' : 'New to Credora?'} <button type="button" onClick={() => { setMode(mode === 'register' ? 'login' : 'register'); setError('') }}>{mode === 'register' ? 'Sign in' : 'Create an account'}</button></div>
          <div className="privacy-foot"><ShieldCheck size={14} /> Sharing controls will be added before lender access.</div>
        </section>
      </section>}

      <footer className="footer"><span>© 2026 Credora</span><span className="footer-center">Built for financial understanding, not lending decisions.</span><span className="footer-links">Privacy-first <span>·</span> Educational prototype</span></footer>
    </main>
  )
}

function Dashboard({ user, dashboard, records, loading, busy, error, onSave, onDelete, onAssess }: {
  user: AuthUser; dashboard: DashboardData | null; records: FinancialRecord[]; loading: boolean; busy: boolean; error: string
  onSave: (kind: RecordKind, value: { month: string; amount: number; category: string; source: string; payment: number | null }) => Promise<void>
  onDelete: (record: FinancialRecord) => void; onAssess: () => void
}) {
  const [kind, setKind] = useState<RecordKind>('income')
  const analysis = dashboard?.analysis
  const indicators = analysis?.indicators ?? []
  const assessmentSnapshot = dashboard?.latest_assessment
  const displayedAssessmentIndicators = assessmentSnapshot?.indicators ?? indicators
  const displayedRecommendations = toRecommendations(assessmentSnapshot ?? analysis)
  const find = (name: string) => indicators.find(item => item.name === name)

  return <div className="dashboard-page">
    <aside className="side-nav">
      <div className="side-user"><div className="avatar">{user.email.slice(0, 1).toUpperCase()}</div><span><strong>My finances</strong><small>{user.email}</small></span></div>
      <p className="nav-label">WORKSPACE</p>
      <a className="nav-item active" href="#overview"><ChartNoAxesCombined size={16} /> Overview</a>
      <a className="nav-item" href="#records"><Wallet size={16} /> Financial records</a>
      <a className="nav-item" href="#assessment"><Activity size={16} /> Assessment</a>
      <div className="side-note"><ShieldCheck size={15} /><span>Your records are visible only in your account. Lender sharing is not enabled yet.</span></div>
      <div className="side-prototype"><span className="status-dot" /> EDUCATIONAL PROTOTYPE</div>
    </aside>

    <section className="dashboard-main" id="overview">
      <div className="dashboard-heading"><div><p className="eyebrow">YOUR FINANCIAL OVERVIEW</p><h1>Hello, {user.email.split('@')[0]}</h1><p>Track your monthly money patterns and understand what they may be telling you.</p></div><div className="heading-actions"><span className="date-chip"><Clock3 size={14} /> {new Date().toLocaleDateString('en-IN', { month: 'long', year: 'numeric' })}</span><button className="submit-button compact" onClick={onAssess} disabled={busy}>{busy ? 'Saving…' : <><Sparkles size={15} /> Save assessment</>}</button></div></div>
      {error && <div className="dashboard-alert" role="alert">{error}</div>}
      {loading || !dashboard || !analysis ? <div className="loading-panel"><span className="status-dot" /> Loading your financial profile…</div> : <>
        <div className="metric-grid">
          <MetricCard title="Average monthly income" indicator={find('average_monthly_income')} icon={<ArrowDownRight size={17} />} tint="green" />
          <MetricCard title="Average monthly expenses" indicator={find('average_monthly_expenditure')} icon={<ArrowUpRight size={17} />} tint="peach" />
          <MetricCard title="Savings rate" indicator={find('savings_rate')} icon={<Banknote size={17} />} tint="lavender" />
          <MetricCard title="Monthly debt payments / income" indicator={find('debt_to_income_ratio')} icon={<Landmark size={17} />} tint="blue" />
        </div>

        <div className="content-columns">
          <div className="main-column">
            <section className="panel chart-panel">
              <div className="panel-heading"><div><h2>Monthly money flow</h2><p>Reported income, expenses and savings contributions</p></div><span className="period-tag">{analysis.reporting_months} reported months</span></div>
              {analysis.monthly.length ? <div className="chart-wrap"><ResponsiveContainer width="100%" height="100%"><AreaChart data={analysis.monthly} margin={{ top: 10, right: 12, left: 0, bottom: 0 }}>
                <defs><linearGradient id="incomeFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#3f966b" stopOpacity={0.17} /><stop offset="95%" stopColor="#3f966b" stopOpacity={0} /></linearGradient></defs>
                <CartesianGrid stroke="#edf0ed" vertical={false} />
                <XAxis dataKey="month" tickFormatter={value => new Date(`${value}-02`).toLocaleDateString('en-IN', { month: 'short', year: '2-digit' })} axisLine={false} tickLine={false} tick={{ fill: '#8b958e', fontSize: 10 }} dy={9} />
                <YAxis tickFormatter={value => value >= 100000 ? `₹${(value / 100000).toFixed(1)}L` : `₹${Math.round(value / 1000)}k`} axisLine={false} tickLine={false} tick={{ fill: '#8b958e', fontSize: 10 }} width={44} />
                <Tooltip formatter={(value, name) => [inr(Number(value)), name === 'income' ? 'Income' : name === 'expenses' ? 'Expenses' : 'Savings']} labelFormatter={value => new Date(`${value}-02`).toLocaleDateString('en-IN', { month: 'long', year: 'numeric' })} contentStyle={{ border: '1px solid #e6ece7', borderRadius: 9, fontSize: 11 }} />
                <Area type="monotone" dataKey="income" name="income" stroke="#438c68" strokeWidth={2.5} fill="url(#incomeFill)" connectNulls={false} />
                <Area type="monotone" dataKey="expenses" name="expenses" stroke="#d49a70" strokeWidth={2} fill="none" connectNulls={false} />
                <Area type="monotone" dataKey="savings" name="savings" stroke="#8a7cbe" strokeWidth={2} fill="none" connectNulls={false} />
              </AreaChart></ResponsiveContainer></div> : <div className="empty-chart"><ChartNoAxesCombined size={24} /><strong>Your chart will appear here</strong><span>Add records for a month to start seeing patterns.</span></div>}
              <div className="chart-legend"><span><i className="legend-green" /> Income</span><span><i className="legend-peach" /> Expenses</span><span><i className="legend-purple" /> Savings</span></div>
            </section>

            <section className="panel assessment-panel" id="assessment">
              <div className="panel-heading"><div><h2>Financial health assessment</h2><p>Transparent indicators based on the information you entered</p></div><span className="heuristic-chip"><Sparkles size={12} /> Heuristic</span></div>
              {assessmentSnapshot ? <div className="saved-assessment-line"><BadgeCheck size={15} /> Saved snapshot · {new Date(assessmentSnapshot.created_at).toLocaleString()} <span>· {assessmentSnapshot.overall_category}</span></div> : <div className="saved-assessment-line unsaved"><Activity size={15} /> Live view · Save an assessment to keep a dated snapshot</div>}
              <div className="indicator-grid">{displayedAssessmentIndicators.map(indicator => <IndicatorRow key={indicator.name} indicator={indicator} />)}</div>
              <p className="disclaimer">This baseline framework is experimental. It is not a validated default-risk prediction, official credit score, or lending recommendation. Unreported information is shown as limited data.</p>
              <div className="recommendations"><h3>Ideas to consider</h3>{displayedRecommendations.map(item => <RecommendationRow key={item.id} item={item} />)}</div>
            </section>

            <section className="panel records-panel" id="records">
              <div className="panel-heading"><div><h2>Recent records</h2><p>{dashboard.record_count} reported financial record{dashboard.record_count === 1 ? '' : 's'}</p></div></div>
              {records.length ? <div className="record-list">{records.slice(0, 8).map(record => <RecordRow key={`${record.kind}-${record.id}`} record={record} onDelete={() => onDelete(record)} disabled={busy} />)}</div> : <div className="empty-records"><Wallet size={20} /><span>No financial records yet. Add your first entry to see it here.</span></div>}
            </section>
          </div>

          <div className="right-column"><RecordForm kind={kind} onKindChange={setKind} onSave={onSave} busy={busy} />
            <section className="panel quick-panel"><div className="quick-icon"><ShieldCheck size={17} /></div><h3>Private by design</h3><p>Your financial entries are scoped to your account. Lender access and sharing controls are not implemented yet.</p></section>
          </div>
        </div>
      </>}
    </section>
  </div>
}

function MetricCard({ title, indicator, icon, tint }: { title: string; indicator?: Indicator; icon: ReactNode; tint: string }) {
  return <article className="metric-card"><div className={`metric-icon ${tint}`}>{icon}</div><span className="metric-title">{title}</span><strong className="metric-value">{indicator ? displayIndicator(indicator) : '—'}</strong><span className="metric-caption">{indicator?.status === 'limited_data' ? 'Add matching monthly records' : indicator?.status === 'available' ? 'From reported information' : 'Reported period comparison'}</span></article>
}

function IndicatorRow({ indicator }: { indicator: Indicator }) {
  return <div className="indicator-row"><div className="indicator-copy"><strong>{indicator.label}</strong><small>{indicator.explanation}</small></div><div className="indicator-result"><strong>{displayIndicator(indicator)}</strong><span className={`status-pill ${indicator.status.replace('_', '-')}`}>{indicator.status.replace('_', ' ')}</span></div></div>
}

const severityIcons: Record<Severity, ReactNode> = {
  attention: <TriangleAlert size={13} />,
  watch: <Eye size={13} />,
  info: <Info size={13} />,
  positive: <ThumbsUp size={13} />,
}

function RecommendationRow({ item }: { item: Recommendation }) {
  return <div className={`recommendation ${item.severity}`}><span className="rec-icon" aria-hidden="true">{severityIcons[item.severity]}</span><div><em className="rec-tag">{severityLabels[item.severity]}</em><p>{item.message}</p></div></div>
}

function RecordRow({ record, onDelete, disabled }: { record: FinancialRecord; onDelete: () => void; disabled: boolean }) {
  return <div className="record-row"><span className={`record-kind-icon ${record.kind}`}><Banknote size={15} /></span><div className="record-info"><strong>{record.category}</strong><small>{labels[record.kind]} · {new Date(`${record.period_start}T12:00:00`).toLocaleDateString('en-IN', { month: 'short', year: 'numeric' })}{record.source_label ? ` · ${record.source_label}` : ''}</small></div><div className="record-amount"><strong>{inr(record.amount)}</strong>{record.kind === 'debt' && record.required_payment !== null && <small>{inr(record.required_payment)} / month</small>}</div><button className="icon-button" onClick={onDelete} disabled={disabled} title="Delete record" aria-label={`Delete ${record.category}`}><Trash2 size={14} /></button></div>
}

function RecordForm({ kind, onKindChange, onSave, busy }: {
  kind: RecordKind; onKindChange: (value: RecordKind) => void
  onSave: (kind: RecordKind, value: { month: string; amount: number; category: string; source: string; payment: number | null }) => Promise<void>
  busy: boolean
}) {
  const [month, setMonth] = useState(localMonth())
  const [amount, setAmount] = useState('')
  const [category, setCategory] = useState(categories.income[0])
  const [source, setSource] = useState('')
  const [payment, setPayment] = useState('')
  const [formError, setFormError] = useState('')

  function changeKind(value: RecordKind) {
    onKindChange(value)
    setCategory(categories[value][0])
    setFormError('')
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setFormError('')
    try {
      await onSave(kind, { month, amount: Number(amount), category, source, payment: kind === 'debt' ? Number(payment) : null })
      setAmount('')
      setPayment('')
      setSource('')
    } catch (problem) {
      setFormError(problem instanceof Error ? problem.message : 'Could not save record.')
    }
  }

  return <section className="panel form-panel"><div className="form-heading"><span className="form-plus"><Plus size={16} /></span><div><h2>Add a record</h2><p>Manually enter a monthly amount</p></div></div>
    <form onSubmit={submit}>
      <label htmlFor="record-kind">Record type</label><select id="record-kind" value={kind} onChange={event => changeKind(event.target.value as RecordKind)}>{Object.entries(labels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select>
      <label htmlFor="record-month">Reporting month</label><input id="record-month" type="month" value={month} onChange={event => setMonth(event.target.value)} required />
      <label htmlFor="record-category">{kind === 'reserve' ? 'Balance type' : 'Category'}</label><select id="record-category" value={category} onChange={event => setCategory(event.target.value)}>{categories[kind].map(item => <option key={item}>{item}</option>)}</select>
      <label htmlFor="record-amount">{kind === 'debt' ? 'Outstanding balance' : kind === 'reserve' ? 'Liquid balance at month end' : kind === 'savings' ? 'Amount saved this month' : `${labels[kind]} amount`} <span>(INR)</span></label><input id="record-amount" type="number" min="0" step="0.01" value={amount} onChange={event => setAmount(event.target.value)} placeholder="0.00" required />
      {kind === 'debt' && <><label htmlFor="record-payment">Required monthly payment <span>(INR)</span></label><input id="record-payment" type="number" min="0" step="0.01" value={payment} onChange={event => setPayment(event.target.value)} placeholder="0.00" required /></>}
      {kind !== 'reserve' && <><label htmlFor="record-source">Optional source note</label><input id="record-source" type="text" value={source} onChange={event => setSource(event.target.value)} placeholder="e.g. Main employer" maxLength={100} /></>}
      {formError && <p className="error-message" role="alert">{formError}</p>}
      <button className="submit-button form-submit" type="submit" disabled={busy}>{busy ? 'Saving…' : 'Save record'} <ArrowRight size={15} /></button>
    </form>
    <p className="form-hint"><CircleHelp size={13} /> Savings entries are contributions; liquid reserves are month-end balances.</p>
  </section>
}

export default App
