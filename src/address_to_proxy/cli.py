import json
import shlex
from pathlib import Path
from typing import Annotated
from typing import Literal

import typer

from address_to_proxy.config import AppConfig, load_config
from address_to_proxy.errors import AddressToProxyError, ConfigError
from address_to_proxy.llm import LlmAddressParser
from address_to_proxy.models import ResolveResult
from address_to_proxy.platforms.proxy1024 import Proxy1024Adapter
from address_to_proxy.resolver import AddressToProxyResolver
from address_to_proxy.validation import ProxyValidator

app = typer.Typer(help="Resolve postal addresses into proxy connection details.")


@app.callback()
def root() -> None:
    """Resolve postal addresses into proxy connection details."""


@app.command()
def resolve(
    address: Annotated[
        list[str],
        typer.Argument(help="Address tokens. Multiple tokens are joined with spaces."),
    ],
    config: Path = typer.Option(
        Path("config.yaml"),
        "--config",
        "-c",
        help="Path to YAML config file.",
    ),
    platform: str | None = typer.Option(
        None,
        "--platform",
        "-p",
        help="Proxy platform name. Defaults to the first supported platform in config.",
    ),
    output: Literal["json", "text", "curl"] = typer.Option(
        "json",
        "--output",
        "-o",
        help="Output format.",
    ),
) -> None:
    try:
        address_text = " ".join(address).strip()
        if not address_text:
            raise ConfigError("Address is required")
        app_config = load_config(config)
        resolver = build_resolver(app_config)
        selected_platform = platform or default_platform(app_config)
        result = resolver.resolve(address_text, platform=selected_platform)
    except AddressToProxyError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    except KeyError as exc:
        typer.echo(f"Unsupported platform: {exc.args[0]}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(render_result(result, output))


def build_resolver(config: AppConfig) -> AddressToProxyResolver:
    adapters = {}
    if "1024proxy" in config.platforms:
        adapters["1024proxy"] = Proxy1024Adapter(config.platforms["1024proxy"])
    return AddressToProxyResolver(
        parser=LlmAddressParser(config.llm),
        adapters=adapters,
        validator=ProxyValidator(config.validation),
        validation_config=config.validation,
    )


def default_platform(config: AppConfig) -> str:
    supported = {"1024proxy"}
    for platform_name in config.platforms:
        if platform_name in supported:
            return platform_name
    raise ConfigError("No supported proxy platform is configured")


def render_result(result: ResolveResult, output: Literal["json", "text", "curl"]) -> str:
    if output == "json":
        return json.dumps(result.model_dump(), ensure_ascii=False, indent=2)
    if output == "text":
        validated = "true" if result.validated else "false"
        return "\n".join(
            [
                f"proxy_host={result.proxy_host}",
                f"username={result.username}",
                f"password={result.password}",
                f"validated={validated}",
            ]
        )
    proxy_host = shlex.quote(result.proxy_host)
    credentials = shlex.quote(f"{result.username}:{result.password}")
    return f"curl -x {proxy_host} -U {credentials} https://ipinfo.io/json"


def main() -> None:
    app()
