import { useEffect, useState } from 'react';
import { ReportView } from './report-view';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from 'recharts';
import {
  Table,
  TablePager,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from '@/components/ui/table';

type Review = {
  id: number;
  record_key: string;
  version: string;
  outcome: string;
  note: string;
  created: string;
  owner: string;
  due_date: string;
  status: string;
};
type ReviewResponse = { reviews: Review[]; history: Review[]; version: string };
type Concentration = {
  ida_key: string;
  ida_name: string;
  fiscal_year: string;
  vendor_hhi: number;
  top_vendor_share: number;
  vendor_count: number;
  successful_payment_paise: number;
};
type Forecast = {
  available: boolean;
  reason?: string;
  as_of: string;
  forecast_month: string;
  forecast_paise: number;
  selected_method: string;
  methodology: string;
  limitations: string[];
  metrics: {
    method: string;
    validation_mae_paise: number;
    test_mae_paise: number;
  }[];
  folds: {
    month: string;
    actual_paise: number;
    last_month: number;
    trailing_three_month_mean: number;
    split: string;
  }[];
  test_improved_over_last_month: boolean;
};
const crore = (n: number) =>
  `₹${(n / 1e9).toLocaleString('en-IN', { maximumFractionDigits: 2 })} cr`;
const pct = (n: number) => (n * 100).toFixed(1) + '%';
const method = (m: string) =>
  m === 'last_month' ? 'Last month (baseline)' : 'Trailing three-month mean';
function useLocal<T>(url: string, revision = 0) {
  const [result, setResult] = useState<{
    url: string;
    revision: number;
    data: T | null;
    error: string;
  } | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    void fetch(url, { signal: controller.signal })
      .then(async (response) => {
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Local request failed');
        return data as T;
      })
      .then((data) => setResult({ url, revision, data, error: '' }))
      .catch((e: unknown) => {
        if (!controller.signal.aborted)
          setResult({
            url,
            revision,
            data: null,
            error: e instanceof Error ? e.message : 'Request failed',
          });
      });
    return () => controller.abort();
  }, [url, revision]);
  return result?.url === url && result.revision === revision
    ? result
    : { data: null, error: '' };
}
function Page({
  offset,
  total,
  change,
}: {
  offset: number;
  total: number;
  change: (v: number) => void;
}) {
  return <TablePager offset={offset} total={total} onChange={change} />;
}

export function ReviewForm({
  workId,
  version,
  previous,
  onSaved,
}: {
  workId: string;
  version: string;
  previous?: Review;
  onSaved: () => void;
}) {
  const [owner, setOwner] = useState(previous?.owner || '');
  const [due, setDue] = useState(previous?.due_date || '');
  const [status, setStatus] = useState(previous?.status || 'Open');
  const [outcome, setOutcome] = useState(previous?.outcome || 'Needs evidence');
  const [note, setNote] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  async function save() {
    setBusy(true);
    setMessage('');
    try {
      const response = await fetch('/api/reviews', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          key: workId,
          version,
          note,
          outcome,
          owner,
          due_date: due,
          status,
        }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Save failed');
      setMessage('Saved locally.');
      onSaved();
    } catch (e) {
      setMessage(e instanceof Error ? e.message : 'Save failed');
    } finally {
      setBusy(false);
    }
  }
  return (
    <div>
      <p className="quiet">
        Append-only local history. Assignment names are not authenticated
        identities. Closed means reviewed, not proven issue-free.
      </p>
      <div className="global-filters">
        <label>
          Owner
          <input
            className="s6-input"
            maxLength={120}
            value={owner}
            onChange={(e) => setOwner(e.target.value)}
            placeholder="Unassigned"
          />
        </label>
        <label>
          Follow-up date
          <input
            className="s6-input"
            type="date"
            value={due}
            onInput={(e) => setDue(e.currentTarget.value)}
            onChange={(e) => setDue(e.target.value)}
          />
        </label>
        <label>
          Case status
          <select
            className="s6-input"
            value={status}
            onChange={(e) => setStatus(e.target.value)}
          >
            {['Open', 'In review', 'Escalated', 'Closed'].map((v) => (
              <option key={v}>{v}</option>
            ))}
          </select>
        </label>
        <label>
          Disposition
          <select
            className="s6-input"
            value={outcome}
            onChange={(e) => setOutcome(e.target.value)}
          >
            {[
              'Needs evidence',
              'Expected variation',
              'Data issue',
              'Substantiated issue',
            ].map((v) => (
              <option key={v}>{v}</option>
            ))}
          </select>
        </label>
      </div>
      <label className="s6-note-input">
        Evidence or next action
        <textarea
          value={note}
          maxLength={3000}
          onChange={(e) => setNote(e.target.value)}
          placeholder="Reference the document checked, finding or evidence still needed."
        />
      </label>
      <button disabled={busy || !note.trim()} onClick={() => void save()}>
        {busy ? 'Saving…' : 'Save review locally'}
      </button>
      <output aria-live="polite">{message}</output>
    </div>
  );
}

