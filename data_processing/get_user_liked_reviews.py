#!/usr/local/bin/python3.12

import asyncio
import re
import sys
from pathlib import Path
from typing import Counter
from urllib.parse import urljoin, urlsplit, urlunsplit

from aiohttp import ClientSession, TCPConnector, ClientTimeout
from bs4 import BeautifulSoup

# Make project imports work whether executed from repo root or elsewhere
PROJECT_ROOT = Path(__file__).resolve().parents[1]  # .../Letterboxd Taste Comparer
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data_processing.utils.http_utils import BROWSER_HEADERS, default_request_timeout

LBX_BASE = "https://www.letterboxd.com"


# -----------------------
# Networking
# -----------------------

async def fetch_text(url: str, session: ClientSession, input_data=None):
    if input_data is None:
        input_data = {}
    try:
        async with session.get(url, timeout=ClientTimeout(total=default_request_timeout)) as response:
            text = await response.text()
            return text, {**input_data, "url": url, "status": response.status}
    except Exception:
        return None, {**input_data, "url": url, "status": None}


# -----------------------
# Parsing helpers
# -----------------------

# Review-ish URL patterns:
#   /someuser/film/some-film/
#   /someuser/film/some-film/1/
#   https://www.letterboxd.com/someuser/film/some-film/12345/
REVIEW_URL_RE = re.compile(
    r"(?:https?://(?:www\.)?letterboxd\.com)?/([^/?#\"']+)/film/([^/?#\"']+)(?:/|$|\?)",
    re.IGNORECASE,
)

# Raw scan for embedded URLs/paths (can include extra segments after slug)
REVIEW_URL_RAW_RE = re.compile(
    r"(https?://(?:www\.)?letterboxd\.com)?(/[^\"'\s?#]+/film/[^\"'\s?#]+(?:/[^\"'\s?#]*)?)",
    re.IGNORECASE,
)

_RESERVED_USER_PATHS = {
    "film", "films", "review", "reviews", "likes", "activity", "journal",
    "search", "lists", "members", "about", "contact", "settings", "sign-in",
    "sign-up", "login", "logout"
}


def _canonicalize_url(url: str) -> str:
    """Remove query/fragment; keep scheme/netloc/path for stable dedupe."""
    if not url:
        return url
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def _is_likes_url(url: str) -> bool:
    """
    IMPORTANT: the likes feed includes BOTH:
      /<reviewer>/film/<slug>/...        (review permalink)
      /<reviewer>/film/<slug>/likes/     ("likes" page)
    We must drop the /likes/ URLs to avoid duplicates.
    """
    try:
        path = urlsplit(url).path.rstrip("/")
        return path.endswith("/likes")
    except Exception:
        return False


def _extract_review_urls_from_likes_page(html: str) -> set[str]:
    """
    Extract review permalinks from the likes/reviews listing page.

    Uses:
      1) anchor href parsing
      2) raw HTML regex scanning (catches URLs embedded outside anchors)

    Filters OUT any ".../likes/" URLs to prevent doubled entries.
    """
    urls = set()
    soup = BeautifulSoup(html, "lxml")

    # 1) anchors
    for a in soup.select("a[href]"):
        href = a.get("href") or ""
        if not REVIEW_URL_RE.search(href):
            continue

        abs_url = href if href.startswith("http") else urljoin(LBX_BASE, href)
        abs_url = _canonicalize_url(abs_url)

        if _is_likes_url(abs_url):
            continue

        urls.add(abs_url)

    # 2) raw HTML scan
    for m in REVIEW_URL_RAW_RE.finditer(html):
        prefix = m.group(1) or LBX_BASE
        path = m.group(2)
        abs_url = _canonicalize_url(prefix.rstrip("/") + path)

        if not REVIEW_URL_RE.search(abs_url):
            continue
        if _is_likes_url(abs_url):
            continue

        urls.add(abs_url)

    return urls


def _find_next_page_url(html: str, current_url: str) -> str | None:
    """
    Find the next page in the likes feed, without relying on page counts.
    Tries common patterns: rel=next, .next, .load-more, etc.
    """
    soup = BeautifulSoup(html, "lxml")

    selectors = [
        'a[rel="next"]',
        "a.next",
        "a.load-more",
        "a.paginate-next",
        "div.paginate-nextprev a[rel='next']",
        "div.paginate-nextprev a.next",
    ]

    for sel in selectors:
        a = soup.select_one(sel)
        if a and a.get("href"):
            return urljoin(current_url, a.get("href"))

    # fallback: any link containing '/likes/reviews/page/'
    for a in soup.select("a[href]"):
        href = a.get("href") or ""
        if "/likes/reviews/page/" in href:
            return urljoin(current_url, href)

    return None


