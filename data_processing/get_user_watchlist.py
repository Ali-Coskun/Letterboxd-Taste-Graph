#!/usr/local/bin/python3.12

import asyncio
import sys
from pathlib import Path
from itertools import chain

from aiohttp import ClientSession, TCPConnector, ClientTimeout
from bs4 import BeautifulSoup

PROJECT_ROOT = Path(__file__).resolve().parents[1]  # .../Letterboxd Taste Comparer
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data_processing.utils.http_utils import BROWSER_HEADERS, default_request_timeout
from data_processing.utils.selectors import LBX_REVIEW_TILE
from data_processing.utils.utils import get_page_count


async def fetch(url, session, input_data=None):
    if input_data is None:
        input_data = {}
    async with session.get(url, timeout=ClientTimeout(total=default_request_timeout)) as response:
        try:
            return await response.read(), input_data
        except Exception:
            return None, None


def _extract_slug_and_title(tile) -> tuple[str | None, str | None]:
    """
    Returns (slug, display_name) where slug is the Letterboxd film slug (e.g. "inception")
    and display_name is the film title (e.g. "Inception").
    """
    # 1) Try react-component attributes (fast path)
    rc = tile.select_one("div.react-component")

    slug = None
    title = None

    if rc:
        # Slug candidates seen across various LB pages
        for attr in ("data-item-slug", "data-film-slug", "data-target-link"):
            val = rc.get(attr)
            if val:
                # data-target-link sometimes contains "/film/<slug>/"
                if val.startswith("/film/"):
                    parts = val.strip("/").split("/")
                    if len(parts) >= 2 and parts[0] == "film":
                        slug = parts[1]
                else:
                    slug = val
                if slug:
                    break

        # Title candidates (varies over time)
        for attr in ("data-item-name", "data-film-name", "data-item-title", "data-title"):
            val = rc.get(attr)
            if val:
                title = val.strip()
                break

    # 2) Fallback slug from /film/<slug>/ anchor
    if not slug:
        a = tile.select_one('a[href^="/film/"]')
        if a:
            href = a.get("href", "")
            # Expect /film/<slug>/ (sometimes /film/<slug>/<variant>/ but slug is still parts[1])
            parts = href.strip("/").split("/")
            if len(parts) >= 2 and parts[0] == "film":
                slug = parts[1]

    # 3) Fallback title from poster img alt
    if not title:
        img = tile.find("img")
        if img:
            alt = img.get("alt")
            if alt:
                title = alt.strip()

    # 4) Fallback title from an <a title="...">
    if not title:
        a_title = tile.select_one("a[title]")
        if a_title:
            t = a_title.get("title")
            if t:
                title = t.strip()

    return slug, title


async def parse_watchlist_page(response):
    # response is (bytes, input_data)
    html = response[0]
    if not html:
        return []

    soup = BeautifulSoup(html, "lxml")
    watchlist_tiles = soup.find_all(*LBX_REVIEW_TILE)

    items = []
    for tile in watchlist_tiles:
        slug, title = _extract_slug_and_title(tile)
        if not slug:
            continue

        items.append(
            {
                "movie_id": slug,
                "display_name": title or slug,  # keep something usable even if title missing
            }
        )

    return items


async def get_user_watchlist(username, num_pages):
    url = "https://letterboxd.com/{}/watchlist/page/{}/"

    async with ClientSession(headers=BROWSER_HEADERS, connector=TCPConnector(limit=6)) as session:
        tasks = [
            asyncio.ensure_future(fetch(url.format(username, i + 1), session, {"username": username}))
            for i in range(num_pages)
        ]

        scrape_responses = await asyncio.gather(*tasks)
        scrape_responses = [x for x in scrape_responses if x and x[0]]

    tasks = [asyncio.ensure_future(parse_watchlist_page(resp)) for resp in scrape_responses]
    parse_responses = await asyncio.gather(*tasks)

    # Flatten list-of-lists
    return list(chain.from_iterable(parse_responses))


def get_watchlist_data(username):
    num_pages, _ = get_page_count(username, url="https://letterboxd.com/{}/watchlist")
    if num_pages == -1:
        return [], "user_not_found"

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    future = asyncio.ensure_future(get_user_watchlist(username, num_pages=num_pages))
    loop.run_until_complete(future)

    return future.result(), "success"


if __name__ == "__main__":
    username = "Dcsoeirvy"
    print(get_watchlist_data(username))