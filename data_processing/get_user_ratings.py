#!/usr/local/bin/python3.12

import asyncio
import sys
from pathlib import Path
from itertools import chain

from aiohttp import ClientSession, TCPConnector, ClientTimeout
from bs4 import BeautifulSoup

# Make project imports work whether executed from repo root or elsewhere
PROJECT_ROOT = Path(__file__).resolve().parents[1]  # .../Letterboxd Taste Comparer
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data_processing.utils.http_utils import BROWSER_HEADERS, default_request_timeout
from data_processing.utils.selectors import LBX_REVIEW_TILE
from data_processing.utils.utils import get_page_count


LBX_BASE = "https://www.letterboxd.com"


async def fetch(url, session, input_data=None):
    if input_data is None:
        input_data = {}
    async with session.get(url, timeout=ClientTimeout(total=default_request_timeout)) as response:
        try:
            return await response.read(), input_data
        except Exception:
            return None, None


def _parse_rating_from_class(class_list) -> float:
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
    if not text:
        return -1
    t = text.strip()
    if "★" not in t:
        return -1
    stars = t.count("★")
    if "½" in t:
        stars += 0.5
    return stars


def _normalize_possible_fraction(val: float) -> float:
    try:
        if 0 <= val <= 1:
            return round(val * 5, 1)
    except Exception:
        pass
    return val


async def parse_ratings_page(response):
    if not response or not response[0]:
        return []

    soup = BeautifulSoup(response[0], "lxml")
    tiles = soup.find_all(*LBX_REVIEW_TILE)

    out = []
    for tile in tiles:
        poster_rc = tile.select_one('div.react-component[data-component-class="LazyPoster"]')
        if not poster_rc:
            continue

        movie_id = poster_rc.get("data-item-slug") or poster_rc.get("data-film-slug")
        if not movie_id:
            continue

        display_name = (
            poster_rc.get("data-item-full-display-name")
            or poster_rc.get("data-item-name")
            or movie_id
        )

        rating_val = -1

        rating_el = tile.select_one("span.rating[class*='rated-']")
        if not rating_el:
            rating_el = tile.select_one("span.rating")

        if rating_el:
            rating_val = _parse_rating_from_class(rating_el.get("class", []))
            if rating_val == -1:
                rating_val = _parse_rating_text(rating_el.get_text(" ", strip=True))

        if rating_val == -1:
            vd = tile.select_one(".poster-viewingdata, p.poster-viewingdata")
            if vd:
                rating_val = _parse_rating_text(vd.get_text(" ", strip=True))

        rating_val = _normalize_possible_fraction(rating_val)

        liked = False
        if tile.select_one(".liked") or tile.select_one("span.like") or tile.select_one(".icon-liked"):
            liked = True

        out.append(
            {
                "movie_id": movie_id,
                "display_name": display_name,
                "rating_val": rating_val,
                "liked": liked
            }
        )

    return out


# ✅ CHANGED: reviews page parser no longer uses LBX_REVIEW_TILE
async def parse_reviewed_films_page(response):
    """
    Parse a /films/reviews/ page and return a set of film slugs the user has reviewed.

    ✅ Uses LazyPoster components directly because /films/reviews/ markup
    doesn't always match LBX_REVIEW_TILE.
    """
    if not response or not response[0]:
        return set()

    soup = BeautifulSoup(response[0], "lxml")

    reviewed = set()
    for rc in soup.select('div.react-component[data-component-class="LazyPoster"]'):
        slug = rc.get("data-item-slug") or rc.get("data-film-slug")
        if slug:
            reviewed.add(slug)

    return reviewed


async def get_user_ratings(username: str, num_pages: int, session: ClientSession):
    url = f"{LBX_BASE}/{{}}/films/ratings/page/{{}}/"
    tasks = [
        asyncio.ensure_future(fetch(url.format(username, i + 1), session, {"username": username}))
        for i in range(num_pages)
    ]
    scrape_responses = await asyncio.gather(*tasks)
    scrape_responses = [x for x in scrape_responses if x and x[0]]

    parse_tasks = [asyncio.ensure_future(parse_ratings_page(r)) for r in scrape_responses]
    parse_responses = await asyncio.gather(*parse_tasks)
    return list(chain.from_iterable(parse_responses))


async def get_user_reviewed_films_set(username: str, session: ClientSession) -> set[str]:
    # ✅ CHANGED: still uses get_page_count, but parsing is now robust
    num_pages, _ = get_page_count(username, url=f"{LBX_BASE}/{{}}/films/reviews")
    if num_pages == -1:
        return set()

    # Always fetch page 1 via the base URL
    page_urls = [f"{LBX_BASE}/{username}/films/reviews/"]
    for p in range(2, num_pages + 1):
        page_urls.append(f"{LBX_BASE}/{username}/films/reviews/page/{p}/")

    tasks = [
        asyncio.ensure_future(fetch(u, session, {"username": username, "page": idx + 1}))
        for idx, u in enumerate(page_urls)
    ]
    scrape_responses = await asyncio.gather(*tasks)
    scrape_responses = [x for x in scrape_responses if x and x[0]]

    parse_tasks = [asyncio.ensure_future(parse_reviewed_films_page(r)) for r in scrape_responses]
    reviewed_sets = await asyncio.gather(*parse_tasks)

    reviewed = set()
    for s in reviewed_sets:
        reviewed |= s
    return reviewed


async def get_user_ratings_enriched(username: str):
    num_pages, _ = get_page_count(username, url=f"{LBX_BASE}/{{}}/films/ratings")
    if num_pages == -1:
        return [], "user_not_found"

    connector = TCPConnector(limit=6, ttl_dns_cache=3600)

    async with ClientSession(headers=BROWSER_HEADERS, connector=connector) as session:
        ratings_task = asyncio.create_task(get_user_ratings(username, num_pages=num_pages, session=session))
        reviewed_task = asyncio.create_task(get_user_reviewed_films_set(username, session=session))

        films, reviewed_set = await asyncio.gather(ratings_task, reviewed_task)

    for f in films:
        f["has_review"] = f["movie_id"] in reviewed_set

    return films, "success"


def get_ratings_data(username: str):
    return asyncio.run(get_user_ratings_enriched(username))


if __name__ == "__main__":
    username = "Dcsoeirvy"
    films, status = get_ratings_data(username)

    print(status)
    for film in films:
        print(
            f'{film["display_name"]} | '
            f'slug={film["movie_id"]} | '
            f'rating={film["rating_val"]} | '
            f'liked={film["liked"]} | '
            f'reviewed={film["has_review"]}'
        )