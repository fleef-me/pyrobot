#!/usr/bin/env python3
# Copyright 2022 Andrew Ivanov <okolefleef@disr.it>
# All rights reserved

from pathlib import Path
from typing import Union

from pyrogram import Client, types
from pyrogram.types.messages_and_media.message import Message
from markdown import markdown
from PIL import Image, ImageChops
from playwright.async_api._context_manager import PlaywrightContextManager as PWContextManager

from config import Settings
from modules.pretty_json import pretty_dumps


def gen_html(html_path: Path, text: str) -> bool:
    html_text_ = markdown(text).replace('\n', '<br>')
    html_text = f"<div class='iban'>{html_text_}</div>"

    with open(html_path, 'w') as outfile:
        outfile.write(html_text)

    return html_path.is_file() or False


async def gen_pictures(browser_session: PWContextManager, image_path: Path, html_path: Path) -> bool:
    async with browser_session as p:
        browser = await p.chromium.launch(proxy=dict(server="socks5://127.0.0.1:8443"))
        page = await browser.new_page()

        await page.goto(f"file://{html_path}")
        await page.screenshot(path=image_path, type="jpeg", caret="initial", quality=100, full_page=True)

    return image_path.is_file() or False


def crop_image(image_path: Path) -> bool:
    im = Image.open(image_path)
    bg = Image.new(im.mode, im.size, im.getpixel((0, 0)))

    diff_ = ImageChops.difference(im, bg)
    diff = ImageChops.add(diff_, diff_)

    if box := diff.getbbox():
        im.crop(box).save(image_path)

        return True
    return False


async def limit_symbols_message(
            settings: Settings(), browser_session: PWContextManager,
            message: Message, client: Client, reply: bool = False, tti: bool = True) -> Union[Message, None]:

    text = message.text
    if not text:
        raise RuntimeError("text is None")
    if not isinstance(text, str):
        if isinstance(text, (dict, types.Message)):
            text = pretty_dumps(text)
        else:
            text = str(text)

    if not tti:
        return await message.edit(text, disable_web_page_preview=True)

    if len(text.replace(" ", "")) <= 700:
        if reply:
            return await message.reply(text, disable_web_page_preview=True)
        else:
            return await message.edit(text, disable_web_page_preview=True)

    image_path = settings.IMAGE_LIMITER_PATH
    html_path = settings.HTML_LIMITER_PATH

    gen_html(html_path=html_path, text=text)
    await gen_pictures(browser_session=browser_session, image_path=image_path, html_path=html_path)
    crop_image(image_path=image_path)

    await message.edit("<code>The length of the text exceeds the allowed limit \U0001F447</code>")
    return await client.send_document(chat_id=message.chat.id, document=image_path)

