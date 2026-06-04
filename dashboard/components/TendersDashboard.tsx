"use client";

import { useEffect, useMemo, useState } from "react";
import { dedupe, fetchTenders, isClosingSoon } from "@/lib/tenders";
import type { DisplayTender, Tender } from "@/lib/types";
import { EMPTY_FILTERS, FilterBar, type Filters } from "./FilterBar";
import { TenderTable } from "./TenderTable";

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; rows: DisplayTender[] };

export function TendersDashboard() {
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [filters, setFilters] = useState<Filters>(EMPTY_FILTERS);

  async function load() {
    setState({ status: "loading" });
    try {
      const tenders: Tender[] = await fetchTenders();
      setState({ status: "ready", rows: dedupe(tenders) });
    } catch (err) {
      setState({
        status: "error",
        message: err instanceof Error ? err.message : "Failed to load tenders.",
      });
    }
  }

  useEffect(() => {
    load();
  }, []);

  const allRows = state.status === "ready" ? state.rows : [];

  const buyers = useMemo(
    () =>
      Array.from(new Set(allRows.map((r) => r.buyer).filter((b): b is string => !!b))).sort(),
    [allRows]
  );
  const statuses = useMemo(
    () =>
      Array.from(new Set(allRows.map((r) => r.status).filter((s): s is string => !!s))).sort(),
    [allRows]
  );
  const newTodayCount = useMemo(
    () => allRows.filter((r) => r.is_new_today).length,
    [allRows]
  );

  const visible = useMemo(() => {
    const q = filters.search.trim().toLowerCase();
    return allRows.filter((r) => {
      if (q && !(r.title ?? "").toLowerCase().includes(q)) return false;
      if (filters.buyer && r.buyer !== filters.buyer) return false;
      if (filters.source && !r.sources.includes(filters.source)) return false;
      if (filters.status && r.status !== filters.status) return false;
      if (filters.newToday && !r.is_new_today) return false;
      if (filters.closingSoon && !isClosingSoon(r.closing_date)) return false;
      return true;
    });
  }, [allRows, filters]);

  return (
    <main className="mx-auto max-w-7xl px-4 py-8">
      <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-mono text-2xl font-bold text-primary">
            eSupply Tender Watcher
          </h1>
          <p className="mt-1 text-sm text-muted-fg">
            Dubai Government eSupply — Current Opportunities &amp; open RFQs, refreshed daily.
          </p>
        </div>
        <button
          onClick={load}
          className="cursor-pointer rounded-md border border-border bg-white px-4 py-2 text-sm font-medium text-primary transition-colors hover:bg-muted"
        >
          Refresh
        </button>
      </header>

      {state.status === "error" && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
          <p className="font-semibold">Couldn’t load tenders.</p>
          <p className="mt-1">{state.message}</p>
          <button
            onClick={load}
            className="mt-3 cursor-pointer rounded-md border border-destructive/40 px-3 py-1.5 font-medium hover:bg-destructive/10"
          >
            Retry
          </button>
        </div>
      )}

      {state.status === "loading" && (
        <div className="space-y-2">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="h-12 animate-pulse rounded-md bg-muted" />
          ))}
        </div>
      )}

      {state.status === "ready" && (
        <div className="space-y-4">
          <FilterBar
            filters={filters}
            onChange={setFilters}
            buyers={buyers}
            statuses={statuses}
            newTodayCount={newTodayCount}
          />
          <p className="text-sm text-muted-fg">
            Showing <span className="font-semibold text-foreground">{visible.length}</span> of{" "}
            {allRows.length} tenders
          </p>
          <TenderTable rows={visible} />
        </div>
      )}
    </main>
  );
}
