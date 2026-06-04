import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers import parse_opportunities, parse_rfqs, normalise, _ref_number

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


def _load(name):
    with open(os.path.join(FIXTURES, name), encoding="utf-8") as f:
        return f.read()


def test_parse_opportunities_extracts_all_rows():
    rows = parse_opportunities(_load("opportunities_sample.html"))
    assert len(rows) == 3
    first = rows[0]
    assert first["opportunity_id"] == "241440"
    assert first["currency"] == "AED"
    assert first["buyer"] == "Dubai Municipality"
    assert "Transportation Maintenance Dept" in first["title"]
    assert first["supply_category"] == "Vehicles & Transport"
    # dd/mm/yyyy HH:MM -> ISO
    assert first["publication_date"] == "2026-06-01T09:00:00"
    assert first["closing_date"] == "2026-06-20T14:00:00"


def test_parse_opportunities_handles_arabic_title():
    rows = parse_opportunities(_load("opportunities_sample.html"))
    arabic = rows[1]
    assert arabic["opportunity_id"] == "241441"
    assert "توريد معدات مختبر" in arabic["title"]


def test_parse_rfqs_extracts_class_named_cells():
    rows = parse_rfqs(_load("rfqs_sample.html"))
    assert len(rows) == 2
    first = rows[0]
    assert first["reference_code"] == "rfq_242035"
    assert first["rfq_id"] == "rfq_404636"
    assert first["project_code"] == "tender_237320"
    assert first["status"] == "Running"
    assert first["buyer"] == "Dubai Municipality"
    assert first["detail_path"] == "/esop/toolkit/negotiation/rfq/initDetailRfq.do?rfqId=rfq_404636"
    assert first["closing_date"] == "2026-06-20T14:00:00"


def test_ref_number_extraction():
    assert _ref_number("12612591 Transportation Maintenance Dept") == "12612591"
    assert _ref_number("صيانة أنظمة التكييف - مرجع 554433") == "554433"
    assert _ref_number("Consultancy services - no ref code here") is None
    assert _ref_number("short 123") is None  # fewer than 6 digits
    assert _ref_number(None) is None


def test_normalise_shape_and_dedup_key():
    opps = parse_opportunities(_load("opportunities_sample.html"))
    rfqs = parse_rfqs(_load("rfqs_sample.html"))
    out = normalise(opps, rfqs)

    # 3 opportunities + 2 rfqs, all have valid ids
    assert len(out) == 5

    opp_rows = [r for r in out if r["source"] == "opportunity"]
    rfq_rows = [r for r in out if r["source"] == "rfq"]
    assert len(opp_rows) == 3
    assert len(rfq_rows) == 2

    # opportunity rows carry no detail_url; rfq rows build a full URL
    assert all(r["detail_url"] is None for r in opp_rows)
    assert rfq_rows[0]["detail_url"] == (
        "https://esupply.dubai.gov.ae/esop/toolkit/negotiation/rfq/initDetailRfq.do?rfqId=rfq_404636"
    )

    # cross-source link: the same ref_number appears in both feeds
    opp_match = next(r for r in opp_rows if r["ref_number"] == "12612591")
    rfq_match = next(r for r in rfq_rows if r["ref_number"] == "12612591")
    assert opp_match["source"] == "opportunity"
    assert rfq_match["source"] == "rfq"

    # every row has last_seen_at and the dedup key fields
    for r in out:
        assert r["last_seen_at"]
        assert r["source"] and r["ext_id"]
        assert "first_seen_at" not in r  # preserved by DB, never sent on upsert


def test_normalise_skips_rows_without_ids():
    out = normalise(
        [{"opportunity_id": None, "currency": "AED", "buyer": "X", "title": "t",
          "publication_date": None, "supply_category": None, "closing_date": None}],
        [{"reference_code": None, "rfq_id": None, "title": "t", "project_code": None,
          "closing_date": None, "status": None, "buyer": None, "detail_path": None}],
    )
    assert out == []
