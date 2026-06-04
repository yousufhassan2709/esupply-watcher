import re
from datetime import datetime, timezone
from bs4 import BeautifulSoup

def _iso(s):
    s = (s or "").strip()
    try:
        return datetime.strptime(s, "%d/%m/%Y %H:%M").isoformat()
    except ValueError:
        return s or None

def _ref_number(title):
    if not title:
        return None
    m = re.search(r"\b(\d{6,})\b", title)
    return m.group(1) if m else None

def parse_opportunities(html):
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table", class_="list-table")
    body = table.find("tbody", class_="async-list-tbody")
    rows = []
    for tr in body.find_all("tr", recursive=False):
        cells = tr.find_all(["th", "td"], recursive=False)
        if len(cells) < 7:
            continue
        link = cells[3].find("a", class_="detailLink")
        title = link.get_text(strip=True) if link else cells[3].get_text(strip=True)
        opp_id = None
        if link and link.has_attr("onclick"):
            m = re.search(r"goToDetail\('(\d+)'", link["onclick"])
            if m:
                opp_id = m.group(1)
        rows.append({
            "opportunity_id": opp_id,
            "currency": cells[1].get_text(strip=True),
            "buyer": cells[2].get_text(strip=True),
            "title": title,
            "publication_date": _iso(cells[4].get_text(strip=True)),
            "supply_category": cells[5].get_text(strip=True),
            "closing_date": _iso(cells[6].get_text(strip=True)),
        })
    return rows

def parse_rfqs(html):
    soup = BeautifulSoup(html, "lxml")
    body = soup.find("tbody", class_="async-list-tbody")
    rows = []
    for tr in body.find_all("tr", recursive=False):
        def cell(cls):
            td = tr.find("td", class_=cls)
            return td.get_text(strip=True) if td else None
        link = tr.select_one("td.col_TITLE a.detailLink")
        title = link.get_text(strip=True) if link else cell("col_TITLE")
        detail_path, rfq_id = None, None
        if link and link.has_attr("href"):
            m = re.search(r"'(/esop/[^']+)'", link["href"])
            if m:
                detail_path = m.group(1)
            m2 = re.search(r"rfqId=([\w]+)", link["href"])
            if m2:
                rfq_id = m2.group(1)
        rows.append({
            "reference_code": cell("col_REFERENCE_CODE"),
            "rfq_id": rfq_id,
            "title": title,
            "project_code": cell("col_TENDER_CODE"),
            "closing_date": _iso(cell("col_INTEREST_TIME_LIMIT")),
            "status": cell("col_STATE"),
            "buyer": cell("col_COMPANY_NAME"),
            "detail_path": detail_path,
        })
    return rows

BASE = "https://esupply.dubai.gov.ae"

def normalise(opportunities, rfqs):
    now = datetime.now(timezone.utc).isoformat()
    out = []
    for r in opportunities:
        if not r["opportunity_id"]:
            continue
        out.append({
            "source": "opportunity",
            "ext_id": r["opportunity_id"],
            "ref_number": _ref_number(r["title"]),
            "title": r["title"],
            "buyer": r["buyer"],
            "supply_category": r["supply_category"],
            "status": None,
            "publication_date": r["publication_date"],
            "closing_date": r["closing_date"],
            "detail_url": None,
            "last_seen_at": now,
        })
    for r in rfqs:
        if not r["reference_code"]:
            continue
        out.append({
            "source": "rfq",
            "ext_id": r["reference_code"],
            "ref_number": _ref_number(r["title"]),
            "title": r["title"],
            "buyer": r["buyer"],
            "supply_category": None,
            "status": r["status"],
            "publication_date": None,
            "closing_date": r["closing_date"],
            "detail_url": (BASE + r["detail_path"]) if r["detail_path"] else None,
            "last_seen_at": now,
        })
    return out
