import re
from collections.abc import Sequence
from difflib import get_close_matches

from address_to_proxy.errors import LocationMatchError
from address_to_proxy.models import City, Country, State

_US_STATE_ABBREVIATIONS = {
    "AL": "Alabama",
    "AK": "Alaska",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DE": "Delaware",
    "FL": "Florida",
    "GA": "Georgia",
    "HI": "Hawaii",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "IA": "Iowa",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "ME": "Maine",
    "MD": "Maryland",
    "MA": "Massachusetts",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MS": "Mississippi",
    "MO": "Missouri",
    "MT": "Montana",
    "NE": "Nebraska",
    "NV": "Nevada",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NY": "New York",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VT": "Vermont",
    "VA": "Virginia",
    "WA": "Washington",
    "WV": "West Virginia",
    "WI": "Wisconsin",
    "WY": "Wyoming",
    "DC": "District of Columbia",
}


def normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def match_country(value: str, countries: Sequence[Country]) -> Country:
    candidates = list(countries)
    normalized = normalize(value)
    for country in candidates:
        names = [country.code]
        if country.name:
            names.append(country.name)
        if normalized in {normalize(name) for name in names}:
            return country
    raise LocationMatchError(
        f"Unable to match country: {value}",
        [country.code for country in candidates],
    )


def match_state(value: str, states: Sequence[State]) -> State:
    expanded = _US_STATE_ABBREVIATIONS.get(value.strip().upper(), value)
    return _match_named("state", expanded, states)


def match_city(value: str, cities: Sequence[City]) -> City:
    return _match_named("city", value, cities)


def _match_named(kind: str, value: str, candidates: Sequence[State] | Sequence[City]):
    candidate_list = list(candidates)
    normalized = normalize(value)
    by_normalized = {normalize(candidate.name): candidate for candidate in candidate_list}
    if normalized in by_normalized:
        return by_normalized[normalized]

    close = get_close_matches(normalized, list(by_normalized), n=1, cutoff=0.92)
    if close:
        return by_normalized[close[0]]

    names = [candidate.name for candidate in candidate_list]
    raise LocationMatchError(f"Unable to match {kind}: {value}", names)
