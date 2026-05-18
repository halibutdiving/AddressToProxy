from address_to_proxy.config import ValidationConfig
from address_to_proxy.errors import LocationMatchError
from address_to_proxy.models import (
    City,
    Country,
    ParsedAddress,
    ProxyCredentials,
    SelectedLocation,
    State,
    ValidationAttempt,
)
from address_to_proxy.resolver import AddressToProxyResolver


class FakeParser:
    def parse(self, address: str) -> ParsedAddress:
        assert "Example City" in address
        return ParsedAddress(
            country="US",
            state="North Carolina",
            city="Charlotte",
            postal_code="28214",
            street="123 Example St",
            confidence=0.95,
        )


class FakeNearestCityParser(FakeParser):
    def parse(self, address: str) -> ParsedAddress:
        return ParsedAddress(
            country="US",
            state="North Carolina",
            city="Huntersville",
            postal_code="28078",
            street="100 Main St",
            confidence=0.9,
        )

    def choose_nearest_city(self, parsed: ParsedAddress, cities: list[City]) -> City:
        assert parsed.city == "Huntersville"
        assert [city.name for city in cities] == ["Charlotte", "Raleigh"]
        return City(name="Charlotte")


class FakePlatformCountryParser:
    def __init__(self) -> None:
        self.country_choices = 0

    def parse(self, address: str) -> ParsedAddress:
        return ParsedAddress(
            country="United States",
            state="Illinois",
            city="Rockford",
            postal_code="61104",
            street="456 Sample Ave",
            confidence=0.95,
        )

    def choose_country(self, parsed: ParsedAddress, countries: list[Country]) -> Country:
        self.country_choices += 1
        assert parsed.country == "United States"
        assert [country.code for country in countries] == ["US"]
        return countries[0]


class FakePlatformStateParser:
    def __init__(self) -> None:
        self.state_choices = 0

    def parse(self, address: str) -> ParsedAddress:
        return ParsedAddress(
            country="US",
            state="伊利诺伊州",
            city="Rockford",
            postal_code="61104",
            street="456 Sample Ave",
            confidence=0.95,
        )

    def choose_state(
        self,
        parsed: ParsedAddress,
        country: Country,
        states: list[State],
    ) -> State:
        self.state_choices += 1
        assert parsed.state == "伊利诺伊州"
        assert country.code == "US"
        assert [state.name for state in states] == ["Illinois"]
        return states[0]


class FakeAdapter:
    proxy_host = "us.1024proxy.io:3000"
    password = "fake-fake-proxy-password"

    def __init__(self) -> None:
        self.generated = 0

    def fetch_countries(self):
        return [
            Country(
                code="US",
                name="United States",
                states=[State(name="North Carolina")],
            )
        ]

    def fetch_cities(self, country: str, state: str):
        assert country == "US"
        assert state == "North Carolina"
        return [
            City(name="Charlotte", latitude=35.2271, longitude=-80.8431),
            City(name="Raleigh"),
        ]

    def generate_username(self, location: SelectedLocation) -> str:
        self.generated += 1
        return f"user-{self.generated}-{location.city}"


class FakeIllinoisAdapter(FakeAdapter):
    def fetch_countries(self):
        return [
            Country(
                code="US",
                name="美国",
                states=[State(name="Illinois")],
            )
        ]

    def fetch_cities(self, country: str, state: str):
        assert country == "US"
        assert state == "Illinois"
        return [City(name="Rockford")]


class SequenceValidator:
    def __init__(self, attempts: list[ValidationAttempt]) -> None:
        self.attempts = attempts
        self.seen_credentials: list[ProxyCredentials] = []

    def validate(
        self,
        location: SelectedLocation,
        credentials: ProxyCredentials,
    ) -> ValidationAttempt:
        self.seen_credentials.append(credentials)
        return self.attempts.pop(0)


def _attempt(valid: bool, reason: str) -> ValidationAttempt:
    return ValidationAttempt(valid=valid, mode="strict", reason=reason)


def test_resolver_happy_path_returns_valid_connection_details():
    adapter = FakeAdapter()
    validator = SequenceValidator([_attempt(True, "matched")])
    resolver = AddressToProxyResolver(
        parser=FakeParser(),
        adapters={"1024proxy": adapter},
        validator=validator,
        validation_config=ValidationConfig(mode="strict", max_retries=3),
    )

    result = resolver.resolve(
        "123 Example St,Example City,North Carolina,28214, US",
        platform="1024proxy",
    )

    assert result.platform == "1024proxy"
    assert result.proxy_host == "us.1024proxy.io:3000"
    assert result.username == "user-1-Charlotte"
    assert result.password == "fake-fake-proxy-password"
    assert result.validated is True
    assert result.selected_location.city == "Charlotte"
    assert result.selected_location.latitude == 35.2271
    assert result.selected_location.longitude == -80.8431
    assert result.validation["attempts"] == 1


