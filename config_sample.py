#!/usr/bin/env python3

# Copyright 2022 Andrew Ivanov <okolefleef@disr.it>
# All rights reserved

from pathlib import Path

from pydantic import BaseSettings, SecretStr

path: Path = Path(__file__).resolve().parent


class Settings(BaseSettings):
    TG_APP_ID:              int
    PLUGINS:                dict  # ex: = {"root": "plugins"}
    DEBUG:                  bool = False

    # MODULES_WEATHER_URL:    str
    # MODULE_SITE_HOST:       str
    MODULE_SITE_HOST:       str  # = "https://example.com/"
    MODULES_WEATHER_URL:    str = "http://api.openweathermap.org/data/2.5/forecast"
    MODULES_SEARCH_HOST:    str  # = "http://example.com/search?"

    OPENAI_API_KEY:         SecretStr
    TG_APP_HASH:            SecretStr
    MODULES_WEATHER_TOKEN:  SecretStr
    MODULE_SITE_SALT:       SecretStr

    HANDLERS_CHECK_SESSION_PATH:        Path = path / "tmp"
    HANDLERS_FILE_OGG_PATH:             Path = path / "files" / "voice.ogg"
    IMAGE_LIMITER_PATH:                 Path = path / "files" / "screenshot.jpg"
    HTML_LIMITER_PATH:                  Path = path / "files" / "file.html"
    SESSION_NAME:                       Path = path / "data" / "sn"
    PRIVATE_DATABASE_PATH:              Path = path / "data" / "private.sqlite"
    MODULE_SITE_DATABASE_MY_SITE_PATH:  Path = Path('/var/site/data/database.db')
    MODULE_SITE_DATABASE_PATH:          Path = MODULE_SITE_DATABASE_MY_SITE_PATH

    class Config:
        env_file: Path = path / "data" / ".env"


def get_env() -> Settings:
    return Settings()


__all__ = ["get_env", "Settings"]
