from collections.abc import Mapping
from typing import Protocol

from address_to_proxy.config import ValidationConfig
from address_to_proxy.errors import LocationMatchError
from address_to_proxy.matching import match_city, match_country, match_state
from address_to_proxy.models import (
    City,
    Country,
    ParsedAddress,
    ProxyCredentials,
    ResolveResult,
    SelectedLocation,
    ValidationAttempt,
)
from address_to_proxy.platforms.base import PlatformAdapter


class AddressParser(Protocol):
    def parse(self, address: str) -> ParsedAddress: ...


class Validator(Protocol):
    def validate(
        self,
        location: SelectedLocation,
        credentials: ProxyCredentials,
    ) -> ValidationAttempt: ...


class AddressToProxyResolver:
    def __init__(
        self,
        parser: AddressParser,
        adapters: Mapping[str, PlatformAdapter],
        validator: Validator,
        validation_config: ValidationConfig,
    ) -> None:
        self.parser = parser
        self.adapters = adapters
        self.validator = validator
        self.validation_config = validation_config

    def resolve(self, address: str, platform: str) -> ResolveResult:
        adapter = self.adapters[platform]
        parsed = self.parser.parse(address)
        location = self._select_location(adapter, parsed)
        max_attempts = 1 if self.validation_config.mode == "off" else self.validation_config.max_retries

        attempts: list[ValidationAttempt] = []
        last_credentials: ProxyCredentials | None = None
        last_username = ""
        for _ in range(max_attempts):
            username = adapter.generate_username(location)
            credentials = ProxyCredentials(
                host=adapter.proxy_host,
                username=username,
                password=adapter.password,
            )
            last_credentials = credentials
            last_username = username
            attempt = self.validator.validate(location, credentials)
            attempts.append(attempt)
            if attempt.valid:
                return self._result(platform, parsed, location, credentials, attempts, True)

        if last_credentials is None:
            raise LocationMatchError("No proxy credentials were generated")
        return self._result(platform, parsed, location, last_credentials, attempts, False)

    def _select_location(
        self,
        adapter: PlatformAdapter,
        parsed: ParsedAddress,
    ) -> SelectedLocation:
        countries = adapter.fetch_countries()
        try:
            country = match_country(parsed.country, countries)
        except LocationMatchError:
            selector = getattr(self.parser, "choose_country", None)
            if not callable(selector):
                raise
            country = selector(parsed, countries)

        try:
            state = match_state(parsed.state, country.states)
        except LocationMatchError:
            selector = getattr(self.parser, "choose_state", None)
            if not callable(selector):
                raise
            state = selector(parsed, country, country.states)

        cities = adapter.fetch_cities(country.code, state.name)
        try:
            city = match_city(parsed.city, cities)
        except LocationMatchError:
            selector = getattr(self.parser, "choose_nearest_city", None)
            if not callable(selector):
                raise
            city = selector(parsed, cities)
        return SelectedLocation(
            country=country.code,
            state=state.name,
            city=city.name,
            latitude=city.latitude,
            longitude=city.longitude,
        )

    def _result(
        self,
        platform: str,
        parsed: ParsedAddress,
        location: SelectedLocation,
        credentials: ProxyCredentials,
        attempts: list[ValidationAttempt],
        validated: bool,
    ) -> ResolveResult:
        last = attempts[-1] if attempts else None
        validation = {
            "mode": self.validation_config.mode,
            "attempts": len(attempts),
            "failures": [attempt.reason for attempt in attempts if not attempt.valid],
        }
        if last and last.ipinfo:
            validation["ipinfo"] = last.ipinfo.model_dump(exclude_none=True)
        return ResolveResult(
            platform=platform,
            proxy_host=credentials.host,
            username=credentials.username,
            password=credentials.password,
            validated=validated,
            parsed_address=parsed,
            selected_location=location,
            validation=validation,
        )
