import math
from urllib.parse import quote

import httpx

from address_to_proxy.config import ValidationConfig
from address_to_proxy.errors import ValidationError
from address_to_proxy.matching import normalize
from address_to_proxy.models import IpInfo, ProxyCredentials, SelectedLocation, ValidationAttempt

IPINFO_URL = "https://ipinfo.io/json"


def evaluate_validation(
    config: ValidationConfig,
    location: SelectedLocation,
    ipinfo: IpInfo,
) -> ValidationAttempt:
    mode = config.mode
    if mode == "off":
        return ValidationAttempt(valid=True, mode=mode, reason="validation disabled", ipinfo=ipinfo)

    if normalize(ipinfo.country or "") != normalize(location.country):
        return ValidationAttempt(valid=False, mode=mode, reason="country mismatch", ipinfo=ipinfo)
    if normalize(ipinfo.region or "") != normalize(location.state):
        return ValidationAttempt(valid=False, mode=mode, reason="region mismatch", ipinfo=ipinfo)
    if mode == "state":
        return ValidationAttempt(valid=True, mode=mode, reason="country and region matched", ipinfo=ipinfo)

    if mode == "strict":
        if normalize(ipinfo.city or "") != normalize(location.city):
            return ValidationAttempt(valid=False, mode=mode, reason="city mismatch", ipinfo=ipinfo)
        return ValidationAttempt(valid=True, mode=mode, reason="country, region, and city matched", ipinfo=ipinfo)

    if mode == "distance":
        if normalize(ipinfo.city or "") == normalize(location.city):
            return ValidationAttempt(valid=True, mode=mode, reason="city matched", ipinfo=ipinfo)
        if location.latitude is None or location.longitude is None or not ipinfo.loc:
            return ValidationAttempt(
                valid=False,
                mode=mode,
                reason="distance validation requires target and ipinfo coordinates",
                ipinfo=ipinfo,
            )
        try:
            ip_lat, ip_lon = _parse_loc(ipinfo.loc)
        except ValueError:
            return ValidationAttempt(
                valid=False,
                mode=mode,
                reason="distance validation requires valid ipinfo coordinates",
                ipinfo=ipinfo,
            )
        distance = haversine_km(location.latitude, location.longitude, ip_lat, ip_lon)
        if distance <= config.distance_km:
            return ValidationAttempt(
                valid=True,
                mode=mode,
                reason=f"city within {config.distance_km} km ({distance:.1f} km)",
                ipinfo=ipinfo,
            )
        return ValidationAttempt(
            valid=False,
            mode=mode,
            reason=f"city outside {config.distance_km} km ({distance:.1f} km)",
            ipinfo=ipinfo,
        )

    return ValidationAttempt(valid=False, mode=mode, reason="unsupported validation mode", ipinfo=ipinfo)


def proxy_url(credentials: ProxyCredentials) -> str:
    username = quote(credentials.username, safe="")
    password = quote(credentials.password, safe="")
    return f"http://{username}:{password}@{credentials.host}"


class ProxyValidator:
    def __init__(
        self,
        config: ValidationConfig,
        client: httpx.Client | None = None,
        timeout: float = 20.0,
    ) -> None:
        self.config = config
        self.client = client
        self.timeout = timeout

    def validate(
        self,
        location: SelectedLocation,
        credentials: ProxyCredentials,
    ) -> ValidationAttempt:
        if self.config.mode == "off":
            return ValidationAttempt(
                valid=True,
                mode="off",
                reason="validation disabled",
                ipinfo=None,
            )

        proxy = proxy_url(credentials)
        try:
            if self.client is not None:
                response = self.client.get(IPINFO_URL, extensions={"proxy_url": proxy})
            else:
                with httpx.Client(proxy=proxy, timeout=self.timeout) as client:
                    response = client.get(IPINFO_URL)
            response.raise_for_status()
            ipinfo = IpInfo.model_validate(response.json())
        except (httpx.HTTPError, ValueError) as exc:
            raise ValidationError(f"Proxy validation request failed: {exc}") from exc

        return evaluate_validation(self.config, location, ipinfo)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    return radius_km * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _parse_loc(loc: str) -> tuple[float, float]:
    lat, lon = loc.split(",", 1)
    return float(lat), float(lon)
