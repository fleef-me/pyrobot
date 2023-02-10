#!/usr/bin/env python3

# Copyright 2021 Andrew Ivanov <okolefleef@disr.it>
# All rights reserved

from httpx import AsyncClient, AsyncHTTPTransport, Timeout
from lxml.html import fromstring, HtmlElement


def create_session() -> AsyncClient:
    return AsyncClient(
        http2=True,
        transport=AsyncHTTPTransport(retries=2),
        timeout=Timeout(10.0, connect=30.0)
    )


async def translate(session: AsyncClient, options: dict) -> HtmlElement:
    response = await session.get("https://translate.google.com/m", params=options)
    text_translate = fromstring(response.text).find_class("result-container")[0].text_content()

    return text_translate


# # ex:
# if __name__ == "__main__":
#     import anyio
#     session = create_session()
#     output = anyio.run(translate, session, dict(q='text', sl='auto', tl='ru'), backend='trio')
#     print(output)


# def test(tree):
#     tree.xpath("//div[@class='result-container']")[0].text_content()
#     #tree.find_class("result-container")[0].text_content()
#
# async def main():
#     options = {
#         "q": "Чтобы это работало, вы должны быть администратором супергруппы и иметь соответствующие права администратора.",
#         "sl": "auto",
#         "tl": "en"
#         }
#     session = create_session()
#
#     tree = await translate(session, options)
#     await session.close()
#
#     print("""**# Number of calls per lap:** ```1000```
# **# Total calls:** ```100000```""")
#     print()
#
#     timeit_average_value_list = []
#     for c in range(0, 101):
#         output_timeit = timeit(lambda: test(tree), number=1000)
#         print(f"{c}: {output_timeit}")
#         timeit_average_value_list.append(output_timeit)
#
#     print()
#     print(f"**# Average value:**```{sum(timeit_average_value_list) / len(timeit_average_value_list)}```")
#
#
# if __name__ == "__main__":
#     import asyncio
#
#     asyncio.run(main())
