"""eSupply Tender Watcher — daily scraper.

Logs into the Dubai Government eSupply portal, scrapes both list pages across
all paginated pages, and upserts the results into the Supabase `tenders` table.

Runs as a Railway cron. Exits non-zero on hard failure so the cron surfaces it.
"""
import math
import os
import sys

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from supabase import create_client

from pagination import parse_total
from parsers import parse_opportunities, parse_rfqs, normalise

load_dotenv()

LOGIN_URL = "https://esupply.dubai.gov.ae/esupply/web/index.html#login"
OPPORTUNITIES_URL = (
    "https://esupply.dubai.gov.ae/esop/toolkit/opportunity/current/list.si"
    "?reset=true&resetstored=true&_ncp=1"
)
RFQS_URL = (
    "https://esupply.dubai.gov.ae/esop/toolkit/negotiation/pubRfq/list.si"
    "?reset=true&_ncp=1"
)
STORAGE_STATE = "storage_state.json"
PER_PAGE = 100
MAX_PAGES = 50  # safety cap for the count-unknown fallback walk


def log(msg):
    print(f"[scraper] {msg}", flush=True)


# --- pagination helpers (from the verified portal spec) ---------------------

def total_count(page):
    """Return (total, raw_text). total is None if the count can't be parsed."""
    try:
        txt = page.inner_text("#paginationId")
    except Exception:
        return None, None
    return parse_total(txt), (txt or "").strip()


SESSION_EXPIRED_MARKERS = (
    "session is invalid or expired",
    "\u0627\u0646\u062a\u0647\u062a \u0635\u0644\u0627\u062d\u064a\u0629 \u062c\u0644\u0633\u0629 \u0639\u0645\u0644\u0643",
)


def session_expired(page):
    """True if the portal served its 'session invalid or expired' interstitial.

    The opportunities list is public, so it renders fine with no session at all.
    Only the RFQ list actually requires auth — which means a silently failed
    login looks like a 30s selector timeout on RFQs rather than a login error.
    Detect the interstitial explicitly so the real cause is in the logs.
    """
    try:
        text = page.inner_text("body").lower()
    except Exception:
        return False
    return any(m.lower() in text for m in SESSION_EXPIRED_MARKERS)


def go_next(page):
    arrow = page.locator("#paginationId path[d^='M17.7,8']").last
    btn = arrow.locator(
        "xpath=ancestor-or-self::*[self::button or self::a or @role='button'][1]"
    )
    before = page.locator("tbody.async-list-tbody tr").first.inner_text()
    btn.click()
    # clicking next reloads the tbody asynchronously; wait for the first row to change
    page.wait_for_function(
        "(prev) => { const r = document.querySelector('tbody.async-list-tbody tr');"
        " return r && r.innerText !== prev; }",
        arg=before,
        timeout=20000,
    )


# --- login ------------------------------------------------------------------

def login(page):
    username = require_env("ESUPPLY_USERNAME")
    password = require_env("ESUPPLY_PASSWORD")
    log("logging in via form")
    page.goto(LOGIN_URL, wait_until="domcontentloaded")
    page.wait_for_selector("#username", timeout=30000)
    page.fill("#username", username)
    page.fill("#password", password)
    page.click("#Go")
    page.wait_for_load_state("networkidle", timeout=30000)
    if page.locator("#username").count() and page.locator("#username").is_visible():
        raise RuntimeError(
            "login failed — still on the login form after submitting. "
            "Check ESUPPLY_USERNAME / ESUPPLY_PASSWORD."
        )
    log("login submitted")


# --- per-list scrape --------------------------------------------------------

def scrape_list(page, url, parser, label):
    """Navigate to a list page, walk all paginated pages, return parsed rows."""
    log(f"{label}: navigating")
    page.goto(url, wait_until="domcontentloaded")
    if session_expired(page):
        raise RuntimeError(
            f"{label}: portal served 'session invalid or expired' — the login did "
            "not produce a valid session. Check ESUPPLY_USERNAME / ESUPPLY_PASSWORD."
        )
    page.wait_for_selector("tbody.async-list-tbody tr", timeout=30000)

    table = page.locator("table.list-table:has(tbody.async-list-tbody)").first
    total, raw = total_count(page)
    log(f"{label}: pagination text = {raw!r}")

    # Parse page 1 first so we can learn the *actual* page size. The two lists
    # use different sizes (opportunities show 100/page, RFQs 10/page), so a
    # fixed PER_PAGE would mis-count the number of pages and silently drop rows.
    rows = parser(table.evaluate("e => e.outerHTML"))
    per_page = len(rows) or PER_PAGE
    log(f"{label}: page 1 parsed {len(rows)} rows (per_page={per_page})")

    if total is not None:
        pages = max(1, math.ceil(total / per_page))
        log(f"{label}: total={total}, pages={pages}")
        for i in range(2, pages + 1):
            go_next(page)
            page_rows = parser(table.evaluate("e => e.outerHTML"))
            rows.extend(page_rows)
            log(f"{label}: page {i}/{pages} parsed {len(page_rows)} rows")
    else:
        # Count unreadable: walk pages until one comes back short or the next
        # arrow is gone. A page with fewer than per_page rows is the last page.
        log(f"{label}: total unknown — walking pages until exhausted")
        last_count = len(rows)
        page_no = 1
        while last_count == per_page and page_no < MAX_PAGES:
            if page.locator("#paginationId path[d^='M17.7,8']").count() == 0:
                break
            try:
                go_next(page)
            except Exception:
                log(f"{label}: next did not advance — stopping at page {page_no}")
                break
            page_no += 1
            page_rows = parser(table.evaluate("e => e.outerHTML"))
            rows.extend(page_rows)
            last_count = len(page_rows)
            log(f"{label}: page {page_no} parsed {len(page_rows)} rows")

    log(f"{label}: collected {len(rows)} rows total")
    return rows