def test_resolver_retries_with_new_username_until_validation_passes():
    adapter = FakeAdapter()
    validator = SequenceValidator([_attempt(False, "city mismatch"), _attempt(True, "matched")])
    resolver = AddressToProxyResolver(
        parser=FakeParser(),
        adapters={"1024proxy": adapter},
        validator=validator,
        validation_config=ValidationConfig(mode="strict", max_retries=3),
    )

    result = resolver.resolve(
        "123 Example St,Example City,North Carolina,28214, US",
        platform="1024proxy",
    )

    assert result.validated is True
    assert result.username == "user-2-Charlotte"
    assert [item.username for item in validator.seen_credentials] == [
        "user-1-Charlotte",
        "user-2-Charlotte",
    ]
    assert result.validation["attempts"] == 2


def test_resolver_returns_last_credentials_when_retries_exhaust():
    adapter = FakeAdapter()
    validator = SequenceValidator([_attempt(False, "city mismatch"), _attempt(False, "city mismatch")])
    resolver = AddressToProxyResolver(
        parser=FakeParser(),
        adapters={"1024proxy": adapter},
        validator=validator,
        validation_config=ValidationConfig(mode="strict", max_retries=2),
    )

    result = resolver.resolve(
        "123 Example St,Example City,North Carolina,28214, US",
        platform="1024proxy",
    )

    assert result.validated is False
    assert result.username == "user-2-Charlotte"
    assert result.validation["attempts"] == 2
    assert result.validation["failures"] == ["city mismatch", "city mismatch"]


def test_resolver_uses_nearest_city_selector_when_city_is_not_supported():
    adapter = FakeAdapter()
    validator = SequenceValidator([_attempt(True, "matched")])
    resolver = AddressToProxyResolver(
        parser=FakeNearestCityParser(),
        adapters={"1024proxy": adapter},
        validator=validator,
        validation_config=ValidationConfig(mode="strict", max_retries=3),
    )

    result = resolver.resolve("100 Main St,Huntersville,NC,28078,US", platform="1024proxy")

    assert result.selected_location.city == "Charlotte"
    assert result.username == "user-1-Charlotte"


def test_resolver_uses_platform_country_selector_when_country_is_not_directly_supported():
    parser = FakePlatformCountryParser()
    adapter = FakeIllinoisAdapter()
    resolver = AddressToProxyResolver(
        parser=parser,
        adapters={"1024proxy": adapter},
        validator=SequenceValidator([_attempt(True, "matched")]),
        validation_config=ValidationConfig(mode="strict", max_retries=3),
    )

    result = resolver.resolve(
        "456 Sample Ave,Rockford,Illinois,61104, US",
        platform="1024proxy",
    )

    assert parser.country_choices == 1
    assert result.selected_location.country == "US"
    assert result.selected_location.state == "Illinois"
    assert result.selected_location.city == "Rockford"


def test_resolver_uses_platform_state_selector_when_state_is_not_directly_supported():
    parser = FakePlatformStateParser()
    adapter = FakeIllinoisAdapter()
    resolver = AddressToProxyResolver(
        parser=parser,
        adapters={"1024proxy": adapter},
        validator=SequenceValidator([_attempt(True, "matched")]),
        validation_config=ValidationConfig(mode="strict", max_retries=3),
    )

    result = resolver.resolve(
        "456 Sample Ave,Rockford,Illinois,61104, US",
        platform="1024proxy",
    )

    assert parser.state_choices == 1
    assert result.selected_location.country == "US"
    assert result.selected_location.state == "Illinois"
    assert result.selected_location.city == "Rockford"


def test_resolver_raises_when_city_is_not_supported_and_no_nearest_selector_exists():
    class NoNearestParser(FakeNearestCityParser):
        choose_nearest_city = None

    resolver = AddressToProxyResolver(
        parser=NoNearestParser(),
        adapters={"1024proxy": FakeAdapter()},
        validator=SequenceValidator([_attempt(True, "matched")]),
        validation_config=ValidationConfig(mode="strict", max_retries=3),
    )

    try:
        resolver.resolve("100 Main St,Huntersville,NC,28078,US", platform="1024proxy")
    except LocationMatchError as exc:
        assert exc.candidates == ["Charlotte", "Raleigh"]
    else:
        raise AssertionError("LocationMatchError was not raised")
