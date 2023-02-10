#!/usr/bin/env python3

# Copyright 2022 Andrew Ivanov <okolefleef@disr.it>
# All rights reserved


from __future__ import annotations
from typing import List, Tuple

from pydantic import BaseModel
from httpx import AsyncClient

from config import get_env, Settings


__all__ = ('request', 'engines', )
settings: Settings = get_env()
url = settings.MODULES_SEARCH_HOST
engines: Tuple = (
    'bing_images', 'mediawiki', 'searchcode_code', 'yahoo_news',
    'semantic_scholar', 'btdigg', 'nyaa', '1337x', 'bing_news',
    'reddit', 'startpage', 'apkmirror', 'bandcamp', 'genius',
    'wolframalpha_noapi', 'torrentz', 'youtube_noapi', 'archlinux',
    'vimeo', 'sepiasearch', 'fdroid', 'piratebay', 'soundcloud',
    'bing', 'frinkiac', 'ina', 'google_videos', 'openstreetmap',
    'pdbe', 'rumble', 'openverse', 'ebay', 'tvmaze', 'mediathekviewweb',
    'onesearch', 'mixcloud', 'duckduckgo', 'bing_videos', 'duckduckgo_images',
    'pubmed', 'yahoo', 'github', 'microsoft_academic', 'digg',
    'google_images', 'tineye', 'google_scholar', 'framalibre',
    'duckduckgo_definitions', 'xpath', 'currency_convert', 'gentoo',
    'translated', 'unsplash', 'json_engine', 'invidious', 'google', 'kickass',
    'etools', 'dictzone', 'photon', 'yggtorrent', 'deezer', 'duden', 'seznam',
    'gigablast', 'deviantart', 'wikidata',
    'tokyotoshokan', 'flickr_noapi', 'peertube',
    'qwant', 'stackexchange', 'imdb', 'wordnik', 'loc', 'www1x',
    'solidtorrents', 'google_news', 'sjp', 'wikipedia', 'dailymotion', 'arxiv'
)


class Result(BaseModel):
    title: str
    content: str
    url: str
    engine: str
    parsed_url: List[str]
    engines: List[str]
    positions: List[int]
    score: float
    category: str
    pretty_url: str


class Model(BaseModel):
    query: str
    number_of_results: int
    results: List[Result]
    answers: List
    corrections: List
    infoboxes: List
    suggestions: List
    unresponsive_engines: List


async def request(session: AsyncClient, query: str, count_results: int = 3, engine: str = "duckduckgo"):
    if engine not in engines:
        raise RuntimeError("This engine is not found")

    if not query:
        raise RuntimeError("Specify a request")

    def_params = dict(
        category_general="1",
        q=query,
        language="ru-RU",
        format='json',
        engines=engine
    )
    response = await session.get(url, params={**def_params})
    text_result_ = response.text

    pretty_result = []
    for _, result in zip(range(int(count_results)), Model.parse_raw(text_result_).results):
        content = result.content[:30]
        pretty_result.append(f"-> [{content}...]({result.pretty_url})")

    return f"<strong>Engine:</strong> {engine}\n\n" + "\n".join(pretty_result) if pretty_result \
        else f"<strong>Engine:</strong> {engine}\n<strong>Result:</strong> Nothing found"



# if __name__ == '__main__':
#     session = urllib3.PoolManager()
#
#     text = input("Text:\n -> ").split("&")
#     print(text)
#
#     results = request(session, *text)
#     print(results)
