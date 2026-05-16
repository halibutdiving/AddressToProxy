from typing import Protocol

from address_to_proxy.models import City, Country, SelectedLocation


class PlatformAdapter(Protocol):
    @property
    def proxy_host(self) -> str: ...

    @property
    def password(self) -> str: ...

    def fetch_countries(self) -> list[Country]: ...

    def fetch_cities(self, country: str, state: str) -> list[City]: ...

    def generate_username(self, location: SelectedLocation) -> str: ...
