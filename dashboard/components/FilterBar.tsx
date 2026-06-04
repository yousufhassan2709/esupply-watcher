"use client";

import type { Source } from "@/lib/types";

export interface Filters {
  search: string;
  buyer: string; // "" = all
  source: "" | Source; // "" = all
  status: string; // "" = all
  closingSoon: boolean;
  newToday: boolean;
}

export const EMPTY_FILTERS: Filters = {
  search: "",
  buyer: "",
  source: "",
  status: "",
  closingSoon: false,
  newToday: false,
};

interface Props {
  filters: Filters;
  onChange: (next: Filters) => void;
  buyers: string[];
  statuses: string[];
  newTodayCount: number;
}

const fieldClass =
  "rounded-md border border-border bg-white px-3 py-2 text-sm text-foreground " +
  "focus:outline-none focus:ring-2 focus:ring-primary";

export function FilterBar({ filters, onChange, buyers, statuses, newTodayCount }: Props) {
  const set = <K extends keyof Filters>(key: K, value: Filters[K]) =>
    onChange({ ...filters, [key]: value });

  return (
    <div className="flex flex-wrap items-end gap-3">
      <div className="flex flex-col gap-1">
        <label htmlFor="search" className="text-xs font-medium text-muted-fg">
          Search title
        </label>
        <input
          id="search"
          type="search"
          value={filters.search}
          onChange={(e) => set("search", e.target.value)}
          placeholder="Search titles…"
          className={`${fieldClass} min-w-56`}
        />
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor="buyer" className="text-xs font-medium text-muted-fg">
          Buyer
        </label>
        <select
          id="buyer"
          value={filters.buyer}
          onChange={(e) => set("buyer", e.target.value)}
          className={fieldClass}
        >
          <option value="">All buyers</option>
          {buyers.map((b) => (
            <option key={b} value={b}>
              {b}
            </option>
          ))}
        </select>
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor="source" className="text-xs font-medium text-muted-fg">
          Source
        </label>
        <select
          id="source"
          value={filters.source}
          onChange={(e) => set("source", e.target.value as Filters["source"])}
          className={fieldClass}
        >
          <option value="">All sources</option>
          <option value="opportunity">Opportunity</option>
          <option value="rfq">RFQ</option>
        </select>
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor="status" className="text-xs font-medium text-muted-fg">
          Status
        </label>
        <select
          id="status"
          value={filters.status}
          onChange={(e) => set("status", e.target.value)}
          className={fieldClass}
        >
          <option value="">All statuses</option>
          {statuses.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </div>

      <label className="flex cursor-pointer items-center gap-2 py-2 text-sm text-foreground">
        <input
          type="checkbox"
          checked={filters.closingSoon}
          onChange={(e) => set("closingSoon", e.target.checked)}
          className="h-4 w-4 cursor-pointer accent-primary"
        />
        Closing within 48h
      </label>

      <label className="flex cursor-pointer items-center gap-2 py-2 text-sm text-foreground">
        <input
          type="checkbox"
          checked={filters.newToday}
          onChange={(e) => set("newToday", e.target.checked)}
          className="h-4 w-4 cursor-pointer accent-accent"
        />
        New today
        <span className="rounded-full bg-accent px-2 py-0.5 text-xs font-semibold text-white">
          {newTodayCount}
        </span>
      </label>
    </div>
  );
}