# --- supabase ---------------------------------------------------------------

def existing_keys(client, source):
    """Return the set of ext_ids already stored for a given source."""
    keys = set()
    start = 0
    step = 1000
    while True:
        resp = (
            client.table("tenders")
            .select("ext_id")
            .eq("source", source)
            .range(start, start + step - 1)
            .execute()
        )
        batch = resp.data or []
        keys.update(r["ext_id"] for r in batch)
        if len(batch) < step:
            break
        start += step
    return keys


def upsert_rows(client, rows):
    """Upsert on (source, ext_id). Returns (new, updated) counts per the prior state."""
    # Dedupe within each source by ext_id; a single upsert batch must not contain
    # the same conflict key twice (Postgres: "cannot affect row a second time").
    by_source = {}
    for r in rows:
        by_source.setdefault(r["source"], {})[r["ext_id"]] = r

    new_total = updated_total = 0
    for source, mapping in by_source.items():
        src_rows = list(mapping.values())
        before = existing_keys(client, source)
        new = sum(1 for ext_id in mapping if ext_id not in before)
        updated = len(src_rows) - new
        client.table("tenders").upsert(src_rows, on_conflict="source,ext_id").execute()
        log(f"{source}: {len(src_rows)} rows -> {new} new, {updated} updated")
        new_total += new
        updated_total += updated
    return new_total, updated_total


def db_total(client):
    resp = client.table("tenders").select("id", count="exact").limit(1).execute()
    return resp.count


# --- helpers ----------------------------------------------------------------

def require_env(name):
    val = os.environ.get(name)
    if not val:
        log(f"FATAL missing required env var {name}")
        sys.exit(1)
    return val


# --- main -------------------------------------------------------------------

def main():
    supabase_url = require_env("SUPABASE_URL")
    supabase_key = require_env("SUPABASE_KEY")
    client = create_client(supabase_url, supabase_key)

    use_storage = os.path.exists(STORAGE_STATE)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = (
            browser.new_context(storage_state=STORAGE_STATE)
            if use_storage
            else browser.new_context()
        )
        page = context.new_page()

        if use_storage:
            log(f"using saved session from {STORAGE_STATE}")
        else:
            login(page)

        # Scrape each list independently. A failure in one must not discard the
        # rows already collected from the other — that is what turned a broken
        # RFQ page into three months of no writes at all.
        collected = {"opportunities": [], "rfqs": []}
        failures = {}
        for label, url, parser in (
            ("opportunities", OPPORTUNITIES_URL, parse_opportunities),
            ("rfqs", RFQS_URL, parse_rfqs),
        ):
            try:
                collected[label] = scrape_list(page, url, parser, label)
            except Exception as exc:  # noqa: BLE001 — one list must not sink the other
                failures[label] = f"{type(exc).__name__}: {exc}"
                log(f"ERROR {label} failed — {failures[label]}")

        browser.close()

    rows = normalise(collected["opportunities"], collected["rfqs"])
    log(f"normalised {len(rows)} rows "
        f"({sum(1 for r in rows if r['source'] == 'opportunity')} opportunities, "
        f"{sum(1 for r in rows if r['source'] == 'rfq')} rfqs)")

    if not rows:
        log("FATAL no rows parsed — treating as failure")
        sys.exit(1)

    new, updated = upsert_rows(client, rows)
    total = db_total(client)
    log(f"SUMMARY: {len(rows)} scraped, {new} new, {updated} updated, {total} total in DB")

    if failures:
        # The good rows are committed above; still exit non-zero so the cron
        # surfaces the partial run instead of reporting a clean success.
        for label, err in failures.items():
            log(f"PARTIAL {label} did not scrape: {err}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 — cron needs a non-zero exit on any failure
        log(f"FATAL {type(exc).__name__}: {exc}")
        sys.exit(1)
