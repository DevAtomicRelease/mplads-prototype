'use client';
import { useEffect, useState } from 'react';
import {
  ArrowUpRight,
  Check,
  CircleAlert,
  Download,
  FlaskConical,
} from 'lucide-react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { number, percent, dateLabel } from '@/lib/model';

type Signal = { selected: number; available: number; coverage: number };
type RealBudget = {
  review_fraction: number;
  review_count: number;
  overlap_fraction: number;
  a: Record<string, Signal>;
  b: Record<string, Signal>;
  top_work_ids_a: number[];
  top_work_ids_b: number[];
};
type Scenario = { recovered: number; injected: number; recovery: number };
type SyntheticBudget = {
  review_fraction: number;
  review_count: number;
  injected_count: number;
  a: {
    recovered: number;
    recovery: number;
    scenario_recovery: Record<string, Scenario>;
  };
  b: {
    recovered: number;
    recovery: number;
    scenario_recovery: Record<string, Scenario>;
  };
  recovery_difference_b_minus_a: number;
  paired_bootstrap_95_interval_difference: number[];
};
type Report = {
  experiment_id: string;
  split: { cutoff_inclusive: string; train_rows: number; test_rows: number };
  actual_data: { budgets: RealBudget[] };
  synthetic_benchmark: {
    rows: number;
    budgets: SyntheticBudget[];
    diagnostic_signal_trigger_rates: Record<
      string,
      {
        score_component_increased: number;
        signal_present_before_injection: number;
      }
    >;
    bootstrap: { replicates: number };
  };
  checks: Record<string, boolean>;
};
const pp = (v: number) => `${v >= 0 ? '+' : ''}${(v * 100).toFixed(2)} pp`;

