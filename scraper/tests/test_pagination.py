import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pagination import parse_total


# These two strings are the *real* pagination text captured from the live
# portal (see the Railway run logs). The total is the number after "of" — the
# leading "1 - 100" is the displayed row range and must NOT be read as the total.
def test_parse_total_opportunities_ignores_row_range():
    assert parse_total("Showing Result 1 - 100 of 301 1 2 3 4") == 301


def test_parse_total_rfqs_ignores_row_range_and_show_options():
    text = "Showing Result 1 - 10 of 252 Show: 10 20 50 100 1 2 3 4 5 6 26"
    assert parse_total(text) == 252


def test_parse_total_handles_out_of_phrasing():
    assert parse_total("100 out of 280") == 280


def test_parse_total_handles_thousands_separator():
    assert parse_total("Showing Result 1 - 100 of 1,234") == 1234


def test_parse_total_unparseable_returns_none():
    assert parse_total("") is None
    assert parse_total(None) is None
    assert parse_total("no totals here") is None
