import { StrictMode, useEffect, useState } from 'react';
import { EntityProfile } from './entity-profile';
import { IndiaMap } from './india-map';
import type { LucideIcon } from 'lucide-react';
import { CaseRegister, Insights, ReviewForm } from './project-tools';
import { createRoot } from 'react-dom/client';
import {
  Search,
  ChevronLeft,
  Download,
  ShieldCheck,
  ArrowUpRight,
  Building2,
  TrendingUp,
  LayoutDashboard,
  ListFilter,
  Layers3,
  Copy,
  FlaskConical,
  Database,
  MessageSquareText,
  Users,
  CircleAlert,
  Sun,
  Moon,
  ClipboardCopy,
  Wrench,
} from 'lucide-react';
import {
  Sidebar,
  SidebarProvider,
  SidebarInset,
  SidebarHeader,
  SidebarContent,
  SidebarFooter,
  SidebarMenu,
  SidebarMenuItem,
  SidebarMenuButton,
  SidebarTrigger,
  useSidebar,
} from '@/components/ui/sidebar';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '@/components/ui/sheet';
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from '@/components/ui/select';
import {
  Table,
  TablePager,
  TableSearch,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from '@/components/ui/table';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';
import './globals.css';
import './six.css';

// Schema-variable local API rows support the full-field inspector.
// Operational forms in project-tools.tsx use explicit interfaces.
// oxlint-disable-next-line typescript/no-explicit-any
type Row = Record<string, any>;
const display = (v: unknown): string => {
  if (typeof v === 'string') return v;
  if (typeof v === 'number' || typeof v === 'boolean' || typeof v === 'bigint')
    return v.toString();
  return JSON.stringify(v) ?? 'Not available';
};
const heat = (frac: number) =>
  `hsl(${Math.round(12 + 96 * Math.max(0, 1 - frac / 0.09))} 72% 85%)`;
const count = (n: unknown) =>
  n == null ? 'Not available' : Number(n).toLocaleString('en-IN');
const rupees = (n: unknown) =>
  n == null
    ? 'Not observed'
    : new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: 'INR',
        maximumFractionDigits: 2,
      }).format(Number(n) / 100);
const crore = (n: unknown) =>
  n == null
    ? 'Not observed'
    : `₹${(Number(n) / 1e9).toLocaleString('en-IN', { maximumFractionDigits: 2 })} cr`;
const percent = (n: unknown) =>
  n == null ? 'Not available' : `${(Number(n) * 100).toFixed(1)}%`;
const settled = (n: unknown) => (Number(n) > 0 ? rupees(n) : 'Not observed'); // 0 settled = no observed successful payment, not a confirmed zero
const COHORT_LABEL: Record<string, string> = {
  lok_sabha: 'Lok Sabha',
  rs_sitting: 'Rajya Sabha (sitting)',
  rs_retired: 'Rajya Sabha (retired)',
};
const signals: [string, string][] = [
  ['', 'All signals'],
  ['open_over_one_year_flag', 'Open beyond one year'],
  ['no_payment_three_months_flag', 'No payment observed after 3 months'],
  ['pending_recommendation_45d_flag', 'Pending recommendation >45 days'],
  ['sanction_delay_45d_flag', 'Sanction delay proxy >45 days'],
  ['repeat_payment_report_flag', 'Repeated payment-report rows'],
  ['march_rush_flag', 'Year-end (March) disbursement concentration'],
  ['high_cost_peer_flag', 'High historical peer amount'],
  ['high_similarity_review_flag', 'Similar work descriptions'],
  ['dbscan_outlier_flag', 'Unsupervised pattern outlier (DBSCAN)'],
  ['paid_over_sanction_flag', 'Payments above sanction'],
  ['completion_over_sanction_flag', 'Completion amount above sanction'],
  ['completion_without_payment_flag', 'Completion without payment evidence'],
  ['description_changed_flag', 'Description differs at completion'],
  ['recommendation_missing_flag', 'Recommendation row missing'],
];

const NAV: [string, string, LucideIcon][] = [
  ['overview', 'Overview', LayoutDashboard],
  ['ask', 'Ask the data', MessageSquareText],
  ['queue', 'Work investigation', ListFilter],
  ['mp', 'MP view', Users],
  ['entities', 'Entities', Layers3],
  ['pairs', 'Similar works', Copy],
  ['validation', 'A/B validation', FlaskConical],
  ['sources', 'Data & research', Database],
  ['status', 'Project status & tools', Wrench],
  ['cases', 'Review register', ClipboardCopy],
  ['insights', 'Insights & forecast', TrendingUp],
];
const HEAD: Record<string, [string, string]> = {
  cases: [
    'Assignments, due dates and review history retained across releases.',
    'REVIEW WORKFLOW',
  ],
  insights: [
    'Payment concentration, connected-data patterns and experimental forecasts.',
    'ANALYSIS',
  ],
  overview: [
    'A national-to-local view of the works that need a closer look.',
    'MONITOR · INVESTIGATE · REVIEW',
  ],
  ask: [
    'Ask plain-English questions answered locally over the connected data.',
    'LOCAL QUERY',
  ],
  queue: [
    'Follow recommendations, sanctions, completion and vendor payments in one record.',
    'CASE QUEUE',
  ],
  mp: [
    'Allocation, utilisation, progress and flagged works for a member.',
    'MEMBER VIEW',
  ],
  entities: [
    'Full-extract profiles for MPs, authorities and vendors.',
    'CONNECTED ENTITIES',
  ],
  pairs: [
    'Compare near-identical work descriptions within an authority and activity.',
    'DUPLICATE REVIEW',
  ],
  validation: [
    'Equal-capacity baseline vs enhanced screening, offline.',
    'EVALUATION',
  ],
  sources: [
    'Sources, feature dictionary, evidence limits and research.',
    'PROVENANCE',
  ],
  status: [
    'Dataset, verification, methodology, reproducibility, downloads and tools.',
    'PROJECT STATUS & TOOLS',
  ],
};

