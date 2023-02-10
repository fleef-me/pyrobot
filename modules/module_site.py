#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright 2022 Andrew Ivanov <okolefleef@disr.it>
# All rights reserved

"""
This script is designed to generate short versions of URL links and track their usage statistics.
It uses the `urllib3` library to parse URL links and the `Hashids` library to generate unique short IDs.
The script also uses the `sqlite3` library to store original URL links and their usage statistics in a database.
The database schema is defined in the `config.py` module.

The script has the following functions:
 - generate_short_link_for_url(url: str) -> str: generates a short link for the provided URL.
 - retrieve_usage_statistics_for_short_link(url: str) -> str: retrieves the usage statistics for the provided short link.

Example usage:
 - Generate short link for the URL https://www.example.com:
   short_link = generate_short_link_for_url("https://www.example.com")
 - Retrieve usage statistics for the short link:
   stats = retrieve_usage_statistics_for_short_link(short_link)

The script requires the `urllib3`, `hashids`, and `sqlite3` libraries to be installed.
To install them, run the following commands:
 - pip install urllib3
 - pip install hashids
 - pip install sqlite3

To run the script, use the following command:
 - python module_site.py
"""


import sqlite3
import re
from typing import Union

from urllib import parse
from hashids import Hashids

from config import get_env, Settings
from modules.pretty_json import pretty_dumps


__all__ = (
    "generate_short_link_for_url",
    "retrieve_usage_statistics_for_short_link",
)

MIN_SHORT_LINK_LEN = 4

SETTINGS: Settings = get_env()
hashids = Hashids(min_length=MIN_SHORT_LINK_LEN, salt=SETTINGS.MODULE_SITE_SALT.get_secret_value())


def insert_url_into_database(url: str) -> int:
    """Insert a url into the database and return the id.
    Arguments:
        url (str): The url to insert into the database.
    Returns:
        int: The id of the inserted url.
    Raises:
        RuntimeError: If there is an error inserting the url into the database.
    """

    try:
        with sqlite3.connect(SETTINGS.MODULE_SITE_DATABASE_MY_SITE_PATH) as connect:
            connect.row_factory = sqlite3.Row
            cursor = connect.cursor()
            cursor.execute("INSERT INTO urls (original_url) VALUES (?)", (url,))

        return cursor.lastrowid

    except sqlite3.Error as error:
        raise RuntimeError(f"(insert_url_into_database) Database error: {error}") from error

def select_url_by_id_from_database(original_id: int) -> sqlite3.Row:
    """Retrieve a row from the database by id.
    Arguments:
        original_id (int): The id of the row to retrieve.
    Returns:
        sqlite3.Row: A row object representing the retrieved data.
    Raises:
        RuntimeError: If there is an error retrieving the row from the database.
    """

    try:
        with sqlite3.connect(SETTINGS.MODULE_SITE_DATABASE_MY_SITE_PATH) as connect_:
            connect_.row_factory = sqlite3.Row
            with connect_ as cursor:
                row = cursor.execute(
                    'SELECT original_url, clicks FROM urls WHERE id = (?)',
                    (original_id,)
                ).fetchone()
                if row is None:
                    raise RuntimeError("ID not found in the database")
                return row

    except sqlite3.Error as error:
        raise RuntimeError(f"(select_url_by_id_from_database) Database error: {error.args}") from error

def select_url_by_url_from_database(url: str) -> Union[sqlite3.Row, None]:
    """Retrieve a row from the database by url.
    Arguments:
        url (str): The url of the row to retrieve.
    Returns:
        sqlite3.Row: A row object representing the retrieved data.
        None: If the row was not found in the database.
    Raises:
        RuntimeError: If there is an error retrieving the row from the database.
    """

    try:
        with sqlite3.connect(SETTINGS.MODULE_SITE_DATABASE_MY_SITE_PATH) as connect_:
            connect_.row_factory = sqlite3.Row
            with connect_ as cursor:
                row = cursor.execute(
                    'SELECT original_url, clicks, id FROM urls WHERE original_url = (?)',
                    (url,)
                ).fetchone()
                if row is None:
                    return False
                    # raise RuntimeError("URL not found in the database")
                return row

    except sqlite3.Error as error:
        raise RuntimeError(f"(select_url_by_url_from_database) Database error: {error.args}") from error


def generate_short_link_for_url(url: str) -> str:
    """Generate a shortened url for a given url.
    Arguments:
        url (str): The url to shorten.
    Returns:
        str: The shortened url.
    Raises:
        ValueError: If the url is invalid.
        urllib3.exceptions.ConnectionError: If the url is invalid or there is an error parsing it.
        RuntimeError: If there is an error inserting the url into the database or
                     if the url stored in the database does not match the provided url.
    """

    try:
        if not url.startswith(("https", "http")):
            url = f"https://{url}"

        if re.search(r'\.[a-zA-Z]{2,}$', url) is None:
            raise ValueError("Invalid link provided")

    except BaseException as _error:
        raise RuntimeError(f"<strong>{_error.__class__.__name__}!</strong>\n<code>{_error}</code>") from _error

    if original_url_raw := select_url_by_url_from_database(url):
        original_url, clicks, url_id = original_url_raw
        if original_url == url:
            url_path = hashids.encode(url_id)
        else:
            raise RuntimeError("Invalid database url provided")
    else:
        url_path = hashids.encode(insert_url_into_database(url))

    return SETTINGS.MODULE_SITE_HOST + url_path

def retrieve_usage_statistics_for_short_link(url: str) -> str:
    """Retrieve statistic data for a shortened url.
    Arguments:
        url (str): The shortened url.
    Returns:
        str: A JSON-formatted string with statistic data.
    Raises:
        ValueError: If the url is invalid.
        RuntimeError: If there is an error retrieving the row from the database.
    """

    host = SETTINGS.MODULE_SITE_HOST
    if not url.startswith(host):
        raise ValueError("Invalid link provided")

    hashid = hashids.decode(url.replace(host, ""))[0]
    url_data = select_url_by_id_from_database(original_id=hashid)

    return pretty_dumps({
        "<strong>Short URL</strong>": url,
        "<strong>Original URL</strong>": url_data[0],
        "<strong>Clicks</strong>": url_data[1],
    })


if __name__ == "__main__":
    raise RuntimeError("This code is an additional module to the «UserBOT for Telegram» project and"
                       " it does not support launching directly.")
