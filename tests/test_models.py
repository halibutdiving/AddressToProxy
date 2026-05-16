import pytest
from pydantic import ValidationError

from address_to_proxy.models import City, Country, ParsedAddress, State


def test_parsed_address_requires_country_state_city():
    with pytest.raises(ValidationError):
        ParsedAddress(country="US", state="", city="Charlotte")


def test_location_models_trim_names():
    country = Country(code=" us ", name=" United States ", states=[])
    state = State(name=" North Carolina ")
    city = City(name=" Charlotte ")

    assert country.code == "US"
    assert country.name == "United States"
    assert state.name == "North Carolina"
    assert city.name == "Charlotte"
