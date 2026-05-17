import re

import respx
from httpx import Response

from address_to_proxy.config import Proxy1024Config
from address_to_proxy.models import City, Country, SelectedLocation
from address_to_proxy.platforms.proxy1024 import Proxy1024Adapter, generate_sid


def _config() -> Proxy1024Config:
    return Proxy1024Config(
        token="fake-platform-token",
        proxy_host="us.1024proxy.io:3000",
        account_id="acct_example",
        password="fake-proxy-password",
        ttl_minutes=10,
    )


@respx.mock
def test_fetch_countries_posts_expected_form_and_normalizes_states():
    route = respx.post("https://api.1024proxy.com/v3/country").mock(
        return_value=Response(
            200,
            json={
                "code": 0,
                "data": [
                    {
                        "country": "US",
                        "country_name": "United States",
                        "state": ["California", "North Carolina"],
                    }
                ],
            },
        )
    )

    countries = Proxy1024Adapter(_config()).fetch_countries()

    request = route.calls.last.request
    assert request.headers["content-type"] == "application/x-www-form-urlencoded;charset=UTF-8"
    assert request.content == b"cate=traffic&lang=zh&token=fake-platform-token"
    assert countries == [
        Country(
            code="US",
            name="United States",
            states=[{"name": "California"}, {"name": "North Carolina"}],
        )
    ]


@respx.mock
def test_fetch_countries_normalizes_real_1024proxy_states_key():
    respx.post("https://api.1024proxy.com/v3/country").mock(
        return_value=Response(
            200,
            json={
                "code": 0,
                "data": [
                    {
                        "code": "US",
                        "name": "美国",
                        "States": [{"state": "North Carolina"}],
                    }
                ],
            },
        )
    )

    countries = Proxy1024Adapter(_config()).fetch_countries()

    assert countries == [
        Country(code="US", name="美国", states=[{"name": "North Carolina"}])
    ]


@respx.mock
def test_fetch_countries_skips_empty_state_entries_from_real_payload():
    respx.post("https://api.1024proxy.com/v3/country").mock(
        return_value=Response(
            200,
            json={
                "code": 0,
                "data": [
                    {
                        "code": "VG",
                        "name": "英属维尔京群岛",
                        "States": [{"state": ""}],
                    }
                ],
            },
        )
    )

    countries = Proxy1024Adapter(_config()).fetch_countries()

    assert countries == [Country(code="VG", name="英属维尔京群岛", states=[])]


@respx.mock
def test_fetch_cities_posts_expected_form_and_normalizes_city_names():
    route = respx.post("https://api.1024proxy.com/v2/city").mock(
        return_value=Response(
            200,
            json={
                "code": 0,
                "data": [
                    {"city": "Los Angeles"},
                    {"city_name": "San Francisco", "lat": "37.7749", "lng": "-122.4194"},
                    "San Diego",
                ],
            },
        )
    )

    cities = Proxy1024Adapter(_config()).fetch_cities("US", "California")

    request = route.calls.last.request
    assert request.content == b"country=US&state=California&lang=zh&token=fake-platform-token"
    assert cities == [
        City(name="Los Angeles"),
        City(name="San Francisco", latitude=37.7749, longitude=-122.4194),
        City(name="San Diego"),
    ]


def test_generate_username_uses_1024proxy_rule():
    adapter = Proxy1024Adapter(_config(), sid_generator=lambda: "W4xtvPvQ")

    username = adapter.generate_username(
        SelectedLocation(country="US", state="North Carolina", city="Charlotte")
    )

    assert username == (
        "acct_example-region-US-st-North Carolina-city-Charlotte-sid-W4xtvPvQ-t-10"
    )


def test_generate_sid_returns_eight_alphanumeric_characters():
    sid = generate_sid()

    assert re.fullmatch(r"[A-Za-z0-9]{8}", sid)
