import re
import time
from dataclasses import dataclass
from typing import Optional

import requests
from bs4 import BeautifulSoup

LB_FILM_URL = "https://letterboxd.com/film/{slug}/"

TMDB_RE = re.compile(r"themoviedb\.org/(movie|tv)/(\d+)")

