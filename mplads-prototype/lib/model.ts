export type Scalar = string | number | boolean | null;
export type Row = Record<string, Scalar>;
export type Packed = { columns: string[]; rows: Scalar[][] };
export type Snapshot = {
  meta: {
    snapshot: string;
    sourceFile: string;
    sourceSha256: string;
    pipelineVersion?: string;
    reviewVersion?: string;
    sourceFiles?: Record<string, { file: string; sha256: string }>;
    reportedWorksTotal: number;
    visibleWorksTotal: number;
    allocationTotal: number;
    calamityTotal: number;
    guidelines: string;
    counts: Record<string, number>;
  };
  tables: Record<string, Packed>;
  rules: Scalar[][];
};
export type Data = Snapshot & {
  works: Row[];
  mps: Row[];
  idas: Row[];
  calamities: Row[];
  pairs: Row[];
  dictionary: Row[];
};
export const n = (r: Row, k: string): number =>
  typeof r[k] === 'number' ? (r[k] as number) : 0;
export const s = (r: Row, k: string): string => String(r[k] ?? '');
export const b = (r: Row, k: string): boolean => r[k] === true;
export function unpack(p: Packed): Row[] {
  return p.rows.map((row) =>
    Object.fromEntries(p.columns.map((key, i) => [key, row[i] ?? null])),
  );
}
export function decode(input: unknown): Data {
  const p = input as Snapshot;
  if (
    !p?.meta?.snapshot ||
    !p?.tables?.Work_Features?.columns ||
    !Array.isArray(p.tables.Work_Features.rows)
  )
    throw new Error('Invalid local dataset schema');
  const core = Boolean(p.meta.pipelineVersion);
  const works = unpack(p.tables.Work_Features).map((w) =>
    core
      ? {
          ...w,
          peer_group_count: w.peer_count,
          peer_amount_median: w.peer_median_amount,
          peer_cost_robust_z: w.peer_robust_z,
          robust_multivariate_anomaly_percentile: w.isolation_forest_percentile,
        }
      : w,
  );
  const map = new Map(works.map((w) => [s(w, 'work_id'), w]));
  const pairs = unpack(p.tables.Duplicate_Candidates).map((pair) => {
    if (!core) return pair;
    const a = map.get(s(pair, 'work_id_a'))!,
      z = map.get(s(pair, 'work_id_b'))!;
    return {
      ...pair,
      mp_name_a: a.mp_name,
      mp_name_b: z.mp_name,
      ida_a: a.ida_authority,
      ida_b: z.ida_authority,
      same_work_type_flag: a.work_type === z.work_type,
      amount_difference: Math.abs(
        n(a, 'sanction_amount') - n(z, 'sanction_amount'),
      ),
    };
  });
  const rawRules = p.rules as unknown as (
    | { code: string; weight: number; definition: string; caution: string }
    | Scalar[]
  )[];
  const rules: Scalar[][] = rawRules.map((r) =>
    Array.isArray(r) ? r : ['Work', r.definition, r.weight, r.code, r.caution],
  );
  const dictionary = unpack(p.tables.Feature_Dictionary).map((r) =>
    core
      ? {
          ...r,
          sheet: r.table,
          data_type: r.dtype,
          model_use: 'See definition and availability',
          caution: r.availability_and_caution,
        }
      : r,
  );
  const meta = {
    ...p.meta,
    reviewVersion:
      p.meta.pipelineVersion +
      ':' +
      Object.keys(p.meta.sourceFiles ?? {})
        .sort()
        .map((key) => p.meta.sourceFiles![key].sha256.slice(0, 12))
        .join('-'),
    sourceFile: p.meta.sourceFile ?? 'Three original MPLADS workbooks',
    sourceSha256:
      p.meta.sourceSha256 ??
      Object.values(p.meta.sourceFiles ?? {})
        .map((x) => `${x.file}: ${x.sha256}`)
        .join(' | '),
  };
  return {
    ...p,
    meta,
    rules,
    works,
    pairs,
    dictionary,
    mps: unpack(p.tables.MP_Features),
    idas: unpack(p.tables.IDA_Features),
    calamities: unpack(p.tables.Calamity_Features),
  };
}
export type Filters = {
  state: string;
  fy: string;
  search: string;
  band: string;
  signal: string;
  status: string;
  sort: string;
};
export const defaults: Filters = {
  state: 'all',
  fy: 'all',
  search: '',
  band: 'all',
  signal: 'all',
  status: 'all',
  sort: 'priority',
};
export function portfolio(works: Row[], state: string, fy: string): Row[] {
  return works.filter(
    (w) =>
      (state === 'all' || w.state === state) &&
      (fy === 'all' || w.sanction_fiscal_year === fy),
  );
}
export function selectWorks(works: Row[], f: Filters): Row[] {
  const query = f.search.trim().toLowerCase();
  const rows = portfolio(works, f.state, f.fy).filter(
    (w) =>
      (f.band === 'all' ||
        w.review_priority_band === f.band ||
        (f.band === 'priority' &&
          ['High', 'Medium'].includes(s(w, 'review_priority_band')))) &&
      (f.status === 'all' || w.work_status === f.status) &&
      (f.signal === 'all' ||
        (f.signal === 'delay' && b(w, 'potential_sla_over_45_flag')) ||
        (f.signal === 'aging' && b(w, 'early_stage_age_over_180_flag')) ||
        (f.signal === 'cost' && b(w, 'high_cost_outlier_flag')) ||
        (f.signal === 'duplicate' && b(w, 'near_duplicate_review_flag'))) &&
      (!query ||
        [
          'work_id',
          'work_description',
          'mp_name',
          'ida_authority',
          'ida_district',
          'constituency',
        ].some((k) => s(w, k).toLowerCase().includes(query))),
  );
  const key =
    f.sort === 'amount'
      ? 'sanction_amount'
      : f.sort === 'delay'
        ? 'sanction_delay_days'
        : f.sort === 'age'
          ? 'age_days_at_snapshot_proxy'
          : 'review_priority_score';
  return rows.sort(
    (a, b) => n(b, key) - n(a, key) || n(a, 'work_id') - n(b, 'work_id'),
  );
}
export function summarize(works: Row[]) {
  const bands = { High: 0, Medium: 0, Low: 0, Routine: 0 };
  const states: Record<
    string,
    { count: number; priority: number; amount: number; delay: number }
  > = {};
  const stages: Record<string, number> = {};
  const months: Record<string, number> = {};
  let total = 0,
    delay = 0,
    aging = 0,
    cost = 0,
    duplicate = 0;
  works.forEach((w) => {
    total += Math.round(n(w, 'sanction_amount') * 100);
    delay += +b(w, 'potential_sla_over_45_flag');
    aging += +b(w, 'early_stage_age_over_180_flag');
    cost += +b(w, 'high_cost_outlier_flag');
    duplicate += +b(w, 'near_duplicate_review_flag');
    const band = s(w, 'review_priority_band') as keyof typeof bands;
    if (band in bands) bands[band]++;
    const state = s(w, 'state');
    const z = (states[state] ??= {
      count: 0,
      priority: 0,
      amount: 0,
      delay: 0,
    });
    z.count++;
    z.amount += Math.round(n(w, 'sanction_amount') * 100);
    z.delay += +b(w, 'potential_sla_over_45_flag');
    z.priority += +['High', 'Medium'].includes(band);
    const stage = s(w, 'status_stage');
    stages[stage] = (stages[stage] || 0) + 1;
    const month = s(w, 'sanction_date').slice(0, 7);
    months[month] = (months[month] || 0) + 1;
  });
  Object.values(states).forEach((state) => {
    state.amount /= 100;
  });
  return {
    count: works.length,
    total: total / 100,
    bands,
    priority: bands.High + bands.Medium,
    delay,
    aging,
    cost,
    duplicate,
    states,
    stages,
    months,
  };
}
export function reasons(work: Row, rules: Scalar[][]) {
  return s(work, 'review_reason_codes')
    .split(';')
    .filter(Boolean)
    .map((code) => {
      const rule = rules.find((r) => r[3] === code);
      const points =
        code === 'DATA_QUALITY_REVIEW'
          ? Math.min(9, 3 * n(work, 'data_quality_issue_count'))
          : typeof rule?.[2] === 'number'
            ? rule[2]
            : 0;
      return {
        code,
        label: String(rule?.[1] ?? code.replaceAll('_', ' ').toLowerCase()),
        points,
        note: String(rule?.[4] ?? ''),
      };
    });
}
export function csv(rows: Row[], columns?: string[]): string {
  const keys = columns ?? (rows[0] ? Object.keys(rows[0]) : []);
  const escape = (v: Scalar | undefined) => {
    let x = String(v ?? '');
    if (typeof v === 'string' && /^[=+@\-\t\r]/.test(x)) x = "'" + x;
    return '"' + x.replaceAll('"', '""') + '"';
  };
  return (
    '\uFEFF' +
    [
      keys.map(escape).join(','),
      ...rows.map((r) => keys.map((k) => escape(r[k])).join(',')),
    ].join('\r\n')
  );
}
export const number = (v: number) => new Intl.NumberFormat('en-IN').format(v);
export const money = (v: number | null | undefined, compact = true) =>
  v == null
    ? 'Not supplied'
    : compact && Math.abs(v) >= 1e7
      ? `₹${(v / 1e7).toFixed(2)} Cr`
      : compact && Math.abs(v) >= 1e5
        ? `₹${(v / 1e5).toFixed(2)} L`
        : `₹${new Intl.NumberFormat('en-IN', { maximumFractionDigits: 2 }).format(v)}`;
export const percent = (v: number) => `${(v * 100).toFixed(1)}%`;
export const dateLabel = (v: string) =>
  v
    ? new Date(v + 'T00:00:00').toLocaleDateString('en-IN', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
      })
    : 'Not supplied';
