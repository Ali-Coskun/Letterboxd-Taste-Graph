import asyncio
import sys
from pathlib import Path
import re
from urllib.parse import urlsplit, urlunsplit

from aiohttp import ClientSession, TCPConnector, ClientTimeout
from bs4 import BeautifulSoup

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data_processing.utils.http_utils import BROWSER_HEADERS, default_request_timeout

LBX_BASE = "https://letterboxd.com"


async def fetch(url: str, session: ClientSession) -> bytes | None:
    try:
        async with session.get(url, timeout=ClientTimeout(total=default_request_timeout)) as r:
            return await r.read()
    except Exception:
        return None


def _is_page_not_found(html: bytes) -> bool:
    return b"Page not found" in html or b"page-not-found" in html


def get_page_count_from_html(html: bytes) -> int:
    """Find last pagination number (fallback to 1)."""
    soup = BeautifulSoup(html, "lxml")

    pages = []
    for a in soup.select("div.paginate-pages a"):
        t = (a.get_text() or "").strip()
        if t.isdigit():
            pages.append(int(t))
    if pages:
        return max(pages)

    last = soup.select_one('link[rel="last"]')
    if last and last.get("href"):
        m = re.search(r"/page/(\d+)/", last["href"])
        if m:
            return int(m.group(1))

    return 1


def parse_display_name_from_profile(html: bytes) -> str | None:
    """Extract display name from a profile page (robust fallbacks)."""
    soup = BeautifulSoup(html, "lxml")

    for sel in ("h1.person-display-name", "h1.profile-name", "h1"):
        el = soup.select_one(sel)
        if el:
            txt = (el.get_text() or "").strip()
            if txt and "Letterboxd" not in txt and "Your life in film" not in txt:
                return txt

    meta = soup.select_one("meta[property='og:title']")
    if meta and meta.get("content"):
        t = meta["content"].strip()
        m = re.match(r"(.+?)’s profile", t)
        if m:
            return m.group(1).strip()

    return None


def _extract_int_from_text(text: str) -> int | None:
    m = re.search(r"(\d[\d,]*)", text)
    if not m:
        return None
    return int(m.group(1).replace(",", ""))


def parse_reviews_written_from_profile(html: bytes, username: str) -> int | None:
    """
    Extract the reviews count from the profile page by finding the
    '/<username>/reviews/' link and pulling a number from its text/children/attrs.
    """
    soup = BeautifulSoup(html, "lxml")
    target_href = f"/{username.lower()}/reviews/"

    anchors = soup.select(f"a[href='{target_href}']")
    if not anchors:
        anchors = [
            a for a in soup.select("a[href]")
            if (a.get("href") or "").lower().startswith(target_href)
        ]

    for a in anchors:
        # 1) Number in the anchor text
        txt = " ".join(a.stripped_strings)
        n = _extract_int_from_text(txt)
        if n is not None:
            return n

        # 2) Number in common child spans (stats often have a value span)
        for child_sel in ("span.value", "span.count", "span.stat-value", "strong"):
            child = a.select_one(child_sel)
            if child:
                n = _extract_int_from_text(child.get_text(" ", strip=True))
                if n is not None:
                    return n

        # 3) data-* attributes
        for attr in ("data-count", "data-value", "data-stat"):
            if a.has_attr(attr):
                n = _extract_int_from_text(str(a.get(attr)))
                if n is not None:
                    return n

    return None


def _canonicalize_url(url: str) -> str:
    """Remove query/fragment; keep scheme/netloc/path for stable dedupe."""
    if not url:
        return url
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def parse_review_items_count(html: bytes, username: str) -> int:
    """
    Count review entries on /<username>/reviews/ by extracting review permalinks:
      /<username>/film/<slug>/
      /<username>/film/<slug>/<id>/
    This avoids counting generic film links like /film/<slug>/ which caused your bug.
    """
    user = username.lower()
    soup = BeautifulSoup(html, "lxml")

    # Restrict to main content to avoid picking up unrelated links
    main = (
        soup.select_one("div.col-main") or
        soup.select_one("main") or
        soup.select_one("section.section") or
        soup
    )

    # Match review permalinks for THIS user only
    # group(1) = film slug
    review_re = re.compile(
        rf"(?:https?://(?:www\.)?letterboxd\.com)?/{re.escape(user)}/film/([^/?#\"']+)",
        re.IGNORECASE,
    )

    # Raw scan can catch embedded paths that aren't direct anchors
    raw_re = re.compile(
        rf"(https?://(?:www\.)?letterboxd\.com)?(/" + re.escape(user) + r"/film/[^\"'\s?#]+)",
        re.IGNORECASE,
    )

    review_keys: set[str] = set()

    # 1) Anchor hrefs
    for a in main.select("a[href]"):
        href = a.get("href") or ""
        if not href:
            continue

        # Build absolute URL to canonicalize
        abs_url = href if href.startswith("http") else (LBX_BASE.rstrip("/") + href)
        abs_url = _canonicalize_url(abs_url)

        m = review_re.search(abs_url)
        if not m:
            continue

        film_slug = m.group(1).strip().lower()
        # Canonical key: one review per film per user
        review_keys.add(f"/{user}/film/{film_slug}/")

    # 2) Raw HTML scan fallback (covers odd markup)
    html_text = html.decode("utf-8", errors="ignore")
    for m in raw_re.finditer(html_text):
        prefix = m.group(1) or LBX_BASE
        path = m.group(2)
        abs_url = _canonicalize_url(prefix.rstrip("/") + path)

        m2 = review_re.search(abs_url)
        if not m2:
            continue

        film_slug = m2.group(1).strip().lower()
        review_keys.add(f"/{user}/film/{film_slug}/")

    return len(review_keys)


def build_paged_url(base: str, page: int) -> str:
    return base if page <= 1 else f"{base}page/{page}/"


async def get_reviews_written_count_from_reviews_pages(username: str, session: ClientSession) -> int:
    """
    Fallback: estimate count using /<username>/reviews/ pagination:
      total = (pages - 1) * per_page + last_page_count
    """
    base = f"https://letterboxd.com/{username}/reviews/"
    first_html = await fetch(base, session)
    if not first_html or _is_page_not_found(first_html):
        return 0

    pages = get_page_count_from_html(first_html)
    per_page = parse_review_items_count(first_html, username)
    if per_page == 0:
        return 0

    if pages == 1:
        return per_page

    last_html = await fetch(build_paged_url(base, pages), session)
    if not last_html or _is_page_not_found(last_html):
        return pages * per_page

    last_count = parse_review_items_count(last_html, username)
    if last_count == 0:
        return pages * per_page

    return (pages - 1) * per_page + last_count


async def get_user_profile(username: str) -> tuple[str | None, int]:
    """Returns (display_name, reviews_written_count)."""
    profile_url = f"https://letterboxd.com/{username}/"

    async with ClientSession(headers=BROWSER_HEADERS, connector=TCPConnector(limit=6)) as session:
        profile_html = await fetch(profile_url, session)
        if not profile_html or _is_page_not_found(profile_html):
            return None, 0

        display_name = parse_display_name_from_profile(profile_html)

        reviews_written = parse_reviews_written_from_profile(profile_html, username)
        if reviews_written is None:
            reviews_written = await get_reviews_written_count_from_reviews_pages(username, session)

        return display_name, reviews_written


if __name__ == "__main__":
    username = "lettylander"
    display_name, reviews_written = asyncio.run(get_user_profile(username))
    print("display_name:", display_name)
    print("reviews_written:", reviews_written)