import httpx

from address_to_proxy.config import ValidationConfig
from address_to_proxy.models import IpInfo, ProxyCredentials, SelectedLocation
from address_to_proxy.validation import ProxyValidator, evaluate_validation


def test_strict_accepts_exact_country_region_and_city():
    result = evaluate_validation(
        ValidationConfig(mode="strict", max_retries=3),
        SelectedLocation(country="US", state="North Carolina", city="Charlotte"),
        IpInfo(country="US", region="North Carolina", city="Charlotte"),
    )

    assert result.valid is True


def test_strict_rejects_city_mismatch():
    result = evaluate_validation(
        ValidationConfig(mode="strict", max_retries=3),
        SelectedLocation(country="US", state="North Carolina", city="Charlotte"),
        IpInfo(country="US", region="North Carolina", city="Raleigh"),
    )

    assert result.valid is False
    assert "city" in result.reason


def test_state_accepts_city_mismatch_when_country_and_region_match():
    result = evaluate_validation(
        ValidationConfig(mode="state", max_retries=3),
        SelectedLocation(country="US", state="North Carolina", city="Charlotte"),
        IpInfo(country="US", region="North Carolina", city="Raleigh"),
    )

    assert result.valid is True


def test_distance_accepts_city_within_configured_km():
    result = evaluate_validation(
        ValidationConfig(mode="distance", max_retries=3, distance_km=20),
        SelectedLocation(
            country="US",
            state="North Carolina",
            city="Charlotte",
            latitude=35.2271,
            longitude=-80.8431,
        ),
        IpInfo(
            country="US",
            region="North Carolina",
            city="Near Charlotte",
            loc="35.3000,-80.9000",
        ),
    )

    assert result.valid is True
    assert "within" in result.reason


def test_distance_rejects_city_outside_configured_km():
    result = evaluate_validation(
        ValidationConfig(mode="distance", max_retries=3, distance_km=10),
        SelectedLocation(
            country="US",
            state="North Carolina",
            city="Charlotte",
            latitude=35.2271,
            longitude=-80.8431,
        ),
        IpInfo(
            country="US",
            region="North Carolina",
            city="Raleigh",
            loc="35.7796,-78.6382",
        ),
    )

    assert result.valid is False
    assert "outside" in result.reason


def test_distance_requires_coordinates_when_city_does_not_match():
    result = evaluate_validation(
        ValidationConfig(mode="distance", max_retries=3, distance_km=20),
        SelectedLocation(country="US", state="North Carolina", city="Charlotte"),
        IpInfo(country="US", region="North Carolina", city="Near Charlotte"),
    )

    assert result.valid is False
    assert "coordinates" in result.reason


def test_off_returns_valid_without_network_call():
    called = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return httpx.Response(200, json={})

    validator = ProxyValidator(
        ValidationConfig(mode="off", max_retries=3),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    result = validator.validate(
        SelectedLocation(country="US", state="North Carolina", city="Charlotte"),
        ProxyCredentials(host="us.1024proxy.io:3000", username="user", password="pass"),
    )

    assert result.valid is True
    assert called is False


def test_validator_requests_ipinfo_through_generated_proxy():
    seen_request = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal seen_request
        seen_request = request
        return httpx.Response(
            200,
            json={"country": "US", "region": "North Carolina", "city": "Charlotte"},
        )

    validator = ProxyValidator(
        ValidationConfig(mode="strict", max_retries=3),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    result = validator.validate(
        SelectedLocation(country="US", state="North Carolina", city="Charlotte"),
        ProxyCredentials(
            host="us.1024proxy.io:3000",
            username="user",
            password="pass",
        ),
    )

    assert result.valid is True
    assert str(seen_request.url) == "https://ipinfo.io/json"
    assert seen_request.extensions["proxy_url"] == "http://user:pass@us.1024proxy.io:3000"
