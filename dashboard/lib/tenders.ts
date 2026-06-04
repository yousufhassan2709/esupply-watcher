import { supabase } from "./supabase";
import type { DisplayTender, Source, Tender } from "./types";

// Dubai has a fixed UTC+4 offset (no DST), so we can treat it as a constant.
const DUBAI_OFFSET_MS = 4 * 60 * 60 * 1000;

// Start of "today" in Asia/Dubai, expressed as a UTC epoch (ms).
export function dubaiTodayStartUtc(now: number = Date.now()): number {
  const dubaiNow = new Date(now + DUBAI_OFFSET_MS);
  const y = dubaiNow.getUTCFullYear();
  const m = dubaiNow.getUTCMonth();
  const d = dubaiNow.getUTCDate();
  return Date.UTC(y, m, d, 0, 0, 0) - DUBAI_OFFSET_MS;
}

// Closing dates are stored as naive ISO strings in Dubai local time
// (e.g. "2026-06-20T14:00:00"). Parse them as Dubai time. Returns null for
// values that aren't parseable ISO timestamps (the parser falls back to the
// raw cell text when a date can't be formatted).
export function parseClosing(value: string | null): number | null {
  if (!value) return null;
  const isoNoTz = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?$/;
  const withTz = isoNoTz.test(value) ? `${value}+04:00` : value;
  const ms = Date.parse(withTz);
  return Number.isNaN(ms) ? null : ms;
}

export function isClosingSoon(
  closing: string | null,
  withinHours = 48,
  now: number = Date.now()
): boolean {
  const ms = parseClosing(closing);
  if (ms === null) return false;
  return ms >= now && ms <= now + withinHours * 60 * 60 * 1000;
}

export async function fetchTenders(): Promise<Tender[]> {
  const { data, error } = await supabase
    .from("tenders")
    .select("*")
    .order("closing_date", { ascending: true });
  if (error) throw error;
  return (data ?? []) as Tender[];
}

function uniqueSources(sources: Source[]): Source[] {
  // stable order: opportunity then rfq
  const order: Source[] = ["opportunity", "rfq"];
  return order.filter((s) => sources.includes(s));
}

// Collapse rows that share a non-null ref_number into a single display row
// carrying both source tags. Rows without a ref_number are never merged.
export function dedupe(
  tenders: Tender[],
  dubaiStart: number = dubaiTodayStartUtc()
): DisplayTender[] {
  const groups = new Map<string, Tender[]>();
  for (const t of tenders) {
    const key = t.ref_number ? `ref:${t.ref_number}` : `id:${t.source}:${t.ext_id}`;
    const arr = groups.get(key);
    if (arr) arr.push(t);
    else groups.set(key, [t]);
  }

  const out: DisplayTender[] = [];
  for (const [key, rows] of groups) {
    const sources = uniqueSources(rows.map((r) => r.source));
    // Prefer the RFQ row's detail_url (opportunities never carry one).
    const rfq = rows.find((r) => r.source === "rfq");
    const pick = <K extends keyof Tender>(field: K): Tender[K] | null => {
      for (const r of rows) {
        const v = r[field];
        if (v !== null && v !== undefined && v !== "") return v;
      }
      return null;
    };
    // soonest closing date across the merged rows
    const closing = rows
      .map((r) => r.closing_date)
      .filter((c): c is string => !!c)
      .sort((a, b) => (parseClosing(a) ?? Infinity) - (parseClosing(b) ?? Infinity))[0] ?? null;

    const firstSeen = rows
      .map((r) => r.first_seen_at)
      .sort((a, b) => Date.parse(a) - Date.parse(b))[0];

    out.push({
      key,
      sources,
      ref_number: rows[0].ref_number,
      title: pick("title"),
      buyer: pick("buyer"),
      supply_category: pick("supply_category"),
      status: pick("status"),
      closing_date: closing,
      detail_url: rfq?.detail_url ?? pick("detail_url"),
      first_seen_at: firstSeen,
      is_new_today: rows.some((r) => Date.parse(r.first_seen_at) >= dubaiStart),
      relevance: pick("relevance") as number | null,
    });
  }

  // default sort: soonest closing first, nulls last
  out.sort((a, b) => {
    const ca = parseClosing(a.closing_date);
    const cb = parseClosing(b.closing_date);
    if (ca === null && cb === null) return 0;
    if (ca === null) return 1;
    if (cb === null) return -1;
    return ca - cb;
  });

  return out;
}
