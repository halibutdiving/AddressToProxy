# Address To Proxy CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Build the first working Python CLI for resolving an input address into 1024proxy connection details, with LLM parsing, platform dictionary matching, username generation, and configurable validation.

**Architecture:** Use a small `src/address_to_proxy` package with focused modules for config, models, LLM parsing, platform adapters, matching, validation, resolver orchestration, and CLI. Tests mock all network calls so the suite never depends on live LLM, 1024proxy, or ipinfo.

**Tech Stack:** Python 3.11+, Typer CLI, Pydantic models, PyYAML config loading, HTTPX for HTTP clients, Pytest and respx for tests.

---

## File Structure

- `pyproject.toml`: package metadata, runtime dependencies, test dependencies, CLI entrypoint.
- `README.md`: usage, config, and development commands.
- `config.example.yaml`: sample configuration with environment placeholders.
- `src/address_to_proxy/__init__.py`: package version.
- `src/address_to_proxy/errors.py`: typed application exceptions.
- `src/address_to_proxy/models.py`: shared Pydantic data models.
- `src/address_to_proxy/config.py`: YAML loading, environment expansion, config validation.
- `src/address_to_proxy/llm.py`: OpenAI-compatible LLM client and structured parsing.
- `src/address_to_proxy/matching.py`: country/state/city matching helpers.
- `src/address_to_proxy/platforms/__init__.py`: platform adapter exports.
- `src/address_to_proxy/platforms/base.py`: adapter protocol.
- `src/address_to_proxy/platforms/proxy1024.py`: 1024proxy API adapter and username generation.
- `src/address_to_proxy/validation.py`: ipinfo validation modes and proxy request logic.
- `src/address_to_proxy/resolver.py`: end-to-end orchestration with retries.
- `src/address_to_proxy/cli.py`: `address-to-proxy resolve` command.
- `tests/`: pytest suite covering each module and CLI.

## Task 1: Python Project Scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `README.md`
- Create: `config.example.yaml`
- Create: `src/address_to_proxy/__init__.py`
- Create: `tests/conftest.py`

- [x] **Step 1: Write scaffold test**

Create `tests/test_project_scaffold.py`:

```python
from typer.testing import CliRunner

from address_to_proxy import __version__
from address_to_proxy.cli import app


def test_package_exposes_version():
    assert __version__


def test_cli_help_renders():
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "resolve" in result.stdout
```

- [x] **Step 2: Run scaffold test and verify it fails**

Run: `python -m pytest tests/test_project_scaffold.py -q`

Expected: FAIL because `address_to_proxy` does not exist yet.

- [x] **Step 3: Add package scaffold**

Create `pyproject.toml` with:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "address-to-proxy"
version = "0.1.0"
description = "Resolve postal addresses into proxy account connection details."
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
  "httpx>=0.27",
  "pydantic>=2.7",
  "PyYAML>=6.0",
  "typer>=0.12",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.0",
  "respx>=0.21",
]

[project.scripts]
address-to-proxy = "address_to_proxy.cli:main"

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

Create `src/address_to_proxy/__init__.py`:

```python
__version__ = "0.1.0"
```

Create a minimal `src/address_to_proxy/cli.py`:

```python
import typer

app = typer.Typer(help="Resolve postal addresses into proxy connection details.")


@app.command()
def resolve(address: str) -> None:
    typer.echo(address)


def main() -> None:
    app()
```

Create `README.md` and `config.example.yaml` with the user-facing config shape from the design spec.

- [x] **Step 4: Run scaffold test and verify it passes**

Run: `python -m pytest tests/test_project_scaffold.py -q`

Expected: PASS.

## Task 2: Config, Models, and Errors

**Files:**
- Create: `src/address_to_proxy/errors.py`
- Create: `src/address_to_proxy/models.py`
- Create: `src/address_to_proxy/config.py`
- Create: `tests/test_config.py`
- Create: `tests/test_models.py`

- [x] **Step 1: Write failing config and model tests**

Create tests that verify:

