import random
import string
from collections.abc import Callable
from typing import Any

import httpx

from address_to_proxy.config import Proxy1024Config
from address_to_proxy.errors import PlatformError
from address_to_proxy.models import City, Country, SelectedLocation, State

COUNTRY_URL = "https://api.1024proxy.com/v3/country"
CITY_URL = "https://api.1024proxy.com/v2/city"
FORM_CONTENT_TYPE = "application/x-www-form-urlencoded;charset=UTF-8"


def generate_sid() -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(random.SystemRandom().choice(alphabet) for _ in range(8))


class Proxy1024Adapter:
    def __init__(
        self,
        config: Proxy1024Config,
        client: httpx.Client | None = None,
        sid_generator: Callable[[], str] = generate_sid,
        timeout: float = 20.0,
    ) -> None:
        self.config = config
        self.client = client or httpx.Client(timeout=timeout)
        self.sid_generator = sid_generator

    @property
    def proxy_host(self) -> str:
        return self.config.proxy_host

    @property
    def password(self) -> str:
        return self.config.password

    def fetch_countries(self) -> list[Country]:
        payload = self._post_form(
            COUNTRY_URL,
            {"cate": "traffic", "lang": "zh", "token": self.config.token},
        )
        entries = _extract_data_list(payload)
        return [_country_from_entry(entry) for entry in entries]

    def fetch_cities(self, country: str, state: str) -> list[City]:
        payload = self._post_form(
            CITY_URL,
            {
                "country": country,
                "state": state,
                "lang": "zh",
                "token": self.config.token,
            },
        )
        entries = _extract_data_list(payload)
        return [_city_from_entry(entry) for entry in entries]

    def generate_username(self, location: SelectedLocation) -> str:
        sid = self.sid_generator()
        return (
            f"{self.config.account_id}-region-{location.country}"
            f"-st-{location.state}-city-{location.city}"
            f"-sid-{sid}-t-{self.config.ttl_minutes}"
        )

    def _post_form(self, url: str, data: dict[str, str]) -> dict[str, Any]:
        try:
            response = self.client.post(
                url,
                data=data,
                headers={"Content-Type": FORM_CONTENT_TYPE},
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise PlatformError(f"1024proxy API request failed: {url}") from exc
        if not isinstance(payload, dict):
            raise PlatformError("1024proxy API response must be a JSON object")
        return payload


def _extract_data_list(payload: dict[str, Any]) -> list[Any]:
    data = payload.get("data", payload.get("result", payload))
    if isinstance(data, dict):
        for key in ("list", "rows", "items", "data"):
            if isinstance(data.get(key), list):
                return data[key]
        return list(data.values())
    if isinstance(data, list):
        return data
    raise PlatformError("1024proxy API response did not contain a list")


def _country_from_entry(entry: Any) -> Country:
    if isinstance(entry, str):
        return Country(code=entry, name=None, states=[])
    if not isinstance(entry, dict):
        raise PlatformError("Invalid country entry in 1024proxy response")

    code = _first_present(entry, "country", "code", "country_code", "value")
    name = _first_present(entry, "country_name", "name", "label", default=code)
    states_raw = _first_present(entry, "state", "states", "state_list", "children", default=[])
    states = [_state_from_entry(item) for item in _as_list(states_raw)]
    return Country(code=str(code), name=str(name) if name else None, states=states)


def _state_from_entry(entry: Any) -> State:
    if isinstance(entry, str):
        return State(name=entry)
    if not isinstance(entry, dict):
        raise PlatformError("Invalid state entry in 1024proxy response")
    name = _first_present(entry, "state", "state_name", "name", "label", "value")
    return State(name=str(name))


def _city_from_entry(entry: Any) -> City:
    if isinstance(entry, str):
        return City(name=entry)
    if not isinstance(entry, dict):
        raise PlatformError("Invalid city entry in 1024proxy response")
    name = _first_present(entry, "city", "city_name", "name", "label", "value")
    latitude = _optional_float(_optional_present(entry, "lat", "latitude"))
    longitude = _optional_float(_optional_present(entry, "lng", "lon", "longitude"))
    return City(name=str(name), latitude=latitude, longitude=longitude)


def _first_present(entry: dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        value = entry.get(key)
        if value not in (None, ""):
            return value
    if default is not None:
        return default
    raise PlatformError(f"Missing expected field in 1024proxy response: {', '.join(keys)}")


def _optional_present(entry: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = entry.get(key)
        if value not in (None, ""):
            return value
    return None


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    return float(value)
