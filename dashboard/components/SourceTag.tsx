import type { Source } from "@/lib/types";

const LABELS: Record<Source, string> = {
  opportunity: "Opportunity",
  rfq: "RFQ",
};

const STYLES: Record<Source, string> = {
  opportunity: "bg-muted text-foreground border-border",
  rfq: "bg-secondary/10 text-primary border-secondary/30",
};

export function SourceTag({ source }: { source: Source }) {
  return (
    <span
      className={`inline-block rounded-full border px-2 py-0.5 text-xs font-medium ${STYLES[source]}`}
    >
      {LABELS[source]}
    </span>
  );
}