export function CaseRegister({ open }: { open: (id: string) => void }) {
  const [revision, setRevision] = useState(0);
  const [state, setState] = useState('');
  const [query, setQuery] = useState('');
  const [offset, setOffset] = useState(0);
  const data = useLocal<ReviewResponse>('/api/reviews', revision);
  const rows = (data.data?.reviews || [])
    .filter(
      (r) =>
        (!state || r.status === state) &&
        `${r.owner} ${r.record_key} ${r.note} ${r.outcome}`
          .toLowerCase()
          .includes(query.toLowerCase()),
    )
    .sort((a, b) => b.id - a.id);
  const today = new Date().toLocaleDateString('en-CA');
  return (
    <div className="panel">
      <div className="panel-head">
        <div>
          <h2>Review register</h2>
          <p>
            Latest decision per record, including earlier releases. Open a work
            to check current evidence before updating it. Follow-up dates are
            local task dates, not scheme deadlines.
          </p>
        </div>
        <button onClick={() => setRevision((r) => r + 1)}>
          Refresh reviews
        </button>
      </div>
      <div className="global-filters">
        <label>
          Case status
          <select
            className="s6-input"
            value={state}
            onChange={(e) => {
              setState(e.target.value);
              setOffset(0);
            }}
          >
            <option value="">All statuses</option>
            {['Open', 'In review', 'Escalated', 'Closed'].map((v) => (
              <option key={v}>{v}</option>
            ))}
          </select>
        </label>
        <label>
          Find owner, work or note
          <input
            className="s6-input"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setOffset(0);
            }}
          />
        </label>
        <a
          className="text-link"
          href="/api/reviews"
          download="review-history.json"
        >
          Export complete history
        </a>
      </div>
      {data.error && <p role="alert">{data.error}</p>}
      {!data.data && !data.error && <output>Loading reviews…</output>}
      <div style={{ overflowX: 'auto' }}>
        <Table server>
          <TableHeader>
            <TableRow>
              {[
                'Work',
                'Owner',
                'Status / disposition',
                'Due',
                'Latest evidence',
                'Release',
              ].map((h) => (
                <TableHead key={h}>{h}</TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.slice(offset, offset + 50).map((r) => (
              <TableRow key={r.id}>
                <TableCell>
                  {r.record_key.startsWith('pair:') ? (
                    r.record_key
                  ) : (
                    <button
                      className="record-title"
                      onClick={() => open(r.record_key)}
                    >
                      {r.record_key}
                    </button>
                  )}
                </TableCell>
                <TableCell>{r.owner || 'Unassigned'}</TableCell>
                <TableCell>
                  {r.status}
                  <small className="record-meta">{r.outcome}</small>
                </TableCell>
                <TableCell>
                  {r.due_date || 'Not set'}
                  {r.due_date &&
                    r.due_date < today &&
                    r.status !== 'Closed' && <strong> · Overdue</strong>}
                </TableCell>
                <TableCell style={{ minWidth: 220, whiteSpace: 'pre-wrap' }}>
                  {r.note}
                </TableCell>
                <TableCell>
                  {r.version === data.data?.version
                    ? 'Current'
                    : 'Previous — recheck'}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      <Page offset={offset} total={rows.length} change={setOffset} />
      {data.data && !rows.length && (
        <p className="section-note">
          No matching reviews. Open a work from Work investigation, then save an
          evidence note.
        </p>
      )}
    </div>
  );
}

export function Insights({
  inspect,
}: {
  inspect: (key: string, value: string) => void;
}) {
  const [offset, setOffset] = useState(0);
  const [query, setQuery] = useState('');
  const concentration = useLocal<{ items: Concentration[]; total: number }>(
    `/api/table?kind=concentration&offset=${offset}&q=${encodeURIComponent(query)}`,
  );
  const forecast = useLocal<Forecast>('/api/forecast');
  const patterns = useLocal<{ text: string }>('/api/patterns');
  const f = forecast.data;
  return (
    <>
      <div className="panel">
        <div className="panel-head">
          <div>
            <h2>Experimental payment forecast</h2>
            <p>
              One-month projection of reported settlement totals. No fraud or
              project-completion prediction.
            </p>
          </div>
          <a className="text-link" href="/api/download/forecast.json" download>
            Forecast & backtest
          </a>
        </div>
        {forecast.error && <p role="alert">{forecast.error}</p>}
        {!f && !forecast.error && <output>Loading forecast…</output>}
        {f && !f.available && <p className="section-note">{f.reason}</p>}
        {f?.available && (
          <>
            <div className="metric-grid">
              <div className="metric">
                <span>Projected full month: {f.forecast_month}</span>
                <strong>{crore(f.forecast_paise)}</strong>
                <span>Not remaining-month expenditure</span>
              </div>
              <div className="metric">
                <span>Selected on validation months</span>
                <strong style={{ fontSize: 19 }}>
                  {method(f.selected_method)}
                </strong>
                <span>
                  {f.test_improved_over_last_month
                    ? 'Lower error than baseline on the three test months'
                    : 'No demonstrated test improvement over last-month baseline'}
                </span>
              </div>
            </div>
            <p className="section-note">{f.methodology}</p>
            <div style={{ height: 260, padding: 20 }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart
                  margin={{ top: 8, right: 16, bottom: 8, left: 8 }}
                  data={f.folds.slice(-12).map((r) => ({
                    month: r.month,
                    Observed: r.actual_paise / 1e9,
                    Baseline: r.last_month / 1e9,
                    'Three-month mean': r.trailing_three_month_mean / 1e9,
                  }))}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis
                    dataKey="month"
                    tick={{ fontSize: 11 }}
                    minTickGap={25}
                  />
                  <YAxis
                    width={60}
                    tick={{ fontSize: 11 }}
                    label={{
                      value: 'INR crore',
                      angle: -90,
                      position: 'insideLeft',
                    }}
                  />
                  <Tooltip
                    formatter={(value) =>
                      `${Number(value).toLocaleString('en-IN', { maximumFractionDigits: 2 })} crore`
                    }
                  />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  <Line dataKey="Observed" stroke="#277780" dot={false} />
                  <Line
                    dataKey="Baseline"
                    stroke="#9a6427"
                    strokeDasharray="5 4"
                    dot={false}
                  />
                  <Line
                    dataKey="Three-month mean"
                    stroke="#7852a5"
                    strokeDasharray="2 3"
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <p className="section-note">
              Backtest amounts in ₹ crore. Solid teal: observed. Dashed amber:
              last-month baseline. Dotted purple: three-month mean. Every
              prediction uses only earlier months.
            </p>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Method</TableHead>
                  <TableHead>Validation MAE</TableHead>
                  <TableHead>Last 3 months test MAE</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {f.metrics.map((m) => (
                  <TableRow key={m.method}>
                    <TableCell>{method(m.method)}</TableCell>
                    <TableCell>{crore(m.validation_mae_paise)}</TableCell>
                    <TableCell>{crore(m.test_mae_paise)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <p className="section-note">
              Mean absolute error (MAE) is the average size of prediction
              errors; lower is better. Test months were not used to select the
              method.
            </p>
            <details style={{ padding: 20 }}>
              <summary>Show all chronological test predictions</summary>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Month</TableHead>
                    <TableHead>Observed</TableHead>
                    <TableHead>Baseline</TableHead>
                    <TableHead>Three-month mean</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {f.folds
                    .filter((r) => r.split === 'test')
                    .map((r) => (
                      <TableRow key={r.month}>
                        <TableCell>{r.month}</TableCell>
                        <TableCell>{crore(r.actual_paise)}</TableCell>
                        <TableCell>{crore(r.last_month)}</TableCell>
                        <TableCell>
                          {crore(r.trailing_three_month_mean)}
                        </TableCell>
                      </TableRow>
                    ))}
                </TableBody>
              </Table>
            </details>
          </>
        )}
        {f && (
          <ul className="quiet" style={{ padding: '0 32px 20px' }}>
            {f.limitations.map((t) => (
              <li key={t}>{t}</li>
            ))}
          </ul>
        )}
      </div>
      <div className="panel">
        <div className="panel-head">
          <div>
            <h2>Authority-year vendor concentration</h2>
            <p>
              HHI is the sum of squared payment shares (0–1). A high value may
              reflect few works or legitimate specialization, not collusion.
              Click an authority for its profile, review signals and
              year-by-year details.
            </p>
          </div>
          <a
            className="text-link"
            href="/api/download/IDA_Year_Concentration.csv"
            download
          >
            Full table
          </a>
        </div>
        {concentration.error && <p role="alert">{concentration.error}</p>}
        <div style={{ overflowX: 'auto' }}>
          <Table
            server
            search={query}
            onSearch={(v) => {
              setQuery(v);
              setOffset(0);
            }}
          >
            <TableHeader>
              <TableRow>
                {[
                  'Authority',
                  'FY',
                  'Vendors',
                  'HHI',
                  'Largest share',
                  'Reported settled',
                ].map((h) => (
                  <TableHead key={h}>{h}</TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {concentration.data?.items.map((r) => (
                <TableRow key={r.ida_key + r.fiscal_year}>
                  <TableCell>
                    <button
                      className="record-title"
                      onClick={() => inspect('ida', r.ida_key)}
                    >
                      {r.ida_name}
                    </button>
                  </TableCell>
                  <TableCell>{r.fiscal_year}</TableCell>
                  <TableCell>{r.vendor_count}</TableCell>
                  <TableCell>{r.vendor_hhi.toFixed(3)}</TableCell>
                  <TableCell>{pct(r.top_vendor_share)}</TableCell>
                  <TableCell>{crore(r.successful_payment_paise)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
        <Page
          offset={offset}
          total={concentration.data?.total || 0}
          change={setOffset}
        />
      </div>
      <div className="panel">
        <div className="panel-head">
          <div>
            <h2>Connected-data patterns and explanations</h2>
            <p>
              Generated from this release. Observations are hypotheses for
              review, not proof of wrongdoing.
            </p>
          </div>
          <a
            className="text-link"
            href="/api/download/DATA_PATTERNS.md"
            download
          >
            Download report
          </a>
        </div>
        {patterns.error && <p role="alert">{patterns.error}</p>}
        <ReportView text={patterns.data?.text || 'Loading report.'} />
      </div>
    </>
  );
}
