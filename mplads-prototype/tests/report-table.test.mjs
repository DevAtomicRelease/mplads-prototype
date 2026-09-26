import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { transpileModule, ModuleKind } from 'typescript';

const source = readFileSync(
  new URL('../lib/report-table.ts', import.meta.url),
  'utf8',
);
const js = transpileModule(source, {
  compilerOptions: { module: ModuleKind.ESNext },
}).outputText;
const { reportTable } = await import(
  'data:text/javascript;base64,' + Buffer.from(js).toString('base64')
);

test('preserves multi-word state labels and the pandas index heading', () => {
  assert.deepEqual(
    reportTable(
      'works high\nstate\nUttar Pradesh 28436 902\nWest Bengal 7954 607',
    ),
    {
      headings: ['state', 'works', 'high'],
      rows: [
        ['Uttar Pradesh', '28436', '902'],
        ['West Bengal', '7954', '607'],
      ],
    },
  );
});

test('preserves financial years, multi-word authorities and signed numeric values', () => {
  assert.deepEqual(
    reportTable(
      'authority financial_year vendors hhi\nDistrict Magistrate Jaunpur 2025-2026 5 0.527',
    ),
    {
      headings: ['authority', 'financial year', 'vendors', 'hhi'],
      rows: [['District Magistrate Jaunpur', '2025-2026', '5', '0.527']],
    },
  );
  assert.deepEqual(reportTable('feature correlation\nOpen age -0.03')?.rows, [
    ['Open age', '-0.03'],
  ]);
});

test('adds a readable count heading for a pandas series', () => {
  assert.deepEqual(reportTable('priority_band\nLow 84163\nHigh 6641'), {
    headings: ['priority band', 'Works'],
    rows: [
      ['Low', '84163'],
      ['High', '6641'],
    ],
  });
});

test('falls back rather than silently dropping malformed or differently sized rows', () => {
  assert.equal(reportTable(''), null);
  assert.equal(
    reportTable('state works\nBihar 123\nUnparsed content here'),
    null,
  );
  assert.equal(reportTable('state works\nBihar 123\nWest Bengal 4 5'), null);
});
