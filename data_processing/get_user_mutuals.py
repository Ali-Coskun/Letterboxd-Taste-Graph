import asyncio
import sys
from pathlib import Path
import re

from aiohttp import ClientSession, TCPConnector, ClientTimeout
from bs4 import BeautifulSoup

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data_processing.utils.http_utils import BROWSER_HEADERS, default_request_timeout


async def fetch(url: str, session: ClientSession) -> bytes | None:
    try:
        async with session.get(url, timeout=ClientTimeout(total=default_request_timeout)) as r:
            return await r.read()
    except Exception:
        return None


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

    # fallback: rel="last"
    last = soup.select_one('link[rel="last"]')
    if last and last.get("href"):
        m = re.search(r"/page/(\d+)/", last["href"])
        if m:
            return int(m.group(1))

    return 1


def parse_people_page(html: bytes) -> list[str]:
    """
    Extract usernames from a followers/following page.
    Tries table links first, then a general fallback.
    """
    soup = BeautifulSoup(html, "lxml")
    usernames: set[str] = set()

    # Common Letterboxd markup: "person-table"
    for a in soup.select("table a[href^='/'][href$='/']"):
        href = a.get("href", "")
        if href.count("/") == 2:  # "/username/"
            usernames.add(href.strip("/"))

    # Fallback if markup differs
    if not usernames:
        for a in soup.select("a[href^='/'][href$='/']"):
            href = a.get("href", "")
            if href.count("/") == 2:
                usernames.add(href.strip("/"))

    return sorted(usernames)


async def get_all_people(username: str, kind: str) -> list[str]:
    """
    kind: "followers" or "following"
    """
    if kind not in {"followers", "following"}:
        raise ValueError("kind must be 'followers' or 'following'")

    base = f"https://letterboxd.com/{username}/{kind}/"

    async with ClientSession(headers=BROWSER_HEADERS, connector=TCPConnector(limit=6)) as session:
        first_html = await fetch(base, session)
        if not first_html:
            return []

        if b"Page not found" in first_html:
            return []

        num_pages = get_page_count_from_html(first_html)

        # page 1 is base; subsequent pages are /page/N/
        tasks = [fetch(base, session)]
        for p in range(2, num_pages + 1):
            tasks.append(fetch(f"https://letterboxd.com/{username}/{kind}/page/{p}/", session))

        pages = await asyncio.gather(*tasks)

    people: set[str] = set()
    for html in pages:
        if html:
            people.update(parse_people_page(html))

    return sorted(people)


async def get_followers(username: str) -> list[str]:
    return await get_all_people(username, "followers")


async def get_following(username: str) -> list[str]:
    return await get_all_people(username, "following")


def get_mutuals(followers: list[str], following: list[str]) -> list[str]:
    """Intersection of followers + following."""
    return sorted(set(followers) & set(following))


async def get_mutuals_for_user(username: str) -> tuple[list[str], list[str], list[str]]:
    """
    Returns (followers, following, mutuals)
    Fetches followers+following concurrently.
    """
    followers, following = await asyncio.gather(
        get_followers(username),
        get_following(username),
    )
    mutuals = get_mutuals(followers, following)
    return followers, following, mutuals


if __name__ == "__main__":
    username = "Dcsoeirvy"

    followers, following, mutuals = asyncio.run(get_mutuals_for_user(username))

    print(f"followers_count: {len(followers)}")
    # for u in followers: print(u)

    print(f"following_count: {len(following)}")
    # for u in following: print(u)

    print(f"mutuals_count: {len(mutuals)}")
    for u in mutuals:
        print(u)