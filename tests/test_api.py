from pathlib import Path

import address_to_proxy.api as api
from address_to_proxy import resolve_address
from address_to_proxy.models import ParsedAddress, ResolveResult, SelectedLocation


class FakeResolver:
    def resolve(self, address: str, platform: str) -> ResolveResult:
        assert address == "456 Sample Ave,Rockford,Illinois,61104, US"
        assert platform == "1024proxy"
        return ResolveResult(
            platform="1024proxy",
            proxy_host="us.1024proxy.io:3000",
            username="fake-fake-generated-user",
            password="fake-fake-proxy-password",
            validated=True,
            parsed_address=ParsedAddress(
                country="US",
                state="Illinois",
                city="Rockford",
                postal_code="61104",
                street="456 Sample Ave",
                confidence=0.95,
            ),
            selected_location=SelectedLocation(
                country="US",
                state="Illinois",
                city="Rockford",
            ),
            validation={"mode": "strict", "attempts": 1, "failures": []},
        )


def test_resolve_address_loads_config_selects_default_platform_and_returns_result(
    monkeypatch,
    tmp_path,
):
    config_file = tmp_path / "config.yaml"
    loaded_paths: list[Path] = []

    def fake_load_config(path):
        loaded_paths.append(Path(path))
        return object()

    monkeypatch.setattr(api, "load_config", fake_load_config)
    monkeypatch.setattr(api, "build_resolver", lambda config: FakeResolver())
    monkeypatch.setattr(api, "default_platform", lambda config: "1024proxy")

    result = resolve_address(
        "456 Sample Ave,Rockford,Illinois,61104, US",
        config_path=config_file,
    )

    assert loaded_paths == [config_file]
    assert result.platform == "1024proxy"
    assert result.selected_location.city == "Rockford"
    assert result.validated is True


def test_resolve_address_uses_explicit_platform(monkeypatch, tmp_path):
    default_platform_calls = 0

    def fake_default_platform(config):
        nonlocal default_platform_calls
        default_platform_calls += 1
        return "1024proxy"

    monkeypatch.setattr(api, "load_config", lambda path: object())
    monkeypatch.setattr(api, "build_resolver", lambda config: FakeResolver())
    monkeypatch.setattr(api, "default_platform", fake_default_platform)

    result = resolve_address(
        "456 Sample Ave,Rockford,Illinois,61104, US",
        config_path=tmp_path / "config.yaml",
        platform="1024proxy",
    )

    assert default_platform_calls == 0
    assert result.proxy_host == "us.1024proxy.io:3000"
