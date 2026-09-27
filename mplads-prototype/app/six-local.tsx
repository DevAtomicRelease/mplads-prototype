import {
  StrictMode,
  createContext,
  useContext,
  useEffect,
  useState,
} from 'react';
import { EntityProfile } from './entity-profile';
import { IndiaMap } from './india-map';
import { ruleText } from '../lib/plain-text';
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
  ['open_over_one_year_flag', 'Still open after one year'],
  ['no_payment_three_months_flag', 'No payment seen after 3 months'],
  ['pending_recommendation_45d_flag', 'Recommendation waiting over 45 days'],
  ['sanction_delay_45d_flag', 'Sanctioned over 45 days after recommendation'],
  ['repeat_payment_report_flag', 'Same payment reported more than once'],
  ['march_rush_flag', 'Most money paid in March (year-end)'],
  ['high_cost_peer_flag', 'Costs much more than similar earlier works'],
  ['high_similarity_review_flag', 'Almost the same description as another work'],
  ['dbscan_outlier_flag', 'Unusual pattern (machine learning, DBSCAN)'],
  ['paid_over_sanction_flag', 'More paid than sanctioned'],
  ['completion_over_sanction_flag', 'Final cost more than sanctioned'],
  ['completion_without_payment_flag', 'Completed, but no payment seen'],
  ['description_changed_flag', 'Description changed at completion'],
  ['recommendation_missing_flag', 'No recommendation record found'],
];
const LIFECYCLE_LABEL: Record<string, string> = {
  'Not in sanction export': 'Recommended, not yet sanctioned',
  'Sanctioned / open': 'Sanctioned, still open',
  'Reported complete': 'Reported complete',
};
const life = (v: unknown) => LIFECYCLE_LABEL[String(v)] ?? display(v);
// True when the server is a hosted, read-only demo copy (no review saving or tools).
const ReadOnly = createContext(false);
// Plain-language version of the release's evidence limits. The exact original
// sentences stay available under “Exact wording”.
const PLAIN_LIMITS = [
  'The data has no officially confirmed fraud cases, transaction IDs, invoices, revised-sanction records, quantities, approved due dates or full progress history.',
  '“Payment Success” rows are counted as paid. “Payment In-Progress” rows are shown separately and never added in. Repeated report lines are kept as reported.',
  'There are no SC/ST area tags, trust register, work locations or photos, so those checks are shown as not checked — never as passed.',
  'The final cost and the vendor payments can differ for normal reasons (what the report covers, tax, retention, timing). A difference is not treated as fraud.',
  'The data, results and review notes all stay on this computer. Nothing is published.',
  'The machine-learning score only says how unusual a work is compared with others. It is separate from the flag score and is not a prediction.',
];
function Limits({ items, className }: { items: string[]; className?: string }) {
  return (
    <>
      <ul className={className}>
        {PLAIN_LIMITS.map((v) => (
          <li key={v} style={{ margin: '6px 0' }}>
            {v}
          </li>
        ))}
      </ul>
      {!!items.length && (
        <details>
          <summary>Exact wording from the data release</summary>
          <ul className="quiet">
            {items.map((v) => (
              <li key={v}>{v}</li>
            ))}
          </ul>
        </details>
      )}
    </>
  );
}

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
    'Who is reviewing which work, by when, and what they found — kept even when the data is updated.',
    'REVIEW WORKFLOW',
  ],
  insights: [
    'Which vendors get most of an authority’s money, other patterns, and a simple payment forecast.',
    'ANALYSIS',
  ],
  overview: [
    'A national-to-local view of the works that need a closer look.',
    'MONITOR · INVESTIGATE · REVIEW',
  ],
  ask: [
    'Type a question in plain English. Answers are worked out on this computer from the loaded data.',
    'LOCAL QUERY',
  ],
  queue: [
    'See each work’s full story in one place: recommendation, sanction, completion and payments.',
    'CASE QUEUE',
  ],
  mp: [
    'For each MP: money allocated, how much has been spent, progress, and works that need a look.',
    'MEMBER VIEW',
  ],
  entities: [
    'Full profiles of MPs, district authorities and vendors, using all the loaded data.',
    'CONNECTED ENTITIES',
  ],
  pairs: [
    'Works in the same district and category with almost the same description, side by side.',
    'DUPLICATE REVIEW',
  ],
  validation: [
    'A test on sample data: do three extra checks help reviewers catch more problems?',
    'EVALUATION',
  ],
  sources: [
    'Where the data comes from, what each field means, what we cannot check, and the research we used.',
    'PROVENANCE',
  ],
  status: [
    'Data details, automatic checks, how scoring works, downloads and maintenance tools.',
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
// keepPrevious: while a new URL loads, keep showing the last successful data
// (marked stale) instead of unmounting the view — used where a click refines
// the same page, e.g. picking a state on the Overview map.
function useData<T>(url: string | null, revision = 0, keepPrevious = false) {
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
  if (result?.url === url && result?.revision === revision)
    return { ...result, stale: false };
  if (keepPrevious && result?.data && !result.error)
    return { data: result.data, error: '', stale: true };
  return { data: null, error: '', stale: false };
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
  const readOnly = useContext(ReadOnly);
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
            Facts taken from the source files to help you investigate. This is
            not a finding of misuse.
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
                      ? 'From the recommendation file'
                      : 'No recommendation record; date taken from sanction',
                  ],
                  ['Sanctioned', w.sanction_date, 'From the sanction file'],
                  ['Reported complete', w.completion_date, 'From the completion file'],
                ].map(([name, date, source]) => (
                  <div key={name}>
                    <strong>{name}</strong>
                    <span>{date || 'Not observed'}</span>
                    <small>{source}</small>
                  </div>
                ))}
              </div>
              <h3>Money: sanctioned and paid</h3>
              <dl className="s6-facts">
                {[
                  ['Recommended', w.recommended_amount_paise],
                  ['Sanctioned', w.sanction_amount_paise],
                  [
                    'Paid (reported as successful)',
                    w.has_successful_payment_evidence
                      ? w.successful_payment_paise
                      : null,
                  ],
                  [
                    'Payments still in progress (not yet paid)',
                    w.pending_payment_paise,
                  ],
                  ['Final cost reported at completion', w.completion_actual_paise],
                  [
                    'Paid, counting repeated report lines once',
                    w.has_successful_payment_evidence
                      ? w.unique_fingerprint_sensitivity_paise
                      : null,
                  ],
                  [
                    'Final cost minus payments seen',
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
                If no payment is shown, that does not mean nothing was paid —
                the report may be incomplete. “Counting repeated report lines
                once” is a check, not a corrected total. A gap between final cost
                and payments needs invoices, tax/retention details and a check
                of what the reports cover.
              </p>
              <h3>
                Why this work was flagged · score {w.priority_score} out of 100
              </h3>
              {detail.data!.reasons.length ? (
                <ul className="s6-reasons">
                  {detail.data!.reasons.map((r: Row) => {
                    const [why, check] = ruleText(r.rule, r.reason, r.caution);
                    return (
                      <li key={r.rule}>
                        <strong>
                          +{r.points} · {why}
                        </strong>
                        <span>Next step: {check}</span>
                      </li>
                    );
                  })}
                </ul>
              ) : (
                <p>
                  No check was triggered. This does not mean the work has been
                  verified as problem-free.
                </p>
              )}
              <p>
                Machine-learning “unusualness” score:{' '}
                <strong>{Number(w.isolation_percentile).toFixed(1)}</strong> out
                of 100 (higher means more unusual than other works; Isolation
                Forest)
                {w.dbscan_outlier_flag
                  ? '. DBSCAN also marks it as an unusual pattern'
                  : ''}
                . These are separate from the flag score above. They are not a
                fraud probability or a prediction.
              </p>
              <h3>Cost compared with similar earlier works</h3>
              <dl className="s6-facts">
                <div>
                  <dt>Compared with</dt>
                  <dd>
                    {w.peer_level} · {count(w.peer_count)} earlier-year works
                  </dd>
                </div>
                <div>
                  <dt>Typical (median) cost</dt>
                  <dd>
                    {w.peer_median_inr == null
                      ? 'Not available'
                      : rupees(w.peer_median_inr * 100)}
                  </dd>
                </div>
                <div>
                  <dt>This work vs typical</dt>
                  <dd>
                    {w.cost_peer_ratio == null
                      ? 'Not available'
                      : Number(w.cost_peer_ratio).toFixed(2) + '×'}
                  </dd>
                </div>
              </dl>
              <p className="quiet">
                Only works from earlier years are used for the comparison. It
                compares total amounts, not cost per unit — a bigger work may
                simply cost more.
              </p>
              <h3>Payments</h3>
              <TableSearch
                value={paymentSearch}
                onChange={(v) => {
                  setPaymentSearch(v);
                  setPaymentOffset(0);
                }}
                label="Search all payments"
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
                          'Times in report',
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
                              Vendor ID {p.vendor_id} · record {p.source_record}
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
              <h3>Works with similar descriptions</h3>
              <p className="quiet">
                Up to 100 are shown here. Download the similar-works list for
                all of them.
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
                    {percent(p.similarity)} similar
                    {p.number_conflict ? ' · different numbers in the text' : ''}
                    {p.continuation_cue ? ' · looks like a next phase or extension' : ''}
                  </button>
                ))
              ) : (
                <p>
                  No similar work found. The search does not compare every
                  possible pair, so some may be missed.
                </p>
              )}
              <h3>Record your review</h3>
              {readOnly && (
                <p className="quiet">
                  This is a read-only demo copy, so reviews cannot be saved
                  here. Run the app on your own computer to record reviews.
                </p>
              )}
              {!readOnly && reviews.data && (
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
                        ? ' · Saved on an older data version — check the evidence again'
                        : ''}
                    </small>
                    <p>{r.note}</p>
                  </div>
                ))}
              <details>
                <summary>
                  All {Object.keys(w).length} data fields for this work
                  (technical)
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
    0,
    true,
  );
  const months = useData<Row>('/api/months');
  const n = data.data?.national;
  const d = data.data;
  const settledFrac = (r: Row) =>
    r.sanction_paise > 0 ? r.successful_payment_paise / r.sanction_paise : null;
  const topStates = (d?.states || []).slice(0, 10).map((s: Row) => ({
    name: s.state.length > 12 ? s.state.slice(0, 11) + '…' : s.state,
    'High priority': s.high,
  }));
  const trend = (months.data?.items || []).map((m: Row) => ({
    month: m.payment_month,
    'Paid (₹ crore)': Math.round(m.successful_payment_paise / 1e7) / 100,
  }));
  const idas = state ? d?.idas : d?.top_idas;
  return (
    <>
      <Status error={data.error} loading={!n} card />
      {n && (
        <>
          <div className="metric-grid">
            <Metric label="Works in the data" value={count(n.works)} />
            <Metric label="Flagged high priority" value={count(n.high)} />
            <Metric label="Sanctioned" value={crore(n.sanction_paise)} />
            <Metric
              label="Share of sanctioned money paid"
              value={percent(settledFrac(n))}
              note={`${crore(n.successful_payment_paise)} paid`}
            />
            <Metric
              label="Still open after one year"
              value={count(n.open_over_year)}
            />
            <Metric
              label="No payment seen after 3 months"
              value={count(n.no_payment_3m)}
            />
            <Metric label="MPs with works" value={count(n.mp_count)} />
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
                  {count(c.high)} high priority · {crore(c.sanction_paise)}{' '}
                  sanctioned · {percent(settledFrac(c))} paid
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
                    <Bar
                      dataKey="High priority"
                      fill="#c96263"
                      radius={[3, 3, 0, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
            <div className="panel">
              <div className="panel-head">
                <div>
                  <h2>Money paid each month (₹ crore)</h2>
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
                      dataKey="Paid (₹ crore)"
                      stroke="#2f7f91"
                      dot={false}
                      strokeWidth={2}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <p className="section-note">
                Shows when payments were reported. The latest month is not
                complete yet, so a lower last point means missing reports, not
                a drop in spending.
              </p>
            </div>
          </div>

          <Choropleth states={d!.states} selected={state} onPick={setState} />

          <div className="panel">
            <div className="panel-head">
              <div>
                <h2>States at a glance</h2>
                <p>
                  The coloured cell shows what share of a state’s works are
                  high priority. Click a state to see its district authorities;
                  “Investigate” opens those works in the case list.
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
                      'High priority',
                      '% high priority',
                      'Open over 1 year',
                      'Sanctioned',
                      '% paid',
                      'Average score',
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
                    : 'District authorities with the most high-priority works (top 20)'}
                </h2>
              </div>
              <Building2 size={18} />
            </div>
            {state && (
              <p className="section-note">
                <button className="text-link" onClick={() => setState('')}>
                  Back to the top 20 for India
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
                      'High priority',
                      'Open over 1 year',
                      'Sanctioned',
                      'Paid',
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
          placeholder="e.g. Which states have the most delays? or: Jaunpur details"
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
            <h2>Several matches found — pick the one you mean</h2>
          </div>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>ID in the data</TableHead>
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
              <p>How your question was read: {data.data!.interpretation}</p>
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
              Show the database query used ({data.data!.row_count} rows)
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
            {count(mp.work_count)} works flagged high priority
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
          label="Allocated (as in the data)"
          value={crore(mp.allocated_paise)}
        />
        <Metric label="Sanctioned" value={crore(mp.sanction_paise)} />
        <Metric
          label="Paid (reported)"
          value={crore(mp.successful_payment_paise)}
        />
        <Metric
          label="Paid ÷ allocated"
          value={percent(mp.observed_paid_to_allocation_ratio)}
        />
        <Metric
          label="Sanctioned ÷ allocated"
          value={percent(mp.sanction_to_allocation_ratio)}
        />
        <Metric label="Given for calamity relief" value={crore(mp.consented_paise)} />
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
              ['Recommended', count(mp.recommended_record_count)],
              ['Sanctioned', count(mp.sanctioned_count)],
              ['Reported complete', count(mp.completed_count)],
              [
                'Completed ÷ sanctioned',
                percent(mp.completion_to_sanction_ratio),
              ],
              ['Still open after one year', count(mp.open_over_one_year_count)],
              [
                'No payment seen after 3 months',
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
              <h2>Rule checks we cannot do yet</h2>
            </div>
          </div>
          <dl className="s6-facts" style={{ padding: '4px 24px 8px' }}>
            {[
              ['15% of funds for SC areas'],
              ['7.5% of funds for ST areas'],
              ['₹75 lakh limit for trusts and societies'],
              ['Work is inside the MP’s area'],
            ].map(([l]) => (
              <div key={l}>
                <dt>{l}</dt>
                <dd>Cannot check</dd>
              </div>
            ))}
          </dl>
          <p className="section-note">
            These checks need data that the portal files do not include: which
            areas benefit, a register of trusts, and work locations. They are
            shown as <strong>not checked</strong> — not as passed.
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
          label="Search this MP’s works"
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
                      'Stage',
                      'Sanctioned',
                      'Paid',
                      'Priority',
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
                        {life(w.lifecycle)}
                        <small className="record-meta">
                          {w.sanction_date || 'No sanction date'}
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
              Highest priority first. Open a work to see why it was flagged.
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
          label="Stage"
          value={lifecycle}
          onChange={(v) => {
            setLifecycle(v);
            setOffset(0);
          }}
          items={[
            ['', 'All stages'],
            ...[
              'Not in sanction export',
              'Sanctioned / open',
              'Reported complete',
            ].map((v) => [v, life(v)] as [string, string]),
          ]}
        />
        <Pick
          label="Reason flagged"
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
          label="Priority"
          value={band}
          onChange={(v) => {
            setBand(v);
            setOffset(0);
          }}
          items={[
            ['', 'All priorities'],
            ['Critical', 'Critical (score 81–100)'],
            ['High', 'High (40–80)'],
            ['Medium', 'Medium (20–39)'],
            ['Low', 'Low (1–19)'],
            ['Routine', 'Routine (0)'],
          ]}
        />
        <DownloadLink file="Work_Features.csv">Download all works</DownloadLink>
      </div>
      {!!Object.keys(entity).length && (
        <div className="selection-summary">
          Showing works for the selected {Object.keys(entity).join(', ')}{' '}
          <button onClick={clearEntity}>Clear</button>
        </div>
      )}
      <Status error={works.error || options.error} loading={!works.data} />
      {summary && (
        <>
          <div className="selection-summary">
            <strong>{count(summary.total)}</strong> works ·{' '}
            {count(summary.completions)} complete ·{' '}
            {crore(summary.sanction_paise)} sanctioned ·{' '}
            {crore(summary.successful_payment_paise)} paid ·{' '}
            {count(summary.open_over_year)} open over 1 year ·{' '}
            {count(summary.no_payment_three_months)} with no payment after 3
            months
          </div>
          <div style={{ overflowX: 'auto' }}>
            <Table server>
              <TableHeader>
                <TableRow>
                  {[
                    'Work / purpose',
                    'MP / authority',
                    'Stage',
                    'Sanctioned',
                    'Paid',
                    'Priority',
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
                      {life(w.lifecycle)}
                      <small className="record-meta">
                        {w.sanction_date || 'No sanction date'}
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
                        Unusualness {Number(w.isolation_percentile).toFixed(0)}
                        /100 · {w.data_quality_issue_count} data issues
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
            Allocation figures come from the portal file, not a bank
            statement. Two vendors with the same name may be different firms.
            A vendor getting most of the money is a pattern to look at, not
            proof of collusion.
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
          <h2>Pairs of works with similar descriptions</h2>
          <p>
            Compare both works. A matching description alone does not prove
            the same thing was built or paid for twice.
          </p>
        </div>
        <DownloadLink file="Duplicate_Candidates.csv">Download all pairs</DownloadLink>
      </div>
      <TableSearch
        value={query}
        onChange={(v) => {
          setQuery(v);
          setOffset(0);
        }}
        label="Search all pairs"
      />
      <Status error={data.error} loading={!data.data} />
      {data.data && (
        <>
          <div style={{ overflowX: 'auto' }}>
            <Table server>
              <TableHeader>
                <TableRow>
                  {['First work', 'Second work', 'How similar', 'Things to note'].map(
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
                        p.number_conflict ? 'Different numbers in the text' : '',
                        p.continuation_cue ? 'May be a next phase or repair' : '',
                        p.generic_text ? 'Very general description' : '',
                      ]
                        .filter(Boolean)
                        .join(' · ') ||
                        'Check location and scope before concluding'}
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
        Only works in the same district authority and category are
        compared, so some similar pairs may be missed. We have not measured
        how many real duplicates this finds.
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
            <p className="eyebrow">TEST ON SAMPLE DATA</p>
            <h2>1. What this test checks</h2>
            <p>
              <strong>The question:</strong> if we add three extra checks, do
              reviewers catch more problem cases while checking the same number
              of works?
            </p>
            <div className="overview-grid">
              <div>
                <h3>Method A — basic checks</h3>
                <p>
                  Seven checks: recommendation not acted on for a long time,
                  slow sanction, work still open after a year, no payment seen,
                  more paid than sanctioned, completion cost more than
                  sanctioned, and the same payment reported more than once.
                </p>
              </div>
              <div>
                <h3>Method B — basic checks plus three extra</h3>
                <p>
                  All of Method A, plus: cost much higher than similar earlier
                  works, almost the same description as another work, and most
                  of the money paid in March (year-end rush). Both methods use
                  the same scoring as the live system.
                </p>
              </div>
            </div>
            <p>
              <strong>
                {count(m.synthetic_pool)} test cases, of which{' '}
                {count(m.synthetic_positives)} are planted problems · random
                seed {m.seed}
              </strong>
            </p>
            <p>
              <strong>How to read this:</strong> we built realistic test data in
              which we know exactly which cases are problems, then ran both
              methods on it. This shows whether the methods work as designed.
              It does <em>not</em> show how well they catch real fraud. The two
              machine-learning models (Isolation Forest and DBSCAN) are checked
              separately in section 4; they are not Method A or B.
            </p>
            <details>
              <summary>How the test data was built</summary>
              <p>
                We created test works that look like the real portal data: a
                background of normal works from the previous year, planted
                problem cases of each type, and tricky normal cases that look
                suspicious but are legitimate. All of them go through the same
                steps as the real data and are scored by the real rules. We
                then compare what each method sends for review when both are
                allowed the same number of reviews.
              </p>
              <p className="quiet">Technical description: {m.design}</p>
            </details>
          </section>
          <section className="panel evidence-section">
            <h2>2. Results: how many problems each method catches</h2>
            <Pick
              label="How many works can reviewers check?"
              value={budget}
              onChange={setBudget}
              items={m.budgets.map((r: Row) => [
                String(r.fraction),
                `${percent(r.fraction)} of works (up to ${r.k})`,
              ])}
            />
            <div className="metric-grid">
              <Metric
                label="Method A caught"
                value={percent(result.a_recovery)}
                note={`of planted problems · ${result.a_reviewed} works checked · ${result.a_false_alerts} flagged by mistake`}
              />
              <Metric
                label="Method B caught"
                value={percent(result.b_recovery)}
                note={`of planted problems · ${result.b_reviewed} works checked · ${result.b_false_alerts} flagged by mistake`}
              />
              <Metric
                label="B catches more by"
                value={`${(result.difference * 100).toFixed(1)} points`}
                note="Difference between the two catch rates"
              />
              <Metric
                label="Likely range of that difference"
                value={`${(result.ci95[0] * 100).toFixed(1)} to ${(result.ci95[1] * 100).toFixed(1)}`}
                note="95% range, in points, on this test data only"
              />
            </div>
            <p>
              Reviewers could check up to {result.k} works, but a method only
              sends works that fail at least one check, so it may send fewer.
              Of the works each method sent, the share that were planted
              problems was: A {percent(result.a_findings_per_review)}, B{' '}
              {percent(result.b_findings_per_review)}.
            </p>
            <p>
              {result.ci95[0] <= 0 && result.ci95[1] >= 0
                ? 'The likely range includes zero, so at this review size we cannot say for sure that B is better.'
                : 'The likely range is above zero, so B does better on this test data. This is not a measure of real-world accuracy.'}{' '}
              A very narrow range can simply mean the test cases are
              repetitive — it does not mean the result is certain.
            </p>
            <h3>All review sizes</h3>
            <Table>
              <TableHeader>
                <TableRow>
                  {[
                    'Review size',
                    'A caught',
                    'B caught',
                    'Works checked (A / B)',
                    'Flagged by mistake (A / B)',
                    'Hit rate (A / B)',
                  ].map((h) => (
                    <TableHead key={h}>{h}</TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {m.budgets.map((r: Row) => (
                  <TableRow key={r.fraction}>
                    <TableCell>
                      {percent(r.fraction)} (up to {r.k})
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
              Caught = planted problems found ÷ all planted problems. Hit rate
              = planted problems found ÷ works checked. Flagged by mistake =
              normal test cases that were sent for review, including cases that
              look unusual but are legitimate.
            </p>
          </section>
          <section className="panel evidence-section">
            <h2>3. Which kinds of problems each method catches</h2>
            <p>
              At the {percent(result.fraction)} review size. These are planted
              test cases, not confirmed real problems.
            </p>
            <Table>
              <TableHeader>
                <TableRow>
                  {[
                    'Type of planted problem',
                    'Planted',
                    'A caught',
                    'B caught',
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
            <h3>On the real data: how similar are the two review lists?</h3>
            <p>
              The top works picked by A and by B overlap by{' '}
              {percent(result.actual_queue_overlap)}. This only shows how
              alike the two lists are (every work counts the same, whatever its
              amount). It does not show which method is more accurate, how much
              money is saved, or how many real alerts are wrong.
            </p>
          </section>
          <section className="panel evidence-section">
            <h2>4. Does the result hold up? And the machine-learning checks</h2>
            <h3>Same test, different random test data</h3>
            <p>
              We rebuilt the test data with different random seeds to see
              whether the results stay the same. This is still our own test
              data, not an independent check.
            </p>
            <Table>
              <TableHeader>
                <TableRow>
                  {[
                    'Seed',
                    'Review size',
                    'A caught',
                    'B caught',
                    'Flagged by mistake (A / B)',
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
                <h3>Machine-learning checks (on the same test data)</h3>
                <p>
                  Isolation Forest and DBSCAN look for works that are unusual
                  compared with the rest, without being told which cases are
                  problems. They were run on the same test data they are scored
                  on, so these numbers describe the data rather than predict new
                  cases. They are not fraud detectors and are not part of Method
                  A or B.
                </p>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>
                        Share of works flagged by Isolation Forest
                      </TableHead>
                      <TableHead>Planted problems caught</TableHead>
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
                  DBSCAN marked {count(m.ml.dbscan.flagged)} works as unusual;{' '}
                  {count(m.ml.dbscan.positives_flagged)} of them were planted
                  problems. So {percent(m.ml.dbscan.precision)} of its flags
                  were right, and it found {percent(m.ml.dbscan.recall)} of all
                  planted problems.
                </p>
              </>
            )}
          </section>
          <section className="panel evidence-section">
            <h2>5. Check it yourself</h2>
            <ol>
              <li>
                See where the data came from, and its file fingerprints
                (hashes), on Data & research.
              </li>
              <li>
                On Project status & tools, run the checks and re-run this A/B
                test on this computer.
              </li>
              <li>
                Compare with the files below. The same page can also rebuild
                everything from scratch.
              </li>
            </ol>
            <button onClick={onTools}>Open the tools page</button>
            <div className="evidence-links">
              <DownloadLink file="AB_Report.md">Full method report</DownloadLink>
              <DownloadLink file="ab_metrics.json">
                Numbers and seeds (JSON)
              </DownloadLink>
              <DownloadLink file="ab_actual_scores.csv">
                Every test case with its score
              </DownloadLink>
              <DownloadLink file="ab_controlled_benchmark.csv">
                Results by problem type
              </DownloadLink>
              <DownloadLink file="release_manifest.json">
                List of release files (manifest)
              </DownloadLink>
            </div>
            <p className="quiet">
              Test version: {m.version}. All data stays on this computer. The
              downloads are for checking; everything important is shown above.
            </p>
          </section>
          <section className="panel evidence-section">
            <h2>6. What this test cannot tell us, and the next step</h2>
            <ul>
              <li>
                There are no officially confirmed fraud cases to test against.
                The “problems” here are ones we planted.
              </li>
              <li>
                Some legitimate cases — a bigger scope, an approved extension, a
                revised sanction — look just like problems in the available
                data. Some mistaken flags cannot be avoided with these fields,
                and we count them.
              </li>
              <li>
                The catch rates and mistaken-flag counts apply to this test
                data, where problems are rare by design — not to the national
                data.
              </li>
              <li>
                On the real data we only compare how much the two review lists
                overlap. We make no claim about accuracy, mistaken flags or
                money saved on real works.
              </li>
              <li>
                The test design, seed, cut-off date and comparison groups were
                fixed before scoring, and the live system’s settings were used
                unchanged (no tuning to make the test look good).
              </li>
              <li>
                This is an offline comparison, not a live trial with officially
                confirmed outcomes.
              </li>
            </ul>
            <details>
              <summary>Exact wording from the method report</summary>
              <ul className="quiet">
                {m.limitations.map((v: string) => (
                  <li key={v}>{v.replaceAll('\\u2014', '—')}</li>
                ))}
              </ul>
            </details>
            <p>
              <strong>Before real-world use:</strong> lock the methods, get
              cases confirmed by independent officials, and run a live trial
              that measures reviewer time and also checks a sample of works that
              were not flagged. This test is not that trial.
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
            <h2>1. Where the data comes from</h2>
            <p>
              {meta.scope}. Figures are as of {meta.as_of}. The portal files do
              not say exactly when they were downloaded.
            </p>
          </div>
        </div>
        <div style={{ overflowX: 'auto' }}>
          <Table>
            <TableHeader>
              <TableRow>
                {['File', 'Records in file', 'Used', 'Set aside (invalid)'].map(
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
          One payment record was cut off in the source file and set aside.
          Payments that appear more than once in a report are kept as
          reported. A missing document or payment does not prove that a work
          does not exist, that money was misused, or that a bill is unpaid.
        </p>
        <p className="section-note">
          <DownloadLink file="MPLADS_Review.xlsx">
            Excel review workbook
          </DownloadLink>{' '}
          &nbsp;{' '}
          <DownloadLink file="audit.json">Check results and file fingerprints</DownloadLink>{' '}
          &nbsp;{' '}
          <DownloadLink file="Quarantine.csv">Set-aside record</DownloadLink>
        </p>
      </div>
      <section className="panel evidence-section">
        <h2>2. How the data is prepared</h2>
        <ol>
          <li>
            Keep the 18 original portal files (6 file types for each of Lok
            Sabha, Rajya Sabha sitting and Rajya Sabha retired) unchanged, and
            record a fingerprint (hash) of each.
          </li>
          <li>
            Store money in paise (whole numbers, no rounding errors), read the
            dates, give every work a unique ID (the Rajya Sabha files reuse
            IDs), and set aside invalid records.
          </li>
          <li>
            Join each work’s recommendation, sanction, completion and payments
            into one record, without counting any work twice.
          </li>
          <li>
            Work out the checks: timing, money, cost compared with earlier
            works, similar descriptions and how concentrated vendor payments
            are.
          </li>
          <li>
            Keep the rule-based flag score separate from the machine-learning
            “unusualness” score. Check that all totals match the source files,
            then lock the result as a release.
          </li>
        </ol>
        <p>
          The data dictionary below explains every field. A missing record
          means the evidence is missing — not that the work itself does not
          exist.
        </p>
      </section>
      <section className="panel evidence-section">
        <h2>3. Research we used, and why</h2>
        <p>
          Each source is listed with the design choice it shaped. Dates are
          publication dates, not data download dates.
        </p>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Source</TableHead>
              <TableHead>Date</TableHead>
              <TableHead>How we used it</TableHead>
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
            <h2>4. Data dictionary (what each field means)</h2>
          </div>
          <input
            className="dictionary-search s6-input"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setOffset(0);
            }}
            aria-label="Search the data dictionary"
            placeholder="Search a field name, table or meaning"
          />
        </div>
        <Status error={dictionary.error} loading={!dictionary.data} />
        {dictionary.data && (
          <>
            <div style={{ overflowX: 'auto' }}>
              <Table server>
                <TableHeader>
                  <TableRow>
                    {['Table / field', 'Meaning', 'Unit / where available'].map(
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
        <h2>5. What the data cannot tell us</h2>
        <Limits items={meta.limits || []} />
        <p>
          Before official use this needs user log-ins for reviewers, results
          confirmed by independent officials, and an officially approved map.
          It does not replace checking documents or visiting the site.
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
              label="Data version"
              value={
                <span style={{ fontSize: 15, wordBreak: 'break-all' }}>
                  {s.active_release || String(s.version).slice(0, 24)}
                </span>
              }
              note={`as of ${s.as_of}`}
            />
            <Metric
              label="Groups of MPs"
              value={String((s.cohorts || []).length)}
              note={(s.cohorts || [])
                .map((c: string) => COHORT_LABEL[c] || c)
                .join(', ')}
            />
            <Metric
              label="Totals match the source files"
              value={s.all_checks_passed ? '21 / 21 checks passed' : 'FAILED'}
              note={s.all_checks_passed ? 'safe to use' : 'do not use this data'}
            />
            <Metric
              label="Source files unchanged"
              value={
                s.read_only ? 'Not on this server' : s.source_fresh ? 'Yes' : 'CHANGED'
              }
              note={
                s.read_only
                  ? 'release files verified at startup'
                  : s.source_fresh
                    ? 'fingerprints match the build'
                    : s.stale_reason
              }
            />
          </div>

          <div className="panel">
            <div className="panel-head">
              <div>
                <h2>Source files and their fingerprints</h2>
                <p>
                  The original portal files, which are never changed: how many
                  records each has, how many were used or set aside, and each
                  file’s fingerprint (hash).
                </p>
              </div>
            </div>
            <div style={{ overflowX: 'auto' }}>
              <Table>
                <TableHeader>
                  <TableRow>
                    {[
                      'Group',
                      'File',
                      'Records',
                      'Used',
                      'Set aside',
                      'Fingerprint (SHA-256)',
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
                  <h2>Money and progress summary</h2>
                </div>
              </div>
              <dl className="s6-facts" style={{ padding: '4px 24px 18px' }}>
                {[
                  ['Works', count(s.totals.works)],
                  ['Sanctioned', crore(s.totals.sanction_paise)],
                  [
                    'Paid (reported)',
                    crore(s.totals.successful_payment_paise),
                  ],
                  [
                    'Payments in progress (not counted as paid)',
                    crore(s.totals.pending_payment_paise),
                  ],
                  ['Reported complete', count(s.totals.completions)],
                  [
                    'Priority bands',
                    ['Critical', 'High', 'Medium', 'Low', 'Routine']
                      .map((k) => `${k} ${count(s.priority_counts?.[k] ?? 0)}`)
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
                  <h2>Can the results be rebuilt? Do the tests pass?</h2>
                  <p>For this exact data version.</p>
                </div>
              </div>
              <dl className="s6-facts" style={{ padding: '4px 24px 8px' }}>
                <div>
                  <dt>Rebuild gives the same result</dt>
                  <dd>
                    {repro
                      ? repro.reproducible
                        ? `Yes — all ${Object.keys(repro.artifacts || {}).length} output files identical`
                        : 'NO — outputs differ'
                      : 'Not checked yet — use “Run” below'}
                  </dd>
                </div>
                <div>
                  <dt>Last checked</dt>
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
                The rebuild check builds everything again in a separate folder
                and compares the files. It does not change the data you are
                using.
              </p>
            </div>
          </div>

          <div className="panel">
            <div className="panel-head">
              <div>
                <h2>Tools — run checks and create files</h2>
                <p>
                  {s.read_only
                    ? 'Turned off in this read-only demo copy. Run the app on your own computer to use these tools.'
                    : 'Each button starts a task on this computer, which can take a few minutes. Only one task runs at a time. After a new data version is switched on, reload the other pages.'}
                </p>
              </div>
            </div>
            <div style={{ padding: '4px 20px 16px' }}>
              {!s.read_only && available.map((a: Row) => (
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
                <h2>Downloads — data, reports and evidence</h2>
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
              {dl('Work_Features.csv', 'All works with their checks (CSV)', true)}
              {dl('Payment_Features.csv', 'All payments (CSV)', true)}
              {dl(
                'Duplicate_Candidates.csv',
                'Pairs of similar works (CSV)',
                true,
              )}
              {dl('Feature_Dictionary.csv', 'Data dictionary (CSV)', true)}
              {dl(
                'Quarantine.csv',
                'Set-aside record (CSV)',
                s.artifacts.quarantine.available,
              )}
              {dl(
                'audit.json',
                'Check results and file fingerprints',
                s.artifacts.audit.available,
              )}
              {dl(
                'AB_Report.md',
                'A/B test report',
                s.artifacts.ab_metrics.available,
              )}
              {dl(
                'ab_controlled_benchmark.csv',
                'A/B results by problem type (CSV)',
                s.artifacts.ab_metrics.available,
              )}
              {dl(
                'ab_actual_scores.csv',
                'A/B test cases with scores (CSV)',
                s.artifacts.ab_metrics.available,
              )}
              {dl(
                'reproducibility.json',
                'Rebuild check result',
                s.artifacts.reproducibility.available,
              )}
              <DownloadLink file="Rule_Contributions.csv">
                Why each work was flagged (CSV)
              </DownloadLink>
              <DownloadLink file="IDA_Year_Concentration.csv">
                Vendor share of payments (CSV)
              </DownloadLink>
              <DownloadLink file="DATA_PATTERNS.md">
                Data patterns report
              </DownloadLink>
              <DownloadLink file="forecast.json">
                Payment forecast and its tests
              </DownloadLink>
            </div>
          </div>

          <div className="panel">
            <div className="panel-head">
              <div>
                <h2>How the score works, and its limits</h2>
              </div>
            </div>
            <div style={{ padding: '4px 24px 20px' }}>
              <h3 style={{ marginTop: 8 }}>
                The checks and their points
              </h3>
              <p className="quiet">
                Each check a work fails adds its points. The flag score is the
                total, capped at 100: 0 Routine · 1–19 Low · 20–39 Medium ·
                40–80 High · 81–100 Critical.
              </p>
              <div style={{ overflowX: 'auto' }}>
                <Table>
                  <TableHeader>
                    <TableRow>
                      {[
                        'Check',
                        'Points',
                        'Works flagged',
                        'What to verify',
                      ].map(
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
                          {ruleText(r.field, r.reason, r.caution)[0]}
                          <small className="record-meta">{r.field}</small>
                        </TableCell>
                        <TableCell>{r.weight}</TableCell>
                        <TableCell>
                          {s.rule_counts?.[r.field] === 0 ? (
                            <span title="The check is switched on and was tested in the A/B test, but no work in this data meets it.">
                              0 — none in this data
                            </span>
                          ) : (
                            count(s.rule_counts?.[r.field])
                          )}
                        </TableCell>
                        <TableCell className="quiet">
                          {ruleText(r.field, r.reason, r.caution)[1]}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
              <h3>What the data cannot tell us</h3>
              <Limits items={s.limits || []} className="quiet" />
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
                <h2>Help — how to check a work and record a review</h2>
              </div>
            </div>
            <div
              className="quiet"
              style={{ padding: '4px 24px 22px', lineHeight: 1.7 }}
            >
              <p>
                <strong>Find works:</strong> open <em>Work investigation</em>.
                Filter by state, year, stage or <em>reason flagged</em> (for
                example “still open after one year”), or type in the search
                box.
              </p>
              <p>
                <strong>Look at the evidence:</strong> click a work. A panel
                opens with its key dates, money sanctioned and paid, the{' '}
                <em>reasons it was flagged</em> (each with what to verify), a
                cost comparison with similar earlier works, its payments, and
                any works with a similar description.
              </p>
              <p>
                <strong>Record a review:</strong> in that panel, choose an
                outcome (Needs evidence · Expected variation · Data issue ·
                Substantiated issue), write a note on what you checked, and
                save. Reviews are saved on this computer only, linked to this
                data version, and kept when the data is rebuilt. They are never
                uploaded.
              </p>
              <p>
                <strong>Remember:</strong> a score is never proof of fraud.
                Every flag is a request to look at the evidence. Checks we
                cannot do are shown as “cannot check”, never as passed.
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
  const readOnly = !!meta.data?.read_only;
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
    <ReadOnly.Provider value={readOnly}>
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
            Data loaded on this computer<small>{cohorts || 'MPLADS'}</small>
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
          {readOnly && (
            <div className="demo-banner" role="note">
              <strong>Demo copy · read-only.</strong> Review signals, not
              findings of fraud. Saving reviews and running tools are turned
              off here.
            </div>
          )}
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
                <strong>The app’s data service is not running.</strong>
              </span>
              <span className="quiet">
                Start it by double-clicking <code>START.cmd</code> (or running{' '}
                <code>run.ps1</code>) in the project folder, then reload this
                page. This page cannot start it for you.
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
              Research prototype running on this computer · no user log-ins
              and not an official audit.
            </div>
            <a
              className="text-link"
              href="/api/reviews"
              target="_blank"
              rel="noreferrer"
            >
              Download review history
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
    </ReadOnly.Provider>
  );
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
