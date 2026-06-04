import type { DisplayTender } from "@/lib/types";
import { parseClosing } from "@/lib/tenders";
import { SourceTag } from "./SourceTag";

function formatClosing(value: string | null): string {
  const ms = parseClosing(value);
  if (ms === null) return value ?? "—";
  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Asia/Dubai",
  }).format(ms);
}

const th = "px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-muted-fg";
const td = "px-3 py-3 align-top text-sm";

export function TenderTable({ rows }: { rows: DisplayTender[] }) {
  if (rows.length === 0) {
    return (
      <div className="rounded-lg border border-border bg-white p-10 text-center text-muted-fg">
        No tenders match the current filters.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-border bg-white">
      <table className="w-full border-collapse">
        <thead className="border-b border-border bg-muted/60">
          <tr>
            <th className={th}>Title</th>
            <th className={th}>Buyer</th>
            <th className={th}>Source</th>
            <th className={th}>Supply Category</th>
            <th className={th}>Status</th>
            <th className={th}>Closing</th>
            {/* Future hook: AI relevance score against Manno's criteria.
            <th className={th}>Relevance</th> */}
            <th className={th}>Link</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr
              key={r.key}
              className={`border-b border-border last:border-0 transition-colors hover:bg-muted/40 ${
                r.is_new_today ? "bg-accent/5" : ""
              }`}
            >
              <td className={`${td} max-w-md`}>
                <div className="flex items-start gap-2">
                  {r.is_new_today && (
                    <span className="mt-0.5 shrink-0 rounded-full bg-accent px-2 py-0.5 text-[10px] font-bold uppercase text-white">
                      New
                    </span>
                  )}
                  <span className="font-medium text-foreground">{r.title ?? "—"}</span>
                </div>
                {r.ref_number && (
                  <span className="mt-1 block font-mono text-xs text-muted-fg">
                    ref {r.ref_number}
                  </span>
                )}
              </td>
              <td className={`${td} text-foreground`}>{r.buyer ?? "—"}</td>
              <td className={td}>
                <div className="flex flex-wrap gap-1">
                  {r.sources.map((s) => (
                    <SourceTag key={s} source={s} />
                  ))}
                </div>
              </td>
              <td className={`${td} text-muted-fg`}>{r.supply_category ?? "—"}</td>
              <td className={td}>
                {r.status ? (
                  <span className="inline-block rounded-full bg-success/10 px-2 py-0.5 text-xs font-medium text-success">
                    {r.status}
                  </span>
                ) : (
                  <span className="text-muted-fg">—</span>
                )}
              </td>
              <td className={`${td} tabular whitespace-nowrap text-foreground`}>
                {formatClosing(r.closing_date)}
              </td>
              {/* Future hook: relevance score cell
              <td className={td}>{r.relevance ?? "—"}</td> */}
              <td className={td}>
                {r.detail_url ? (
                  <a
                    href={r.detail_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="cursor-pointer font-medium text-primary underline-offset-2 hover:underline"
                  >
                    Open in eSupply
                  </a>
                ) : (
                  <span className="text-muted-fg">—</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
