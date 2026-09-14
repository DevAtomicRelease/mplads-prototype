"""Independently verify exported Excel values and controls against the frozen core."""
import json
import math
from datetime import date, datetime
from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET
import openpyxl

ROOT = Path(__file__).resolve().parents[2]
FILE = ROOT / 'outputs/01a06d6b-9b94-7a61-b28b-6f9116f20942/MPLADS_Final_Core_Dataset_2026-09-06.xlsx'
source = json.loads((ROOT / 'pipeline_research/artifacts/snapshot.json').read_text(encoding='utf-8'))
book = openpyxl.load_workbook(FILE, read_only=True, data_only=True)
checks = {}
for name, table in source['tables'].items():
    rows = book[name].iter_rows(values_only=True)
    columns = list(next(rows))
    assert set(columns) == set(table['columns']), name + ' fields'
    indices = [table['columns'].index(column) for column in columns]
    count = 0
    for actual, raw in zip(rows, table['rows'], strict=True):
        count += 1
        for j, index in enumerate(indices):
            expected, value = raw[index], actual[j]
            if isinstance(value, (datetime, date)):
                value = value.isoformat()[:10]
            if isinstance(expected, str) and expected.startswith(('=', '+', '@')) and value == "'" + expected:
                value = expected
            if isinstance(expected, (float, int)) and not isinstance(expected, bool):
                assert isinstance(value, (float, int)) and math.isclose(value, expected, rel_tol=1e-12, abs_tol=1e-7), (name, count, columns[j])
            else:
                assert value == expected or (value is None and expected == ''), (name, count, columns[j], value, expected)
    checks[name] = {'rows': count, 'columns': len(columns), 'all_values_match': True}
summary = book['Summary']
for address, expected in {'B4': 10000, 'B5': 5276800278, 'B9': 83336673298.01, 'B12': 40567400, 'B13': 21092, 'B14': 1, 'B15': 811, 'B16': 1680, 'B17': 7508}.items():
    assert math.isclose(summary[address].value, expected, abs_tol=0.005), address
checks['summary_cached_totals'] = True
book.close()
ns = {'x': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
with ZipFile(FILE) as archive:
    for i, name in enumerate(source['tables'], 2):
        tree = ET.fromstring(archive.read(f'xl/worksheets/sheet{i}.xml'))
        pane = tree.find('x:sheetViews/x:sheetView/x:pane', ns)
        assert pane is not None and pane.get('xSplit') == '1' and pane.get('ySplit') == '1', (name, 'freeze panes')
    checks['headers_and_identifier_frozen'] = True
    checks['six_filterable_tables'] = len([n for n in archive.namelist() if n.startswith('xl/tables/table') and n.endswith('.xml')]) == 6
assert checks['six_filterable_tables']
report = {'workbook': FILE.name, 'checks': checks, 'all_passed': True}
(Path(__file__).parent / 'verification.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
