#!/usr/bin/env -S pipenv run python3 -B

# SPDX-FileCopyrightText: 2023 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-FileCopyrightText: 2023 Andrew Ivanov <okolefleef@disr.it>
#
# SPDX-License-Identifier: ISC

# Python-Requires:
#   >=3.8
# Install-Requires:
#   orm[sqlite]
#   yarl
#   anyio
#   attrs
#   httpx
#   uvloop
#   aiocache
#   tgcrypto
#   Pyrogram
#   aiorwlock
#   databases
#   python-dotenv

import sys
import shlex
import logging
import subprocess

from weakref import WeakMethod
from contextlib import AsyncExitStack, asynccontextmanager
from collections import defaultdict, deque
from contextvars import ContextVar
from functools import lru_cache
from io import BytesIO, StringIO
from random import choice
# from re import DOTALL, search as re_search
from time import perf_counter
from traceback import format_exc
from typing import Optional

import anyio

from attrs import field, frozen, mutable, setters
from anyio import (
    Event,
    sleep,
    move_on_after,
    create_task_group,
)
from pyrogram import Client, enums, filters, idle, errors as pyrogram_errors, types as pyrogram_types
from playwright.async_api import async_playwright, Error as pw_Error

from config import get_env, Settings
from utils import Commands
from modules import (dd_message, host_info, limit_symbols, module_site, pretty_json, search, translate, tts, weather)


@mutable(eq=False)
class OrderLock:
    deep = field(kw_only=True, default=False)

    _queues = field(init=False, repr=False, on_setattr=setters.frozen)

    __event_var = field(init=False, repr=False, on_setattr=setters.frozen)
    __depth_var = field(init=False, repr=False, on_setattr=setters.frozen)

    @_queues.default
    def _(self, /):
        return defaultdict(deque)

    @__event_var.default
    def _(self, /):
        return ContextVar('__event_var', default=None)

    @__depth_var.default
    def _(self, /):
        return ContextVar('__depth_var', default=0)

    def __enter__(self, /):
        self.acquire()

        return self

    def __exit__(self, /, exc_type, exc_value, traceback):
        self.release()

    def acquire(self, /, *, force=False):
        if self._event is not None:
            if not force:
                return

        self._event = event = Event()

        self._queue.append(event)

    def release(self, /):
        if self._event is None:
            return

        event = self._event
        queue = self._queue

        if queue[0] is event:
            queue.popleft()

            if queue:
                queue[0].set()
            elif self.deep:
                del self._queue
        else:
            queue.remove(event)

        self._event = None

        if self.deep:
            self._depth += 1

    async def wait(self, /):
        if self.locked():
            await self._event.wait()

    def locked(self, /):
        event = self._event

        if event is None:
            return False

        if self._depth not in self._queues:
            return False

        queue = self._queue

        if queue[0] is event:
            return False

        return True

    @property
    def _queue(self, /):
        return self._queues[self._depth]

    @_queue.deleter
    def _queue(self, /):
        try:
            del self._queues[self._depth]
        except KeyError:
            raise AttributeError('_queue')

    @property
    def _event(self, /):
        return self.__event_var.get()

    @_event.setter
    def _event(self, /, value):
        self.__event_var.set(value)

    @property
    def _depth(self, /):
        return self.__depth_var.get()

    @_depth.setter
    def _depth(self, /, value):
        self.__depth_var.set(value)


class Capturing(list):
    """
    A context manager that captures the output of the executed code.
    """
    def __enter__(self):
        self._stdout = sys.stdout
        sys.stdout = self._stringio = StringIO()
        return self

    def __exit__(self, *args):
        self.extend(self._stringio.getvalue().splitlines())
        del self._stringio
        sys.stdout = self._stdout


