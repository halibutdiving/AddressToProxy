import json

import pytest
import respx
from httpx import Response

from address_to_proxy.config import LlmConfig
from address_to_proxy.errors import LlmParseError, LocationMatchError
from address_to_proxy.llm import LlmAddressParser
from address_to_proxy.models import City, Country, ParsedAddress, State


def _parser() -> LlmAddressParser:
    return LlmAddressParser(
        LlmConfig(
            base_url="https://llm.example/v1",
            api_key="fake-llm-key",
            model="fast-model",
        )
    )


@respx.mock
def test_parse_posts_openai_compatible_request_and_returns_address():
    route = respx.post("https://llm.example/v1/chat/completions").mock(
        return_value=Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": """
{
  "country": "US",
  "state": "North Carolina",
  "city": "Charlotte",
  "postal_code": "28214",
  "street": "123 Example St",
  "confidence": 0.95
}
"""
                        }
                    }
                ]
            },
        )
    )

    parsed = _parser().parse("123 Example St,Example City,North Carolina,28214, US")

    request = route.calls.last.request
    assert request.headers["authorization"] == "Bearer fake-llm-key"
    body = request.content.decode()
    assert '"model":"fast-model"' in body
    assert "123 Example St" in body
    assert parsed.country == "US"
    assert parsed.state == "North Carolina"
    assert parsed.city == "Charlotte"
    assert parsed.postal_code == "28214"


@respx.mock
def test_parse_raises_for_invalid_json_content():
    respx.post("https://llm.example/v1/chat/completions").mock(
        return_value=Response(
            200,
            json={"choices": [{"message": {"content": "not json"}}]},
        )
    )

    with pytest.raises(LlmParseError, match="valid JSON"):
        _parser().parse("bad input")


@respx.mock
def test_parse_raises_llm_parse_error_when_http_response_is_not_json():
    respx.post("https://llm.example/v1/chat/completions").mock(
        return_value=Response(200, text="<html>not json</html>")
    )

    with pytest.raises(LlmParseError, match="response was not JSON"):
        _parser().parse("bad input")


@respx.mock
def test_parse_raises_for_missing_required_fields():
    respx.post("https://llm.example/v1/chat/completions").mock(
        return_value=Response(
            200,
            json={"choices": [{"message": {"content": '{"country": "US"}'}}]},
        )
    )

    with pytest.raises(LlmParseError, match="required"):
        _parser().parse("missing fields")


@respx.mock
def test_choose_nearest_city_posts_bounded_city_list_and_returns_supported_city():
    route = respx.post("https://llm.example/v1/chat/completions").mock(
        return_value=Response(
            200,
            json={"choices": [{"message": {"content": '{"city": "Charlotte"}'}}]},
        )
    )

    city = _parser().choose_nearest_city(
        ParsedAddress(country="US", state="North Carolina", city="Huntersville"),
        [City(name="Charlotte"), City(name="Raleigh")],
    )

    request = route.calls.last.request
    body = request.content.decode()
    assert "Huntersville" in body
    assert "Charlotte" in body
    assert "Raleigh" in body
    assert city == City(name="Charlotte")


@respx.mock
def test_choose_country_posts_supported_country_list_and_returns_validated_country():
    route = respx.post("https://llm.example/v1/chat/completions").mock(
        return_value=Response(
            200,
            json={"choices": [{"message": {"content": '{"country_code": "US"}'}}]},
        )
    )

    country = _parser().choose_country(
        ParsedAddress(country="United States", state="Illinois", city="Rockford"),
        [Country(code="US", name="美国"), Country(code="GB", name="英国")],
    )

    request = route.calls.last.request
    body = json.loads(request.content)
    content = body["messages"][-1]["content"]
    assert "United States" in content
    assert '"code": "US"' in content
    assert '"name": "美国"' in content
    assert country == Country(code="US", name="美国")


@respx.mock
def test_choose_country_rejects_unsupported_llm_choice():
    respx.post("https://llm.example/v1/chat/completions").mock(
        return_value=Response(
            200,
            json={"choices": [{"message": {"content": '{"country_code": "CA"}'}}]},
        )
    )

    with pytest.raises(LocationMatchError, match="Unable to match country"):
        _parser().choose_country(
            ParsedAddress(country="United States", state="Illinois", city="Rockford"),
            [Country(code="US", name="美国")],
        )


@respx.mock
def test_choose_state_posts_supported_state_list_and_returns_validated_state():
    route = respx.post("https://llm.example/v1/chat/completions").mock(
        return_value=Response(
            200,
            json={"choices": [{"message": {"content": '{"state": "Illinois"}'}}]},
        )
    )

    state = _parser().choose_state(
        ParsedAddress(country="US", state="伊利诺伊州", city="Rockford"),
        Country(code="US", name="美国"),
        [State(name="Illinois"), State(name="California")],
    )

    request = route.calls.last.request
    body = json.loads(request.content)
    content = body["messages"][-1]["content"]
    assert "伊利诺伊州" in content
    assert '"country": {"code": "US", "name": "美国"}' in content
    assert "Illinois" in content
    assert state == State(name="Illinois")


@respx.mock
def test_choose_state_rejects_unsupported_llm_choice():
    respx.post("https://llm.example/v1/chat/completions").mock(
        return_value=Response(
            200,
            json={"choices": [{"message": {"content": '{"state": "Ontario"}'}}]},
        )
    )

    with pytest.raises(LocationMatchError, match="Unable to match state"):
        _parser().choose_state(
            ParsedAddress(country="US", state="伊利诺伊州", city="Rockford"),
            Country(code="US", name="美国"),
            [State(name="Illinois")],
        )