```python
def test_load_config_expands_environment_variables(tmp_path, monkeypatch):
    monkeypatch.setenv("ADDRESS_TO_PROXY_LLM_API_KEY", "fake-llm-key")
    monkeypatch.setenv("ADDRESS_TO_PROXY_1024_TOKEN", "fake-platform-token")
    monkeypatch.setenv("ADDRESS_TO_PROXY_1024_PASSWORD", "fake-proxy-password")
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
llm:
  base_url: "https://llm.example/v1"
  api_key: "${ADDRESS_TO_PROXY_LLM_API_KEY}"
  model: "fast-model"
platforms:
  1024proxy:
    token: "${ADDRESS_TO_PROXY_1024_TOKEN}"
    proxy_host: "us.1024proxy.io:3000"
    account_id: "acct_example"
    password: "${ADDRESS_TO_PROXY_1024_PASSWORD}"
    ttl_minutes: 10
validation:
  mode: "strict"
  max_retries: 5
  distance_km: 100
""",
        encoding="utf-8",
    )

    config = load_config(config_file)

    assert config.llm.api_key == "fake-llm-key"
    assert config.platforms["1024proxy"].token == "fake-platform-token"
    assert config.platforms["1024proxy"].password == "fake-proxy-password"
    assert config.validation.mode == "strict"
```

```python
def test_parsed_address_requires_country_state_city():
    with pytest.raises(ValidationError):
        ParsedAddress(country="US", state="", city="Charlotte")
```

- [x] **Step 2: Run tests and verify they fail**

Run: `python -m pytest tests/test_config.py tests/test_models.py -q`

Expected: FAIL because modules do not exist.

- [x] **Step 3: Implement config, models, and errors**

Use Pydantic models:

```python
class ParsedAddress(BaseModel):
    country: str
    state: str
    city: str
    postal_code: str | None = None
    street: str | None = None
    confidence: float | None = None
```

Implement non-empty validators for required strings, config models for `llm`, `platforms`, and `validation`, and `load_config(path: Path) -> AppConfig` with `${ENV_VAR}` expansion.

- [x] **Step 4: Run tests and verify they pass**

Run: `python -m pytest tests/test_config.py tests/test_models.py -q`

Expected: PASS.

## Task 3: LLM Parser

**Files:**
- Create: `src/address_to_proxy/llm.py`
- Create: `tests/test_llm.py`

- [x] **Step 1: Write failing LLM tests**

Test that `LlmAddressParser.parse()` posts to `{base_url}/chat/completions`, includes model and prompt messages, parses JSON content into `ParsedAddress`, and raises `LlmParseError` for invalid JSON or missing required fields.

- [x] **Step 2: Run LLM tests and verify they fail**

Run: `python -m pytest tests/test_llm.py -q`

Expected: FAIL because `llm.py` does not exist.

- [x] **Step 3: Implement LLM parser**

Implement an HTTPX-based parser that accepts injected `httpx.Client`, sends an OpenAI-compatible chat completions request, extracts `choices[0].message.content`, parses it as JSON, and returns `ParsedAddress`.

- [x] **Step 4: Run LLM tests and verify they pass**

Run: `python -m pytest tests/test_llm.py -q`

Expected: PASS.

## Task 4: Matching Helpers

**Files:**
- Create: `src/address_to_proxy/matching.py`
- Create: `tests/test_matching.py`

- [x] **Step 1: Write failing matching tests**

Tests cover exact case-insensitive matching, punctuation-insensitive matching, common US state abbreviation matching such as `NC -> North Carolina`, and error behavior when no match exists.

- [x] **Step 2: Run matching tests and verify they fail**

Run: `python -m pytest tests/test_matching.py -q`

Expected: FAIL because `matching.py` does not exist.

- [x] **Step 3: Implement matching helpers**

Implement:

```python
def match_country(value: str, countries: Sequence[Country]) -> Country
def match_state(value: str, states: Sequence[State]) -> State
def match_city(value: str, cities: Sequence[City]) -> City
```

Prefer exact normalized matches, then known aliases. Raise `LocationMatchError` with candidates on failure.

- [x] **Step 4: Run matching tests and verify they pass**

Run: `python -m pytest tests/test_matching.py -q`

Expected: PASS.

## Task 5: 1024proxy Adapter

**Files:**
- Create: `src/address_to_proxy/platforms/__init__.py`
- Create: `src/address_to_proxy/platforms/base.py`
- Create: `src/address_to_proxy/platforms/proxy1024.py`
- Create: `tests/test_proxy1024.py`

- [x] **Step 1: Write failing 1024proxy tests**

Tests verify:

- `fetch_countries()` POSTs to `https://api.1024proxy.com/v3/country` with form fields `cate=traffic`, `lang=zh`, and configured `token`.
- Countries and states are normalized from representative nested payloads.
- `fetch_cities("US", "California")` POSTs to `https://api.1024proxy.com/v2/city` with form fields `country`, `state`, `lang`, and `token`.
- `generate_username()` returns `acct_example-region-US-st-North Carolina-city-Charlotte-sid-W4xtvPvQ-t-10` when the injected SID is `W4xtvPvQ`.
- Generated random SID is eight alphanumeric characters.

