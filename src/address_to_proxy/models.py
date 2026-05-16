from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _strip_required(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError("must not be empty")
    return stripped


class City(BaseModel):
    name: str
    latitude: float | None = None
    longitude: float | None = None

    @field_validator("name")
    @classmethod
    def _clean_name(cls, value: str) -> str:
        return _strip_required(value)


class State(BaseModel):
    name: str
    cities: list[City] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def _clean_name(cls, value: str) -> str:
        return _strip_required(value)


class Country(BaseModel):
    code: str
    name: str | None = None
    states: list[State] = Field(default_factory=list)

    @field_validator("code")
    @classmethod
    def _clean_code(cls, value: str) -> str:
        return _strip_required(value).upper()

    @field_validator("name")
    @classmethod
    def _clean_name(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _strip_required(value)


class ParsedAddress(BaseModel):
    country: str
    state: str
    city: str
    postal_code: str | None = None
    street: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)

    @field_validator("country", "state", "city")
    @classmethod
    def _clean_required(cls, value: str) -> str:
        return _strip_required(value)

    @field_validator("postal_code", "street")
    @classmethod
    def _clean_optional(cls, value: str | None) -> str | None:
        if value is None:
            return value
        stripped = value.strip()
        return stripped or None


class SelectedLocation(BaseModel):
    country: str
    state: str
    city: str
    latitude: float | None = None
    longitude: float | None = None

    @field_validator("country", "state", "city")
    @classmethod
    def _clean_required(cls, value: str) -> str:
        return _strip_required(value)


class ProxyCredentials(BaseModel):
    host: str
    username: str
    password: str


class IpInfo(BaseModel):
    model_config = ConfigDict(extra="allow")

    country: str | None = None
    region: str | None = None
    city: str | None = None
    loc: str | None = None


class ValidationAttempt(BaseModel):
    valid: bool
    mode: Literal["strict", "state", "distance", "off"]
    reason: str
    ipinfo: IpInfo | None = None


class ResolveResult(BaseModel):
    platform: str
    proxy_host: str
    username: str
    password: str
    validated: bool
    parsed_address: ParsedAddress
    selected_location: SelectedLocation
    validation: dict