def _parse_rating_from_class(class_list) -> float:
    """
    Parse rating from classes like 'rated-45' => 4.5 stars (out of 5).
    Returns -1 when missing/unparseable.
    """
    if not class_list:
        return -1

    for c in class_list:
        if isinstance(c, str) and c.startswith("rated-"):
            try:
                n = int(c.split("-", 1)[1])
                if n < 5 or n > 50 or (n % 5 != 0):
                    return -1
                return n / 10
            except Exception:
                return -1

    return -1


def _parse_rating_text(text: str) -> float:
    """
    Parse glyph ratings like '★★★½' into 3.5 stars (out of 5).
    Returns -1 when missing/unparseable.
    """
    if not text:
        return -1
    t = text.strip()
    if "★" not in t:
        return -1
    stars = t.count("★")
    if "½" in t:
        stars += 0.5
    return stars


def _reviewer_from_review_url(url: str) -> str:
    m = REVIEW_URL_RE.search(url or "")
    if not m:
        return "unknown"
    reviewer = m.group(1)
    if reviewer.lower() in _RESERVED_USER_PATHS:
        return "unknown"
    return reviewer


def _parse_movie_title_from_review_page(soup: BeautifulSoup) -> str:
    """
    Best-effort film title extraction from a review page.
    """
    a = soup.select_one('h1 a[href^="/film/"]')
    if a:
        t = a.get_text(" ", strip=True)
        if t:
            return t

    a = soup.select_one('a[href^="/film/"][data-track-action], a[href^="/film/"].headline')
    if a:
        t = a.get_text(" ", strip=True)
        if t:
            return t

    for a in soup.select('a[href^="/film/"]'):
        t = a.get_text(" ", strip=True)
        if t:
            return t

    return "Unknown"


async def parse_review_detail(response):
    """
    Given the HTML for a single review permalink, return a dict:
      { reviewer, movie, rating_val, review_url }
    """
    if not response or not response[0]:
        return None

    html, meta = response
    url = (meta or {}).get("url", "")
    url = _canonicalize_url(url)

    # Safety: ignore likes pages if they slip through
    if _is_likes_url(url):
        return None

    soup = BeautifulSoup(html, "lxml")

    reviewer = _reviewer_from_review_url(url)
    movie = _parse_movie_title_from_review_page(soup)

    rating_val = -1
    rating_el = soup.select_one("span.rating[class*='rated-']")
    if rating_el:
        rating_val = _parse_rating_from_class(rating_el.get("class", []))
    if rating_val == -1:
        rating_el = soup.select_one("span.rating")
        if rating_el:
            rating_val = _parse_rating_text(rating_el.get_text(" ", strip=True))

    return {
        "reviewer": reviewer,
        "movie": movie,
        "rating_val": rating_val,  # out of 5, or -1
        "review_url": url,
    }


# -----------------------
# Scrapers
# -----------------------

async def get_all_likes_review_urls(username: str, session: ClientSession) -> list[str]:
    """
    Crawl /{username}/likes/reviews/ by following "next" links until none remain.
    """
    start_url = f"{LBX_BASE}/{username}/likes/reviews/"
    current = start_url
    seen_pages = set()
    review_urls = set()

    while current and current not in seen_pages:
        seen_pages.add(current)

        html, _meta = await fetch_text(current, session, {"username": username})
        if not html:
            break

        review_urls |= _extract_review_urls_from_likes_page(html)

        nxt = _find_next_page_url(html, current)
        current = _canonicalize_url(nxt) if nxt else None

    return sorted(review_urls)


async def get_user_liked_reviews(username: str):
    """
    Returns (liked_reviews, status) where liked_reviews is a list of dicts:
      { reviewer, movie, rating_val, review_url }
    """
    connector = TCPConnector(limit=6, ttl_dns_cache=3600)
    async with ClientSession(headers=BROWSER_HEADERS, connector=connector) as session:
        review_urls = await get_all_likes_review_urls(username, session=session)
        if not review_urls:
            return [], "success"

        sem = asyncio.Semaphore(6)

        async def bounded_fetch(u: str):
            async with sem:
                return await fetch_text(u, session, {"url": u})

        review_pages = await asyncio.gather(*[bounded_fetch(u) for u in review_urls])
        parsed = await asyncio.gather(*[parse_review_detail(r) for r in review_pages])

        # Filter None and dedupe by URL
        out = {}
        for item in parsed:
            if not item:
                continue
            out[item["review_url"]] = item

        return list(out.values()), "success"


def get_liked_reviews_data(username: str):
    return asyncio.run(get_user_liked_reviews(username))


def reviews_liked_from_user(user: str):
    liked_reviews, status = get_liked_reviews_data(username)

    if status:
        return Counter([review["reviewer"] for review in liked_reviews]), True
    else:
        return [], False


# -----------------------
# Run (consistent style)
# -----------------------

if __name__ == "__main__":
    username = "Dcsoeirvy"
    liked_reviews, status = reviews_liked_from_user(username)

    print(liked_reviews)