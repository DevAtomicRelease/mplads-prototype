'use client';

import { useEffect, useMemo, useState } from 'react';
import {
  ShieldCheck,
  LayoutDashboard,
  ListFilter,
  Copy,
  Building2,
  Database,
  Download,
  Search,
  ArrowUpRight,
  ArrowRight,
  ChevronLeft,
  ChevronRight,
  CircleAlert,
  Check,
  Clock3,
  Layers3,
  FlaskConical,
  RefreshCw,
  ExternalLink,
} from 'lucide-react';
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarTrigger,
} from '@/components/ui/sidebar';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Pagination,
  PaginationContent,
  PaginationItem,
} from '@/components/ui/pagination';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyTitle,
} from '@/components/ui/empty';
import {
  b,
  csv,
  dateLabel,
  decode,
  defaults,
  money,
  n,
  number,
  percent,
  portfolio,
  reasons,
  s,
  selectWorks,
  summarize,
} from '@/lib/model';
import type { Data, Filters, Row } from '@/lib/model';
import Validation from './validation';

const NAV = [
  { key: 'overview', label: 'Portfolio overview', icon: LayoutDashboard },
  { key: 'queue', label: 'Review queue', icon: ListFilter },
  { key: 'duplicates', label: 'Duplicate review', icon: Copy },
  { key: 'entities', label: 'MPs & authorities', icon: Building2 },
  { key: 'validation', label: 'A/B validation', icon: FlaskConical },
  { key: 'method', label: 'Data & solution plan', icon: Database },
];
const SIGNALS = [
  ['all', 'All signals'],
  ['delay', 'Sanction delay'],
  ['aging', 'Early-stage aging'],
  ['cost', 'High peer cost'],
  ['duplicate', 'Duplicate candidate'],
];
type Decision = {
  outcome: string;
  note: string;
  updated: string;
  version?: string;
  id?: number;
};
type Focus = { kind: 'work' | 'pair' | 'mp' | 'ida'; key: string } | null;

