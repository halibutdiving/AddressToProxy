import pytest

from address_to_proxy.errors import LocationMatchError
from address_to_proxy.matching import match_city, match_country, match_state
from address_to_proxy.models import City, Country, State


def test_match_country_accepts_code_case_insensitive():
    countries = [Country(code="US", name="United States")]

    assert match_country("us", countries).code == "US"


def test_match_state_accepts_punctuation_and_case_differences():
    states = [State(name="North Carolina")]

    assert match_state(" north-carolina ", states).name == "North Carolina"


def test_match_state_accepts_common_us_abbreviation():
    states = [State(name="North Carolina"), State(name="California")]

    assert match_state("NC", states).name == "North Carolina"


def test_match_city_accepts_case_insensitive_value():
    cities = [City(name="Charlotte")]

    assert match_city("charlotte", cities).name == "Charlotte"


def test_match_city_raises_with_candidates_when_missing():
    cities = [City(name="Charlotte"), City(name="Raleigh")]

    with pytest.raises(LocationMatchError) as exc:
        match_city("Durham", cities)

    assert exc.value.candidates == ["Charlotte", "Raleigh"]