async function get<T>(url: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(url, { signal });
  const data = await response.json();
  if (!response.ok)
    throw new Error(data.error || `Request failed (${response.status})`);
  return data;
}
function useData<T>(url: string | null, revision = 0) {
  const [result, setResult] = useState<{
    url: string;
    revision: number;
    data: T | null;
    error: string;
  } | null>(null);
  useEffect(() => {
    if (!url) return;
    const abort = new AbortController();
    void get<T>(url, abort.signal)
      .then((data) => setResult({ url, revision, data, error: '' }))
      .catch((e: unknown) => {
        if (!abort.signal.aborted)
          setResult({
            url,
            revision,
            data: null,
            error: e instanceof Error ? e.message : 'Request failed',
          });
      });
    return () => abort.abort();
  }, [url, revision]);
  return result?.url === url && result?.revision === revision
    ? result
    : { data: null, error: '' };
}
function Band({ b }: { b: string }) {
  return <span className={`band band-${String(b).toLowerCase()}`}>{b}</span>;
}
function Pick({
  label,
  value,
  items,
  onChange,
}: {
  label: string;
  value: string;
  items: [string, string][];
  onChange: (v: string) => void;
}) {
  const values = items.map(([value, label]) => ({
    value: value || '__all',
    label,
  }));
  return (
    <div className="pick">
      <label>{label}</label>
      <Select
        items={values}
        value={value || '__all'}
        onValueChange={(v) => onChange(v === '__all' ? '' : display(v))}
      >
        <SelectTrigger className="pick-trigger" aria-label={label}>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {values.map((v) => (
            <SelectItem key={v.value} value={v.value}>
              {v.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
const Pager = TablePager;
function Skeleton({ card }: { card?: boolean }) {
  return (
    <div className="sk-rows" aria-hidden="true">
      {[0, 1, 2, 3].map((i) => (
        <div
          key={i}
          className={`sk ${card ? 'sk-card' : 'sk-bar'}`}
          style={card ? undefined : { width: `${92 - i * 13}%` }}
        />
      ))}
    </div>
  );
}
function Status({
  error,
  loading,
  card,
}: {
  error: string;
  loading: boolean;
  card?: boolean;
}) {
  return error ? (
    <div role="alert" className="s6-empty">
      <CircleAlert size={24} />
      <span>{error}</span>
    </div>
  ) : loading ? (
    <div role="status" aria-label="Loading local records">
      <Skeleton card={card} />
    </div>
  ) : null;
}
function DownloadLink({
  file,
  children,
}: {
  file: string;
  children: React.ReactNode;
}) {
  return (
    <a className="text-link" href={`/api/download/${file}`} download>
      <Download size={15} />
      {children}
    </a>
  );
}
function Metric({
  label,
  value,
  note,
}: {
  label: string;
  value: React.ReactNode;
  note?: string;
}) {
  return (
    <div className="metric">
      <span className="metric-label">{label}</span>
      <strong>{value}</strong>
      {note && <span>{note}</span>}
    </div>
  );
}

function WorkEvidence({
  id,
  onClose,
  onWork,
  onEntity,
}: {
  id: string | null;
  onClose: () => void;
  onWork: (id: string) => void;
  onEntity: (key: string, value: string) => void;
}) {
  const detail = useData<Row>(id ? `/api/work/${id}` : null);
  const [paymentOffset, setPaymentOffset] = useState(0);
  const [paymentSearch, setPaymentSearch] = useState('');
  const [revision, setRevision] = useState(0);
  const payments = useData<Row>(
    id
      ? `/api/table?kind=payments&work_id=${id}&offset=${paymentOffset}&q=${encodeURIComponent(paymentSearch)}`
      : null,
  );
  const reviews = useData<Row>(
    id ? '/api/reviews?key=' + encodeURIComponent(id) : null,
    revision,
  );
  const w = detail.data?.work;
  return (
    <Sheet
      open={!!id}
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
    >
      <SheetContent className="s6-sheet evidence-sheet">
        <SheetHeader>
          <SheetTitle>Work {id} · Evidence</SheetTitle>
          <SheetDescription>
            Source-backed observations for investigation, not a finding of
            misuse.
          </SheetDescription>
        </SheetHeader>
        <div className="s6-evidence">
          <Status error={detail.error} loading={!w} />
          {w && (
            <>
              <h2 className="case-description">
                {w.description || 'Description not supplied'}
              </h2>
              <p>
                {w.ida_name} · {w.state} · <Band b={w.priority_band} />
              </p>
              <div className="s6-inline">
                <button onClick={() => onEntity('mp', w.mp_key)}>
                  MP: {w.mp_name}
                  <ArrowUpRight size={14} />
                </button>
                <button onClick={() => onEntity('ida', w.ida_key)}>
                  Authority profile
                  <ArrowUpRight size={14} />
                </button>
              </div>
              <div className="s6-lifecycle">
                {[
                  [
                    'Recommended',
                    w.recommendation_date,
                    w.in_recommended
                      ? 'Source 03'
                      : 'Date from sanction; source 03 row absent',
                  ],
                  ['Sanctioned', w.sanction_date, 'Source 04'],
                  ['Reported complete', w.completion_date, 'Source 05'],
                ].map(([name, date, source]) => (
                  <div key={name}>
                    <strong>{name}</strong>
                    <span>{date || 'Not observed'}</span>
                    <small>{source}</small>
                  </div>
                ))}
              </div>
              <h3>Financial reconciliation</h3>
              <dl className="s6-facts">
                {[
                  ['Recommended', w.recommended_amount_paise],
                  ['Sanctioned', w.sanction_amount_paise],
                  [
                    'Successful payments (reported)',
                    w.has_successful_payment_evidence
                      ? w.successful_payment_paise
                      : null,
                  ],
                  [
                    'In-progress payments (not settled)',
                    w.pending_payment_paise,
                  ],
                  ['Completion actual amount', w.completion_actual_paise],
                  [
                    'One-row-per-fingerprint sensitivity',
                    w.has_successful_payment_evidence
                      ? w.unique_fingerprint_sensitivity_paise
                      : null,
                  ],
                  [
                    'Completion actual less observed payments',
                    w.completion_payment_gap_paise,
                  ],
                ].map(([label, value]) => (
                  <div key={label}>
                    <dt>{label}</dt>
                    <dd>{rupees(value)}</dd>
                  </div>
                ))}
              </dl>
              <p className="quiet">
                Missing payments are not assumed to be zero in the real world.
                The fingerprint sensitivity retains one identical report row; it
                is not corrected expenditure. Completion and payment differences
                need invoices, taxes/retention and source-coverage checks.
              </p>
              <h3>Why this work is in the queue · {w.priority_score}/100</h3>
              {detail.data!.reasons.length ? (
                <ul className="s6-reasons">
                  {detail.data!.reasons.map((r: Row) => (
                    <li key={r.rule}>
                      <strong>
                        +{r.points} · {r.reason}
                      </strong>
                      <span>{r.caution}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p>
                  No active weighted rule. Routine does not mean verified
                  issue-free.
                </p>
              )}
              <p>
                Isolation-Forest atypicality percentile:{' '}
                <strong>{Number(w.isolation_percentile).toFixed(1)}</strong>
                {w.dbscan_outlier_flag
                  ? ' · flagged as a DBSCAN pattern outlier'
                  : ''}
                . These unsupervised views are separate from the rule queue and
                are neither fraud probability nor forecast.
              </p>
              <h3>Historical cost comparison</h3>
              <dl className="s6-facts">
                <div>
                  <dt>Reference</dt>
                  <dd>
                    {w.peer_level} · {count(w.peer_count)} earlier-year works
                  </dd>
                </div>
                <div>
                  <dt>Peer median</dt>
                  <dd>
                    {w.peer_median_inr == null
                      ? 'Not available'
                      : rupees(w.peer_median_inr * 100)}
                  </dd>
                </div>
                <div>
                  <dt>Amount / peer median</dt>
                  <dd>
                    {w.cost_peer_ratio == null
                      ? 'Not available'
                      : Number(w.cost_peer_ratio).toFixed(2) + '×'}
                  </dd>
                </div>
              </dl>
              <p className="quiet">
                The current work and current financial year do not set the
                benchmark. Amount comparisons are not unit-cost estimates.
              </p>
              <h3>Payment evidence</h3>
              <TableSearch
                value={paymentSearch}
                onChange={(v) => {
                  setPaymentSearch(v);
                  setPaymentOffset(0);
                }}
                label="Search all payment evidence"
              />
              <Status error={payments.error} loading={!payments.data} />
              {payments.data && (
                <>
                  <Table server>
                    <TableHeader>
                      <TableRow>
                        {[
                          'Date',
                          'Vendor',
                          'Amount',
                          'Status',
                          'Identical rows',
                        ].map((h) => (
                          <TableHead key={h}>{h}</TableHead>
                        ))}
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {payments.data.items.map((p: Row) => (
                        <TableRow key={p.source_record}>
                          <TableCell>{p.payment_date}</TableCell>
                          <TableCell>
                            <button
                              className="record-title"
                              onClick={() => onEntity('vendor', p.vendor_id)}
                            >
                              {p.vendor_name}
                            </button>
                            <small className="record-meta">
                              ID {p.vendor_id} · source record {p.source_record}
                            </small>
                          </TableCell>
                          <TableCell className="amount-cell">
                            {rupees(p.amount_paise)}
                          </TableCell>
                          <TableCell>{p.payment_status}</TableCell>
                          <TableCell>{p.same_fingerprint_count}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                  <Pager
                    offset={paymentOffset}
                    total={payments.data.total}
                    onChange={setPaymentOffset}
                  />
                </>
              )}
              <h3>Similar-work candidates</h3>
              <p className="quiet">
                At most 100 connected candidates shown here. See the complete
                pair export for all edges.
              </p>
              {detail.data!.pairs.length ? (
                detail.data!.pairs.map((p: Row) => (
                  <button
                    className="s6-pair-link"
                    key={p.pair_id}
                    onClick={() =>
                      onWork(p.work_id_a === id ? p.work_id_b : p.work_id_a)
                    }
                  >
                    Work {p.work_id_a === id ? p.work_id_b : p.work_id_a} ·
                    similarity {percent(p.similarity)}
                    {p.number_conflict ? ' · number conflict' : ''}
                    {p.continuation_cue ? ' · phase/extension cue' : ''}
                  </button>
                ))
              ) : (
                <p>
                  No retained candidate. Candidate search is bounded and not
                  exhaustive.
                </p>
              )}
              <h3>Record your review</h3>
              {reviews.data && (
                <ReviewForm
                  key={reviews.data.history.at(-1)?.id ?? 'new'}
                  workId={id!}
                  version={detail.data!.version}
                  previous={reviews.data.history.at(-1)}
                  onSaved={() => setRevision((r) => r + 1)}
                />
              )}
              <Status error={reviews.error} loading={!reviews.data} />
              {reviews.data?.history
                .filter((r: Row) => r.record_key === id)
                .slice()
                .reverse()
                .map((r: Row) => (
                  <div className="s6-review" key={r.id}>
                    <strong>{r.outcome}</strong>
                    <small>
                      {r.created} · {r.owner || 'Unassigned'} · {r.status} ·{' '}
                      {r.due_date || 'No due date'}
                      {r.version !== detail.data!.version
                        ? ' · Previous release — recheck evidence'
                        : ''}
                    </small>
                    <p>{r.note}</p>
                  </div>
                ))}
              <details>
                <summary>
                  All {Object.keys(w).length} work fields and source row
                  references
                </summary>
                <dl className="s6-facts">
                  {Object.entries(w).map(([key, value]) => (
                    <div key={key}>
                      <dt>{key}</dt>
                      <dd>
                        {value == null ? 'Not available' : display(value)}
                      </dd>
                    </div>
                  ))}
                </dl>
              </details>
            </>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}

const Choropleth = IndiaMap;
function Overview({
  inspect,
}: {
  inspect: (key: string, value: string) => void;
}) {
  const [state, setState] = useState('');
  const data = useData<Row>(
    '/api/overview' + (state ? `?state=${encodeURIComponent(state)}` : ''),
  );
  const months = useData<Row>('/api/months');
  const n = data.data?.national;
  const d = data.data;
  const settledFrac = (r: Row) =>
    r.sanction_paise > 0 ? r.successful_payment_paise / r.sanction_paise : null;
  const topStates = (d?.states || []).slice(0, 10).map((s: Row) => ({
    name: s.state.length > 12 ? s.state.slice(0, 11) + '…' : s.state,
    High: s.high,
  }));
  const trend = (months.data?.items || []).map((m: Row) => ({
    month: m.payment_month,
    Settled: Math.round(m.successful_payment_paise / 1e7) / 100,
  }));
  const idas = state ? d?.idas : d?.top_idas;
  return (
    <>
      <Status error={data.error} loading={!n} card />
      {n && (
        <>
          <div className="metric-grid">
            <Metric label="Connected works" value={count(n.works)} />
            <Metric label="High-priority reviews" value={count(n.high)} />
            <Metric label="Sanctioned" value={crore(n.sanction_paise)} />
            <Metric
              label="Settled / sanctioned"
              value={percent(settledFrac(n))}
              note={`${crore(n.successful_payment_paise)} settled`}
            />
            <Metric
              label="Open beyond one year"
              value={count(n.open_over_year)}
            />
            <Metric
              label="No payment after 3 months"
              value={count(n.no_payment_3m)}
            />
            <Metric label="Members with works" value={count(n.mp_count)} />
            <Metric label="District authorities" value={count(n.ida_count)} />
          </div>

          <div
            className="metric-grid"
            style={{ gridTemplateColumns: 'repeat(3,minmax(0,1fr))' }}
          >
            {(d!.cohorts || []).map((c: Row) => (
              <div key={c.cohort} className="metric">
                <span className="metric-label">
                  {COHORT_LABEL[c.cohort] || c.cohort}
                </span>
                <strong style={{ fontSize: 26 }}>{count(c.works)}</strong>
                <span>
                  {count(c.high)} High · {crore(c.sanction_paise)} sanctioned ·{' '}
                  {percent(settledFrac(c))} settled
                </span>
              </div>
            ))}
          </div>

          <div className="overview-grid">
            <div className="panel">
              <div className="panel-head">
                <div>
                  <h2>Top states by high-priority works</h2>
                </div>
                <TrendingUp size={18} />
              </div>
              <div style={{ padding: '6px 16px 18px' }}>
                <ResponsiveContainer width="100%" height={230}>
                  <BarChart
                    data={topStates}
                    margin={{ top: 4, right: 8, bottom: 4, left: 0 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis
                      dataKey="name"
                      tick={{ fontSize: 11 }}
                      interval={0}
                      angle={-30}
                      textAnchor="end"
                      height={56}
                    />
                    <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                    <Tooltip />
                    <Bar dataKey="High" fill="#c96263" radius={[3, 3, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
            <div className="panel">
              <div className="panel-head">
                <div>
                  <h2>Monthly settled payments (₹ cr)</h2>
                </div>
                <TrendingUp size={18} />
              </div>
              <div style={{ padding: '6px 16px 18px' }}>
                <ResponsiveContainer width="100%" height={230}>
                  <LineChart
                    data={trend}
                    margin={{ top: 4, right: 8, bottom: 4, left: 0 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis
                      dataKey="month"
                      tick={{ fontSize: 10 }}
                      interval={Math.ceil(trend.length / 8)}
                    />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip />
                    <Line
                      dataKey="Settled"
                      stroke="#2f7f91"
                      dot={false}
                      strokeWidth={2}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <p className="section-note">
                Reported settlement timing only. The most recent month is an
                incomplete reporting period — a lower last point is a coverage
                gap, not a spending collapse.
              </p>
            </div>
          </div>

          <Choropleth states={d!.states} selected={state} onPick={setState} />

          <div className="panel">
            <div className="panel-head">
              <div>
                <h2>State risk heatmap</h2>
                <p>
                  Cell shade = share of works in the High band. Select a state
                  for its authorities; “Investigate” opens the filtered queue.
                </p>
              </div>
            </div>
            <div style={{ overflowX: 'auto' }}>
              <Table>
                <TableHeader>
                  <TableRow>
                    {[
                      'State / UT',
                      'Works',
                      'High',
                      'High %',
                      'Open >1yr',
                      'Sanctioned',
                      'Settled/sanction',
                      'Mean priority',
                      '',
                    ].map((h) => (
                      <TableHead key={h}>{h}</TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {d!.states.map((s: Row) => {
                    const f = s.high / s.works;
                    return (
                      <TableRow key={s.state}>
                        <TableCell>
                          <button
                            className="record-title"
                            onClick={() =>
                              setState(state === s.state ? '' : s.state)
                            }
                          >
                            {s.state}
                          </button>
                        </TableCell>
                        <TableCell>{count(s.works)}</TableCell>
                        <TableCell>{count(s.high)}</TableCell>
                        <TableCell>
                          <span
                            className="s6-heatcell"
                            style={{ background: heat(f) }}
                          >
                            {(f * 100).toFixed(1)}%
                          </span>
                        </TableCell>
                        <TableCell>{count(s.open_over_year)}</TableCell>
                        <TableCell className="amount-cell">
                          {crore(s.sanction_paise)}
                        </TableCell>
                        <TableCell>{percent(settledFrac(s))}</TableCell>
                        <TableCell>
                          {Number(s.mean_priority).toFixed(1)}
                        </TableCell>
                        <TableCell>
                          <button onClick={() => inspect('state', s.state)}>
                            Investigate
                            <ArrowUpRight size={13} />
                          </button>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          </div>

          <div className="panel">
            <div className="panel-head">
              <div>
                <h2>
                  {state
                    ? `District authorities · ${state}`
                    : 'Highest-risk district authorities (national top 20)'}
                </h2>
              </div>
              <Building2 size={18} />
            </div>
            {state && (
              <p className="section-note">
                <button className="text-link" onClick={() => setState('')}>
                  Back to national top 20
                </button>
              </p>
            )}
            <div style={{ overflowX: 'auto' }}>
              <Table>
                <TableHeader>
                  <TableRow>
                    {[
                      'Authority',
                      'State',
                      'Works',
                      'High',
                      'Open >1yr',
                      'Sanctioned',
                      'Settled',
                      'Details',
                    ].map((h) => (
                      <TableHead key={h}>{h}</TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {(idas || []).map((r: Row) => (
                    <TableRow key={r.ida_key}>
                      <TableCell>
                        <button
                          className="record-title"
                          onClick={() => inspect('ida', r.ida_key)}
                        >
                          {r.ida_name}
                        </button>
                      </TableCell>
                      <TableCell>{r.state}</TableCell>
                      <TableCell>{count(r.works)}</TableCell>
                      <TableCell>{count(r.high)}</TableCell>
                      <TableCell>{count(r.open_over_year)}</TableCell>
                      <TableCell className="amount-cell">
                        {crore(r.sanction_paise)}
                      </TableCell>
                      <TableCell className="amount-cell">
                        {crore(r.successful_payment_paise)}
                      </TableCell>
                      <TableCell>
                        <button onClick={() => inspect('ida', r.ida_key)}>
                          Authority details
                          <ArrowUpRight size={13} />
                        </button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </div>
        </>
      )}
    </>
  );
}

function Ask({ inspect }: { inspect: (key: string, value: string) => void }) {
  const [draft, setDraft] = useState('');
  const [query, setQuery] = useState('');
  const data = useData<Row>(
    '/api/ask' + (query ? `?q=${encodeURIComponent(query)}` : ''),
  );
  const examples: string[] = data.data?.examples || [];
  const answered = !!data.data?.columns?.length;
  const clarify = !!query && !!data.data && !answered ? data.data.summary : '';
  const cell = (kind: string, v: unknown) =>
    kind === 'money'
      ? crore(v)
      : kind === 'pct'
        ? percent(v)
        : kind === 'num'
          ? v == null
            ? '—'
            : Number(v).toFixed(1)
          : kind === 'count'
            ? count(v)
            : v == null
              ? '—'
              : display(v);
  return (
    <>
      <form
        className="s6-ask"
        onSubmit={(e) => {
          e.preventDefault();
          setQuery(draft.trim());
        }}
      >
        <Search size={18} />
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          aria-label="Ask a question about the local data"
          maxLength={300}
          placeholder="Authority name + details, or a metric question…"
        />
        <button type="submit" disabled={!draft.trim()}>
          Ask
        </button>
      </form>
      <div className="s6-chips">
        {examples.map((x) => (
          <button
            key={x}
            className="s6-chip"
            onClick={() => {
              setDraft(x);
              setQuery(x);
            }}
          >
            {x}
          </button>
        ))}
      </div>
      <Status error={data.error} loading={!!query && !data.data} />
      {data.data?.entity && (
        <p className="section-note">
          <button
            onClick={() =>
              inspect(data.data!.entity.kind, data.data!.entity.key)
            }
          >
            Open full profile: {data.data.entity.name}
          </button>
        </p>
      )}
      {!!data.data?.matches?.length && (
        <div className="panel">
          <div className="panel-head">
            <h2>Choose the exact entity</h2>
          </div>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Source key</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.data.matches.map((m: Row) => (
                <TableRow key={m.kind + m.key}>
                  <TableCell>
                    <button
                      className="record-title"
                      onClick={() => inspect(m.kind, m.key)}
                    >
                      {m.name}
                    </button>
                  </TableCell>
                  <TableCell>{m.kind}</TableCell>
                  <TableCell>{m.key}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
      {answered && (
        <div className="panel">
          <div className="panel-head">
            <div>
              <h2>{data.data!.summary}</h2>
              <p>Interpreted as: {data.data!.interpretation}</p>
            </div>
          </div>
          <div style={{ overflowX: 'auto' }}>
            <Table>
              <TableHeader>
                <TableRow>
                  {data.data!.columns.map((c: Row) => (
                    <TableHead key={c.key}>{c.label}</TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.data!.rows.map((r: Row, i: number) => (
                  <TableRow key={i}>
                    {data.data!.columns.map((c: Row) => (
                      <TableCell
                        key={c.key}
                        className={
                          c.kind === 'money' || c.kind === 'count'
                            ? 'amount-cell'
                            : ''
                        }
                      >
                        {c.key === '_dim' && r._entity_kind && r._entity_key ? (
                          <button
                            className="record-title"
                            onClick={() =>
                              inspect(r._entity_kind, r._entity_key)
                            }
                          >
                            {cell(c.kind, r[c.key])}
                          </button>
                        ) : (
                          cell(c.kind, r[c.key])
                        )}
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          <p className="section-note">{data.data!.caveat}</p>
          <details style={{ padding: '0 24px 22px' }}>
            <summary>
              Generated SQL ({data.data!.row_count} rows)
              <button
                className="copy-btn"
                onClick={(e) => {
                  e.preventDefault();
                  try {
                    void navigator.clipboard
                      ?.writeText(data.data!.sql)
                      .catch(() => {});
                  } catch {}
                }}
              >
                <ClipboardCopy size={13} />
                Copy
              </button>
            </summary>
            <pre className="s6-sql">
              {data.data!.sql}
              {data.data!.params.length
                ? `\n-- parameters: ${data.data!.params.join(', ')}`
                : ''}
            </pre>
          </details>
        </div>
      )}
      {!!clarify && (
        <div className="panel">
          <div className="panel-head">
            <div>
              <h2>Could not answer that directly</h2>
              <p>{clarify}</p>
            </div>
          </div>
          <p className="section-note">{data.data!.caveat}</p>
        </div>
      )}
    </>
  );
}

function MPView({ open }: { open: (id: string) => void }) {
  const [query, setQuery] = useState('');
  const [search, setSearch] = useState('');
  const [mOffset, setMOffset] = useState(0);
  const [mp, setMp] = useState<Row | null>(null);
  useEffect(() => {
    const t = setTimeout(() => setSearch(query), 300);
    return () => clearTimeout(t);
  }, [query]);
  const list = useData<Row>(
    mp
      ? null
      : '/api/table?' +
          new URLSearchParams({
            kind: 'mps',
            q: search,
            offset: String(mOffset),
          }),
  );
  const [wOffset, setWOffset] = useState(0);
  const [workSearch, setWorkSearch] = useState('');

  const works = useData<Row>(
    mp
      ? `/api/works?mp=${encodeURIComponent(mp.mp_key)}&sort=priority_score&order=desc&offset=${wOffset}&q=${encodeURIComponent(workSearch)}`
      : null,
  );
  const light = (m: Row) => {
    const f = m.work_count ? m.high_priority_count / m.work_count : 0;
    return f >= 0.06
      ? ['#c96263', 'High attention']
      : f >= 0.03
        ? ['#d5a64c', 'Some attention']
        : ['#388e8a', 'Mostly routine'];
  };
  if (!mp) {
    return (
      <div className="panel">
        <div className="queue-controls">
          <div className="search-box">
            <Search size={17} />
            <input
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setMOffset(0);
              }}
              placeholder="Search member by name"
            />
          </div>
        </div>
        <Status error={list.error} loading={!list.data} />
        {list.data && (
          <div style={{ overflowX: 'auto' }}>
            <Table server>
              <TableHeader>
                <TableRow>
                  {[
                    'Member',
                    'State',
                    'Works',
                    'High-priority',
                    'Settled / allocation',
                  ].map((h) => (
                    <TableHead key={h}>{h}</TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {list.data.items.map((m: Row) => (
                  <TableRow key={m.mp_key}>
                    <TableCell>
                      <button
                        className="record-title"
                        onClick={() => {
                          setWOffset(0);
                          setMp(m);
                        }}
                      >
                        {m.mp_name}
                        <ArrowUpRight size={14} />
                      </button>
                    </TableCell>
                    <TableCell>{m.state}</TableCell>
                    <TableCell>{count(m.work_count)}</TableCell>
                    <TableCell>{count(m.high_priority_count)}</TableCell>
                    <TableCell>
                      {percent(m.observed_paid_to_allocation_ratio)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
        {list.data && (
          <Pager
            total={list.data.total}
            offset={mOffset}
            onChange={setMOffset}
          />
        )}
      </div>
    );
  }
  const [colour, label] = light(mp);
  return (
    <>
      <div className="page-heading" style={{ marginTop: -8 }}>
        <div>
          <p className="eyebrow" style={{ color: colour }}>
            ● {label}
          </p>
          <h1 style={{ fontSize: 26 }}>{mp.mp_name}</h1>
          <p className="page-description">
            {mp.constituency ? mp.constituency + ' · ' : ''}
            {mp.state} — {count(mp.high_priority_count)} of{' '}
            {count(mp.work_count)} works in the High band
          </p>
        </div>
        <button
          onClick={() => {
            setMp(null);
            setQuery('');
          }}
        >
          <ChevronLeft size={16} />
          Back to search
        </button>
      </div>
      <div className="metric-grid">
        <Metric
          label="Allocated (limit snapshot)"
          value={crore(mp.allocated_paise)}
        />
        <Metric label="Sanctioned" value={crore(mp.sanction_paise)} />
        <Metric
          label="Settled (reported)"
          value={crore(mp.successful_payment_paise)}
        />
        <Metric
          label="Settled / allocation"
          value={percent(mp.observed_paid_to_allocation_ratio)}
        />
        <Metric
          label="Sanction / allocation"
          value={percent(mp.sanction_to_allocation_ratio)}
        />
        <Metric label="Calamity consent" value={crore(mp.consented_paise)} />
      </div>
      <div className="overview-grid">
        <div className="panel">
          <div className="panel-head">
            <div>
              <h2>Work progress</h2>
            </div>
          </div>
          <dl className="s6-facts" style={{ padding: '4px 24px 20px' }}>
            {[
              ['Recommended records', count(mp.recommended_record_count)],
              ['Sanctioned', count(mp.sanctioned_count)],
              ['Reported complete (export)', count(mp.completed_count)],
              [
                'Reported completion / sanction',
                percent(mp.completion_to_sanction_ratio),
              ],
              ['Open beyond one year', count(mp.open_over_one_year_count)],
              [
                'No payment after 3 months',
                count(mp.no_payment_three_months_count),
              ],
            ].map(([l, v]) => (
              <div key={l}>
                <dt>{l}</dt>
                <dd>{v}</dd>
              </div>
            ))}
          </dl>
        </div>
        <div className="panel">
          <div className="panel-head">
            <div>
              <h2>Compliance checks</h2>
            </div>
          </div>
          <dl className="s6-facts" style={{ padding: '4px 24px 8px' }}>
            {[
              ['SC-area allocation (15% mandate)'],
              ['ST-area allocation (7.5% mandate)'],
              ['Trust/society ₹75L ceiling'],
              ['Jurisdiction of recommendation'],
            ].map(([l]) => (
              <div key={l}>
                <dt>{l}</dt>
                <dd>Unavailable</dd>
              </div>
            ))}
          </dl>
          <p className="section-note">
            These mandates need beneficiary-area tags, a trust register and
            geocoding not in the supplied exports. They are shown as{' '}
            <strong>unavailable, not passed</strong>.
          </p>
        </div>
      </div>
      <div className="panel">
        <div className="panel-head">
          <div>
            <h2>Flagged and recent works</h2>
          </div>
        </div>
        <TableSearch
          value={workSearch}
          onChange={(v) => {
            setWorkSearch(v);
            setWOffset(0);
          }}
          label="Search this member’s connected works"
        />
        <Status error={works.error} loading={!works.data} />
        {works.data && (
          <>
            <div style={{ overflowX: 'auto' }}>
              <Table server>
                <TableHeader>
                  <TableRow>
                    {[
                      'Work / purpose',
                      'Lifecycle',
                      'Sanctioned',
                      'Settled',
                      'Review priority',
                    ].map((h) => (
                      <TableHead key={h}>{h}</TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {works.data.items.map((w: Row) => (
                    <TableRow key={w.work_id}>
                      <TableCell className="work-cell">
                        <button
                          className="record-title"
                          onClick={() => open(w.work_id)}
                        >
                          {w.description || 'No description supplied'}
                        </button>
                        <small className="record-meta">#{w.work_id}</small>
                      </TableCell>
                      <TableCell>
                        {w.lifecycle}
                        <small className="record-meta">
                          {w.sanction_date || 'No observed sanction'}
                        </small>
                      </TableCell>
                      <TableCell className="amount-cell">
                        {rupees(w.sanction_amount_paise)}
                      </TableCell>
                      <TableCell className="amount-cell">
                        {settled(w.successful_payment_paise)}
                      </TableCell>
                      <TableCell>
                        <Band b={w.priority_band} />{' '}
                        <span className="quiet">{w.priority_score}</span>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
            <Pager
              offset={wOffset}
              total={works.data.summary.total}
              onChange={setWOffset}
            />
            <p className="section-note">
              Highest priority first. Open a work for its evidence trail.
            </p>
          </>
        )}
      </div>
    </>
  );
}

function Queue({
  open,
  entity,
  clearEntity,
}: {
  open: (id: string) => void;
  entity: Row;
  clearEntity: () => void;
}) {
  const options = useData<Row>('/api/options');
  const [state, setState] = useState('');
  const [year, setYear] = useState('');
  const [lifecycle, setLifecycle] = useState('');
  const [signal, setSignal] = useState('');
  const [cohort, setCohort] = useState('');
  const [band, setBand] = useState('');
  const [query, setQuery] = useState('');
  const [search, setSearch] = useState('');
  const [offset, setOffset] = useState(0);
  const [sort, setSort] = useState('priority_score');
  useEffect(() => {
    const t = setTimeout(() => {
      setSearch(query);
      setOffset(0);
    }, 300);
    return () => clearTimeout(t);
  }, [query]);

  const args = new URLSearchParams({
    state,
    cohort,
    band,
    fy: year,
    lifecycle,
    signal,
    q: search,
    sort,
    offset: String(offset),
    ...entity,
  });
  const works = useData<Row>('/api/works?' + args);
  const summary = works.data?.summary;
  return (
    <div className="panel">
      <div className="queue-controls">
        <div className="search-box">
          <Search size={17} />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Work ID, description, MP or authority"
          />
        </div>
        <Pick
          label="State / UT"
          value={state}
          onChange={(v) => {
            setState(v);
            setOffset(0);
          }}
          items={[
            ['', 'All states'],
            ...(options.data?.states || []).map((v: string) => [v, v]),
          ]}
        />
        <Pick
          label="Sanction FY"
          value={year}
          onChange={(v) => {
            setYear(v);
            setOffset(0);
          }}
          items={[
            ['', 'All years'],
            ...(options.data?.years || []).map((v: string) => [v, v]),
          ]}
        />
        <Pick
          label="Lifecycle"
          value={lifecycle}
          onChange={(v) => {
            setLifecycle(v);
            setOffset(0);
          }}
          items={[
            ['', 'All lifecycles'],
            ...[
              'Not in sanction export',
              'Sanctioned / open',
              'Reported complete',
            ].map((v) => [v, v] as [string, string]),
          ]}
        />
        <Pick
          label="Signal"
          value={signal}
          onChange={(v) => {
            setSignal(v);
            setOffset(0);
          }}
          items={signals}
        />
        <Pick
          label="Sort"
          value={sort}
          onChange={(v) => {
            setSort(v);
            setOffset(0);
          }}
          items={[
            ['priority_score', 'Rule priority'],
            ['isolation_percentile', 'Model atypicality'],
            ['sanction_amount_paise', 'Sanction amount'],
            ['successful_payment_paise', 'Successful payments'],
            ['sanction_age_days', 'Sanction age'],
          ]}
        />
        <Pick
          label="Cohort"
          value={cohort}
          onChange={(v) => {
            setCohort(v);
            setOffset(0);
          }}
          items={[['', 'All cohorts'], ...Object.entries(COHORT_LABEL)]}
        />
        <Pick
          label="Priority band"
          value={band}
          onChange={(v) => {
            setBand(v);
            setOffset(0);
          }}
          items={['', 'Routine', 'Low', 'Medium', 'High', 'Critical'].map(
            (v) => [v, v || 'All bands'],
          )}
        />
        <DownloadLink file="Work_Features.csv">Dataset</DownloadLink>
      </div>
      {!!Object.keys(entity).length && (
        <div className="selection-summary">
          Connected-entity filter: {Object.keys(entity).join(', ')}{' '}
          <button onClick={clearEntity}>Clear</button>
        </div>
      )}
      <Status error={works.error || options.error} loading={!works.data} />
      {summary && (
        <>
          <div className="selection-summary">
            <strong>{count(summary.total)}</strong> matching ·{' '}
            {count(summary.completions)} complete ·{' '}
            {crore(summary.sanction_paise)} sanctioned ·{' '}
            {crore(summary.successful_payment_paise)} settled ·{' '}
            {count(summary.open_over_year)} open &gt;1yr ·{' '}
            {count(summary.no_payment_three_months)} no payment 3mo
          </div>
          <div style={{ overflowX: 'auto' }}>
            <Table server>
              <TableHeader>
                <TableRow>
                  {[
                    'Work / purpose',
                    'MP / authority',
                    'Lifecycle',
                    'Sanctioned',
                    'Settled',
                    'Review priority',
                  ].map((h) => (
                    <TableHead key={h}>{h}</TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {works.data!.items.map((w: Row) => (
                  <TableRow key={w.work_id}>
                    <TableCell className="work-cell">
                      <button
                        className="record-title"
                        onClick={() => open(w.work_id)}
                      >
                        {w.description || 'No description supplied'}
                      </button>
                      <small className="record-meta">
                        #{w.work_id} · {w.activity_type}
                      </small>
                    </TableCell>
                    <TableCell>
                      {w.mp_name}
                      <small className="record-meta">
                        {w.ida_name} · {w.state}
                      </small>
                    </TableCell>
                    <TableCell>
                      {w.lifecycle}
                      <small className="record-meta">
                        {w.sanction_date || 'No observed sanction'}
                      </small>
                    </TableCell>
                    <TableCell className="amount-cell">
                      {rupees(w.sanction_amount_paise)}
                    </TableCell>
                    <TableCell className="amount-cell">
                      {settled(w.successful_payment_paise)}
                    </TableCell>
                    <TableCell>
                      <div className="score-line">
                        <Band b={w.priority_band} />
                        <strong>{w.priority_score}</strong>
                      </div>
                      <small className="record-meta">
                        Model pct {Number(w.isolation_percentile).toFixed(0)} ·{' '}
                        {w.data_quality_issue_count} DQ
                      </small>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          <Pager offset={offset} total={summary.total} onChange={setOffset} />
        </>
      )}
    </div>
  );
}

function Entities({
  inspect,
}: {
  inspect: (key: string, value: string) => void;
}) {
  const [kind, setKind] = useState('mps');
  const [query, setQuery] = useState('');
  const [offset, setOffset] = useState(0);
  const [focus, setFocus] = useState<Row | null>(null);
  const data = useData<Row>(
    '/api/table?' +
      new URLSearchParams({ kind, q: query, offset: String(offset) }),
  );

  return (
    <div className="panel">
      <div className="queue-controls">
        <Pick
          label="Entity"
          value={kind}
          onChange={(v) => {
            setKind(v);
            setOffset(0);
            setFocus(null);
          }}
          items={[
            ['mps', 'Members of Parliament'],
            ['idas', 'District authorities'],
            ['vendors', 'Vendors'],
          ]}
        />
        <div className="search-box">
          <Search size={17} />
          <input
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setOffset(0);
              setFocus(null);
            }}
            placeholder="Search name"
          />
        </div>
        <DownloadLink
          file={
            kind === 'mps'
              ? 'MP_Features.csv'
              : kind === 'idas'
                ? 'IDA_Features.csv'
                : 'Vendor_Features.csv'
          }
        >
          Dataset
        </DownloadLink>
      </div>
      <Status error={data.error} loading={!data.data} />
      {data.data && (
        <>
          <div style={{ overflowX: 'auto' }}>
            <Table server>
              <TableHeader>
                <TableRow>
                  {[
                    'Entity',
                    'Connected works',
                    'Successful payments',
                    'Pending payments',
                    'Details',
                  ].map((v) => (
                    <TableHead key={v}>{v}</TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.data.items.map((r: Row) => {
                  const key = r.mp_key || r.ida_key || r.vendor_id;
                  return (
                    <TableRow key={key}>
                      <TableCell className="record-title">
                        {r.mp_name || r.ida_name || r.vendor_name}
                        <small className="record-meta">
                          {r.state || `Vendor ID ${r.vendor_id}`}
                        </small>
                      </TableCell>
                      <TableCell>{count(r.work_count)}</TableCell>
                      <TableCell className="amount-cell">
                        {rupees(r.successful_payment_paise)}
                      </TableCell>
                      <TableCell className="amount-cell">
                        {rupees(r.pending_payment_paise)}
                      </TableCell>
                      <TableCell>
                        <button onClick={() => setFocus(r)}>All fields</button>{' '}
                        <button
                          onClick={() =>
                            inspect(
                              kind === 'mps'
                                ? 'mp'
                                : kind === 'idas'
                                  ? 'ida'
                                  : 'vendor',
                              key,
                            )
                          }
                        >
                          Open profile
                        </button>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
          <Pager offset={offset} total={data.data.total} onChange={setOffset} />
        </>
      )}
      {focus && (
        <div style={{ padding: 24, borderTop: '1px solid #edf1f5' }}>
          <h2 style={{ margin: '0 0 6px' }}>
            {focus.mp_name || focus.ida_name || focus.vendor_name}
          </h2>
          <p className="quiet">
            Allocation ratios use the supplied limit snapshot, not a certified
            bank balance. Shared vendor names do not mean the same legal entity.
            Concentration is descriptive, not evidence of collusion.
          </p>
          <dl className="s6-facts">
            {Object.entries(focus)
              .filter(([k]) => k.toLowerCase() === k)
              .map(([k, v]) => (
                <div key={k}>
                  <dt>{k.replaceAll('_', ' ')}</dt>
                  <dd>
                    {k.endsWith('_paise')
                      ? rupees(v)
                      : k.endsWith('_ratio')
                        ? percent(v)
                        : v == null
                          ? 'Not observed'
                          : String(v)}
                  </dd>
                </div>
              ))}
          </dl>
        </div>
      )}
    </div>
  );
}

function Pairs({ open }: { open: (id: string) => void }) {
  const [offset, setOffset] = useState(0);
  const [query, setQuery] = useState('');
  const data = useData<Row>(
    `/api/duplicates?offset=${offset}&q=${encodeURIComponent(query)}`,
  );
  return (
    <div className="panel">
      <div className="panel-head">
        <div>
          <h2>Similar-work candidates</h2>
          <p>
            Compare both records. Matching descriptions do not establish
            duplicate assets.
          </p>
        </div>
        <DownloadLink file="Duplicate_Candidates.csv">All pairs</DownloadLink>
      </div>
      <TableSearch
        value={query}
        onChange={(v) => {
          setQuery(v);
          setOffset(0);
        }}
        label="Search all similar-work candidates"
      />
      <Status error={data.error} loading={!data.data} />
      {data.data && (
        <>
          <div style={{ overflowX: 'auto' }}>
            <Table server>
              <TableHeader>
                <TableRow>
                  {['First work', 'Second work', 'Similarity', 'Cautions'].map(
                    (h) => (
                      <TableHead key={h}>{h}</TableHead>
                    ),
                  )}
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.data.items.map((p: Row) => (
                  <TableRow key={p.pair_id}>
                    <TableCell className="work-cell">
                      <button
                        className="record-title"
                        onClick={() => open(p.work_id_a)}
                      >
                        {p.description_a}
                      </button>
                      <small className="record-meta">
                        #{p.work_id_a} · {rupees(p.amount_a)}
                      </small>
                    </TableCell>
                    <TableCell className="work-cell">
                      <button
                        className="record-title"
                        onClick={() => open(p.work_id_b)}
                      >
                        {p.description_b}
                      </button>
                      <small className="record-meta">
                        #{p.work_id_b} · {rupees(p.amount_b)}
                      </small>
                    </TableCell>
                    <TableCell>
                      <strong>{percent(p.similarity)}</strong>
                    </TableCell>
                    <TableCell className="quiet">
                      {[
                        p.number_conflict ? 'Different number tokens' : '',
                        p.continuation_cue ? 'Phase/repair cue' : '',
                        p.generic_text ? 'Generic text' : '',
                      ]
                        .filter(Boolean)
                        .join(' · ') ||
                        'Location and scope still need verification'}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          <Pager offset={offset} total={data.data.total} onChange={setOffset} />
        </>
      )}
      <p className="section-note">
        Bounded same-authority/activity matching; cross-authority pairs and
        matches outside candidate windows may be missed. No measured real
        duplicate recall.
      </p>
    </div>
  );
}

function WorkspaceNavigation({
  view,
  navigate,
}: {
  view: string;
  navigate: (key: string) => void;
}) {
  const { isMobile, setOpenMobile } = useSidebar();
  return (
    <SidebarMenu>
      {NAV.map(([key, label, Icon]) => (
        <SidebarMenuItem key={key}>
          <SidebarMenuButton
            isActive={view === key}
            className="nav-item"
            onClick={() => {
              navigate(key);
              if (isMobile) setOpenMobile(false);
            }}
          >
            <Icon size={19} />
            <span>{label}</span>
          </SidebarMenuButton>
        </SidebarMenuItem>
      ))}
    </SidebarMenu>
  );
}

function Validation({ onTools }: { onTools: () => void }) {
  const data = useData<Row>('/api/validation');
  const [budget, setBudget] = useState('0.1');
  const m = data.data;
  const result = m?.budgets.find((r: Row) => String(r.fraction) === budget);
  return (
    <>
      <Status error={data.error} loading={!m} />
      {m && result && (
        <>
          <section className="panel evidence-section">
            <p className="eyebrow">OFFLINE DEVELOPMENT BENCHMARK</p>
            <h2>1. What this comparison establishes</h2>
            <p>
              Does adding three screening signals recover more constructed
              review-worthy cases at the same maximum review capacity?
            </p>
            <div className="overview-grid">
              <div>
                <h3>A — operational baseline</h3>
                <p>
                  Seven signals: recommendation pending, sanction delay,
                  long-open work, no observed payment, payment above sanction,
                  completion amount above sanction and repeated payment reports.
                </p>
              </div>
              <div>
                <h3>B — enhanced screening</h3>
                <p>
                  The same baseline plus historical peer-cost outliers, similar
                  work descriptions and March payment concentration. Production
                  rule weights and tie ordering are retained.
                </p>
              </div>
            </div>
            <p>
              <strong>
                {count(m.synthetic_pool)} synthetic cases ·{' '}
                {count(m.synthetic_positives)} labelled positive cases · seed{' '}
                {m.seed}
              </strong>
            </p>
            <p>
              This is a reproducible mechanism check, not a randomized live
              trial or evidence of real-world fraud-detection accuracy.
              Isolation Forest and DBSCAN are evaluated separately, not used as
              the two A/B arms.
            </p>
            <details>
              <summary>Full experimental design</summary>
              <p>{m.design}</p>
            </details>
          </section>
          <section className="panel evidence-section">
            <h2>2. Results and review workload</h2>
            <Pick
              label="Maximum review capacity"
              value={budget}
              onChange={setBudget}
              items={m.budgets.map((r: Row) => [
                String(r.fraction),
                percent(r.fraction),
              ])}
            />
            <div className="metric-grid">
              <Metric
                label="Baseline A recovery"
                value={percent(result.a_recovery)}
                note={`${result.a_reviewed} reviewed · ${result.a_false_alerts} false alerts`}
              />
              <Metric
                label="Enhanced B recovery"
                value={percent(result.b_recovery)}
                note={`${result.b_reviewed} reviewed · ${result.b_false_alerts} false alerts`}
              />
              <Metric
                label="Recovery difference (B − A)"
                value={`${(result.difference * 100).toFixed(1)} pp`}
                note="pp = percentage points"
              />
              <Metric
                label="Conditional 95% interval"
                value={`${(result.ci95[0] * 100).toFixed(1)} to ${(result.ci95[1] * 100).toFixed(1)}`}
                note="Percentage points; generated contexts only"
              />
            </div>
            <p>
              Capacity is a ceiling of {result.k} cases, not equal actual
              workload. Only positive-score cases are reviewed. Yield per
              review: A {percent(result.a_findings_per_review)}, B{' '}
              {percent(result.b_findings_per_review)}.
            </p>
            <p>
              {result.ci95[0] <= 0 && result.ci95[1] >= 0
                ? 'The interval includes zero: this benchmark does not demonstrate a stable recovery gain at this capacity.'
                : 'The interval excludes zero within these generated contexts only; it is not a real-world accuracy interval.'}{' '}
              A narrow or zero-width interval can result from repetitive
              constructed mechanisms, not certainty.
            </p>
            <h3>All capacity settings</h3>
            <Table>
              <TableHeader>
                <TableRow>
                  {[
                    'Capacity',
                    'A recovery',
                    'B recovery',
                    'A / B reviewed',
                    'A / B false alerts',
                    'A / B yield',
                  ].map((h) => (
                    <TableHead key={h}>{h}</TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {m.budgets.map((r: Row) => (
                  <TableRow key={r.fraction}>
                    <TableCell>
                      {percent(r.fraction)} ({r.k} max)
                    </TableCell>
                    <TableCell>{percent(r.a_recovery)}</TableCell>
                    <TableCell>{percent(r.b_recovery)}</TableCell>
                    <TableCell>
                      {r.a_reviewed} / {r.b_reviewed}
                    </TableCell>
                    <TableCell>
                      {r.a_false_alerts} / {r.b_false_alerts}
                    </TableCell>
                    <TableCell>
                      {percent(r.a_findings_per_review)} /{' '}
                      {percent(r.b_findings_per_review)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <p className="quiet">
              Recovery = selected synthetic positives ÷ all synthetic positives.
              Yield = selected positives ÷ actual reviewed cases. False alerts =
              reviewed synthetic negatives, including legitimate exceptions.
            </p>
          </section>
          <section className="panel evidence-section">
            <h2>3. Where the methods differ</h2>
            <p>
              Per-mechanism evidence at the selected {percent(result.fraction)}{' '}
              capacity. Counts are constructed cases, not confirmed real
              irregularities.
            </p>
            <Table>
              <TableHeader>
                <TableRow>
                  {[
                    'Injected mechanism',
                    'Positive cases',
                    'A selected',
                    'B selected',
                  ].map((h) => (
                    <TableHead key={h}>{h}</TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {result.scenarios.map((r: Row) => (
                  <TableRow key={r.scenario}>
                    <TableCell>{r.scenario}</TableCell>
                    <TableCell>{r.assigned}</TableCell>
                    <TableCell>
                      {r.a_selected} ({percent(r.a_selected / r.assigned)})
                    </TableCell>
                    <TableCell>
                      {r.b_selected} ({percent(r.b_selected / r.assigned)})
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <h3>Real dataset: agreement, not correctness</h3>
            <p>
              Unweighted top-k queue overlap is{' '}
              {percent(result.actual_queue_overlap)}. This Jaccard overlap
              compares selection sets; it does not measure accuracy, money saved
              or a real false-positive rate.
            </p>
          </section>
          <section className="panel evidence-section">
            <h2>4. Robustness and separate ML diagnostics</h2>
            <h3>Alternate generated seeds</h3>
            <p>
              Changing the generator seed probes sensitivity. These cases are
              not independent external validation.
            </p>
            <Table>
              <TableHeader>
                <TableRow>
                  {[
                    'Seed',
                    'Capacity',
                    'A recovery',
                    'B recovery',
                    'A / B false alerts',
                  ].map((h) => (
                    <TableHead key={h}>{h}</TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {m.seed_sensitivity.flatMap((seed: Row) =>
                  seed.budgets.map((r: Row) => (
                    <TableRow key={seed.seed + ':' + r.fraction}>
                      <TableCell>{seed.seed}</TableCell>
                      <TableCell>{percent(r.fraction)}</TableCell>
                      <TableCell>{percent(r.a_recovery)}</TableCell>
                      <TableCell>{percent(r.b_recovery)}</TableCell>
                      <TableCell>
                        {r.a_false_alerts} / {r.b_false_alerts}
                      </TableCell>
                    </TableRow>
                  )),
                )}
              </TableBody>
            </Table>
            {m.ml && (
              <>
                <h3>Unsupervised signals — in-sample synthetic diagnostics</h3>
                <p>
                  {m.ml.note} Models were fitted on the same constructed
                  snapshot. These are descriptive, not held-out predictive
                  scores.
                </p>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Isolation Forest capacity</TableHead>
                      <TableHead>Synthetic recovery</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {m.ml.isolation_forest_recovery.map((r: Row) => (
                      <TableRow key={r.fraction}>
                        <TableCell>{percent(r.fraction)}</TableCell>
                        <TableCell>{percent(r.recovery)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
                <p>
                  DBSCAN: {count(m.ml.dbscan.flagged)} outliers;{' '}
                  {count(m.ml.dbscan.positives_flagged)} labelled positives
                  among them; synthetic precision{' '}
                  {percent(m.ml.dbscan.precision)}, recall{' '}
                  {percent(m.ml.dbscan.recall)}.
                </p>
              </>
            )}
          </section>
          <section className="panel evidence-section">
            <h2>5. Evidence and reproduction</h2>
            <ol>
              <li>Inspect source coverage and hashes on Data & research.</li>
              <li>
                Open Project status & tools, run checks and re-run the A/B
                comparison locally.
              </li>
              <li>
                Compare the metrics, scored cases and release manifest below.
                Independent rebuild is available in the same tools page.
              </li>
            </ol>
            <button onClick={onTools}>Open local validation tools</button>
            <div className="evidence-links">
              <DownloadLink file="AB_Report.md">Methods report</DownloadLink>
              <DownloadLink file="ab_metrics.json">
                Metrics and seeds
              </DownloadLink>
              <DownloadLink file="ab_actual_scores.csv">
                Synthetic scored cases
              </DownloadLink>
              <DownloadLink file="ab_controlled_benchmark.csv">
                Controlled benchmark
              </DownloadLink>
              <DownloadLink file="release_manifest.json">
                Release manifest
              </DownloadLink>
            </div>
            <p className="quiet">
              Benchmark version: {m.version}. Data remains local. Downloads are
              supporting evidence; the main results are readable above without a
              terminal.
            </p>
          </section>
          <section className="panel evidence-section">
            <h2>6. Limits and the next validation gate</h2>
            <ul>
              {m.limitations.map((v: string) => (
                <li key={v}>{v.replaceAll('\\u2014', '—')}</li>
              ))}
            </ul>
            <p>
              Before operational rollout, freeze the methods, obtain
              independently adjudicated cases, and run a prospective review
              study with measured reviewer effort and missed-case sampling. Do
              not present this synthetic comparison as that study.
            </p>
          </section>
        </>
      )}
    </>
  );
}

function Sources({ meta }: { meta: Row }) {
  const [query, setQuery] = useState('');
  const [offset, setOffset] = useState(0);
  const dictionary = useData<Row>(
    '/api/table?' +
      new URLSearchParams({
        kind: 'dictionary',
        q: query,
        offset: String(offset),
      }),
  );

  return (
    <>
      <div className="panel">
        <div className="panel-head">
          <div>
            <h2>1. Source coverage and traceability</h2>
            <p>
              {meta.scope}. Assessment date {meta.as_of}; source extraction
              timestamps were not supplied.
            </p>
          </div>
        </div>
        <div style={{ overflowX: 'auto' }}>
          <Table>
            <TableHeader>
              <TableRow>
                {['Source', 'Original records', 'Accepted', 'Quarantined'].map(
                  (v) => (
                    <TableHead key={v}>{v}</TableHead>
                  ),
                )}
              </TableRow>
            </TableHeader>
            <TableBody>
              {meta.sources.map((r: Row, i: number) => (
                <TableRow key={i}>
                  <TableCell className="record-title">{r.file}</TableCell>
                  <TableCell>{count(r.rows)}</TableCell>
                  <TableCell>{count(r.accepted_rows)}</TableCell>
                  <TableCell>{r.quarantined_rows}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
        <p className="section-note">
          One expenditure record is truncated. Repeated payment fingerprints
          remain in reported sums. Missing documents or payments do not
          establish ghost assets, misuse or unpaid liabilities.
        </p>
        <p className="section-note">
          <DownloadLink file="MPLADS_Review.xlsx">
            Excel review workbook
          </DownloadLink>{' '}
          &nbsp;{' '}
          <DownloadLink file="audit.json">Audit & source hashes</DownloadLink>{' '}
          &nbsp;{' '}
          <DownloadLink file="Quarantine.csv">Quarantined record</DownloadLink>
        </p>
      </div>
      <section className="panel evidence-section">
        <h2>2. How the connected dataset is prepared</h2>
        <ol>
          <li>
            Preserve and hash the six export types for each cohort (18 source
            files).
          </li>
          <li>
            Normalize money to integer paise, parse dates, namespace reused work
            IDs by cohort and MP, and quarantine invalid records.
          </li>
          <li>
            Link recommended, sanctioned and completed work membership; attach
            payment evidence without multiplying work rows.
          </li>
          <li>
            Derive lifecycle, timing, finance, historical peer cost,
            text-similarity and authority/vendor concentration features.
          </li>
          <li>
            Keep interpretable rule priority separate from unsupervised
            atypicality. Validate reconciliation and seal the analytical
            release.
          </li>
        </ol>
        <p>
          Use the dictionary below for exact definitions, units and
          availability. An absent export row is missing evidence, not proof of
          an absent physical asset.
        </p>
      </section>
      <section className="panel evidence-section">
        <h2>3. Research register and design decisions</h2>
        <p>
          Each source is linked to the implementation decision it informed.
          Source dates are publication or reference dates, not dataset
          extraction timestamps.
        </p>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Source</TableHead>
              <TableHead>Date</TableHead>
              <TableHead>How it informs the solution</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {meta.research.map((r: Row) => (
              <TableRow key={r.id}>
                <TableCell>
                  <a
                    className="text-link"
                    href={r.url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {r.title}
                  </a>
                </TableCell>
                <TableCell>{r.date}</TableCell>
                <TableCell>{r.use}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </section>
      <div className="panel">
        <div className="panel-head">
          <div>
            <h2>4. Feature dictionary</h2>
          </div>
          <input
            className="dictionary-search s6-input"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setOffset(0);
            }}
            aria-label="Search all feature definitions"
            placeholder="Field, table, definition or unit"
          />
        </div>
        <Status error={dictionary.error} loading={!dictionary.data} />
        {dictionary.data && (
          <>
            <div style={{ overflowX: 'auto' }}>
              <Table server>
                <TableHeader>
                  <TableRow>
                    {['Table / field', 'Definition', 'Unit / availability'].map(
                      (v) => (
                        <TableHead key={v}>{v}</TableHead>
                      ),
                    )}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {dictionary.data.items.map((r: Row) => (
                    <TableRow key={r.table + r.field}>
                      <TableCell className="record-title">
                        {r.table}
                        <small className="record-meta">{r.field}</small>
                      </TableCell>
                      <TableCell>{r.definition}</TableCell>
                      <TableCell>
                        {r.unit}
                        <small className="record-meta">{r.availability}</small>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
            <Pager
              total={dictionary.data.total}
              offset={offset}
              onChange={setOffset}
            />
          </>
        )}
      </div>
      <section className="panel evidence-section">
        <h2>5. Evidence limits and responsible interpretation</h2>
        <ul>
          {meta.limits.map((v: string) => (
            <li key={v}>{v}</li>
          ))}
        </ul>
        <p>
          Official use still requires authenticated reviewer roles, independent
          outcome validation, and current boundary certification. This local
          prototype does not replace documentary or site verification.
        </p>
      </section>
    </>
  );
}

const JOB_TONE: Record<string, string> = {
  queued: '#647788',
  running: '#916710',
  completed: '#287c72',
  failed: '#ae494f',
};
function JobControl({
  name,
  title,
  job,
  onRun,
  blocked,
}: {
  blocked: boolean;
  name: string;
  title: string;
  job: Row | undefined;
  onRun: (n: string) => void;
}) {
  const busy = job && ['queued', 'running'].includes(job.state);
  const when = job?.finished || job?.started || job?.created;
  return (
    <div className="job-row">
      <div className="job-main">
        <strong>{title}</strong>
        {job && (
          <small className="record-meta">
            {job.state}
            {job.exit_code != null ? ` · exit ${job.exit_code}` : ''}
            {when ? ` · ${new Date(when).toLocaleString()}` : ''}
            {job.log?.length ? ` · ${job.log[job.log.length - 1]}` : ''}
          </small>
        )}
        {job?.error && <p role="alert">{job.error}</p>}
        {!!job?.log?.length && (
          <details>
            <summary>Job log</summary>
            <pre
              style={{
                whiteSpace: 'pre-wrap',
                maxHeight: 240,
                overflow: 'auto',
              }}
            >
              {job.log.join('\n')}
            </pre>
          </details>
        )}
        {busy ? (
          <div className="bar-track" style={{ marginTop: 8 }}>
            <i
              style={{
                width: `${Math.round((job.progress || 0) * 100) || 8}%`,
              }}
            />
          </div>
        ) : null}
      </div>
      <div className="job-side">
        {job && (
          <span
            className="band"
            style={{
              background: 'transparent',
              color: JOB_TONE[job.state] || '#647788',
            }}
          >
            ● {job.state}
          </span>
        )}
        <button
          onClick={() => onRun(name)}
          disabled={!!busy || blocked}
          aria-label={'Run ' + title}
        >
          {busy ? 'Running…' : 'Run'}
        </button>
      </div>
    </div>
  );
}
function StatusTools() {
  const [statusRevision, setStatusRevision] = useState(0);
  const [jobError, setJobError] = useState('');
  const status = useData<Row>('/api/status', statusRevision);
  const [rev, setRev] = useState(0);
  const jobs = useData<Row>('/api/jobs', rev);
  useEffect(() => {
    const running = (jobs.data?.jobs || []).some((j: Row) =>
      ['queued', 'running'].includes(j.state),
    );
    if (!running) return;
    const t = setInterval(() => setRev((r) => r + 1), 2500);
    return () => clearInterval(t);
  }, [jobs.data]);
  async function run(name: string) {
    try {
      const r = await fetch('/api/jobs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name }),
      });
      const result = await r.json();
      if (!r.ok) throw new Error(result.error || 'Job request failed');
      setJobError('');
    } catch (e) {
      setJobError(e instanceof Error ? e.message : 'Job request failed');
    }
    setRev((r) => r + 1);
  }
  const finishedStamp = (jobs.data?.jobs || [])
    .map((j: Row) => j.finished || '')
    .join('|');
  useEffect(() => {
    if (!finishedStamp) return;
    const t = setTimeout(() => setStatusRevision((r) => r + 1), 0);
    return () => clearTimeout(t);
  }, [finishedStamp]);
  const s = status.data;
  const latest: Record<string, Row> = {};
  for (const j of jobs.data?.jobs || [])
    if (!latest[j.name]) latest[j.name] = j;
  const available: Row[] = jobs.data?.available || [];
  const repro = s?.reproducibility;
  const testsJob = latest['tests'];
  const dl = (file: string, label: string, ok: boolean) =>
    ok ? (
      <DownloadLink file={file}>{label}</DownloadLink>
    ) : (
      <span className="quiet">{label} — not generated</span>
    );
  return (
    <>
      <Status error={status.error || jobError} loading={!s} card />
      {s && (
        <>
          <div className="metric-grid">
            <Metric
              label="Release version"
              value={
                <span style={{ fontSize: 15, wordBreak: 'break-all' }}>
                  {s.active_release || String(s.version).slice(0, 24)}
                </span>
              }
              note={`as of ${s.as_of}`}
            />
            <Metric
              label="Cohorts"
              value={String((s.cohorts || []).length)}
              note={(s.cohorts || [])
                .map((c: string) => COHORT_LABEL[c] || c)
                .join(', ')}
            />
            <Metric
              label="Reconciliation"
              value={s.all_checks_passed ? '21 / 21 passed' : 'FAILED'}
              note={s.all_checks_passed ? 'build gate green' : 'do not use'}
            />
            <Metric
              label="Source verification"
              value={s.source_fresh ? 'Verified' : 'STALE'}
              note={s.source_fresh ? 'hashes match the build' : s.stale_reason}
            />
          </div>

          <div className="panel">
            <div className="panel-head">
              <div>
                <h2>Dataset inventory & source verification</h2>
                <p>
                  Immutable source files, per cohort, with accepted vs
                  quarantined records and content hashes.
                </p>
              </div>
            </div>
            <div style={{ overflowX: 'auto' }}>
              <Table>
                <TableHeader>
                  <TableRow>
                    {[
                      'Cohort',
                      'File',
                      'Records',
                      'Accepted',
                      'Quarantined',
                      'SHA-256',
                    ].map((h) => (
                      <TableHead key={h}>{h}</TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {(s.sources || []).map((r: Row, i: number) => (
                    <TableRow key={i}>
                      <TableCell>{r.cohort}</TableCell>
                      <TableCell className="record-title">{r.file}</TableCell>
                      <TableCell>{count(r.rows)}</TableCell>
                      <TableCell>{count(r.accepted)}</TableCell>
                      <TableCell>{r.quarantined}</TableCell>
                      <TableCell>
                        <small
                          className="record-meta"
                          style={{ wordBreak: 'break-all' }}
                        >
                          {String(r.sha256).slice(0, 16)}…
                        </small>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
            <p className="section-note">{s.scope}</p>
          </div>

          <div className="overview-grid">
            <div className="panel">
              <div className="panel-head">
                <div>
                  <h2>Financial & lifecycle summary</h2>
                </div>
              </div>
              <dl className="s6-facts" style={{ padding: '4px 24px 18px' }}>
                {[
                  ['Works', count(s.totals.works)],
                  ['Sanctioned', crore(s.totals.sanction_paise)],
                  [
                    'Settled (reported)',
                    crore(s.totals.successful_payment_paise),
                  ],
                  [
                    'In-progress (excluded)',
                    crore(s.totals.pending_payment_paise),
                  ],
                  ['Reported complete', count(s.totals.completions)],
                  [
                    'Priority bands',
                    Object.entries(s.priority_counts || {})
                      .map(([k, v]) => `${k} ${display(v)}`)
                      .join(' · '),
                  ],
                ].map(([l, v]) => (
                  <div key={String(l)}>
                    <dt>{l}</dt>
                    <dd>{v}</dd>
                  </div>
                ))}
              </dl>
            </div>
            <div className="panel">
              <div className="panel-head">
                <div>
                  <h2>Reproducibility & tests</h2>
                  <p>Tied to this exact release version.</p>
                </div>
              </div>
              <dl className="s6-facts" style={{ padding: '4px 24px 8px' }}>
                <div>
                  <dt>Reproducibility</dt>
                  <dd>
                    {repro
                      ? repro.reproducible
                        ? `Byte-identical (${Object.keys(repro.artifacts || {}).length} artifacts)`
                        : 'MISMATCH'
                      : 'Not run — use “Run” below'}
                  </dd>
                </div>
                <div>
                  <dt>Checked</dt>
                  <dd>
                    {repro?.generated
                      ? new Date(repro.generated).toLocaleString()
                      : '—'}
                  </dd>
                </div>
                <div>
                  <dt>Tests</dt>
                  <dd>
                    {s.tests
                      ? s.tests.passed
                        ? 'Passed for this release'
                        : 'Failed for this release'
                      : testsJob
                        ? testsJob.state === 'completed'
                          ? 'Passed'
                          : testsJob.state === 'failed'
                            ? 'Failed'
                            : testsJob.state
                        : 'Not run this session'}
                  </dd>
                </div>
              </dl>
              <p className="section-note">
                Reproducibility rebuilds into a separate release directory and
                compares hashes; it does not touch the running data.
              </p>
            </div>
          </div>

          <div className="panel">
            <div className="panel-head">
              <div>
                <h2>Tools — run checks & prepare outputs</h2>
                <p>
                  These start a background job on this machine (compute),
                  distinct from viewing existing results. Maintenance jobs run
                  one at a time. Reload other views after activating a new
                  release.
                </p>
              </div>
            </div>
            <div style={{ padding: '4px 20px 16px' }}>
              {available.map((a: Row) => (
                <JobControl
                  key={a.name}
                  name={a.name}
                  title={a.title}
                  job={latest[a.name]}
                  blocked={(jobs.data?.jobs || []).some((j: Row) =>
                    ['queued', 'running'].includes(j.state),
                  )}
                  onRun={run}
                />
              ))}
            </div>
            <Status error={jobs.error} loading={false} />
          </div>

          <div className="panel">
            <div className="panel-head">
              <div>
                <h2>Downloads — datasets, reports & evidence</h2>
              </div>
            </div>
            <div
              style={{
                display: 'flex',
                flexWrap: 'wrap',
                gap: '12px 22px',
                padding: '8px 24px 20px',
              }}
            >
              {dl(
                'MPLADS_Review.xlsx',
                'Excel review workbook',
                s.artifacts.workbook.available,
              )}
              {dl('Work_Features.csv', 'Work features (CSV)', true)}
              {dl('Payment_Features.csv', 'Payments (CSV)', true)}
              {dl(
                'Duplicate_Candidates.csv',
                'Duplicate candidates (CSV)',
                true,
              )}
              {dl('Feature_Dictionary.csv', 'Feature dictionary (CSV)', true)}
              {dl(
                'Quarantine.csv',
                'Quarantined record (CSV)',
                s.artifacts.quarantine.available,
              )}
              {dl(
                'audit.json',
                'Audit & source hashes',
                s.artifacts.audit.available,
              )}
              {dl(
                'AB_Report.md',
                'A/B methods & results',
                s.artifacts.ab_metrics.available,
              )}
              {dl(
                'ab_controlled_benchmark.csv',
                'A/B per-family (CSV)',
                s.artifacts.ab_metrics.available,
              )}
              {dl(
                'ab_actual_scores.csv',
                'A/B synthetic scored cases',
                s.artifacts.ab_metrics.available,
              )}
              {dl(
                'reproducibility.json',
                'Reproducibility manifest',
                s.artifacts.reproducibility.available,
              )}
              <DownloadLink file="Rule_Contributions.csv">
                Per-rule explanations
              </DownloadLink>
              <DownloadLink file="IDA_Year_Concentration.csv">
                Vendor concentration
              </DownloadLink>
              <DownloadLink file="DATA_PATTERNS.md">
                Data patterns report
              </DownloadLink>
              <DownloadLink file="forecast.json">
                Forecast and chronological tests
              </DownloadLink>
            </div>
          </div>

          <div className="panel">
            <div className="panel-head">
              <div>
                <h2>Methodology & evidence limits</h2>
              </div>
            </div>
            <div style={{ padding: '4px 24px 20px' }}>
              <h3 style={{ marginTop: 8 }}>
                Rule registry (disclosed weights)
              </h3>
              <div style={{ overflowX: 'auto' }}>
                <Table>
                  <TableHeader>
                    <TableRow>
                      {['Screen', 'Weight', 'Reason', 'Required caution'].map(
                        (h) => (
                          <TableHead key={h}>{h}</TableHead>
                        ),
                      )}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {(s.rules || []).map((r: Row) => (
                      <TableRow key={r.field}>
                        <TableCell className="record-title">
                          {r.field}
                        </TableCell>
                        <TableCell>{r.weight}</TableCell>
                        <TableCell>{r.reason}</TableCell>
                        <TableCell className="quiet">{r.caution}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
              <h3>Evidence limits</h3>
              <ul className="quiet" style={{ paddingLeft: 20 }}>
                {(s.limits || []).map((l: string) => (
                  <li key={l} style={{ margin: '6px 0' }}>
                    {l}
                  </li>
                ))}
              </ul>
              <h3>Research used in the design</h3>
              {(s.research || []).map((r: Row) => (
                <p key={r.id} className="quiet" style={{ margin: '8px 0' }}>
                  <a
                    className="text-link"
                    href={r.url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {r.title}
                  </a>{' '}
                  · {r.date}
                  <br />
                  {r.use}
                </p>
              ))}
            </div>
          </div>

          <div className="panel">
            <div className="panel-head">
              <div>
                <h2>Help — investigate a work & record a review</h2>
              </div>
            </div>
            <div
              className="quiet"
              style={{ padding: '4px 24px 22px', lineHeight: 1.7 }}
            >
              <p>
                <strong>Find works:</strong> open <em>Work investigation</em>,
                filter by state, financial year, lifecycle or an investigation{' '}
                <em>signal</em> (e.g. open beyond one year, cost outlier), or
                type in the search box.
              </p>
              <p>
                <strong>Inspect evidence:</strong> click a work to open its
                evidence drawer — lifecycle dates, a financial reconciliation,
                the <em>reason codes</em> that put it in the queue (each with a
                required caution), the historical cost comparison, the payment
                ledger and any similar-work candidates.
              </p>
              <p>
                <strong>Record a review:</strong> in the drawer, choose a
                disposition (Needs evidence · Expected variation · Data issue ·
                Substantiated issue), write an evidence note, and save. Reviews
                are stored locally on this computer, tied to this dataset
                version, and are preserved across rebuilds — they are never
                uploaded.
              </p>
              <p>
                <strong>Remember:</strong> no score here is a finding of fraud.
                Every alert is a request for evidence and human review;
                unavailable checks are shown as unavailable, not passed.
              </p>
            </div>
          </div>
        </>
      )}
    </>
  );
}

function App() {
  const meta = useData<Row>('/api/meta');
  const [view, setView] = useState('overview');
  useEffect(() => {
    // A new workspace page should begin with its title and explanation.
    window.scrollTo(0, 0);
  }, [view]);
  const [selected, setSelected] = useState<string | null>(null);
  const [entity, setEntity] = useState<Row>({});
  const [profileSelection, setProfileSelection] = useState<{
    kind: string;
    key: string;
  } | null>(null);
  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    try {
      return (
        (localStorage.getItem('mplads-theme') as 'light' | 'dark') || 'light'
      );
    } catch {
      return 'light';
    }
  });
  useEffect(() => {
    try {
      document.documentElement.dataset.theme = theme;
      localStorage.setItem('mplads-theme', theme);
    } catch {}
  }, [theme]);
  function inspect(key: string, value: string) {
    if (['ida', 'mp', 'vendor'].includes(key)) {
      setSelected(null);
      setProfileSelection({ kind: key, key: value });
      return;
    }
    setEntity({ [key]: value });
    setSelected(null);
    setView('queue');
  }
  const cohorts = (meta.data?.cohorts || [])
    .map((c: string) => COHORT_LABEL[c] || c)
    .join(' · ');
  const [desc, eyebrow] = HEAD[view];
  const label = NAV.find((n) => n[0] === view)?.[1] || '';
  return (
    <SidebarProvider
      style={{ '--sidebar-width': '15.5rem' } as React.CSSProperties}
    >
      <Sidebar className="app-sidebar">
        <SidebarHeader className="brand">
          <div className="brand-symbol">
            <ShieldCheck size={25} />
          </div>
          <div>
            <strong>
              MPLADS<span>GUARD</span>
            </strong>
            <small>Investigation workspace</small>
          </div>
        </SidebarHeader>
        <SidebarContent>
          <p className="nav-caption">WORKSPACE</p>
          <WorkspaceNavigation view={view} navigate={setView} />
        </SidebarContent>
        <SidebarFooter>
          <div className="sidebar-source">
            <span className="connection-dot" />
            Local source connected<small>{cohorts || 'MPLADS'}</small>
            {meta.data && (
              <small>
                {count(meta.data.totals.works)} works · as of {meta.data.as_of}
              </small>
            )}
          </div>
          <div className="sidebar-foot">
            PS 26102 <span>Local</span>
          </div>
        </SidebarFooter>
      </Sidebar>
      <SidebarInset className="app-main">
        <header className="topbar">
          <div>
            <SidebarTrigger />
            <span className="crumb">
              MPLADS / <strong>{label}</strong>
            </span>
          </div>
          <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
            <span className="environment-pill">
              <span />
              Local processing · review signals, not findings of fraud
            </span>
            <button
              className="theme-toggle"
              onClick={() => setTheme((t) => (t === 'dark' ? 'light' : 'dark'))}
              aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
            >
              {theme === 'dark' ? <Sun size={15} /> : <Moon size={15} />}
              <span>{theme === 'dark' ? 'Light' : 'Dark'}</span>
            </button>
          </div>
        </header>
        <main className="main-content">
          <div className="page-heading">
            <div>
              <p className="eyebrow">{eyebrow}</p>
              <h1>{label}</h1>
              <p className="page-description">{desc}</p>
            </div>
            {view === 'overview' && meta.data && (
              <DownloadLink file="audit.json">National audit</DownloadLink>
            )}
          </div>
          {meta.error ? (
            <div className="s6-empty">
              <CircleAlert size={26} />
              <span>
                <strong>The local backend is not responding.</strong>
              </span>
              <span className="quiet">
                Start it with the launcher — run <code>run.ps1</code> (or
                double-click <code>START.cmd</code>) in the project folder, then
                reload this page. This page cannot start the backend for you.
              </span>
            </div>
          ) : !meta.data ? (
            <div role="status">
              <Skeleton card />
            </div>
          ) : null}
          {meta.data && (
            <>
              {view === 'overview' && <Overview inspect={inspect} />}
              {view === 'ask' && <Ask inspect={inspect} />}
              {view === 'queue' && (
                <Queue
                  key={JSON.stringify(entity)}
                  open={setSelected}
                  entity={entity}
                  clearEntity={() => setEntity({})}
                />
              )}
              {view === 'mp' && <MPView open={setSelected} />}
              {view === 'entities' && <Entities inspect={inspect} />}
              {view === 'pairs' && <Pairs open={setSelected} />}
              {view === 'validation' && (
                <Validation onTools={() => setView('status')} />
              )}
              {view === 'sources' && <Sources meta={meta.data} />}
              {view === 'status' && <StatusTools />}
              {view === 'cases' && <CaseRegister open={setSelected} />}
              {view === 'insights' && <Insights inspect={inspect} />}
            </>
          )}
          <footer className="workspace-footer">
            <div>
              Local research prototype · no officer authentication or audit
              certification.
            </div>
            <a
              className="text-link"
              href="/api/reviews"
              target="_blank"
              rel="noreferrer"
            >
              Export local review history
            </a>
          </footer>
        </main>
        <EntityProfile
          entity={profileSelection}
          close={() => setProfileSelection(null)}
          works={(kind, key) => {
            setProfileSelection(null);
            setSelected(null);
            setEntity({ [kind]: key });
            setView('queue');
          }}
        />
        <WorkEvidence
          key={selected || 'closed'}
          id={selected}
          onClose={() => setSelected(null)}
          onWork={setSelected}
          onEntity={inspect}
        />
      </SidebarInset>
    </SidebarProvider>
  );
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