function Pick({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: (string | string[])[];
  onChange: (v: string) => void;
}) {
  const items = options.map((o) =>
    Array.isArray(o) ? { value: o[0], label: o[1] } : { value: o, label: o },
  );
  return (
    <div className="pick">
      <label>{label}</label>
      <Select
        value={value}
        onValueChange={(v) => onChange(String(v ?? 'all'))}
        items={items}
      >
        <SelectTrigger aria-label={label} className="pick-trigger">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {items.map((o) => (
            <SelectItem key={o.value} value={o.value}>
              {o.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
function Band({ value }: { value: string }) {
  return <span className={`band band-${value.toLowerCase()}`}>{value}</span>;
}
function DownloadButton({
  rows,
  name,
  label = 'Export CSV',
}: {
  rows: Row[];
  name: string;
  label?: string;
}) {
  function run() {
    const url = URL.createObjectURL(
      new Blob([csv(rows)], { type: 'text/csv;charset=utf-8;' }),
    );
    const a = document.createElement('a');
    a.href = url;
    a.download = name + '.csv';
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  return (
    <Button variant="outline" onClick={run} disabled={!rows.length}>
      <Download size={16} />
      {label}
    </Button>
  );
}
function Pager({
  page,
  total,
  onChange,
}: {
  page: number;
  total: number;
  onChange: (p: number) => void;
}) {
  const pages = Math.max(1, Math.ceil(total / 20));
  return (
    <div className="pager">
      <span>
        {total
          ? `${number(page * 20 + 1)}–${number(Math.min(total, (page + 1) * 20))} of ${number(total)}`
          : '0 results'}
      </span>
      <Pagination className="w-auto m-0">
        <PaginationContent>
          <PaginationItem>
            <Button
              variant="outline"
              size="icon"
              aria-label="Previous page"
              disabled={!page}
              onClick={() => onChange(page - 1)}
            >
              <ChevronLeft />
            </Button>
          </PaginationItem>
          <PaginationItem>
            <span className="page-number">
              {page + 1} / {pages}
            </span>
          </PaginationItem>
          <PaginationItem>
            <Button
              variant="outline"
              size="icon"
              aria-label="Next page"
              disabled={page + 1 >= pages}
              onClick={() => onChange(page + 1)}
            >
              <ChevronRight />
            </Button>
          </PaginationItem>
        </PaginationContent>
      </Pagination>
    </div>
  );
}
function EmptyResults() {
  return (
    <Empty>
      <EmptyHeader>
        <EmptyTitle>No matching records</EmptyTitle>
        <EmptyDescription>
          Adjust the search or filters to broaden your selection.
        </EmptyDescription>
      </EmptyHeader>
    </Empty>
  );
}
function Metric({
  label,
  value,
  detail,
  icon: Icon,
  onClick,
}: {
  label: string;
  value: string;
  detail: string;
  icon: typeof Database;
  onClick?: () => void;
}) {
  return (
    <button className="metric" onClick={onClick} disabled={!onClick}>
      <div className="metric-label">
        {label}
        <Icon size={18} />
      </div>
      <strong>{value}</strong>
      <span>{detail}</span>
    </button>
  );
}
function WorkTable({
  rows,
  onOpen,
  reviews,
  small = false,
}: {
  rows: Row[];
  onOpen: (id: string) => void;
  reviews: Record<string, Decision>;
  small?: boolean;
}) {
  return rows.length ? (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Work / location</TableHead>
          <TableHead>Sanction</TableHead>
          <TableHead>Current stage</TableHead>
          <TableHead>Priority</TableHead>
          {!small && <TableHead>Review</TableHead>}
          <TableHead>
            <span className="sr-only">Open</span>
          </TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((w) => (
          <TableRow key={s(w, 'work_id')}>
            <TableCell className="work-cell">
              <button
                onClick={() => onOpen(s(w, 'work_id'))}
                className="record-title"
              >
                {s(w, 'work_description')}
              </button>
              <span className="record-meta">
                #{s(w, 'work_id')} · {s(w, 'ida_district')} · {s(w, 'state')}
              </span>
            </TableCell>
            <TableCell className="nowrap amount-cell">
              {money(n(w, 'sanction_amount'))}
              <span className="record-meta">
                {dateLabel(s(w, 'sanction_date'))}
              </span>
            </TableCell>
            <TableCell>
              <span className="status-dot" />
              {s(w, 'work_status')}
              <span className="record-meta">
                {number(n(w, 'age_days_at_snapshot_proxy'))} days since sanction
              </span>
            </TableCell>
            <TableCell>
              <div className="score-line">
                <Band value={s(w, 'review_priority_band')} />
                <strong>{n(w, 'review_priority_score')}</strong>
              </div>
            </TableCell>
            {!small && (
              <TableCell className="record-meta">
                {reviews[s(w, 'work_id')]?.outcome ?? 'Unreviewed'}
              </TableCell>
            )}
            <TableCell>
              <Button
                variant="ghost"
                size="icon"
                aria-label={'Open work ' + s(w, 'work_id')}
                onClick={() => onOpen(s(w, 'work_id'))}
              >
                <ArrowUpRight size={18} />
              </Button>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  ) : (
    <EmptyResults />
  );
}

export default function Workspace() {
  const [data, setData] = useState<Data | null>(null),
    [error, setError] = useState('');
  useEffect(() => {
    const c = new AbortController();
    fetch('/api/snapshot', { signal: c.signal })
      .then((r) => {
        if (!r.ok)
          throw new Error(
            'The local data service is unavailable. Start the prototype launcher and refresh.',
          );
        return r.json();
      })
      .then((p) => setData(decode(p)))
      .catch((e) => {
        if (e.name !== 'AbortError') setError(e.message);
      });
    return () => c.abort();
  }, []);
  if (!data)
    return (
      <main className="loading-surface">
        <ShieldCheck size={38} />
        <h1>MPLADS Insight</h1>
        {error ? (
          <>
            <p role="alert">{error}</p>
            <Button onClick={() => window.location.reload()}>
              <RefreshCw />
              Retry
            </Button>
          </>
        ) : (
          <>
            <p>Opening the connected portfolio…</p>
            <Skeleton className="h-5 w-80" />
            <Skeleton className="h-40 w-full max-w-xl" />
          </>
        )}
      </main>
    );
  return <Dashboard data={data} />;
}

function Dashboard({ data }: { data: Data }) {
  const [view, setView] = useState('overview'),
    [filters, setFilters] = useState<Filters>(defaults),
    [page, setPage] = useState(0),
    [focus, setFocus] = useState<Focus>(null),
    [reviews, setReviews] = useState<Record<string, Decision>>({});
  const [pairSearch, setPairSearch] = useState(''),
    [strength, setStrength] = useState('all'),
    [pairPage, setPairPage] = useState(0),
    [entitySearch, setEntitySearch] = useState(''),
    [entityTab, setEntityTab] = useState('mp'),
    [entityPage, setEntityPage] = useState(0);
  const [fieldSearch, setFieldSearch] = useState(''),
    [fieldPage, setFieldPage] = useState(0);
  const [reviewError, setReviewError] = useState('');
  useEffect(() => {
    const c = new AbortController();
    fetch('/api/reviews', { signal: c.signal })
      .then(async (r) => {
        if (!r.ok)
          throw new Error(
            'Stored reviews could not be loaded. Reload before recording a decision.',
          );
        const result = (await r.json()) as {
          reviews: Record<string, Decision>;
        };
        setReviews(result.reviews);
      })
      .catch((e) => {
        if (e.name !== 'AbortError') setReviewError(e.message);
      });
    return () => c.abort();
  }, []);
  async function saveReview(key: string, decision: Decision) {
    if (reviewError) throw new Error(reviewError);
    const response = await fetch('/api/reviews', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        key,
        ...decision,
        version: data.meta.reviewVersion,
      }),
    });
    const result = (await response.json()) as {
      error?: string;
      review: Decision;
    };
    if (!response.ok) throw new Error(result.error || 'Review was not saved.');
    setReviews((prev) => ({ ...prev, [key]: result.review }));
  }

  const states = useMemo(
    () => Array.from(new Set(data.works.map((w) => s(w, 'state')))).sort(),
    [data],
  );
  const fys = useMemo(
    () =>
      Array.from(new Set(data.works.map((w) => s(w, 'sanction_fiscal_year'))))
        .sort()
        .reverse(),
    [data],
  );
  const scope = useMemo(
    () => portfolio(data.works, filters.state, filters.fy),
    [data, filters.state, filters.fy],
  );
  const stats = useMemo(() => summarize(scope), [scope]);
  const queue = useMemo(
    () => selectWorks(data.works, filters),
    [data, filters],
  );
  const priority = useMemo(
    () => selectWorks(scope, { ...defaults, band: 'priority' }).slice(0, 5),
    [scope],
  );
  const workMap = useMemo(
    () => new Map(data.works.map((w) => [s(w, 'work_id'), w])),
    [data],
  );
  const scopeIds = useMemo(
    () => new Set(scope.map((w) => s(w, 'work_id'))),
    [scope],
  );
  const pairRows = useMemo(
    () =>
      data.pairs.filter(
        (p) =>
          (scopeIds.has(s(p, 'work_id_a')) ||
            scopeIds.has(s(p, 'work_id_b'))) &&
          (strength === 'all' || s(p, 'evidence_strength') === strength) &&
          (!pairSearch ||
            [
              'work_id_a',
              'work_id_b',
              'description_a',
              'description_b',
              'mp_name_a',
              'mp_name_b',
            ].some((k) =>
              s(p, k).toLowerCase().includes(pairSearch.toLowerCase()),
            )),
      ),
    [data, scopeIds, strength, pairSearch],
  );
  const entityRows = useMemo(() => {
    const mpKeys = new Set(scope.map((w) => s(w, 'mp_name_key')));
    const idaKeys = new Set(scope.map((w) => s(w, 'ida_key')));
    return (entityTab === 'mp' ? data.mps : data.idas).filter(
      (r) =>
        ((filters.state === 'all' && filters.fy === 'all') ||
          (entityTab === 'mp'
            ? mpKeys.has(s(r, 'mp_name_key'))
            : idaKeys.has(s(r, 'ida_key')))) &&
        Object.values(r).some((v) =>
          String(v ?? '')
            .toLowerCase()
            .includes(entitySearch.toLowerCase()),
        ),
    );
  }, [scope, data, entityTab, entitySearch, filters.state, filters.fy]);
  const dictionary = useMemo(
    () =>
      data.dictionary.filter((r) =>
        Object.values(r).some((v) =>
          String(v ?? '')
            .toLowerCase()
            .includes(fieldSearch.toLowerCase()),
        ),
      ),
    [data, fieldSearch],
  );
  function filter<K extends keyof Filters>(key: K, value: Filters[K]) {
    setFilters((f) => ({ ...f, [key]: value }));
    setPage(0);
    setPairPage(0);
    setEntityPage(0);
  }
  function openWork(id: string) {
    setFocus({ kind: 'work', key: id });
  }
  function showQueue(signal = 'all', band = 'all') {
    setFilters((f) => ({ ...f, signal, band, search: '', status: 'all' }));
    setPage(0);
    setView('queue');
  }
  const active = NAV.find((v) => v.key === view)!;
  const fullStats = useMemo(() => summarize(data.works), [data]);
  const selected =
    focus?.kind === 'work'
      ? workMap.get(focus.key)
      : focus?.kind === 'pair'
        ? data.pairs.find(
            (p) => s(p, 'work_id_a') + '-' + s(p, 'work_id_b') === focus.key,
          )
        : focus?.kind === 'mp'
          ? data.mps.find((m) => s(m, 'mp_name_key') === focus.key)
          : focus?.kind === 'ida'
            ? data.idas.find((m) => s(m, 'ida_key') === focus.key)
            : null;
  const reviewRows = Object.entries(reviews).map(([id, r]) => ({
    record: id,
    ...r,
  }));
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
              MPLADS<span>INSIGHT</span>
            </strong>
            <small>Investigation workspace</small>
          </div>
        </SidebarHeader>
        <SidebarContent>
          <p className="nav-caption">WORKSPACE</p>
          <SidebarMenu>
            {NAV.map((item) => (
              <SidebarMenuItem key={item.key}>
                <SidebarMenuButton
                  isActive={view === item.key}
                  onClick={() => setView(item.key)}
                  className="nav-item"
                >
                  <item.icon size={19} />
                  <span>{item.label}</span>
                  {item.key === 'queue' && (
                    <span className="nav-count">{fullStats.priority}</span>
                  )}
                </SidebarMenuButton>
              </SidebarMenuItem>
            ))}
          </SidebarMenu>
        </SidebarContent>
        <SidebarFooter>
          <div className="sidebar-source">
            <span className="connection-dot" />
            Local source connected
            <small>Snapshot · {dateLabel(data.meta.snapshot)}</small>
            <small>{data.meta.pipelineVersion ?? 'Exploratory workbook'}</small>
          </div>
          <div className="sidebar-foot">
            PS 26102 <span>Prototype</span>
          </div>
        </SidebarFooter>
      </Sidebar>
      <SidebarInset className="app-main">
        <header className="topbar">
          <div>
            <SidebarTrigger />
            <span className="crumb">
              MPLADS / <strong>{active.label}</strong>
            </span>
          </div>
          <span className="environment-pill">
            <span />
            Local prototype
          </span>
        </header>
        <main className="main-content">
          <div className="page-heading">
            <div>
              <p className="eyebrow">MONITOR · INVESTIGATE · REVIEW</p>
              <h1>{active.label}</h1>
              <p className="page-description">
                {view === 'overview'
                  ? 'A clear view of the works that need a closer look.'
                  : view === 'queue'
                    ? 'Find a work, inspect its evidence, and record your review.'
                    : view === 'duplicates'
                      ? 'Compare candidate works before requesting location and scope evidence.'
                      : view === 'entities'
                        ? 'Follow the connections between MPs, implementing authorities and works.'
                        : view === 'validation'
                          ? 'Compare screening approaches at the same review capacity.'
                          : 'Understand the source, screening method and route to an operational system.'}
              </p>
            </div>
            {view === 'queue' ? (
              <DownloadButton rows={queue} name="mplads-selected-works" />
            ) : (
              <div className="snapshot-date">
                <Clock3 size={16} />
                <span>As of {dateLabel(data.meta.snapshot)}</span>
              </div>
            )}
          </div>
          <div className="coverage-strip">
            <CircleAlert size={18} />
            <p>
              <strong>Partial works extract.</strong> 10,000 works represent
              12.75% of the source-reported sanctioned value. All results
              describe this extract.
            </p>
            <button onClick={() => setView('method')}>
              Data notes <ArrowRight size={14} />
            </button>
          </div>
          {!['method', 'validation'].includes(view) && (
            <div className="global-filters">
              <Pick
                label="State"
                value={filters.state}
                options={['all', ...states].map((v) => [
                  v,
                  v === 'all' ? 'All states' : v,
                ])}
                onChange={(v) => filter('state', v)}
              />
              <Pick
                label="Sanction financial year"
                value={filters.fy}
                options={['all', ...fys].map((v) => [
                  v,
                  v === 'all' ? 'All financial years' : v,
                ])}
                onChange={(v) => filter('fy', v)}
              />
              <span className="scope-count">
                {number(scope.length)} works in scope
              </span>
              {(filters.state !== 'all' || filters.fy !== 'all') && (
                <Button
                  variant="ghost"
                  onClick={() => {
                    setFilters(defaults);
                    setPage(0);
                    setPairPage(0);
                    setEntityPage(0);
                  }}
                >
                  Reset scope
                </Button>
              )}
            </div>
          )}
          {view === 'overview' && (
            <>
              <div className="metric-grid">
                <Metric
                  label="Works in scope"
                  value={number(stats.count)}
                  detail={`${number(new Set(scope.map((w) => w.mp_name_key)).size)} MPs · ${number(new Set(scope.map((w) => w.ida_key)).size)} authorities`}
                  icon={Layers3}
                  onClick={() => showQueue()}
                />
                <Metric
                  label="Visible sanctions"
                  value={money(stats.total)}
                  detail="Sanctioned amounts in the selected extract"
                  icon={Building2}
                />
                <Metric
                  label="Priority reviews"
                  value={number(stats.priority)}
                  detail={`${stats.bands.High} high · ${stats.bands.Medium} medium`}
                  icon={ArrowUpRight}
                  onClick={() => showQueue('all', 'priority')}
                />
                <Metric
                  label="Early-stage aging"
                  value={number(stats.aging)}
                  detail="Over 180 days since sanction"
                  icon={Clock3}
                  onClick={() => showQueue('aging')}
                />
              </div>
              <div className="overview-grid">
                <section className="panel">
                  <div className="panel-head">
                    <div>
                      <h2>Signals to investigate</h2>
                      <p>A work may appear in more than one signal.</p>
                    </div>
                    <ListFilter size={20} />
                  </div>
                  <div className="signal-list">
                    {[
                      [
                        'Sanction delay',
                        'delay',
                        stats.delay,
                        'Over 45 calendar days',
                      ],
                      [
                        'Duplicate candidates',
                        'duplicate',
                        stats.duplicate,
                        'Description and contextual matches',
                      ],
                      [
                        'Early-stage aging',
                        'aging',
                        stats.aging,
                        'Awaiting evidence of progress',
                      ],
                      [
                        'High peer cost',
                        'cost',
                        stats.cost,
                        'Unusual compared with peer works',
                      ],
                    ].map(([title, key, count, note]) => (
                      <button
                        key={key}
                        className="signal-row"
                        onClick={() => showQueue(String(key))}
                      >
                        <div>
                          <strong>{title}</strong>
                          <span>{note}</span>
                        </div>
                        <div className="signal-measure">
                          <strong>{number(Number(count))}</strong>
                          <div className="bar-track">
                            <i
                              style={{
                                width: percent(
                                  stats.count ? Number(count) / stats.count : 0,
                                ),
                              }}
                            />
                          </div>
                        </div>
                        <ArrowUpRight size={17} />
                      </button>
                    ))}
                  </div>
                </section>
                <section className="panel priority-panel">
                  <div className="panel-head">
                    <div>
                      <h2>Review priority</h2>
                      <p>Explainable screening score, 0–100</p>
                    </div>
                    <ShieldCheck size={20} />
                  </div>
                  <div className="priority-total">
                    <strong>{number(stats.priority)}</strong>
                    <span>works for focused review</span>
                  </div>
                  <div
                    className="stacked-bar"
                    aria-label="Priority distribution"
                  >
                    {Object.entries(stats.bands).map(([band, count]) => (
                      <div
                        key={band}
                        className={'segment-' + band.toLowerCase()}
                        style={{
                          width: percent(stats.count ? count / stats.count : 0),
                        }}
                        title={`${band}: ${count}`}
                      />
                    ))}
                  </div>
                  <div className="band-grid">
                    {Object.entries(stats.bands).map(([band, count]) => (
                      <button key={band} onClick={() => showQueue('all', band)}>
                        <Band value={band} />
                        <strong>{number(count)}</strong>
                      </button>
                    ))}
                  </div>
                  <p className="quiet">
                    Scores guide evidence review. They do not establish misuse
                    of funds.
                  </p>
                </section>
              </div>
              <div className="overview-grid">
                <section className="panel">
                  <div className="panel-head">
                    <div>
                      <h2>Monthly sanctions</h2>
                      <p>Number of visible works by sanction month</p>
                    </div>
                  </div>
                  <Trend months={stats.months} />
                </section>
                <section className="panel">
                  <div className="panel-head">
                    <div>
                      <h2>Work execution stages</h2>
                      <p>Current status at the snapshot</p>
                    </div>
                  </div>
                  <div className="stage-list">
                    {[
                      'Planning',
                      'Sanctioned',
                      'Procurement',
                      'Execution',
                      'Verification',
                      'Completed',
                    ].map((stage) => (
                      <div key={stage}>
                        <div>
                          <span>{stage}</span>
                          <strong>{number(stats.stages[stage] ?? 0)}</strong>
                        </div>
                        <div className="bar-track">
                          <i
                            style={{
                              width: percent(
                                stats.count
                                  ? (stats.stages[stage] ?? 0) / stats.count
                                  : 0,
                              ),
                            }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </section>
              </div>
              <section className="panel">
                <div className="panel-head">
                  <div>
                    <h2>Start with these works</h2>
                    <p>Highest review priorities in the selected scope</p>
                  </div>
                  <Button
                    variant="ghost"
                    onClick={() => showQueue('all', 'priority')}
                  >
                    Open queue <ArrowRight size={16} />
                  </Button>
                </div>
                <WorkTable
                  rows={priority}
                  onOpen={openWork}
                  reviews={reviews}
                  small
                />
              </section>
            </>
          )}
          {view === 'queue' && (
            <section className="panel">
              <div className="queue-controls">
                <div className="search-box">
                  <Search size={18} />
                  <Input
                    aria-label="Search works"
                    placeholder="Search work ID, description, MP or district"
                    value={filters.search}
                    onChange={(e) => filter('search', e.target.value)}
                  />
                </div>
                <Pick
                  label="Priority"
                  value={filters.band}
                  options={[
                    ['all', 'All priorities'],
                    ['priority', 'High + Medium'],
                    'High',
                    'Medium',
                    'Low',
                    'Routine',
                  ]}
                  onChange={(v) => filter('band', v)}
                />
                <Pick
                  label="Signal"
                  value={filters.signal}
                  options={SIGNALS}
                  onChange={(v) => filter('signal', v)}
                />
                <Pick
                  label="Status"
                  value={filters.status}
                  options={[
                    ['all', 'All statuses'],
                    ...Array.from(
                      new Set(data.works.map((w) => s(w, 'work_status'))),
                    ).sort(),
                  ]}
                  onChange={(v) => filter('status', v)}
                />
                <Pick
                  label="Sort by"
                  value={filters.sort}
                  options={[
                    ['priority', 'Highest priority'],
                    ['amount', 'Largest sanction'],
                    ['delay', 'Longest sanction delay'],
                    ['age', 'Oldest work'],
                  ]}
                  onChange={(v) => filter('sort', v)}
                />
              </div>
              <div className="selection-summary">
                <strong>{number(queue.length)} matching works</strong>
                <span>
                  {money(
                    queue.reduce((t, w) => t + n(w, 'sanction_amount'), 0),
                  )}{' '}
                  visible sanctions
                </span>
                <Button
                  variant="ghost"
                  onClick={() => {
                    setFilters((f) => ({
                      ...defaults,
                      state: f.state,
                      fy: f.fy,
                    }));
                    setPage(0);
                  }}
                >
                  Clear queue filters
                </Button>
              </div>
              <WorkTable
                rows={queue.slice(page * 20, page * 20 + 20)}
                onOpen={openWork}
                reviews={reviews}
              />
              <Pager page={page} total={queue.length} onChange={setPage} />
            </section>
          )}
          {view === 'duplicates' && (
            <section className="panel">
              <div className="queue-controls">
                <div className="search-box">
                  <Search size={18} />
                  <Input
                    aria-label="Search duplicate pairs"
                    placeholder="Search either work ID or description"
                    value={pairSearch}
                    onChange={(e) => {
                      setPairSearch(e.target.value);
                      setPairPage(0);
                    }}
                  />
                </div>
                <Pick
                  label="Evidence strength"
                  value={strength}
                  options={[
                    ['all', 'All strengths'],
                    'Strong',
                    'Moderate',
                    'Weak',
                  ]}
                  onChange={(v) => {
                    setStrength(v);
                    setPairPage(0);
                  }}
                />
                <DownloadButton
                  rows={pairRows}
                  name="mplads-duplicate-candidates"
                />
              </div>
              <div className="selection-summary">
                <strong>{number(pairRows.length)} candidate pairs</strong>
                <span>
                  A pair is included when either work is in scope. Similarity
                  alone cannot confirm a duplicate.
                </span>
              </div>
              {pairRows.length ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Candidate works</TableHead>
                      <TableHead>Location</TableHead>
                      <TableHead>Evidence</TableHead>
                      <TableHead>Text match</TableHead>
                      <TableHead>Amount match</TableHead>
                      <TableHead>Compare</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {pairRows
                      .slice(pairPage * 20, pairPage * 20 + 20)
                      .map((p) => (
                        <TableRow
                          key={s(p, 'work_id_a') + '-' + s(p, 'work_id_b')}
                        >
                          <TableCell className="work-cell">
                            <button
                              className="record-title"
                              onClick={() =>
                                setFocus({
                                  kind: 'pair',
                                  key:
                                    s(p, 'work_id_a') + '-' + s(p, 'work_id_b'),
                                })
                              }
                            >
                              {s(p, 'description_a')}
                            </button>
                            <span className="record-meta">
                              #{s(p, 'work_id_a')} ↔ #{s(p, 'work_id_b')}
                            </span>
                          </TableCell>
                          <TableCell>
                            {s(p, 'state')}
                            <span className="record-meta">{s(p, 'ida_a')}</span>
                          </TableCell>
                          <TableCell>
                            <Band value={s(p, 'evidence_strength')} />
                          </TableCell>
                          <TableCell>{percent(n(p, 'similarity'))}</TableCell>
                          <TableCell>
                            {b(p, 'same_amount_flag')
                              ? 'Same amount'
                              : money(n(p, 'amount_difference')) +
                                ' difference'}
                          </TableCell>
                          <TableCell>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() =>
                                setFocus({
                                  kind: 'pair',
                                  key:
                                    s(p, 'work_id_a') + '-' + s(p, 'work_id_b'),
                                })
                              }
                            >
                              Compare <ArrowUpRight size={15} />
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                  </TableBody>
                </Table>
              ) : (
                <EmptyResults />
              )}
              <Pager
                page={pairPage}
                total={pairRows.length}
                onChange={setPairPage}
              />
            </section>
          )}
          {view === 'entities' && (
            <section className="panel">
              <div className="queue-controls">
                <Tabs
                  value={entityTab}
                  onValueChange={(v) => {
                    setEntityTab(String(v));
                    setEntityPage(0);
                  }}
                >
                  <TabsList>
                    <TabsTrigger value="mp">Members of Parliament</TabsTrigger>
                    <TabsTrigger value="ida">
                      Implementing authorities
                    </TabsTrigger>
                  </TabsList>
                </Tabs>
                <div className="search-box">
                  <Search size={18} />
                  <Input
                    aria-label="Search entities"
                    placeholder="Find an MP, district or authority"
                    value={entitySearch}
                    onChange={(e) => {
                      setEntitySearch(e.target.value);
                      setEntityPage(0);
                    }}
                  />
                </div>
              </div>
              <p className="section-note">
                Profiles show full-extract aggregates. State/year filters select
                entities connected to the works in scope.
              </p>
              {entityRows.length ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>
                        {entityTab === 'mp'
                          ? 'Member of Parliament'
                          : 'Implementing authority'}
                      </TableHead>
                      <TableHead>Visible works</TableHead>
                      <TableHead>Visible sanctions</TableHead>
                      <TableHead>Delay &gt;45 days</TableHead>
                      <TableHead>
                        {entityTab === 'mp'
                          ? 'Calamity consents'
                          : 'Completed status'}
                      </TableHead>
                      <TableHead>Profile priority</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {entityRows
                      .slice(entityPage * 20, entityPage * 20 + 20)
                      .map((e) => {
                        const mp = entityTab === 'mp',
                          key = mp ? 'mp' : 'ida';
                        return (
                          <TableRow key={s(e, mp ? 'mp_name_key' : 'ida_key')}>
                            <TableCell>
                              <button
                                className="record-title"
                                onClick={() =>
                                  setFocus({
                                    kind: mp ? 'mp' : 'ida',
                                    key: s(e, mp ? 'mp_name_key' : 'ida_key'),
                                  })
                                }
                              >
                                {s(e, mp ? 'mp_name' : 'ida_authority')}
                              </button>
                              <span className="record-meta">
                                {s(e, mp ? 'mp_constituency' : 'ida_district')}{' '}
                                · {s(e, mp ? 'mp_state' : 'state')}
                              </span>
                            </TableCell>
                            <TableCell>
                              {number(n(e, key + '_visible_work_count'))}
                            </TableCell>
                            <TableCell>
                              {money(
                                e[key + '_visible_sanction_total'] as
                                  | number
                                  | null,
                              )}
                            </TableCell>
                            <TableCell>
                              {n(e, key + '_visible_work_count')
                                ? percent(n(e, key + '_delay_over45_share'))
                                : 'No works'}
                            </TableCell>
                            <TableCell>
                              {mp
                                ? number(n(e, 'mp_calamity_consent_count'))
                                : percent(n(e, 'ida_completed_share'))}
                            </TableCell>
                            <TableCell>
                              <Band
                                value={s(e, key + '_review_priority_band')}
                              />
                            </TableCell>
                          </TableRow>
                        );
                      })}
                  </TableBody>
                </Table>
              ) : (
                <EmptyResults />
              )}
              <Pager
                page={entityPage}
                total={entityRows.length}
                onChange={setEntityPage}
              />
            </section>
          )}
          {view === 'validation' && <Validation openWork={openWork} />}
          {view === 'method' && (
            <>
              <div className="metric-grid">
                <Metric
                  label="Raw datasets connected"
                  value="3"
                  detail="Works · MP allocation · calamity consent"
                  icon={Database}
                />
                <Metric
                  label="Work-level fields"
                  value={String(data.tables.Work_Features.columns.length)}
                  detail="Source, engineered and screening fields"
                  icon={Layers3}
                />
                <Metric
                  label="MP join coverage"
                  value="100%"
                  detail="Works and consents matched by normalized key"
                  icon={Check}
                />
                <Metric
                  label="Review outcomes"
                  value={number(reviewRows.length)}
                  detail="Saved locally on this computer"
                  icon={ListFilter}
                />
              </div>
              <section className="panel">
                <div className="panel-head">
                  <div>
                    <h2>Solution roadmap</h2>
                    <p>
                      From an evidence review prototype to an operational
                      monitoring service
                    </p>
                  </div>
                  <a
                    className="text-link"
                    href="/api/download/plan.md"
                    download
                  >
                    Download plan <Download size={15} />
                  </a>
                </div>
                <div className="roadmap">
                  {[
                    [
                      '01',
                      'Working prototype',
                      'Connected portfolio, searchable case queue, duplicate evidence, entity profiles and review export.',
                    ],
                    [
                      '02',
                      'Complete the evidence',
                      'Obtain uncapped works, dated allocations, receipt/MCC dates, payments, estimates and progress history.',
                    ],
                    [
                      '03',
                      'Operational pilot',
                      'Add authenticated role scopes, shared case storage, assignment, refresh jobs and an audit trail.',
                    ],
                    [
                      '04',
                      'Expand detection',
                      'Validate unit costs, payment reconciliation, vendor links and geospatial/asset evidence.',
                    ],
                    [
                      '05',
                      'Predictive deployment',
                      'Use independent review labels and temporal holdouts to evaluate delay forecasts and learned ranking.',
                    ],
                  ].map(([id, title, desc]) => (
                    <article key={id}>
                      <span>{id}</span>
                      <div>
                        <h3>{title}</h3>
                        <p>{desc}</p>
                      </div>
                    </article>
                  ))}
                </div>
              </section>
              <section className="panel">
                <div className="panel-head">
                  <h2>Evidence boundaries</h2>
                </div>
                <div className="method-grid">
                  <article>
                    <h3>Observed sanctions ≠ expenditure</h3>
                    <p>
                      Payments and expenditure are absent. Allocation dates are
                      not supplied. Ratios cannot measure spending utilization.
                    </p>
                  </article>
                  <article>
                    <h3>Aging is a review signal</h3>
                    <p>
                      Status has no last-update date. The latest sanction date,
                      01 September 2026, is a snapshot proxy. IDA receipt and
                      MCC dates are needed for a final 45-day rule assessment.
                    </p>
                  </article>
                  <article>
                    <h3>Costs and duplicate candidates</h3>
                    <p>
                      Peer costs need asset dimensions and estimates. Text
                      matches need location, scope and phase evidence. No
                      confirmed fraud labels are supplied.
                    </p>
                  </article>
                  <article>
                    <h3>Model evaluation</h3>
                    <p>
                      These scores come from the versioned raw-data pipeline.
                      The A/B experiment uses a separate frozen ranking model;
                      it does not validate these snapshot scores. Recompute peer
                      and entity features inside each historical training cutoff
                      before predictive use. Rates describe this selected
                      extract.
                    </p>
                  </article>
                </div>
              </section>
              <section className="panel">
                <div className="panel-head">
                  <div>
                    <h2>Connected calamity consents</h2>
                    <p>
                      MP-level context; these records do not identify the works
                      funded.
                    </p>
                  </div>
                </div>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Event</TableHead>
                      <TableHead>MP</TableHead>
                      <TableHead>Consent date</TableHead>
                      <TableHead>Amount</TableHead>
                      <TableHead>Review</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.calamities.map((c) => (
                      <TableRow key={s(c, 'source_row_number')}>
                        <TableCell>
                          {s(c, 'calamity_name')}
                          <span className="record-meta">
                            {s(c, 'calamity_type')}
                          </span>
                        </TableCell>
                        <TableCell>
                          <button
                            className="record-title"
                            onClick={() =>
                              setFocus({ kind: 'mp', key: s(c, 'mp_name_key') })
                            }
                          >
                            {s(c, 'mp_name')}
                          </button>
                        </TableCell>
                        <TableCell>{dateLabel(s(c, 'consent_date'))}</TableCell>
                        <TableCell>{money(n(c, 'consent_amount'))}</TableCell>
                        <TableCell>
                          <Band
                            value={
                              s(c, 'calamity_review_band') ||
                              (b(c, 'potential_limit_breach_flag')
                                ? 'High'
                                : 'Not assessed')
                            }
                          />
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </section>
              <section className="panel">
                <div className="panel-head">
                  <div>
                    <h2>Scoring rules</h2>
                    <p>
                      Work review points; each case shows its contributing
                      rules.
                    </p>
                  </div>
                  <a
                    href={data.meta.guidelines}
                    target="_blank"
                    rel="noreferrer"
                    className="text-link"
                  >
                    Official guidelines <ExternalLink size={14} />
                  </a>
                </div>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Condition</TableHead>
                      <TableHead>Points</TableHead>
                      <TableHead>Interpretation</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.rules.map((r) => (
                      <TableRow key={String(r[3])}>
                        <TableCell>{r[1]}</TableCell>
                        <TableCell>{r[2]}</TableCell>
                        <TableCell>{r[4]}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </section>
              <section className="panel">
                <div className="panel-head">
                  <div>
                    <h2>Feature dictionary</h2>
                    <p>
                      {data.dictionary.length} field definitions across
                      connected tables
                    </p>
                  </div>
                  <Input
                    aria-label="Search feature dictionary"
                    className="dictionary-search"
                    placeholder="Search a field or definition"
                    value={fieldSearch}
                    onChange={(e) => {
                      setFieldSearch(e.target.value);
                      setFieldPage(0);
                    }}
                  />
                </div>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Field</TableHead>
                      <TableHead>Definition</TableHead>
                      <TableHead>Model guidance</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {dictionary
                      .slice(fieldPage * 20, fieldPage * 20 + 20)
                      .map((r) => (
                        <TableRow key={s(r, 'sheet') + s(r, 'field')}>
                          <TableCell>
                            <code>{s(r, 'field')}</code>
                            <span className="record-meta">
                              {s(r, 'sheet')} · {s(r, 'data_type')}
                            </span>
                          </TableCell>
                          <TableCell>{s(r, 'definition')}</TableCell>
                          <TableCell>
                            {s(r, 'model_use')}
                            <span className="record-meta">
                              {s(r, 'caution')}
                            </span>
                          </TableCell>
                        </TableRow>
                      ))}
                  </TableBody>
                </Table>
                <Pager
                  page={fieldPage}
                  total={dictionary.length}
                  onChange={setFieldPage}
                />
              </section>
              <section className="panel provenance">
                <h2>Source provenance</h2>
                <a className="text-link" href="/api/download/final.xlsx" download>
                  Download final Excel dataset <Download size={15} />
                </a>
                <p>{data.meta.sourceFile}</p>
                <code>SHA-256: {data.meta.sourceSha256}</code>
                <p>
                  Data remains on this computer. The feature workbook and raw
                  source files are preserved.
                </p>
              </section>
            </>
          )}
          {reviewError && (
            <p className="evidence-callout" role="alert">
              {reviewError}
            </p>
          )}
          <footer className="workspace-footer">
            <span>MPLADS Insight · PS 26102 · Research prototype</span>
            <div>
              <span>{reviewRows.length} saved reviews</span>
              <DownloadButton
                rows={reviewRows}
                name="mplads-saved-reviews"
                label="Export reviews"
              />
            </div>
          </footer>
        </main>
      </SidebarInset>
      <Sheet
        open={!!focus}
        onOpenChange={(open) => {
          if (!open) setFocus(null);
        }}
      >
        <SheetContent className="evidence-sheet">
          <SheetHeader>
            <SheetTitle>
              {focus?.kind === 'work'
                ? 'Work evidence'
                : focus?.kind === 'pair'
                  ? 'Compare candidate works'
                  : 'Connected profile'}
            </SheetTitle>
            <SheetDescription>
              {focus?.kind === 'pair'
                ? 'Check the similarities and differences before requesting verification.'
                : 'Source records and screening context from the supplied extract.'}
            </SheetDescription>
          </SheetHeader>
          {selected &&
            focus &&
            (focus.kind === 'work' ? (
              <CaseDetail
                work={selected}
                data={data}
                review={reviews[focus.key]}
                save={(r) => saveReview(focus.key, r)}
                openPair={(key) => setFocus({ kind: 'pair', key })}
                openEntity={(kind, key) => setFocus({ kind, key })}
              />
            ) : focus.kind === 'pair' ? (
              <PairDetail
                pair={selected}
                workMap={workMap}
                openWork={openWork}
                review={reviews['pair:' + focus.key]}
                save={(r) => saveReview('pair:' + focus.key, r)}
              />
            ) : (
              <EntityDetail
                entity={selected}
                kind={focus.kind}
                data={data}
                openWork={openWork}
                reviews={reviews}
              />
            ))}
        </SheetContent>
      </Sheet>
    </SidebarProvider>
  );
}

function Trend({ months }: { months: Record<string, number> }) {
  const entries = Object.entries(months).sort(([a], [b]) => a.localeCompare(b));
  const max = Math.max(1, ...entries.map(([, v]) => v));
  if (!entries.length) return <EmptyResults />;
  return (
    <div className="trend">
      <div className="trend-bars">
        {entries.map(([month, count]) => (
          <div key={month} className="trend-column">
            <span className="trend-tip">
              {month}: {number(count)}
            </span>
            <i
              style={{ height: `${Math.max(2, (count / max) * 100)}%` }}
              title={`${month}: ${number(count)} works`}
            />
          </div>
        ))}
      </div>
      <div className="trend-axis">
        <span>{entries[0][0]}</span>
        <span>Peak: {number(max)} works / month</span>
        <span>{entries.at(-1)![0]}</span>
      </div>
    </div>
  );
}
function Facts({ items }: { items: [string, React.ReactNode][] }) {
  return (
    <dl className="facts">
      {items.map(([label, value]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  );
}
function ReviewForm({
  review,
  save,
}: {
  review?: Decision;
  save: (r: Decision) => Promise<void>;
}) {
  const [outcome, setOutcome] = useState(review?.outcome ?? 'Needs evidence'),
    [note, setNote] = useState(review?.note ?? ''),
    [message, setMessage] = useState(''),
    [saving, setSaving] = useState(false);
  useEffect(() => {
    setOutcome(review?.outcome ?? 'Needs evidence');
    setNote(review?.note ?? '');
  }, [review]);
  async function submit() {
    setSaving(true);
    setMessage('');
    try {
      await save({
        outcome,
        note: note.trim(),
        updated: new Date().toISOString(),
      });
      setMessage(
        'Review saved on this computer. Earlier decisions remain in the local history.',
      );
    } catch (e) {
      setMessage(e instanceof Error ? e.message : 'Could not save review.');
    } finally {
      setSaving(false);
    }
  }
  return (
    <section className="review-form">
      <h3>Record your review</h3>
      <p>
        Saved on this computer with a timestamp and dataset version. This
        single-user prototype has no authenticated officer identity.
      </p>
      <Pick
        label="Disposition"
        value={outcome}
        options={[
          'Needs evidence',
          'Expected variation',
          'Data issue',
          'Substantiated issue',
        ]}
        onChange={(v) => {
          setOutcome(v);
          setMessage('');
        }}
      />
      <label htmlFor="review-note">Evidence or next action</label>
      <Textarea
        id="review-note"
        value={note}
        maxLength={3000}
        placeholder="Document what you checked and what evidence is needed next."
        onChange={(e) => {
          setNote(e.target.value);
          setMessage('');
        }}
      />
      <Button onClick={submit} disabled={!note.trim() || saving}>
        <Check size={16} />
        {saving ? 'Saving…' : 'Save review'}
      </Button>
      <span role="status">
        {message ||
          (review
            ? 'Last saved: ' + new Date(review.updated).toLocaleString('en-IN')
            : '')}
      </span>
      <a
        className="text-link"
        href="/api/reviews/history"
        target="_blank"
        rel="noreferrer"
      >
        Open local review history <ExternalLink size={14} />
      </a>
    </section>
  );
}
function CaseDetail({
  work: w,
  data,
  review,
  save,
  openPair,
  openEntity,
}: {
  work: Row;
  data: Data;
  review?: Decision;
  save: (r: Decision) => Promise<void>;
  openPair: (k: string) => void;
  openEntity: (kind: 'mp' | 'ida', key: string) => void;
}) {
  const parts = reasons(w, data.rules);
  const pairs = data.pairs.filter(
    (p) => p.work_id_a === w.work_id || p.work_id_b === w.work_id,
  );
  return (
    <div className="drawer-body">
      <div className="case-heading">
        <span className="case-id">WORK #{s(w, 'work_id')}</span>
        <div>
          <Band value={s(w, 'review_priority_band')} />
          <strong>
            {n(w, 'review_priority_score')}
            <small>/100</small>
          </strong>
        </div>
      </div>
      <h2 className="case-description">{s(w, 'work_description')}</h2>
      <p className="record-meta">
        {s(w, 'work_type')} · {s(w, 'work_category')}
      </p>
      <Facts
        items={[
          ['Sanction amount', money(n(w, 'sanction_amount'), false)],
          ['Current status', s(w, 'work_status')],
          ['State / district', s(w, 'state') + ' / ' + s(w, 'ida_district')],
          ['Financial year', s(w, 'sanction_fiscal_year')],
          ['Recommendation', dateLabel(s(w, 'recommended_date'))],
          ['Sanction', dateLabel(s(w, 'sanction_date'))],
          [
            'Recommendation → sanction',
            number(n(w, 'sanction_delay_days')) + ' calendar days',
          ],
          [
            'Age at snapshot',
            number(n(w, 'age_days_at_snapshot_proxy')) + ' days',
          ],
        ]}
      />
      <section className="evidence-section">
        <h3>Why this work is in the queue</h3>
        {parts.length ? (
          parts.map((p) => (
            <div className="reason" key={p.code}>
              <div>
                <strong>{p.label}</strong>
                <span>{p.note}</span>
              </div>
              <b>+{p.points}</b>
            </div>
          ))
        ) : (
          <p>No priority points under the current screening rules.</p>
        )}
        <p className="quiet">
          Components total {parts.reduce((a, p) => a + p.points, 0)} points,
          capped at 100; published score {n(w, 'review_priority_score')}. The
          anomaly percentile is a relative rank, not a probability.
        </p>
      </section>
      <section className="evidence-section">
        <h3>Cost context</h3>
        <Facts
          items={[
            ['Peer median', money(n(w, 'peer_amount_median'), false)],
            [
              'Amount / peer median',
              n(w, 'amount_to_peer_median_ratio').toFixed(2) + '×',
            ],
            ['Peer sample', number(n(w, 'peer_group_count')) + ' works'],
            ['Peer grouping', s(w, 'peer_group_level')],
            ['Robust cost z-score', n(w, 'peer_cost_robust_z').toFixed(2)],
            [
              'Anomaly percentile',
              n(w, 'robust_multivariate_anomaly_percentile').toFixed(2),
            ],
          ]}
        />
        <p className="quiet">
          Physical dimensions, estimates and spending are needed to assess an
          overrun.
        </p>
      </section>
      <section className="evidence-section">
        <h3>Connected records</h3>
        <button
          className="entity-link"
          onClick={() => openEntity('mp', s(w, 'mp_name_key'))}
        >
          <div>
            <span>Recommending MP</span>
            <strong>{s(w, 'mp_name')}</strong>
          </div>
          <ArrowUpRight />
        </button>
        <button
          className="entity-link"
          onClick={() => openEntity('ida', s(w, 'ida_key'))}
        >
          <div>
            <span>Implementing authority</span>
            <strong>{s(w, 'ida_authority')}</strong>
          </div>
          <ArrowUpRight />
        </button>
        <Facts
          items={[
            ['Allocated limit', money(w.mp_allocated_limit as number | null)],
            [
              'MP calamity consents',
              `${number(n(w, 'mp_calamity_consent_count'))} · ${money(n(w, 'mp_calamity_consent_total'))}`,
            ],
          ]}
        />
      </section>
      {pairs.length > 0 && (
        <section className="evidence-section">
          <h3>
            {pairs.length} duplicate candidate pair
            {pairs.length === 1 ? '' : 's'}
          </h3>
          {pairs.slice(0, 8).map((p) => (
            <button
              className="entity-link"
              key={s(p, 'work_id_a') + '-' + s(p, 'work_id_b')}
              onClick={() =>
                openPair(s(p, 'work_id_a') + '-' + s(p, 'work_id_b'))
              }
            >
              <span>
                #{s(p, 'work_id_a')} ↔ #{s(p, 'work_id_b')} ·{' '}
                {percent(n(p, 'similarity'))}
              </span>
              <Band value={s(p, 'evidence_strength')} />
            </button>
          ))}
          {pairs.length > 8 && (
            <p className="quiet">
              First 8 shown. The duplicate review screen contains all pairs.
            </p>
          )}
        </section>
      )}
      <ReviewForm key={s(w, 'work_id')} review={review} save={save} />
      <details className="feature-details">
        <summary>
          All {data.tables.Work_Features.columns.length} source and engineered
          fields
        </summary>
        <Facts
          items={data.tables.Work_Features.columns.map((key) => [
            key,
            w[key] == null ? 'Not supplied' : String(w[key]),
          ])}
        />
      </details>
    </div>
  );
}
function PairDetail({
  pair: p,
  workMap,
  openWork,
  review,
  save,
}: {
  pair: Row;
  workMap: Map<string, Row>;
  openWork: (id: string) => void;
  review?: Decision;
  save: (r: Decision) => Promise<void>;
}) {
  return (
    <div className="drawer-body">
      <div className="comparison-summary">
        <Band value={s(p, 'evidence_strength')} />
        <strong>{percent(n(p, 'similarity'))} text similarity</strong>
      </div>
      <div className="match-chips">
        {[
          ['same_mp_flag', 'Same MP'],
          ['same_ida_flag', 'Same authority'],
          ['same_amount_flag', 'Same amount'],
          ['same_sanction_date_flag', 'Same date'],
          ['same_work_type_flag', 'Same type'],
        ].map(([key, label]) => (
          <span key={key} className={b(p, key) ? 'match' : 'different'}>
            {b(p, key) ? <Check size={14} /> : <CircleAlert size={14} />}{' '}
            {label}
          </span>
        ))}
      </div>
      <div className="comparison-grid">
        {['a', 'b'].map((side) => {
          const w = workMap.get(s(p, 'work_id_' + side));
          return (
            <article key={side}>
              <p className="eyebrow">CANDIDATE {side.toUpperCase()}</p>
              <button
                className="text-link"
                onClick={() => openWork(s(p, 'work_id_' + side))}
              >
                Work #{s(p, 'work_id_' + side)} <ArrowUpRight size={16} />
              </button>
              <h3>{s(p, 'description_' + side)}</h3>
              <Facts
                items={[
                  ['Sanction', money(n(p, 'sanction_amount_' + side), false)],
                  ['Date', dateLabel(s(p, 'sanction_date_' + side))],
                  ['MP', s(p, 'mp_name_' + side)],
                  ['Authority', s(p, 'ida_' + side)],
                  [
                    'Continuation / phase cue',
                    w && b(w, 'description_continuation_flag')
                      ? 'Present'
                      : 'Not detected',
                  ],
                ]}
              />
            </article>
          );
        })}
      </div>
      <div className="evidence-callout">
        <CircleAlert />
        <p>
          Request site coordinates, scope, asset identifiers and phase
          documents. Similar descriptions can represent legitimate separate
          works.
        </p>
      </div>
      <ReviewForm
        key={s(p, 'work_id_a') + '-' + s(p, 'work_id_b')}
        review={review}
        save={save}
      />
    </div>
  );
}
function EntityDetail({
  entity: e,
  kind,
  data,
  openWork,
  reviews,
}: {
  entity: Row;
  kind: 'mp' | 'ida';
  data: Data;
  openWork: (id: string) => void;
  reviews: Record<string, Decision>;
}) {
  const mp = kind === 'mp',
    key = mp ? 'mp_name_key' : 'ida_key';
  const linked = data.works
    .filter((w) => w[key] === e[key])
    .sort(
      (a, b) => n(b, 'review_priority_score') - n(a, 'review_priority_score'),
    );
  const consents = mp
    ? data.calamities.filter((c) => c.mp_name_key === e.mp_name_key)
    : [];
  const [page, setPage] = useState(0);
  useEffect(() => setPage(0), [e]);
  return (
    <div className="drawer-body">
      <h2 className="case-description">
        {s(e, mp ? 'mp_name' : 'ida_authority')}
      </h2>
      <p>
        {s(e, mp ? 'mp_constituency' : 'ida_district')} ·{' '}
        {s(e, mp ? 'mp_state' : 'state')}
      </p>
      <Facts
        items={[
          ['Visible works', number(n(e, kind + '_visible_work_count'))],
          [
            'Visible sanctions',
            money(e[kind + '_visible_sanction_total'] as number | null),
          ],
          [
            'Delay over 45 days',
            linked.length
              ? percent(n(e, kind + '_delay_over45_share'))
              : 'No works',
          ],
          [
            'Completed status',
            linked.length
              ? percent(n(e, kind + '_completed_share'))
              : 'No works',
          ],
          [
            'Profile priority',
            <Band value={s(e, kind + '_review_priority_band')} />,
          ],
          [
            'Duplicate candidate share',
            linked.length
              ? percent(n(e, kind + '_duplicate_review_share'))
              : 'No works',
          ],
        ]}
      />
      {mp && (
        <section className="evidence-section">
          <h3>Allocation and calamity context</h3>
          <Facts
            items={[
              ['Allocated limit', money(e.mp_allocated_limit as number | null)],
              ['Calamity consents', number(consents.length)],
              ['Consent amount', money(n(e, 'mp_calamity_consent_total'))],
            ]}
          />
          <p className="quiet">
            Allocation period is not supplied. Sanctions and consents are shown
            separately; they do not measure expenditure utilization.
          </p>
          {consents.map((c) => (
            <div className="reason" key={s(c, 'source_row_number')}>
              <div>
                <strong>{s(c, 'calamity_name')}</strong>
                <span>{dateLabel(s(c, 'consent_date'))}</span>
              </div>
              <b>{money(n(c, 'consent_amount'))}</b>
            </div>
          ))}
        </section>
      )}
      <section className="evidence-section">
        <h3>Linked works · full extract</h3>
        <WorkTable
          rows={linked.slice(page * 20, page * 20 + 20)}
          onOpen={openWork}
          reviews={reviews}
          small
        />
        <Pager page={page} total={linked.length} onChange={setPage} />
      </section>
    </div>
  );
}
