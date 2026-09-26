import { useEffect, useMemo, useState } from 'react';

type StateRow = { state: string; works: number; high: number };
type Polygon = number[][][];
type Feature = {
  properties: { shapeName: string };
  geometry: { type: string; coordinates: Polygon | Polygon[] };
};
export const stateKey = (name: string) =>
  name
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/^the /, '')
    .replaceAll('&', 'and')
    .replace(/[^a-z]/g, '');
const shades = ['#e3f1ee', '#b7d9d2', '#70b2aa', '#267e83', '#125269'];
const fill = (r?: StateRow) =>
  !r?.works
    ? '#cbd5e1'
    : shades[Math.min(4, Math.floor(r.high / r.works / 0.02))];
const path = (feature: Feature) => {
  const polygons =
    feature.geometry.type === 'Polygon'
      ? [feature.geometry.coordinates as Polygon]
      : (feature.geometry.coordinates as Polygon[]);
  return polygons
    .map((p) =>
      p
        .map(
          (ring) =>
            ring
              .map(
                ([lon, lat], i) =>
                  `${i ? 'L' : 'M'}${((lon - 67) * 15).toFixed(2)},${((38 - lat) * 16.5).toFixed(2)}`,
              )
              .join(' ') + 'Z',
        )
        .join(' '),
    )
    .join(' ');
};
export function IndiaMap({
  states,
  selected,
  onPick,
}: {
  states: StateRow[];
  selected: string;
  onPick: (state: string) => void;
}) {
  const [features, setFeatures] = useState<Feature[]>([]);
  const [error, setError] = useState('');
  const [hover, setHover] = useState('');
  useEffect(() => {
    const abort = new AbortController();
    void fetch('/india-adm1-geoboundaries.geojson', { signal: abort.signal })
      .then(async (r) => {
        if (!r.ok) throw Error('Geometry unavailable');
        return r.json();
      })
      .then((d) => setFeatures(d.features))
      .catch((e: unknown) => {
        if (!abort.signal.aborted)
          setError(e instanceof Error ? e.message : 'Map unavailable');
      });
    return () => abort.abort();
  }, []);
  const shapes = useMemo(
    () =>
      features.map((f) => ({
        key: stateKey(f.properties.shapeName),
        name: f.properties.shapeName,
        d: path(f),
      })),
    [features],
  );
  const lookup = new Map(states.map((r) => [stateKey(r.state), r]));
  const active = states.find((r) => r.state === (hover || selected));
  const missing = states.filter(
    (r) => !shapes.some((s) => s.key === stateKey(r.state)),
  );
  return (
    <section className="panel" aria-label="India state heatmap">
      <div className="panel-head">
        <div>
          <h2>India — share of works flagged high priority</h2>
          <p>
            Click a state or UT to show its district authorities below. The
            colour shows a percentage of the state’s works — not the number of
            works, and not proven misuse.
          </p>
        </div>
      </div>
      <div className="india-map-layout">
        <div>
          {error && <p role="alert">{error}. Use the state table below.</p>}
          {!features.length && !error && (
            <p role="status">Loading local map…</p>
          )}
          {!!features.length && (
            <svg
              className="india-map"
              viewBox="0 0 480 540"
              aria-label="Selectable state boundaries"
              role="group"
            >
              {shapes.map((s) => {
                const r = lookup.get(s.key);
                const label = r
                  ? `${r.state}: ${r.high} high-priority of ${r.works} works (${((r.high / r.works) * 100).toFixed(1)}%)`
                  : `${s.name}: no matching data`;
                return (
                  <path
                    key={s.key}
                    d={s.d}
                    fill={fill(r)}
                    fillRule="evenodd"
                    stroke={r?.state === selected ? '#e08723' : '#f5f7fa'}
                    strokeWidth={r?.state === selected ? 2 : 0.6}
                    role="button"
                    tabIndex={r ? 0 : -1}
                    aria-label={label}
                    aria-pressed={r?.state === selected}
                    onFocus={() => setHover(r?.state || '')}
                    onBlur={() => setHover('')}
                    onMouseEnter={() => setHover(r?.state || '')}
                    onMouseLeave={() => setHover('')}
                    onClick={() => {
                      if (r) onPick(selected === r.state ? '' : r.state);
                    }}
                    onKeyDown={(e) => {
                      if (r && ['Enter', ' '].includes(e.key)) {
                        e.preventDefault();
                        onPick(selected === r.state ? '' : r.state);
                      }
                    }}
                  >
                    <title>{label}</title>
                  </path>
                );
              })}
            </svg>
          )}
        </div>
        <div className="map-context">
          <h3>{active?.state || 'National view'}</h3>
          {active ? (
            <p>
              <strong>
                {((active.high / active.works) * 100).toFixed(1)}%
              </strong>{' '}
              high priority
              <br />
              {active.high.toLocaleString('en-IN')} of{' '}
              {active.works.toLocaleString('en-IN')} works
            </p>
          ) : (
            <p>
              Point at a state to see how many of its works are high
              priority. Small territories can also be picked from the list
              below or the state table.
            </p>
          )}
          <ul className="map-legend">
            {['0–<2%', '2–<4%', '4–<6%', '6–<8%', '8% or more'].map(
              (label, i) => (
                <li key={label}>
                  <span style={{ background: shades[i] }} />
                  {label}
                </li>
              ),
            )}
            <li>
              <span style={{ background: '#cbd5e1' }} />
              No matching data
            </li>
          </ul>
          <label>
            Selected state / UT
            <select value={selected} onChange={(e) => onPick(e.target.value)}>
              <option value="">All states / UTs</option>
              {states.map((r) => (
                <option key={r.state}>{r.state}</option>
              ))}
            </select>
          </label>
          {selected && (
            <button onClick={() => onPick('')}>Clear state selection</button>
          )}
          <p className="quiet">
            {features.length
              ? `${states.length - missing.length} of ${states.length} states / UTs shown on the map.`
              : 'The map loads from this computer; nothing is fetched online.'}
          </p>
          {!!missing.length && !!features.length && (
            <p role="alert">
              Not on the map: {missing.map((r) => r.state).join(', ')}. They
              are still in the table.
            </p>
          )}
        </div>
      </div>
      <p className="section-note">
        Geometry:{' '}
        <a
          href="https://www.geoboundaries.org/api/current/gbOpen/IND/ADM1/"
          target="_blank"
          rel="noreferrer"
        >
          geoBoundaries / DataMeet, CC BY 2.5 IN
        </a>
        . For illustration only — not an official Survey of India map and not
        a statement on disputed boundaries. The source says 2011, but the file
        already shows 36 states/UTs, including separate Telangana and
        Ladakh.{' '}
        <a href="/india-map-provenance.json" target="_blank" rel="noreferrer">
          Map source details
        </a>
        .
      </p>
    </section>
  );
}
