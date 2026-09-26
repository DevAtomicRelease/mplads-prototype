import type { ReactNode } from 'react';
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from '@/components/ui/table';

import { reportTable } from '../lib/report-table';

export function ReportView({ text }: { text: string }) {
  const lines = text.split('\n');
  const out: ReactNode[] = [];
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line) continue;
    if (line.startsWith('```')) {
      const block: string[] = [];
      while (++i < lines.length && !lines[i].trim().startsWith('```'))
        block.push(lines[i]);
      const parsed = reportTable(block.join('\n'));
      out.push(
        parsed ? (
          <Table key={i}>
            <TableHeader>
              <TableRow>
                {parsed.headings.map((h, j) => (
                  <TableHead key={j}>{h}</TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {parsed.rows.map((r, j) => (
                <TableRow key={j}>
                  {r.map((v, k) => (
                    <TableCell key={k}>{v}</TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : (
          <pre key={i} className="report-code">
            {block.join('\n')}
          </pre>
        ),
      );
    } else if (/^#{1,3}\s/.test(line))
      out.push(<h3 key={i}>{line.replace(/^#+\s*/, '')}</h3>);
    else if (line.startsWith('- ')) {
      const items = [line.slice(2)];
      while (i + 1 < lines.length && lines[i + 1].startsWith('- '))
        items.push(lines[++i].slice(2));
      out.push(
        <ul key={i}>
          {items.map((s, j) => (
            <li key={j}>{s}</li>
          ))}
        </ul>,
      );
    } else out.push(<p key={i}>{line.replace(/^_|_$/g, '')}</p>);
  }
  return <article className="report-view">{out}</article>;
}
