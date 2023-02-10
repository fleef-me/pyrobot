#!/usr/bin/env python3

# Copyright 2021 Andrew Ivanov <okolefleef@disr.it>
# All rights reserved

from pyrogram import Client, types
from pyrogram.errors import (
    ChatAdminRequired, MessageIdInvalid
)


async def start(client: Client, message: types.Message, limit: int = 10, over=True, reply: bool = False):
    """
    Delete messages in a chat based on the provided parameters.
    If the message is a reply, it will delete the replied message.
    If the message text contains a number, it will delete that number of messages.
    If the message text contains two words, the first being a number, it will delete that number of messages including the command message.

    :param client: an instance of the pyrogram client                 :type client: Client
    :param message: the incoming message object                       :type message: types.Message
    :param limit: the number of messages to be deleted, default is 10 :type limit: int
    :param over: a boolean value indicating whether to delete the command message along with the other messages,
    default is True
    :type over: bool
    :param reply: a boolean value indicating whether to delete the replied message, default is False :type reply: bool
    :return: result message :rtype: str
    """
    cid = message.chat.id
    messages_ids = []
    async for message in client.get_chat_history(chat_id=cid, limit=limit):
        if not over and reply and message.from_user.id == message.reply_to_message.from_user.id:
            messages_ids.append(message.id)
        elif not over and not reply and message.from_user.is_self:
            messages_ids.append(message.id)
        elif over:
            messages_ids.append(message.id)

    if not messages_ids:
        return "No messages to delete."

    revoke = False
    deleted_count = len(messages_ids)
    result = "Error occurred"
    if deleted_count:
        try:
            result = f"Deleted {deleted_count} messages"
        except ChatAdminRequired:
            revoke = True
            result = f"Deleted {deleted_count} messages for myself"
        except MessageIdInvalid:
            revoke = True
            result = f"[MessageIdInvalid]: Deleted ~{deleted_count} messages for myself"

    await client.delete_messages(chat_id=cid, message_ids=messages_ids, revoke=revoke)
    return result


#
# async def start(client, message, limit: int = 10, over=True, reply: bool = False):
#     if reply:
#         from_uid = message.reply_to_message.from_user.id
#
#     cid = message.chat.id
#     messages_ids = []
#     async for message in client.get_chat_history(chat_id=cid, limit=limit):
#         # TODO: Многочисленные проверки по условиям, честно хз как это разобрать, оставить на потом
#         if not over and reply \
#                 and message.from_user.id == from_uid \
#                 or not over and not reply \
#                 and message.from_user.is_self \
#                 or over:
#
#             mid = message.id
#             messages_ids.append(mid)
#
#     revoke = False
#     if len_mids := len(messages_ids):
#         try:
#             result = f"Deleted {len_mids} messages"
#         except ChatAdminRequired:
#             revoke = True
#             result = f"Deleted {len_mids} messages for myself"
#         except MessageIdInvalid:
#             revoke = True
#             result = f"[MessageIdInvalid]: Deleted ~{len_mids} messages for myself"
#
#     await client.delete_messages(chat_id=cid, message_ids=messages_ids, revoke=revoke)
#     return result
