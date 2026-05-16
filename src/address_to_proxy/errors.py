class AddressToProxyError(Exception):
    """Base exception for user-facing application errors."""


class ConfigError(AddressToProxyError):
    """Raised when configuration cannot be loaded or validated."""


class LlmParseError(AddressToProxyError):
    """Raised when an LLM response cannot be parsed into an address."""


class PlatformError(AddressToProxyError):
    """Raised when a proxy platform API call or payload is invalid."""


class LocationMatchError(AddressToProxyError):
    """Raised when parsed location fields cannot match platform locations."""

    def __init__(self, message: str, candidates: list[str] | None = None) -> None:
        super().__init__(message)
        self.candidates = candidates or []


class ValidationError(AddressToProxyError):
    """Raised when proxy validation cannot be completed."""
