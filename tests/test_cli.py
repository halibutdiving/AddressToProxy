import json

import respx
from httpx import Response
from typer.testing import CliRunner

from address_to_proxy import cli
from address_to_proxy.models import ParsedAddress, ResolveResult, SelectedLocation


class FakeResolver:
    def __init__(self, config) -> None:
        self.config = config

    def resolve(self, address: str, platform: str) -> ResolveResult:
        assert address == "123 Example St,Example City,North Carolina,28214, US"
        assert platform == "1024proxy"
        return ResolveResult(
            platform="1024proxy",
            proxy_host="us.1024proxy.io:3000",
            username="acct_example-region-US-st-North Carolina-city-Charlotte-sid-W4xtvPvQ-t-10",
            password="fake-proxy-password",
            validated=True,
            parsed_address=ParsedAddress(
                country="US",
                state="North Carolina",
                city="Charlotte",
                postal_code="28214",
                street="123 Example St",
                confidence=0.95,
            ),
            selected_location=SelectedLocation(
                country="US",
                state="North Carolina",
                city="Charlotte",
            ),
            validation={
                "mode": "strict",
                "attempts": 1,
                "failures": [],
                "ipinfo": {
                    "country": "US",
                    "region": "North Carolina",
                    "city": "Charlotte",
                },
            },
        )


def test_resolve_command_prints_json(monkeypatch, tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
llm:
  base_url: "https://llm.example/v1"
  api_key: "fake-llm-key"
  model: "fast-model"
platforms:
  1024proxy:
    token: "fake-platform-token"
    proxy_host: "us.1024proxy.io:3000"
    account_id: "acct_example"
    password: "fake-proxy-password"
    ttl_minutes: 10
validation:
  mode: "strict"
  max_retries: 5
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "build_resolver", lambda config: FakeResolver(config))

    result = CliRunner().invoke(
        cli.app,
        [
            "resolve",
            "123 Example St,Example City,North Carolina,28214, US",
            "--config",
            str(config_file),
            "--platform",
            "1024proxy",
            "--output",
            "json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["proxy_host"] == "us.1024proxy.io:3000"
    assert payload["username"].startswith("acct_example-region-US")
    assert payload["password"] == "fake-proxy-password"
    assert payload["validated"] is True
    assert payload["parsed_address"]["city"] == "Charlotte"
    assert payload["selected_location"]["state"] == "North Carolina"
    assert payload["validation"]["attempts"] == 1


def test_resolve_command_uses_current_directory_config_by_default(monkeypatch, tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
llm:
  base_url: "https://llm.example/v1"
  api_key: "fake-llm-key"
  model: "fast-model"
platforms:
  1024proxy:
    token: "fake-platform-token"
    proxy_host: "us.1024proxy.io:3000"
    account_id: "acct_example"
    password: "fake-proxy-password"
    ttl_minutes: 10
validation:
  mode: "strict"
  max_retries: 5
""",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "build_resolver", lambda config: FakeResolver(config))

    result = CliRunner().invoke(
        cli.app,
        [
            "resolve",
            "123 Example St,Example City,North Carolina,28214, US",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["proxy_host"] == "us.1024proxy.io:3000"
    assert payload["validated"] is True


def test_missing_config_exits_non_zero():
    result = CliRunner().invoke(
        cli.app,
        [
            "resolve",
            "123 Example St,Example City,North Carolina,28214, US",
            "--config",
            "/does/not/exist.yaml",
        ],
    )

    assert result.exit_code == 1
    assert "Unable to read config file" in result.stderr


@respx.mock
def test_llm_non_json_response_exits_non_zero_without_traceback(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
llm:
  base_url: "https://llm.example/v1"
  api_key: "fake-llm-key"
  model: "fast-model"
platforms:
  1024proxy:
    token: "fake-platform-token"
    proxy_host: "us.1024proxy.io:3000"
    account_id: "acct_example"
    password: "fake-proxy-password"
    ttl_minutes: 10
validation:
  mode: "off"
  max_retries: 1
""",
        encoding="utf-8",
    )
    respx.post("https://llm.example/v1/chat/completions").mock(
        return_value=Response(200, text="<html>not json</html>")
    )

    result = CliRunner().invoke(
        cli.app,
        [
            "resolve",
            "123 Example St,Example City,North Carolina,28214, US",
            "--config",
            str(config_file),
        ],
    )

    assert result.exit_code == 1
    assert "LLM HTTP response was not JSON" in result.stderr
    assert "Traceback" not in result.stderr
