'use client';

import * as React from 'react';

import { cn } from '@/lib/utils';

export function TablePager({
  offset,
  total,
  onChange,
  size = 50,
}: {
  offset: number;
  total: number;
  onChange: (offset: number) => void;
  size?: number;
}) {
  const pages = Math.max(1, Math.ceil(total / size));
  const page = Math.min(pages, Math.floor(offset / size) + 1);
  const [draft, setDraft] = React.useState('');
  return (
    <div className="pager">
      <span>
        {total
          ? `${offset + 1}–${Math.min(offset + size, total)} of ${total.toLocaleString('en-IN')}`
          : 'No matching records'}
      </span>
      <div className="table-navigation">
        <button
          type="button"
          disabled={!offset}
          onClick={() => onChange(Math.max(0, offset - size))}
        >
          Previous
        </button>
        <span>
          Page {page} of {pages}
        </span>
        <button
          type="button"
          disabled={offset + size >= total}
          onClick={() => onChange(offset + size)}
        >
          Next
        </button>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            const n = Number(draft);
            if (Number.isInteger(n) && n >= 1 && n <= pages) {
              onChange((n - 1) * size);
              setDraft('');
            }
          }}
        >
          <label>
            Jump to page{' '}
            <input
              aria-label="Jump to page"
              type="number"
              min={1}
              max={pages}
              required
              value={draft}
              placeholder={String(page)}
              onChange={(e) => setDraft(e.target.value)}
            />
          </label>
          <button type="submit" disabled={!total}>
            Go
          </button>
        </form>
      </div>
    </div>
  );
}

// Client tables receive their entire row set. Server tables explicitly opt out:
// their search/pagination must query all matching records, never just this page.
function rowText(node: React.ReactNode): string {
  if (typeof node === 'string' || typeof node === 'number') return String(node);
  if (Array.isArray(node)) return node.map(rowText).join(' ');
  if (React.isValidElement<{ children?: React.ReactNode }>(node))
    return rowText(node.props.children);
  return '';
}
export function TableSearch({
  value,
  onChange,
  label = 'Search all matching records',
}: {
  value: string;
  onChange: (value: string) => void;
  label?: string;
}) {
  return (
    <label className="table-search">
      {label}
      <input
        type="search"
        maxLength={200}
        placeholder="Type to filter records…"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </label>
  );
}
function Table({
  className,
  children,
  server = false,
  search,
  onSearch,
  ...props
}: React.ComponentProps<'table'> & {
  server?: boolean;
  search?: string;
  onSearch?: (value: string) => void;
}) {
  const [query, setQuery] = React.useState('');
  const [offset, setOffset] = React.useState(0);
  const body = React.Children.toArray(children).find(
    (child) => React.isValidElement(child) && child.type === TableBody,
  ) as React.ReactElement<React.ComponentProps<'tbody'>> | undefined;
  const rows = React.Children.toArray(body?.props.children).filter((row) =>
    rowText(row).toLowerCase().includes(query.toLowerCase()),
  );
  const safeOffset = Math.min(
    offset,
    Math.max(0, Math.ceil(rows.length / 50) - 1) * 50,
  );
  // Children.toArray normalizes keys; compare by component type instead of identity.
  const content =
    !server && body
      ? React.Children.map(children, (child) =>
          React.isValidElement(child) && child.type === TableBody
            ? React.cloneElement(
                body,
                {},
                rows.length ? (
                  rows.slice(safeOffset, safeOffset + 50)
                ) : (
                  <TableRow>
                    <TableCell colSpan={50}>No matching records</TableCell>
                  </TableRow>
                ),
              )
            : child,
        )
      : children;
  return (
    <div className="data-table">
      {(!server || onSearch) && (
        <label className="table-search">
          Search {server ? 'all matching records' : 'this table'}
          <input
            type="search"
            maxLength={200}
            placeholder="Type to filter records…"
            value={server ? search || '' : query}
            onChange={(e) => {
              if (server) onSearch?.(e.target.value);
              else {
                setQuery(e.target.value);
                setOffset(0);
              }
            }}
          />
        </label>
      )}
      <div
        data-slot="table-container"
        className="relative w-full overflow-x-auto"
      >
        <table
          data-slot="table"
          className={cn('w-full caption-bottom text-sm', className)}
          {...props}
        >
          {content}
        </table>
      </div>
      {!server && (
        <TablePager
          offset={safeOffset}
          total={rows.length}
          onChange={setOffset}
        />
      )}
    </div>
  );
}

function TableHeader({ className, ...props }: React.ComponentProps<'thead'>) {
  return (
    <thead
      data-slot="table-header"
      className={cn('[&_tr]:border-b', className)}
      {...props}
    />
  );
}

function TableBody({ className, ...props }: React.ComponentProps<'tbody'>) {
  return (
    <tbody
      data-slot="table-body"
      className={cn('[&_tr:last-child]:border-0', className)}
      {...props}
    />
  );
}

function TableFooter({ className, ...props }: React.ComponentProps<'tfoot'>) {
  return (
    <tfoot
      data-slot="table-footer"
      className={cn(
        'bg-muted/50 border-t font-medium [&>tr]:last:border-b-0',
        className,
      )}
      {...props}
    />
  );
}

function TableRow({ className, ...props }: React.ComponentProps<'tr'>) {
  return (
    <tr
      data-slot="table-row"
      className={cn(
        'hover:bg-muted/50 data-[state=selected]:bg-muted border-b transition-colors has-aria-expanded:bg-muted/50',
        className,
      )}
      {...props}
    />
  );
}

function TableHead({ className, ...props }: React.ComponentProps<'th'>) {
  return (
    <th
      data-slot="table-head"
      className={cn(
        'text-foreground h-10 px-2 text-left align-middle font-medium whitespace-nowrap [&:has([role=checkbox])]:pr-0',
        className,
      )}
      {...props}
    />
  );
}

function TableCell({ className, ...props }: React.ComponentProps<'td'>) {
  return (
    <td
      data-slot="table-cell"
      className={cn(
        'p-2 align-middle whitespace-nowrap [&:has([role=checkbox])]:pr-0',
        className,
      )}
      {...props}
    />
  );
}

function TableCaption({
  className,
  ...props
}: React.ComponentProps<'caption'>) {
  return (
    <caption
      data-slot="table-caption"
      className={cn('text-muted-foreground mt-4 text-sm', className)}
      {...props}
    />
  );
}

export {
  Table,
  TableHeader,
  TableBody,
  TableFooter,
  TableHead,
  TableRow,
  TableCell,
  TableCaption,
};