class CommandHandler:
    def __init__(self, client: Client, message: pyrogram_types.Message, sessions: dict, config: Settings, orders):
        """
        Initialize a new CommandHandler instance.
        :param client: the Telegram API Client
        :param message: the incoming Telegram message
        """
        self.client = client
        self.message = message
        self.weather_session = sessions["weather_session"]
        self.tts_session = sessions["tts_session"]
        self.browser_session = sessions["browser_session"]
        self.config = config
        self.orders = orders

    @lru_cache(5)
    def _text_to_speech(self, /, text: str):
        return tts.synthesize_audio(self.tts_session, text, choice(('aidar', 'baya', 'kseniya', 'xenia')))

    async def limit_message(self, reply: bool = False, tti: bool = True, expire: int = 0) -> None:
        """
        Limit the message's symbol count and set an expiration time if specified.
        :param reply: whether to reply to the original message
        :param tti: whether to use Telegram's time-to-live feature
        :param expire: time in seconds for the message to be deleted, 0 for no expiration
        """

        await self.orders.wait()
        msg = await limit_symbols.limit_symbols_message(
            settings=self.config, browser_session=self.browser_session,
            message=self.message, client=self.client, reply=reply, tti=tti
        )
        if bool(expire):
            await sleep(expire)
            await msg.delete()

    async def ping(self) -> None:
        """
        Send a 'PONG' message.
        """
        self.message.text = '<strong>PONG</strong>'
        await self.limit_message()

    async def text_to_speech(self) -> None:
        """
        Convert text to speech and send the voice message.
        """
        message = self.message
        reply_to_message_id = None
        text = message.text

        if message.reply_to_message:
            reply_to_message_id = message.reply_to_message.id
            text = message.reply_to_message.text

        try:
            self.message.text = "<code>Converting text to voice...</code>"
            await self.limit_message(expire=5)

            start: float = perf_counter()
            voice = self._text_to_speech(text)
            await self.client.send_voice(chat_id=self.message.chat.id, voice=voice,
                                         reply_to_message_id=reply_to_message_id)

            self.message.text = f'<strong>Ping:</strong><code> {perf_counter() - start:f}s</code>'
        except (RuntimeError,):
            self.message.text = f'<strong>Error:</strong><code>\n{format_exc(0)}</code>'

        await self.limit_message(reply=True)

    async def shorten_url(self) -> None:
        """
        Shorten a URL.
        """
        message = self.message
        reply_message = message.reply_to_message
        url = reply_message.text if reply_message else message.text
        try:
            self.message.text = module_site.generate_short_link_for_url(url.strip())
        except BaseException as error:
            self.message.text = f"<strong>{error.__class__.__name__}!</strong>\n<code>{error}</code>"

        await self.limit_message()

    async def retrieve_url_statistics(self) -> None:
        """
        Retrieve statistics for a short URL.
        """
        message = self.message
        reply_message = message.reply_to_message
        url = reply_message.text if reply_message else message.text

        try:
            self.message.text = module_site.retrieve_usage_statistics_for_short_link(url.strip())
        except BaseException as error:
            self.message.text = f"<strong>{error.__class__.__name__}!</strong>\n<code>{error}</code>"

        await self.limit_message()

    async def host_information(self) -> None:
        """
        Retrieve information about the host.
        """
        text = self.message.text
        if text:
            output_host_info = host_info.full_info(type_output=text)
        else:
            output_host_info = host_info.full_info(type_output="all")

        await self.orders.wait()
        await self.message.edit(str(output_host_info))

    async def translate_text(self) -> None:
        """
        Translate text to a specified language
        """
        message = self.message
        options = {
            "q": message.text,
            "sl": "auto",
            "tl": "en"
        }

        if reply_message := message.reply_to_message:
            options["q"] = reply_message.text
            options["tl"] = "ru"

        self.message.text = await translate.translate(self.weather_session, options)
        await self.limit_message()

    async def ban_user(self) -> None:
        """
        Ban a user from the chat.
        """
        message = self.message
        cid = message.chat.id
        if reply := message.reply_to_message:
            from_user = reply.from_user
            uid = from_user.id if from_user else reply.sender_chat
        else:
            uid = message.text

        member = await self.client.get_chat_member(cid, uid)
        member_status = member.status

        if enums.ChatMemberStatus.BANNED == member_status:
            self.message.text = f"[User](tg://user?id={uid}) is already blocked in chat"
        else:
            try:
                await self.client.ban_chat_member(cid, uid)
                self.message.text = f"[User](tg://user?id={uid}) blocked"
            except (pyrogram_errors.UserNotParticipant, pyrogram_errors.UsernameNotOccupied):
                self.message.text = f"The [user](tg://user?id={uid}) is not a member of this chat "
            except pyrogram_errors.ChatAdminRequired:
                self.message.text = "The action requires admin privileges."

        await self.limit_message()

    async def unban_user(self) -> None:
        """
        Unban a user from the chat.
        """
        message = self.message
        cid = message.chat.id
        if reply := message.reply_to_message:
            from_user = reply.from_user
            uid = from_user.id if from_user else reply.sender_chat
        else:
            uid = message.text

        member = await self.client.get_chat_member(cid, uid)
        member_status = member.status

        if enums.ChatMemberStatus.BANNED != member_status:
            self.message.text = f"[User](tg://user?id={uid}) is already unblocked in chat"
        else:
            try:
                await self.client.unban_chat_member(cid, uid)
                self.message.text = f"[User](tg://user?id={uid}) unblocked"
            except (pyrogram_errors.UserNotParticipant, pyrogram_errors.UsernameNotOccupied):
                self.message.text = f"The [user](tg://user?id={uid}) is not a member of this chat "
            except pyrogram_errors.ChatAdminRequired:
                self.message.text = "The action requires admin privileges."

        await self.limit_message()

    async def delete_messages(self) -> None:
        """
        Delete messages in a chat based on the provided parameters.
        If the message is a reply, it will delete the replied message.
        If the message text contains a number, it will delete that number of messages.
        If the message text contains two words, the first being a number, it will delete that number of messages  \
            including the command message.

        :param self: The object of the class
        :type self: object
        :return: None
        """
        message, text = self.message, self.message.text
        text_split = text.split()
        options = {"reply": bool(getattr(message, "reply_to_message"))}

        if not text or len(text_split) > 2:
            return

        options["limit"] = int(text_split[0]) if text_split else None
        options["over"] = len(text_split) == 2

        self.message.text = await dd_message.start(self.client, message, **options)
        await message.delete()
        await self.limit_message(reply=True, expire=5)

    async def _weath(self, city: str, limit: int = 4) -> str:
        """
        Get the weather forecast for the given city.
        :param city: the city to get the forecast for
        :param limit: number of forecasts to return
        :return: the weather forecast
        """
        try:
            self.message.text = "<code>Parsing weather...</code>"
            await self.limit_message(tti=False)

            start = perf_counter()
            response_weather = await weather.get_response(session=self.weather_session, city=city)
            output_weather_ = weather.wrapper_data(json_string=response_weather, limit=limit)
            output_weather = f"{output_weather_}\n\n<code>Completed in: {perf_counter() - start:f}s</code>"
        except BaseException as error:
            output_weather = f"<strong>{error.__class__.__name__}!</strong>\n<code>{error}</code>"

        return output_weather

    async def weather(self) -> None:
        """
        Handle weather command
        """
        try:
            self.message.text = await self._weath(*self.message.text.split())
            expire = 0
        except TypeError:
            self.message.text = "<code>Error input value</code>"
            expire = 4

        await self.limit_message(expire=expire)

    async def _run_code(self, /) -> str:
        """
        Asynchronously execute the code in the message and return the code.

        :param self: an instance of the class containing the message to be executed
        :return: the code
        """
        code = '\n\t'.join(self.message.text.splitlines())
        exec_vars = {**locals()}
        exec(f'async def func():\n\t{code}', exec_vars, exec_vars)
        try:
            await exec_vars['func']()
            return code
        except Exception as e:
            raise e

    async def execute_python(self) -> None:
        """
        Asynchronously execute the given python code in the message, capturing the output and execution time.

        :return: None
        """
        try:
            start_time = perf_counter()
            with Capturing() as output_runcode:
                code = await self._run_code()

            execution_time = perf_counter() - start_time
            self.message.text = pretty_json.pretty_dumps({
                "Code": f"`{code}`",
                "\nExecution Output": "\n" + "\n".join(output_runcode),
                "\nExecution Time": f"`{execution_time:.6f}s`"

            })
            print(self.message.text)
        except Exception as error:
            self.message.text = f"<strong>{error.__class__.__name__}!</strong>\n<code>{error}</code>"

        await self.limit_message()

    async def execute_shell(self) -> None:
        """
        Executes a shell command and returns the result to the user.

        The method retrieves the shell command from the `message.text` attribute.
        If the command starts with a list of unauthorized commands \
            (`"rm", "unlink", "poweroff", "reboot", "shutdown"`), \
            the method sends a "Unauthorized stack" message to the user and returns.

        Otherwise, the method uses the `subprocess.run` method to execute the command and capture the output.
        The execution time is also measured and included in the result.
        The result is then formatted as a JSON string and stored in the `message.text` attribute.

        The method finally calls the `limit_message` method to send the result to the user.
        If an exception occurs during the execution, an error message is stored in the `message.text` \
        attribute and sent to the user.

        :return: None
        """
        try:
            code = self.message.text
            if code.startswith(("rm", "unlink", "poweroff", "reboot", "shutdown")):
                self.message.text = "Unauthorized stack"
                await self.limit_message()
                return None

            start_time = perf_counter()
            output_runcode = subprocess.run(
                shlex.split(code),
                input="",
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, check=True
            ).stdout
            execution_time = perf_counter() - start_time

            self.message.text = pretty_json.pretty_dumps({
                "<strong>Code<strong>": f"`{self.message.text}`",
                "\n<strong>Execution Output</strong>": f"\n `{output_runcode}`",
                "\n<strong>Execution Time</strong>": f"`{execution_time:.6f}s`"

            })
        except Exception as error:
            self.message.text = f"<strong>{error.__class__.__name__}!</strong>\n<code>{error}</code>"

        await self.limit_message()

    async def searchig(self) -> None:
        message = self.message
        if not message:
            return None

        await self.orders.wait()
        await message.edit("<strong>Fetching...</strong>")
        text = message.text.split("&")

        if not text or text[0] != "engines":
            self.message.text = await search.request(self.weather_session, *text)
        else:
            self.message.text = "<strong>Engines: </strong>\n" + " ".join(search.engines)

        await self.limit_message(tti=False)

    async def screen_2ip(self, proxy: str) -> Optional[BytesIO]:
        url = r"https://2ip.ru/privacy/"
        start = perf_counter()

        async with self.browser_session as p:
            browser = await p.chromium.launch()
            context = await browser.new_context(
                proxy=dict(server=proxy),
                geolocation=dict(latitude=0, longitude=0),
                locale="en-US",
                permissions=["geolocation"],
                timezone_id="Europe/Moscow",
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/109.0.5392.103 Safari/537.36"
            )
            page = await context.new_page()
            try:
                await page.goto(url)
            except pw_Error as er:
                self.message.text = f"<strong>Error:</strong>\n<code>{er.message.split(' ')[0]}</code>"
                await self.limit_message(expire=10)
                return None

            await page.get_by_role("button", name="Проверить").click()
            await page.locator("#spy table").wait_for()

            binary_image = await page.locator("#spy table").screenshot(type="jpeg", caret="initial", quality=100)
            binary_image = BytesIO(binary_image)
            if title := await page.title():
                url = f"[{title}]({url})"

            caption_screen = "\n".join([
                "<strong>[TEST APPLICATION | NON-STABLE]</strong>\n",
                f"<strong>Website:</strong> {url}",
                f"<strong>Completed in:</strong> {perf_counter() - start:2f}s",
                f"<strong>Proxy:</strong> {proxy}",
            ])

        await self.message.delete()
        await self.client.send_photo(chat_id=self.message.chat.id, photo=binary_image, caption=caption_screen)

    async def screen(self) -> None:
        message = self.message
        reply_message = message.reply_to_message
        url = reply_message.text if reply_message else message.text
        try:
            url, proxy = url.split(" ")
        except ValueError:
            url = url.lstrip()
            proxy = "socks5://127.0.0.1:9050"

        if url == "anon":
            self.message.text = "<strong>[TEST APPLICATION | NON-STABLE]</strong>\n<code>Anonymity check." \
                                "Wait approximately 10 seconds.</code>"
            await self.limit_message()
            await self.screen_2ip(proxy=proxy)
            await message.delete()
            return None

        if not url.startswith("http"):
            url = f"https://{url}"

        self.message.text = f"<code>Upload site screenshot: {url}...</code>"
        await self.limit_message()

        start = perf_counter()
        async with self.browser_session as p:
            browser = await p.chromium.launch(proxy=dict(server=proxy))
            context = await browser.new_context(
                proxy=dict(server=proxy),
                geolocation=dict(latitude=0, longitude=0),
                locale="en-US",
                permissions=["geolocation"],
                timezone_id="Europe/Moscow",
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/109.0.5392.103 Safari/537.36"
            )
            page = await context.new_page()
            try:
                await page.goto(url)
            except pw_Error as er:
                self.message.text = f"<strong>Error:</strong>\n`{er.message.split(' ')[0]}`"
                await self.limit_message(expire=10)
                return None

            binary_image = await page.screenshot(type="jpeg", caret="initial", quality=100)
            binary_image = BytesIO(binary_image)
            if title := await page.title():
                url = f"[{title}]({url})"

            caption_screen = "\n".join([
                f"<strong>Website:</strong> {url}",
                f"<strong>Completed in:</strong> {perf_counter() - start:2f}s",
                f"<strong>Proxy:</strong> {proxy}",
            ])

        await self.message.delete()
        await self.client.send_photo(chat_id=message.chat.id, photo=binary_image, caption=caption_screen)

    #
    # async def rewrite_code(self) -> None:
    #     await self.orders.wait()
    #     await self.message.edit("<code>We work with code. This may take up to 30 seconds.</code>")
    #     if reply_message := self.message.reply_to_message:
    #         text = self.message.text
    #         code_text = reply_message.text
    #
    #         if not text or not code_text:
    #             self.message.text = "<code>Please provide the code or text to be processed.</code>"
    #             await self.limit_message()
    #             return None
    #
    #         if re_search(r"Completed in:", code_text):
    #             if code_match := re_search(r"Code:\n(.+?)\nPrompt:", code_text, DOTALL):
    #                 code_text = code_match.group(1)
    #     else:
    #         self.message.text = "Only reply-mod"
    #         await self.limit_message()
    #         return None
    #
    #     start = perf_counter()
    #     model_name = "code-davinci-edit-001"
    #     response = Edit.create(
    #         model=model_name,
    #         input=code_text,
    #         instruction=text,
    #         temperature=0,
    #         top_p=1
    #     )
    #     code_result = "".join(response["choices"][0]["text"]).lstrip()
    #     self.message.text = f"<strong>Here is the modified code using the model ({model_name}).</strong>\n\n" \
    #                         f"<strong>Code:\n</strong><code>{code_result}</code>\n\n" \
    #                         f"<strong>Prompt:\n</strong><code>{text}</code>\n\n\n" \
    #                         f"<strong>Completed in:</strong> {perf_counter() - start:2f}s"
    #     await self.limit_message()
    #
    # async def generate_code(self) -> None:
    #     await self.message.edit("<code>Code is being generated. This may take up to 30 seconds</code>")
    #
    #     start = perf_counter()
    #     text = self.message.text
    #     model_name = "text-davinci-003"
    #     response = Completion.create(
    #         model=model_name,
    #         prompt=text,
    #         temperature=0.7,
    #         max_tokens=256,
    #         top_p=1,
    #         frequency_penalty=0,
    #         presence_penalty=0
    #     )
    #     code = "".join(response["choices"][0]["text"]).lstrip()
    #     self.message.text = f"<strong>Here is the generated code using the model ({model_name}).</strong>\n\n" \
    #                         f"<strong>Code:\n</strong><code>{code}</code>\n\n" \
    #                         f"<strong>Prompt:\n</strong><code>{text}</code>\n\n\n" \
    #                         f"<strong>Completed in:</strong> {perf_counter() - start:2f}s"
    #     await self.limit_message()


