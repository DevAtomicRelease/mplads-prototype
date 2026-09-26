import { useEffect, useMemo, useState } from 'react';
import { ruleName } from '../lib/plain-text';
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
            Everything in the data linked to this district authority, MP or
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
                  ['Works', num(d.summary.works)],
                  ['High-priority works', num(d.summary.high)],
                  ['Still open after one year', num(d.summary.open_over_year)],
                  ['No payment seen after 3 months', num(d.summary.no_payment_3m)],
                  ['Sanctioned for these works', money(d.summary.sanction_paise)],
                  ['Paid for these works', money(d.summary.settled_paise)],
                ].map(([label, value]) => (
                  <div className="metric" key={label}>
                    <span>{label}</span>
                    <strong style={{ fontSize: 23 }}>{value}</strong>
                  </div>
                ))}
              </div>
              {d.kind === 'vendor' && (
                <p>
                  Paid to this vendor only:{' '}
                  {money(Number(d.profile.successful_payment_paise))}; still in
                  progress: {money(Number(d.profile.pending_payment_paise))}.
                  The totals above cover whole works, so they include other
                  vendors on the same works.
                </p>
              )}
              {d.kind === 'mp' && (
                <p>
                  Allocated (as in the data):{' '}
                  {money(Number(d.profile.allocated_paise))}. This is the
                  spending limit shown in the portal file, not money confirmed
                  to be available.
                </p>
              )}
              <button onClick={() => works(d.kind, d.key)}>
                Open these works in the case list
              </button>
              <h2>Why these works need review</h2>
              <p>
                One work can be flagged for several reasons, so these counts
                can add up to more than the number of works. None of them is a
                finding of misuse.
              </p>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Reason flagged</TableHead>
                    <TableHead>Works</TableHead>
                    <TableHead>Total points added</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {d.reasons.map((r) => (
                    <TableRow key={r.rule}>
                      <TableCell>{ruleName(r.rule)}</TableCell>
                      <TableCell>{num(r.works)}</TableCell>
                      <TableCell>{num(r.points)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              <h2>Year by year</h2>
              <p>
                Works are grouped by the year they were sanctioned. Payments are
                counted in the work’s sanction year, even if paid later.
              </p>
              <Table>
                <TableHeader>
                  <TableRow>
                    {[
                      'Sanction year',
                      'Works',
                      'High priority',
                      'Open over 1 year',
                      'Sanctioned',
                      'Paid',
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
                <summary>Technical details: ID and the query used</summary>
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
