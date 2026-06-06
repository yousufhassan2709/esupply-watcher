"""Pure helpers for reading the portal's pagination widget.

Kept dependency-free (stdlib `re` only) so it can be unit-tested without the
Playwright/Supabase stack the rest of the scraper needs.
"""
import re


def parse_total(text):
    """Extract the total result count from a pagination string.

    The live portal renders text like:

        "Showing Result 1 - 100 of 301 1 2 3 4"
        "Showing Result 1 - 10 of 252 Show: 10 20 50 100 1 2 3 4 5 6 26"

    The total is the number that follows "of" (or "out of" / "/"). The leading
    "1 - 100" is the displayed row *range*, NOT the total — an earlier version
    matched the "-" in that range and wrongly returned 100, which capped the
    scraper at a single page. We deliberately do not treat "-" as a separator.

    Returns the integer total, or None when no count can be read.
    """
    if not text:
        return None
    norm = re.sub(r"\s+", " ", text).strip()  # \s also collapses non-breaking spaces
    m = re.search(r"(?:out of|of|/)\s*(\d[\d,]*)", norm, re.IGNORECASE)
    return int(m.group(1).replace(",", "")) if m else None