@frozen(eq=False)
class ChatBot:
    app = field()
    config = field()
    sessions = field()
    orders = field(init=False, repr=False)
    tasks = field(init=False, repr=False, factory=create_task_group)
    stack = field(init=False, repr=False, factory=AsyncExitStack)
    writers = field(init=False, repr=False)

    @orders.default
    def _(self, /):
        return defaultdict(OrderLock)

    @writers.default
    def _(self, /):
        return defaultdict(dict)

    def __init__(self, /, config, sessions, *args, **kwargs):
        self.__attrs_init__(Client(*args, **kwargs), config, sessions)

    def __attrs_post_init__(self, /):
        @self.app.on_message(
            filters.create(self.is_relevant_message)
        )
        async def _(*args, func=WeakMethod(self.on_message)):
            await func()(*args)

    async def __aenter__(self, /):
        stack = await self.stack.__aenter__()

        try:
            for obj in self.to_stack:
                await stack.enter_async_context(obj)
        except:
            if not await self.stack.__aexit__(*sys.exc_info()):
                raise

        return self

    async def __aexit__(self, /, exc_type, exc_value, traceback):
        print("Exiting program...")
        await self.sessions["weather_session"].aclose()

        return await self.stack.__aexit__(exc_type, exc_value, traceback)

    @staticmethod
    def is_relevant_message(_, __, m: pyrogram_types.Message) -> bool:
        if m.text is not None and isinstance(m.text, str):
            try:
                first_char = m.text[0]
            except UnicodeDecodeError:
                return False
        else:
            return False

        return all([
            m.from_user and m.from_user.is_self or getattr(m, "outgoing", False),
            first_char in "./!*"
        ])

    @staticmethod  # !!!
    async def check_group_type(message):
        if message.chat.type != enums.ChatType.SUPERGROUP:
            # await message.reply("Меня могут тестировать только администраторы в супер группе")
            return False

        return True

    @staticmethod
    def format_text(text, message):
        prefix = text.lstrip("/").split()[0][1:]
        message.text = text[len(prefix) + 1:].strip()
        try:
            return getattr(Commands, prefix)
        except AttributeError:
            return None

    async def on_message(self, /, client, message):
        cid = message.chat.id
        text = message.text

        with self.orders[cid]:
            async with self.writing(cid):
                command = self.format_text(text, message)
                if command is None:
                    return None


                try:
                    print(command)
                    await getattr(
                        CommandHandler(client, message, self.sessions, self.config, self.orders[cid]),
                        command.value
                    )()
                except Exception as error:
                    await self.orders[cid].wait()
                    await message.reply(f"<strong>{error.__class__.__name__}!</strong>\n<code>{error}</code>")
                    # await message.reply(f"<strong>АйУтка!</strong>\n<code>{error}</code>")
                    print('exception')

                if self.writers[cid].get('count'):
                    await self.app.send_chat_action(
                        cid,
                        enums.ChatAction.TYPING,
                    )

    async def progress(self, /, chat_id, event):
        info = self.writers[chat_id]

        try:
            while not event.is_set():
                await self.app.send_chat_action(
                    chat_id,
                    enums.ChatAction.TYPING,
                )

                with move_on_after(3):
                    await event.wait()
        finally:
            del info['event']
            del info['count']

            await self.app.send_chat_action(
                chat_id,
                enums.ChatAction.CANCEL,
            )

    @asynccontextmanager
    async def writing(self, /, chat_id):
        info = self.writers[chat_id]

        event = info.setdefault('event', Event())
        count = info.setdefault('count', 0)

        info['count'] = count = count + 1

        if count == 1:
            self.tasks.start_soon(self.progress, chat_id, event)

        try:
            yield
        finally:
            if 'count' in info:
                count = info['count']

                info['count'] = count = count - 1

                if not count:
                    event.set()

    @property
    def to_stack(self, /):
        yield self.app
        yield self.tasks


async def async_main():
    config = get_env()
    if config.DEBUG:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(filename='logs/error.log', level=logging.ERROR)

    if not all([
        config.SESSION_NAME, config.PLUGINS, config.TG_APP_ID, config.TG_APP_HASH
    ]) or sys.version_info[:3] < (3, 8, 0):
        raise ValueError("Missing required settings or unsupported Python version")

    sessions = dict(
        weather_session=weather.create_session(),
        tts_session=tts.load_model(),
        browser_session=async_playwright()
    )
    bot = ChatBot(
        config=config,
        sessions=sessions,
        name=str(config.SESSION_NAME),
        api_id=config.TG_APP_ID,
        api_hash=config.TG_APP_HASH.get_secret_value(),
    )
    async with bot:
        await idle()


def main():
    anyio.run(
        async_main,
        backend='asyncio',
        backend_options={
            'use_uvloop': True
        }
    )


if __name__ == '__main__':
    sys.exit(main())
