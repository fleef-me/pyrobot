#!/usr/bin/env python3

# Copyright 2022 Andrew Ivanov <okolefleef@disr.it>
# All rights reserved

import datetime
from typing import List, Optional

import arrow
from httpx import AsyncClient, AsyncHTTPTransport, Timeout
from pydantic import BaseModel, Field

from config import get_env, Settings
from modules.pretty_json import pretty_dumps

settings: Settings = get_env()
weather_params = {
    'units': 'metric',
    'lang': 'ru',
    'q': 'Kemerovo',
    'APPID': settings.MODULES_WEATHER_TOKEN.get_secret_value()
}


class Main(BaseModel):
    temp: float
    feels_like: float
    temp_min: float
    temp_max: float
    pressure: int
    sea_level: int
    grnd_level: int
    humidity: int
    temp_kf: float


class WeatherItem(BaseModel):
    id: int
    main: str
    description: str
    icon: str


class Clouds(BaseModel):
    all: int


class Wind(BaseModel):
    speed: float
    deg: int
    gust: float


class Rain(BaseModel):
    field_3h: float = Field(..., alias='3h')


class Sys(BaseModel):
    pod: str


class ListItem(BaseModel):
    dt: int
    main: Main
    weather: List[WeatherItem]
    clouds: Clouds
    wind: Wind
    visibility: int
    pop: float
    rain: Optional[Rain] = None
    sys: Sys
    dt_txt: str


class Coord(BaseModel):
    lat: float
    lon: float


class City(BaseModel):
    id: int
    name: str
    coord: Coord
    country: str
    population: int
    timezone: int
    sunrise: int
    sunset: int


class Model(BaseModel):
    cod: str
    message: int
    cnt: int
    list: List[ListItem]
    city: City


def create_session() -> AsyncClient:
    return AsyncClient(
        # http2=True,
        transport=AsyncHTTPTransport(retries=1),
        timeout=Timeout(180, connect=300, pool=None)
    )


async def get_response(session: AsyncClient, city: str) -> str:
    if weather_params.get("q") != city:
        weather_params["q"] = city

    response = await session.get(settings.MODULES_WEATHER_URL, params=weather_params)
    return response.text


def wrapper_data(json_string: str = None, limit: int = 3) -> str:
    output_model = Model.parse_raw(json_string)
    timezone_city = datetime.timezone(datetime.timedelta(seconds=output_model.city.timezone))

    day_wrap = {
        "<strong>Город</strong>": f"{output_model.city.name}",
        "<strong>Пояс (местное время)</strong>": f"{timezone_city} часов\n"
        }

    for _, day in zip(range(int(limit)), output_model.list):
        main = day.main

        timezone = arrow.get(day.dt)
        data_pretty_1 = timezone.to(timezone_city).format('DD-MM HH:mm')
        data_pretty_2 = timezone.humanize(locale="ru")
        date_pretty = f"**{data_pretty_1} ~ {data_pretty_2}**"

        day_wrap[date_pretty] = {
            "Температура": f"{main.temp:.1f}°C (ощущается как {main.feels_like:.1f}°C)",
            "Влажность": f"{main.humidity}%",
            "Описание": day.weather[0].description
        }

    return pretty_dumps(day_wrap)


# if __name__ == '__main__':
#     session = create_session()
#     response = get_response(session=session, city="Kemerovo")
#     result = wrapper_data(json_string=response)
#     print(result)
