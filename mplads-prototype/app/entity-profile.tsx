import { useEffect, useMemo, useState } from 'react';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '@/components/ui/sheet';
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from '@/components/ui/table';

type Summary = {
  works: number;
  sanctioned: number;
  completed: number;
  high: number;
  open_over_year: number;
  no_payment_3m: number;
  sanction_paise: number;
  settled_paise: number;
  pending_paise: number;
  mean_priority: number;
};
type Profile = {
  name: string;
  kind: string;
  key: string;
  profile: Record<string, string | number | null>;
  summary: Summary;
  years: (Summary & { year: string })[];
  reasons: { rule: string; works: number; points: number }[];
  note: string;
  sql: string;
  params: string[];
  version: string;
};
const num = (n: number | null) =>
  n == null ? 'Not recorded' : n.toLocaleString('en-IN');
const money = (n: number | null) =>
  n == null
    ? 'Not recorded'
    : `INR ${(n / 1e9).toLocaleString('en-IN', { maximumFractionDigits: 2 })} crore`;

export function EntityProfile({
  entity,
  close,
  works,
}: {
  entity: { kind: string; key: string } | null;
  close: () => void;
  works: (kind: string, key: string) => void;
}) {
  const [result, setResult] = useState<{
    url: string;
    data?: Profile;
    error?: string;
  } | null>(null);
  const url = useMemo(
    () => (entity ? '/api/entity?' + new URLSearchParams(entity) : ''),
    [entity],
  );
  useEffect(() => {
    if (!url) return;
    const abort = new AbortController();
    void fetch(url, { signal: abort.signal })
      .then(async (r) => {
        const d = await r.json();
        if (!r.ok) throw Error(d.error);
        return d as Profile;
      })
      .then((data) => setResult({ url, data }))
      .catch((e: unknown) => {
        if (!abort.signal.aborted)
          setResult({
            url,
            error: e instanceof Error ? e.message : 'Profile unavailable',
          });
      });
    return () => abort.abort();
  }, [url]);
  const d = result?.url === url ? result.data : undefined;
  return (
    <Sheet
      open={!!entity}
      onOpenChange={(open) => {
        if (!open) close();
      }}
    >
      <SheetContent className="s6-sheet evidence-sheet entity-sheet">
        <SheetHeader>
          <SheetTitle>{d?.name || 'Entity profile'}</SheetTitle>
          <SheetDescription>
            Connected evidence for the exact selected authority, member or
            vendor.
          </SheetDescription>
        </SheetHeader>
        <div className="s6-evidence">
          {result?.url === url && result.error && (
            <p role="alert">{result.error}</p>
          )}
          {!d && !result?.error && <p role="status">Loading profile…</p>}
          {d && (
            <>
              <p>
                {d.kind === 'ida'
                  ? 'District authority'
                  : d.kind === 'mp'
                    ? 'Member of Parliament'
                    : 'Vendor'}
                {d.profile.state ? ` · ${d.profile.state}` : ''}
              </p>
              <div className="metric-grid">
                {[
                  ['Connected works', num(d.summary.works)],
                  ['High-priority works', num(d.summary.high)],
                  ['Open beyond one year', num(d.summary.open_over_year)],
                  ['No payment after 3 months', num(d.summary.no_payment_3m)],
                  ['Connected-work sanctions', money(d.summary.sanction_paise)],
                  [
                    'Connected-work settlements',
                    money(d.summary.settled_paise),
                  ],
                ].map(([label, value]) => (
                  <div className="metric" key={label}>
                    <span>{label}</span>
                    <strong style={{ fontSize: 23 }}>{value}</strong>
                  </div>
                ))}
              </div>
              {d.kind === 'vendor' && (
                <p>
                  Payments to this vendor only:{' '}
                  {money(Number(d.profile.successful_payment_paise))} settled;{' '}
                  {money(Number(d.profile.pending_payment_paise))} pending.
                  Linked-work totals above include other vendors.
                </p>
              )}
              {d.kind === 'mp' && (
                <p>
                  Allocation snapshot:{' '}
                  {money(Number(d.profile.allocated_paise))}. This is a limit
                  snapshot, not confirmed cash availability.
                </p>
              )}
              <button onClick={() => works(d.kind, d.key)}>
                View this entity’s connected works
              </button>
              <h2>Why these works need review</h2>
              <p>
                Counts can overlap: a work can trigger several rules. None is a
                finding of misuse.
              </p>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Review signal</TableHead>
                    <TableHead>Works</TableHead>
                    <TableHead>Total rule points</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {d.reasons.map((r) => (
                    <TableRow key={r.rule}>
                      <TableCell>{r.rule.replaceAll('_', ' ')}</TableCell>
                      <TableCell>{num(r.works)}</TableCell>
                      <TableCell>{num(r.points)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              <h2>Sanction-year breakdown</h2>
              <p>
                Settlements are attached to each work’s sanction year, not the
                payment year.
              </p>
              <Table>
                <TableHeader>
                  <TableRow>
                    {[
                      'Sanction FY',
                      'Works',
                      'High priority',
                      'Open >1yr',
                      'Sanctioned',
                      'Settled',
                    ].map((h) => (
                      <TableHead key={h}>{h}</TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {d.years.map((r) => (
                    <TableRow key={r.year}>
                      <TableCell>{r.year}</TableCell>
                      <TableCell>{num(r.works)}</TableCell>
                      <TableCell>{num(r.high)}</TableCell>
                      <TableCell>{num(r.open_over_year)}</TableCell>
                      <TableCell>{money(r.sanction_paise)}</TableCell>
                      <TableCell>{money(r.settled_paise)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              <p className="section-note">{d.note}</p>
              <details>
                <summary>Source key and reproducible query</summary>
                <p>{d.key}</p>
                <pre className="s6-sql">
                  {d.sql}
                  {'\nParameters: ' + JSON.stringify(d.params)}
                  {'\nRelease: ' + d.version}
                </pre>
              </details>
            </>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
