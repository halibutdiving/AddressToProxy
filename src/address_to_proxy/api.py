from pathlib import Path

from address_to_proxy.cli import build_resolver, default_platform
from address_to_proxy.config import load_config
from address_to_proxy.models import ResolveResult


def resolve_address(
    address: str,
    *,
    config_path: str | Path = "config.yaml",
    platform: str | None = None,
) -> ResolveResult:
    app_config = load_config(config_path)
    resolver = build_resolver(app_config)
    selected_platform = platform or default_platform(app_config)
    return resolver.resolve(address, platform=selected_platform)