export default function Validation({
  openWork,
}: {
  openWork: (id: string) => void;
}) {
  const [report, setReport] = useState<Report | null>(null),
    [error, setError] = useState(''),
    [budget, setBudget] = useState('0.2');
  useEffect(() => {
    const controller = new AbortController();
    fetch('/api/validation', { signal: controller.signal })
      .then((r) => {
        if (!r.ok)
          throw new Error(
            'The experiment report is unavailable. Run REBUILD_PROJECT.cmd to generate it.',
          );
        return r.json();
      })
      .then((p) => setReport(p as Report))
      .catch((e) => {
        if (e.name !== 'AbortError') setError(e.message);
      });
    return () => controller.abort();
  }, []);
  if (!report)
    return (
      <section className="panel">
        <p className="section-note" role="status">
          {error || 'Loading the reproducible A/B experiment…'}
        </p>
      </section>
    );
  const real = report.actual_data.budgets.find(
    (x) => x.review_fraction === Number(budget),
  )!;
  const synthetic = report.synthetic_benchmark.budgets.find(
    (x) => x.review_fraction === Number(budget),
  )!;
  const interval = synthetic.paired_bootstrap_95_interval_difference;
  return (
    <>
      <section className="panel">
        <div className="panel-head">
          <div>
            <h2>A controlled comparison at equal capacity</h2>
            <p>
              Fixed methods, a historical reference and a later test set. No
              tuning on test results.
            </p>
          </div>
          <a className="text-link" href="/api/download/ab-report.md" download>
            <Download size={15} />
            Full report
          </a>
        </div>
        <div className="method-grid">
          <article className="variant-card">
            <span className="variant-token baseline">A</span>
            <h3>Delay + aging baseline</h3>
            <p>
              Ranks works using continuous delay and early-stage aging
              contributions.
            </p>
          </article>
          <article className="variant-card">
            <span className="variant-token enhanced">B</span>
            <h3>Combined screening</h3>
            <p>
              Adds robust historical peer costs and corroborated description
              matches to A.
            </p>
          </article>
        </div>
        <div className="split-strip">
          <span>
            <strong>{number(report.split.train_rows)}</strong> reference works
          </span>
          <ArrowUpRight size={17} />
          <span>
            Cutoff: <strong>{dateLabel(report.split.cutoff_inclusive)}</strong>
          </span>
          <ArrowUpRight size={17} />
          <span>
            <strong>{number(report.split.test_rows)}</strong> later test works
          </span>
        </div>
        <p className="section-note">
          The comparison evaluates retrospective screening at the September 2026
          snapshot. These frozen research scores are separate from the core-v1
          scores shown in the portfolio queue.
        </p>
      </section>
      <div className="ab-budget">
        <div>
          <h2>Review budget</h2>
          <p>Select the same proportion of cases for each approach.</p>
        </div>
        <Tabs value={budget} onValueChange={(v) => setBudget(String(v))}>
          <TabsList>
            {['0.05', '0.1', '0.2', '0.3'].map((v) => (
              <TabsTrigger key={v} value={v}>
                {Number(v) * 100}%
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
      </div>
      <div className="metric-grid">
        <div className="metric">
          <div className="metric-label">
            A · Scenario recovery
            <FlaskConical size={18} />
          </div>
          <strong>{(synthetic.a.recovery * 100).toFixed(2)}%</strong>
          <span>
            {synthetic.a.recovered} / {synthetic.injected_count} injected
            scenarios
          </span>
        </div>
        <div className="metric">
          <div className="metric-label">
            B · Scenario recovery
            <FlaskConical size={18} />
          </div>
          <strong>{(synthetic.b.recovery * 100).toFixed(2)}%</strong>
          <span>
            {synthetic.b.recovered} / {synthetic.injected_count} injected
            scenarios
          </span>
        </div>
        <div className="metric">
          <div className="metric-label">
            Difference B − A<ArrowUpRight size={18} />
          </div>
          <strong>{pp(synthetic.recovery_difference_b_minus_a)}</strong>
          <span>
            95% interval: {pp(interval[0])} to {pp(interval[1])}
          </span>
        </div>
        <div className="metric">
          <div className="metric-label">
            Real queue overlap
            <Check size={18} />
          </div>
          <strong>{percent(real.overlap_fraction)}</strong>
          <span>
            {number(real.review_count)} real works selected by each method
          </span>
        </div>
      </div>
      <div className="overview-grid">
        <section className="panel">
          <div className="panel-head">
            <div>
              <h2>Recovery by controlled scenario</h2>
              <p>
                {synthetic.review_count} of {report.synthetic_benchmark.rows}{' '}
                benchmark records reviewed
              </p>
            </div>
          </div>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Injected scenario</TableHead>
                <TableHead>A recovery</TableHead>
                <TableHead>B recovery</TableHead>
                <TableHead>Difference</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {Object.entries(synthetic.a.scenario_recovery).map(([key, a]) => {
                const z = synthetic.b.scenario_recovery[key];
                return (
                  <TableRow key={key}>
                    <TableCell>{key.replace('_', ' ')}</TableCell>
                    <TableCell>{percent(a.recovery)}</TableCell>
                    <TableCell>{percent(z.recovery)}</TableCell>
                    <TableCell
                      className={
                        z.recovery < a.recovery
                          ? 'tradeoff-negative'
                          : 'tradeoff-positive'
                      }
                    >
                      {pp(z.recovery - a.recovery)}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </section>
        <section className="panel">
          <div className="panel-head">
            <div>
              <h2>Real-data queue composition</h2>
              <p>Observed signal coverage; correctness is not labeled.</p>
            </div>
          </div>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Signal</TableHead>
                <TableHead>Available</TableHead>
                <TableHead>A selected</TableHead>
                <TableHead>B selected</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {['delay', 'aging', 'cost', 'duplicate'].map((key) => (
                <TableRow key={key}>
                  <TableCell>{key}</TableCell>
                  <TableCell>{number(real.a[key].available)}</TableCell>
                  <TableCell>{number(real.a[key].selected)}</TableCell>
                  <TableCell>{number(real.b[key].selected)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </section>
      </div>
      <div className="evidence-callout">
        <CircleAlert />
        <p>
          <strong>Protect each review objective.</strong> B favors cost and
          duplicate evidence, reducing delay/aging recovery at the same
          capacity. Separate signal queues remain available.{' '}
          {interval[0] <= 0
            ? 'At this budget the interval includes zero, so the aggregate improvement is uncertain.'
            : 'The measured aggregate improvement applies to this designed scenario mixture.'}
        </p>
      </div>
      <section className="panel">
        <div className="panel-head">
          <div>
            <h2>Inspect the selected real cases</h2>
            <p>
              First 12 from each method; open a work to inspect its source
              evidence.
            </p>
          </div>
          <a className="text-link" href="/api/download/ab-scores.csv" download>
            <Download size={15} />
            All test scores
          </a>
        </div>
        <div className="ab-case-grid">
          {[
            ['A · Baseline', real.top_work_ids_a],
            ['B · Combined', real.top_work_ids_b],
          ].map(([label, ids]) => (
            <article key={String(label)}>
              <h3>{String(label)}</h3>
              <div>
                {(ids as number[]).slice(0, 12).map((id) => (
                  <button
                    className="case-chip"
                    key={id}
                    onClick={() => openWork(String(id))}
                  >
                    #{id}
                    <ArrowUpRight size={13} />
                  </button>
                ))}
              </div>
            </article>
          ))}
        </div>
      </section>
      <section className="panel">
        <div className="panel-head">
          <h2>What this experiment establishes</h2>
        </div>
        <div className="method-grid">
          <article>
            <h3>Reproducible offline evidence</h3>
            <p>
              Historical peer statistics and duplicate references use only the{' '}
              {number(report.split.train_rows)} earlier works. Seeds, splits,
              scripts and row scores are retained. The{' '}
              {report.synthetic_benchmark.bootstrap.replicates}-replicate paired
              bootstrap reranks within each resample.
            </p>
          </article>
          <article>
            <h3>Limits of the benchmark</h3>
            <p>
              There are 400 scenario assignments and 800 unchanged records. The
              targeted component increases in{' '}
              {Object.values(
                report.synthetic_benchmark.diagnostic_signal_trigger_rates,
              ).reduce((t, x) => t + x.score_component_increased, 0)}{' '}
              assignments; some source records already had the signal. Unchanged
              records are not verified negatives.
            </p>
          </article>
          <article>
            <h3>No real fraud accuracy claim</h3>
            <p>
              The results measure controlled scenario recovery and real queue
              composition. They do not establish fraud precision, false-positive
              rates, time savings or forecast accuracy.
            </p>
          </article>
          <article>
            <h3>Next: a randomized operational trial</h3>
            <p>
              Randomize comparable officer teams or matched authority clusters
              to A/B, keep equal review capacity, use blinded adjudication, and
              measure substantiated issues per review and time to decision.
              Pre-register a stopping rule and sample size after pilot outcome
              rates are available.
            </p>
          </article>
        </div>
        <div className="validation-checks">
          {Object.entries(report.checks).map(([key, value]) => (
            <span key={key}>
              {value ? <Check size={14} /> : <CircleAlert size={14} />}{' '}
              {key.replaceAll('_', ' ')}
            </span>
          ))}
        </div>
      </section>
    </>
  );
}
