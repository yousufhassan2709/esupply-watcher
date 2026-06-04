create table if not exists tenders (
  id               bigint generated always as identity primary key,
  source           text not null,          -- 'opportunity' | 'rfq'
  ext_id           text not null,          -- opportunity_id or reference_code
  ref_number       text,                   -- digits from title, links the two sources
  title            text,
  buyer            text,
  supply_category  text,
  status           text,
  publication_date text,                    -- ISO string
  closing_date     text,                    -- ISO string (lexicographically sortable)
  detail_url       text,
  first_seen_at    timestamptz not null default now(),
  last_seen_at     timestamptz not null default now(),
  unique (source, ext_id)
);

create index if not exists tenders_closing_idx   on tenders (closing_date);
create index if not exists tenders_firstseen_idx on tenders (first_seen_at);
create index if not exists tenders_ref_idx        on tenders (ref_number);
