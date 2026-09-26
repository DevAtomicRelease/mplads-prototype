// Controlled local reports only. Text is escaped by React; never execute HTML.
// Pandas fixed-width blocks have numeric columns on the right, so preserve a
// multi-word state/authority label as the first column instead of splitting it.
export function reportTable(
  block: string,
): { headings: string[]; rows: string[][] } | null {
  const lines = block.split('\n').filter((s) => s.trim());
  if (!lines.length) return null;
  const numericRows = lines
    .slice(1)
    .map((line) =>
      line.match(/^\s*(.*?)\s+((?:(?:\d{4}-\d{4}|-?\d+(?:\.\d+)?)\s*)+)$/),
    );
  const valid = numericRows.filter((m): m is RegExpMatchArray => !!m);
  if (!valid.length) return null;
  // A single pandas index-name line may follow the header. Any other
  // unparsed row forces a verbatim fallback instead of silently losing data.
  const skipped = numericRows.map((m, i) => (m ? -1 : i)).filter((i) => i >= 0);
  if (
    skipped.length &&
    !(skipped.length === 1 && skipped[0] === 0 && /^\w+$/.test(lines[1].trim()))
  )
    return null;
  const rows = valid.map((m) => [m[1], ...m[2].trim().split(/\s+/)]);
  const width = rows[0].length;
  if (rows.some((row) => row.length !== width)) return null;
  const heads = lines[0].trim().split(/\s+/);
  if (heads.length === 1 && width === 2) heads.push('Works');
  else if (heads.length === width - 1)
    heads.unshift(
      lines[1]?.trim().split(/\s+/).length === 1 && !numericRows[0]
        ? lines[1].trim()
        : 'Category',
    );
  if (heads.length !== width) return null;
  return { headings: heads.map((h) => h.replaceAll('_', ' ')), rows };
}
