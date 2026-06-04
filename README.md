# eSupply Tender Watcher

Automated daily pull of tenders from the Dubai Government **eSupply** procurement
portal, stored in Supabase and shown on a Next.js dashboard with a "new today" view.
Replaces the manual portal check the team does today.

## Architecture

Three components, connected through Supabase:

```
                 ┌──────────────────┐
                 │  eSupply portal  │
                 └────────▲─────────┘
                          │ login + scrape (Playwright)
                 ┌────────┴─────────┐
   Railway cron  │   scraper/       │  Python + Playwright
   (once daily)  │   scraper.py     │  → writes
                 └────────┬─────────┘
                          │ upsert
                 ┌────────▼─────────┐
                 │    Supabase      │  Postgres, single `tenders` table
                 └────────┬─────────┘
                          │ read (anon key)
                 ┌────────▼─────────┐
   Vercel        │   dashboard/     │  Next.js (App Router)
                 └──────────────────┘
```

- **Scraper** (`scraper/`) — logs in, scrapes both list pages across all paginated
  pages, upserts into Supabase. Needs a real browser, so it runs on **Railway**, not Vercel.
- **Supabase** (`supabase/`) — single `tenders` table. Scraper writes; dashboard reads.
- **Dashboard** (`dashboard/`) — reads from Supabase and displays tenders. No scraping,
  no browser. Deployed on **Vercel**.

> Do **not** run Playwright on Vercel — it does not work reliably in serverless. The
> scraper stays on Railway.

## Environment variables

| Variable | Used by | Where it lives | Notes |
|---|---|---|---|
| `ESUPPLY_USERNAME` | scraper | Railway secret | Portal login |
| `ESUPPLY_PASSWORD` | scraper | Railway secret | Portal login |
| `SUPABASE_URL` | scraper | Railway secret | Project URL |
| `SUPABASE_KEY` | scraper | Railway secret | **Service role** key (write access) |
| `NEXT_PUBLIC_SUPABASE_URL` | dashboard | Vercel env var | Same project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | dashboard | Vercel env var | **Anon** key (read-only) |

Never commit secrets. `.env`, `storage_state.json`, and `*.local` are git-ignored.
The dashboard only ever uses the anon key — never the service role key.

## 1. Supabase setup

1. Create a Supabase project.
2. Open the SQL editor and run [`supabase/schema.sql`](supabase/schema.sql). It creates the
   `tenders` table (unique on `(source, ext_id)`) plus indexes.
3. Grab two things from **Project Settings → API**:
   - Project URL → `SUPABASE_URL` / `NEXT_PUBLIC_SUPABASE_URL`
   - `service_role` key → `SUPABASE_KEY` (scraper only)
   - `anon` key → `NEXT_PUBLIC_SUPABASE_ANON_KEY` (dashboard only)

The `tenders` table's `first_seen_at` is set once on insert and preserved on later runs;
`last_seen_at` updates every run so you can tell which tenders are still live.
"New today" = a tender first seen since midnight **Asia/Dubai** time (computed in the dashboard).

## 2. Scraper — run locally

```bash
cd scraper
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium      # local only; the Docker image already has it
cp .env.example .env                        # then fill in the 4 values
python scraper.py
```

A successful run logs a summary like:

```
[scraper] opportunities: total=280, pages=3
[scraper] rfqs: collected 142 rows total
[scraper] opportunity: 280 rows -> 12 new, 268 updated
[scraper] SUMMARY: 422 scraped, 19 new, 403 updated, 422 total in DB
```

Re-running does **not** create duplicates (upsert on `(source, ext_id)`) and preserves
`first_seen_at`. The scraper exits non-zero on hard failure so the cron surfaces it.

### Optional: saved session

For ad-hoc testing you can drop a Playwright `storage_state.json` next to `scraper.py`
(from a manually logged-in session). If present, the scraper reuses it and skips the form
login. The daily cron uses form login (the default).

### Run the parser tests

```bash
cd scraper
pip install pytest
python -m pytest tests/ -q
```

These validate `parse_opportunities`, `parse_rfqs`, and `normalise` against saved HTML
fixtures (including Arabic titles, HTML entities, and a tender that appears in both feeds).

## 3. Scraper — deploy to Railway (daily cron)

1. New Railway project → **Deploy from repo** (point at this repo, root `scraper/`),
   or `railway up` from `scraper/`. The [`Dockerfile`](scraper/Dockerfile) uses the
   official Playwright Python image so Chromium and its system libraries are present.
2. Add the four scraper secrets (`ESUPPLY_USERNAME`, `ESUPPLY_PASSWORD`, `SUPABASE_URL`,
   `SUPABASE_KEY`) under **Variables**.
3. Set the service to run on a schedule: **Settings → Cron Schedule**, e.g. `0 4 * * *`
   (04:00 UTC = 08:00 Dubai). The container runs `python scraper.py` once and exits.
   For twice daily use e.g. `0 4,14 * * *`.

Railway surfaces a non-zero exit as a failed run, so a broken login or empty scrape is visible.

## 4. Dashboard — run locally

```bash
cd dashboard
npm install
cp .env.example .env.local                  # fill in URL + anon key
npm run dev                                  # http://localhost:3000
```

## 5. Dashboard — deploy to Vercel

1. Import the repo into Vercel; set the **Root Directory** to `dashboard`.
2. Add env vars `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY`.
3. Deploy. Framework preset auto-detects Next.js.

### Dashboard features

- Table sorted by closing date (soonest first), with an "open in eSupply" link where a
  `detail_url` exists (RFQs carry one).
- **New today** highlight + filter, plus filters for buyer, source, status, a
  "closing within 48h" toggle, and free-text title search.
- **Cross-source de-duplication in the view**: when the same `ref_number` appears as both
  an opportunity and an RFQ, it shows once with both source tags (preferring the RFQ's
  clickable link and the soonest closing date). Rows in the DB stay separate.
- A clean, unused **relevance** hook (typed field + commented-out column) for a future AI
  classification score against Manno's criteria. Not built in v1.

## Repo layout

```
esupply-watcher/
  scraper/        Python + Playwright scraper, parsers, tests, Dockerfile
  dashboard/      Next.js (App Router) + Tailwind dashboard
  supabase/       schema.sql
  README.md
```
