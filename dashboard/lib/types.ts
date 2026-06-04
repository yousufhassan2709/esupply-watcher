export type Source = "opportunity" | "rfq";

// Mirrors a row in the Supabase `tenders` table.
export interface Tender {
  id: number;
  source: Source;
  ext_id: string;
  ref_number: string | null;
  title: string | null;
  buyer: string | null;
  supply_category: string | null;
  status: string | null;
  publication_date: string | null;
  closing_date: string | null;
  detail_url: string | null;
  first_seen_at: string;
  last_seen_at: string;

  // Future hook: AI relevance score against Manno's criteria.
  // Not populated in v1; the column slot in the table is commented out.
  relevance?: number | null;
}

// A view-model row after cross-source de-duplication. When the same
// ref_number appears as both an opportunity and an RFQ, the two rows are
// merged into one with both source tags.
export interface DisplayTender {
  key: string;
  sources: Source[];
  ref_number: string | null;
  title: string | null;
  buyer: string | null;
  supply_category: string | null;
  status: string | null;
  closing_date: string | null;
  detail_url: string | null;
  first_seen_at: string;
  is_new_today: boolean;
  relevance?: number | null;
}