- [x] **Step 2: Run 1024proxy tests and verify they fail**

Run: `python -m pytest tests/test_proxy1024.py -q`

Expected: FAIL because platform modules do not exist.

- [x] **Step 3: Implement adapter**

Implement a `Proxy1024Adapter` using HTTPX, robust response normalization for common API shapes, `generate_sid()`, and username generation based on config.

- [x] **Step 4: Run 1024proxy tests and verify they pass**

Run: `python -m pytest tests/test_proxy1024.py -q`

Expected: PASS.

## Task 6: Validation

**Files:**
- Create: `src/address_to_proxy/validation.py`
- Create: `tests/test_validation.py`

- [x] **Step 1: Write failing validation tests**

Tests cover:

- `strict` accepts exact country, region, and city.
- `strict` rejects city mismatch.
- `state` accepts city mismatch when country and region match.
- `off` returns valid without network call.
- Proxy request uses `proxy_host`, username, and password for the HTTPX proxy URL.

- [x] **Step 2: Run validation tests and verify they fail**

Run: `python -m pytest tests/test_validation.py -q`

Expected: FAIL because `validation.py` does not exist.

- [x] **Step 3: Implement validation**

Implement `ProxyValidator.validate()` and a pure `evaluate_validation()` helper. Use `https://ipinfo.io/json`. Construct proxy URL as `http://username:password@proxy_host`.

- [x] **Step 4: Run validation tests and verify they pass**

Run: `python -m pytest tests/test_validation.py -q`

Expected: PASS.

## Task 7: Resolver Orchestration

**Files:**
- Create: `src/address_to_proxy/resolver.py`
- Create: `tests/test_resolver.py`

- [x] **Step 1: Write failing resolver tests**

Tests cover:

- Happy path parses address, fetches dictionary, matches location, generates username, validates once, and returns connection details.
- Retry path regenerates SID when validation fails and succeeds on second attempt.
- Retry exhaustion returns the last generated credentials with `validated=false` and validation failures.

- [x] **Step 2: Run resolver tests and verify they fail**

Run: `python -m pytest tests/test_resolver.py -q`

Expected: FAIL because `resolver.py` does not exist.

- [x] **Step 3: Implement resolver**

Implement `AddressToProxyResolver.resolve(address: str, platform: str) -> ResolveResult` using injected parser, adapter, and validator. Support `validation.mode == "off"` by generating one credential without retries.

- [x] **Step 4: Run resolver tests and verify they pass**

Run: `python -m pytest tests/test_resolver.py -q`

Expected: PASS.

## Task 8: CLI Integration

**Files:**
- Modify: `src/address_to_proxy/cli.py`
- Create: `tests/test_cli.py`
- Modify: `README.md`
- Modify: `config.example.yaml`

- [x] **Step 1: Write failing CLI tests**

Tests verify:

- `address-to-proxy resolve <address> --config <file> --platform 1024proxy` prints JSON with `proxy_host`, `username`, `password`, `validated`, `parsed_address`, `selected_location`, and `validation`.
- Missing config exits non-zero with a concise error.

- [x] **Step 2: Run CLI tests and verify they fail**

Run: `python -m pytest tests/test_cli.py -q`

Expected: FAIL because CLI does not wire the resolver yet.

- [x] **Step 3: Implement CLI**

Implement CLI options:

```bash
address-to-proxy resolve ADDRESS --config config.yaml --platform 1024proxy --output json
```

Only JSON output is required for the first version. Use Typer error handling to avoid leaking secrets.

- [x] **Step 4: Run CLI tests and verify they pass**

Run: `python -m pytest tests/test_cli.py -q`

Expected: PASS.

## Task 9: Full Verification

**Files:**
- No new files required.

- [x] **Step 1: Run full test suite**

Run: `python -m pytest -q`

Expected: PASS.

- [x] **Step 2: Inspect git status and diff**

Run: `git status --short` and `git diff --stat`.

Expected: only planned files changed.

- [x] **Step 3: Confirm requirement coverage**

Map the original requirements to code/tests:

- Python CLI exists.
- YAML config and env expansion exist.
- LLM parser uses configured URL, API key, and model.
- 1024proxy country/state and city APIs use token form fields.
- Username format matches the required rule.
- `sid` is eight alphanumeric characters.
- Validation calls `ipinfo.io/json` through the generated proxy credentials.
- Validation strictness is configurable.
- Retry regenerates `sid` and stops at `max_retries`.
- Tests do not call live external services.
