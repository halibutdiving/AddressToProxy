import os
import re
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, ValidationError as PydanticValidationError

from address_to_proxy.errors import ConfigError

_ENV_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


class LlmConfig(BaseModel):
    base_url: str
    api_key: str
    model: str


class Proxy1024Config(BaseModel):
    token: str
    proxy_host: str
    account_id: str
    password: str
    ttl_minutes: int = Field(gt=0)


class ValidationConfig(BaseModel):
    mode: Literal["strict", "state", "distance", "off"] = "strict"
    max_retries: int = Field(default=5, ge=1)
    distance_km: int = Field(default=100, ge=0)


class AppConfig(BaseModel):
    llm: LlmConfig
    platforms: dict[str, Proxy1024Config]
    validation: ValidationConfig = Field(default_factory=ValidationConfig)


def _expand_env(value: str) -> str:
    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in os.environ:
            raise ConfigError(f"Missing environment variable: {name}")
        return os.environ[name]

    return _ENV_PATTERN.sub(replace, value)


def _expand_value(value):
    if isinstance(value, str):
        return _expand_env(value)
    if isinstance(value, list):
        return [_expand_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _expand_value(item) for key, item in value.items()}
    return value


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path)
    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigError(f"Unable to read config file: {config_path}") from exc
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML in config file: {config_path}") from exc

    if not isinstance(raw, dict):
        raise ConfigError("Configuration must be a YAML mapping")

    try:
        expanded = _expand_value(raw)
        return AppConfig.model_validate(expanded)
    except PydanticValidationError as exc:
        raise ConfigError(f"Invalid configuration: {exc}") from exc

