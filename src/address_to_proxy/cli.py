import json
from pathlib import Path
from typing import Literal

import typer

from address_to_proxy.config import AppConfig, load_config
from address_to_proxy.errors import AddressToProxyError
from address_to_proxy.llm import LlmAddressParser
from address_to_proxy.platforms.proxy1024 import Proxy1024Adapter
from address_to_proxy.resolver import AddressToProxyResolver
from address_to_proxy.validation import ProxyValidator

app = typer.Typer(help="Resolve postal addresses into proxy connection details.")


@app.callback()
def root() -> None:
    """Resolve postal addresses into proxy connection details."""


@app.command()
def resolve(
    address: str,
    config: Path = typer.Option(..., "--config", "-c", help="Path to YAML config file."),
    platform: str = typer.Option("1024proxy", "--platform", "-p", help="Proxy platform name."),
    output: Literal["json"] = typer.Option("json", "--output", "-o", help="Output format."),
) -> None:
    try:
        app_config = load_config(config)
        resolver = build_resolver(app_config)
        result = resolver.resolve(address, platform=platform)
    except AddressToProxyError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    except KeyError as exc:
        typer.echo(f"Unsupported platform: {exc.args[0]}", err=True)
        raise typer.Exit(code=1) from exc

    if output == "json":
        typer.echo(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))


def build_resolver(config: AppConfig) -> AddressToProxyResolver:
    adapters = {
        "1024proxy": Proxy1024Adapter(config.platforms["1024proxy"]),
    }
    return AddressToProxyResolver(
        parser=LlmAddressParser(config.llm),
        adapters=adapters,
        validator=ProxyValidator(config.validation),
        validation_config=config.validation,
    )


def main() -> None:
    app()
