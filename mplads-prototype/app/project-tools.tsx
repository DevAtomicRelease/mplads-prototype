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
  m === 'last_month' ? 'Same as last month' : 'Average of last 3 months';
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
        Every save is added to the history; nothing is overwritten. Names
        typed here are not checked log-ins. “Closed” means reviewed — not
        proven problem-free.
      </p>
      <div className="global-filters">
        <label>
          Assigned to
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
          Status
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
          Outcome
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
        What you checked, or what is still needed
        <textarea
          value={note}
          maxLength={3000}
          onChange={(e) => setNote(e.target.value)}
          placeholder="e.g. Checked sanction letter and site photos; completion certificate still missing."
        />
      </label>
      <button disabled={busy || !note.trim()} onClick={() => void save()}>
        {busy ? 'Saving…' : 'Save review'}
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
            The latest review of each work, including reviews saved on older
            data versions. Open a work to check the current evidence before
            updating it. Follow-up dates are your own reminders, not official
            scheme deadlines.
          </p>
        </div>
        <button onClick={() => setRevision((r) => r + 1)}>
          Refresh reviews
        </button>
      </div>
      <div className="global-filters">
        <label>
          Status
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
          Search by person, work or note
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
          Download full history
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
                'Assigned to',
                'Status / outcome',
                'Follow up by',
                'Latest note',
                'Data version',
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
                    : 'Older — check again'}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      <Page offset={offset} total={rows.length} change={setOffset} />
      {data.data && !rows.length && (
        <p className="section-note">
          No reviews found. Open a work from Work investigation, then save a
          review there.
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
            <h2>Payment forecast (experimental)</h2>
            <p>
              A simple estimate of how much will be reported as paid next
              month, for all works together. It does not predict fraud or when
              works will be finished.
            </p>
          </div>
          <a className="text-link" href="/api/download/forecast.json" download>
            Download forecast data
          </a>
        </div>
        {forecast.error && <p role="alert">{forecast.error}</p>}
        {!f && !forecast.error && <output>Loading forecast…</output>}
        {f && !f.available && <p className="section-note">{f.reason}</p>}
        {f?.available && (
          <>
            <div className="metric-grid">
              <div className="metric">
                <span>Expected total for {f.forecast_month}</span>
                <strong>{crore(f.forecast_paise)}</strong>
                <span>For the whole month, not only the days left</span>
              </div>
              <div className="metric">
                <span>Method chosen (on past months)</span>
                <strong style={{ fontSize: 19 }}>
                  {method(f.selected_method)}
                </strong>
                <span>
                  {f.test_improved_over_last_month
                    ? 'More accurate than “same as last month” in the 3 test months'
                    : 'Not more accurate than “same as last month” in the 3 test months'}
                </span>
              </div>
            </div>
            <p className="section-note">
              How it works: we tried two simple methods — “same as last month”
              and “average of the last three months” — on past months, and kept
              the one with smaller errors. We then tested it on the three most
              recent complete months, predicting each month using only the
              months before it.
            </p>
            <div style={{ height: 260, padding: 20 }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart
                  margin={{ top: 8, right: 16, bottom: 8, left: 8 }}
                  data={f.folds.slice(-12).map((r) => ({
                    month: r.month,
                    Actual: r.actual_paise / 1e9,
                    'Same as last month': r.last_month / 1e9,
                    'Average of last 3 months': r.trailing_three_month_mean / 1e9,
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
                      value: '₹ crore',
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
                  <Line dataKey="Actual" stroke="#277780" dot={false} />
                  <Line
                    dataKey="Same as last month"
                    stroke="#9a6427"
                    strokeDasharray="5 4"
                    dot={false}
                  />
                  <Line
                    dataKey="Average of last 3 months"
                    stroke="#7852a5"
                    strokeDasharray="2 3"
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <p className="section-note">
              Amounts in ₹ crore. Solid teal line: actual payments. Dashed
              amber: “same as last month” guess. Dotted purple: “average of
              last 3 months” guess. Each guess uses only earlier months.
            </p>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Method</TableHead>
                  <TableHead>Average error (choosing months)</TableHead>
                  <TableHead>Average error (3 test months)</TableHead>
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
              Average error = how far the guess was from the actual amount, on
              average; lower is better. The 3 test months were not used to
              choose the method.
            </p>
            <details style={{ padding: 20 }}>
              <summary>Show each test month’s guesses</summary>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Month</TableHead>
                    <TableHead>Actual</TableHead>
                    <TableHead>Same as last month</TableHead>
                    <TableHead>Average of last 3 months</TableHead>
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
          <div className="quiet" style={{ padding: '0 32px 20px' }}>
            <ul>
              <li>
                There is only one download of the data, so we cannot see
                whether older months were later corrected or filled in.
              </li>
              <li>
                This is a rough estimate of total payments — not a budget,
                money still owed, a fraud score or a completion date.
              </li>
              <li>
                The current month is left out because its reports are not
                complete. A low month can simply mean missing reports.
              </li>
              <li>
                It was tested on only 3 months, so the error could change a
                lot. We do not give a confidence range.
              </li>
            </ul>
            <details>
              <summary>Exact wording from the forecast file</summary>
              <ul>
                {f.limitations.map((t) => (
                  <li key={t}>{t}</li>
                ))}
              </ul>
              {f.methodology && <p>{f.methodology}</p>}
            </details>
          </div>
        )}
      </div>
      <div className="panel">
        <div className="panel-head">
          <div>
            <h2>Does one vendor get most of the money?</h2>
            <p>
              For each district authority and year: how the payments were
              split between vendors. The concentration score runs from 0
              (spread across many vendors) to 1 (all to one vendor). A high
              score can have normal reasons — few works, or a specialist
              supplier — so it is a pattern to check, not proof of collusion.
              Authority-years with at least 3 vendors and ₹50 lakh paid are
              listed first; those with a single vendor always score 1, so they
              come after. Click an authority to see its profile.
            </p>
          </div>
          <a
            className="text-link"
            href="/api/download/IDA_Year_Concentration.csv"
            download
          >
            Download full table
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
                  'Year',
                  'Vendors',
                  'Concentration (0–1)',
                  'Top vendor’s share',
                  'Paid',
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
            <h2>Patterns found in the data</h2>
            <p>
              Written automatically from this data version. Each pattern is
              something worth checking, not proof of wrongdoing.
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
