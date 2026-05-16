# Address To Proxy Design

## Goal

Build a Python command line tool that accepts a free-form postal address, uses a fast LLM endpoint to extract location fields, matches those fields against a proxy platform's supported country/state/city dictionaries, generates a platform-specific proxy username, and validates the resulting proxy location before returning connection details.

The first supported platform is 1024proxy. The design must allow additional platforms such as cliproxy to be added later with their own dictionary APIs and username rules.

## Product Shape

The first version will be a core Python library plus a CLI wrapper.

The core library owns configuration, LLM parsing, platform adapters, location matching, username generation, and proxy validation. The CLI only handles user input and output formatting. This keeps the initial tool simple while preserving a clean path to add an HTTP API later.

Example command:

```bash
address-to-proxy resolve "123 Example St,Example City,North Carolina,28214, US" --platform 1024proxy
```

The command returns the proxy host URL, generated proxy username, fixed proxy password, parsed address, selected platform location, and validation details.

## Configuration

Configuration is loaded from a YAML file with environment-variable expansion. Environment variables may override sensitive values and deployment-specific settings.

Example:

```yaml
llm:
  base_url: "https://example-llm-provider.invalid/v1"
  api_key: "${ADDRESS_TO_PROXY_LLM_API_KEY}"
  model: "fast-model-id"

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
```

The 1024proxy API token is only used for dictionary API calls. The proxy account ID and password are only used for connecting to the generated proxy.

## Address Parsing

The LLM is the primary address parser. The tool sends the user-provided string to a configured fast model and asks for structured JSON:

```json
{
  "country": "US",
  "state": "North Carolina",
  "city": "Charlotte",
  "postal_code": "28214",
  "street": "123 Example St",
  "confidence": 0.95
}
```

The prompt should tell the model to use available clues such as postal codes, city names, state names, and country abbreviations. For US addresses, postal code may help infer state when the input is incomplete.

If parsing fails or required fields are missing, the tool fails explicitly and does not generate proxy credentials.

## Platform Adapter Model

Each platform implements a common adapter interface:

- Fetch supported countries and states.
- Fetch supported cities for a selected country/state.
- Normalize platform API responses into common `Country`, `State`, and `City` models.
- Generate platform-specific proxy usernames.
- Provide platform-specific proxy host and fixed password from configuration.

This isolates platform rules. Adding cliproxy later should require a new adapter and config schema, not changes to address parsing or validation logic.

## 1024proxy Adapter

The 1024proxy adapter calls the platform's dictionary APIs using the configured token.

Fetch countries and states:

```http
POST https://api.1024proxy.com/v3/country
Content-Type: application/x-www-form-urlencoded;charset=UTF-8

cate=traffic&lang=zh&token=<token>
```

Fetch cities:

```http
POST https://api.1024proxy.com/v2/city
Content-Type: application/x-www-form-urlencoded;charset=UTF-8

country=US&state=California&lang=zh&token=<token>
```

The adapter should include browser-like headers only if required by the API. The essential data contract is the endpoint, POST method, form encoding, and token field.

The 1024proxy username format is:

```text
{account_id}-region-{country_code}-st-{state_name}-city-{city_name}-sid-{sid}-t-{ttl_minutes}
```

Example:

```text
acct_example-region-US-st-North Carolina-city-Charlotte-sid-W4xtvPvQ-t-10
```

The `sid` is exactly eight alphanumeric characters using uppercase letters, lowercase letters, and digits.

## Location Matching

The resolver compares the LLM output to the platform dictionary in this order:

1. Match country against supported platform countries.
2. Match state within the selected country.
3. Fetch and match city within the selected state.

Matching should prefer exact case-insensitive matches. It may also use conservative fuzzy matching for spelling, abbreviations, and punctuation differences. The selected values in the generated username must be platform dictionary values, not raw LLM text.

If the requested city does not exactly match a platform city, the resolver may choose the physically nearest supported city in the selected state. In the first version, nearest-city selection may use the configured fast LLM as an auxiliary selector from a bounded list of platform cities. Later versions can replace this with geocoding or cached coordinates.

If no country or state can be matched, the command returns an error with the parsed address and available candidates.

## Proxy Validation

Validation uses the generated proxy credentials to request `ipinfo.io/json`.

Equivalent curl:

```bash
curl -x us.1024proxy.io:3000 \
  -U "acct_example-region-US-st-North Carolina-city-Charlotte-sid-W4xtvPvQ-t-10:configured-password" \
  https://ipinfo.io/json
```

If validation fails, the resolver generates a new `sid` and retries until `validation.max_retries` is exhausted.

Validation modes:

- `strict`: `ipinfo` country, region/state, and city must match the selected platform country, state, and city.
- `state`: country and region/state must match; city may differ.
- `distance`: country and region/state must match, and city must be within `distance_km` of the selected city.
- `off`: skip proxy validation and return the first generated credentials.

The default mode is `strict`.

On retry exhaustion, the command returns the last generated credentials, all validation failures, and `validated=false`.

## CLI Output

The CLI supports JSON output by default or via an explicit flag. The output includes:

```json
{
  "platform": "1024proxy",
  "proxy_host": "us.1024proxy.io:3000",
  "username": "acct_example-region-US-st-North Carolina-city-Charlotte-sid-W4xtvPvQ-t-10",
  "password": "configured-password",
  "validated": true,
  "parsed_address": {
    "country": "US",
    "state": "North Carolina",
    "city": "Charlotte",
    "postal_code": "28214",
    "street": "123 Example St",
    "confidence": 0.95
  },
  "selected_location": {
    "country": "US",
    "state": "North Carolina",
    "city": "Charlotte"
  },
  "validation": {
    "mode": "strict",
    "attempts": 1,
    "ipinfo": {
      "country": "US",
      "region": "North Carolina",
      "city": "Charlotte"
    }
  }
}
```

## Errors

The tool returns structured errors for:

- Missing or invalid configuration.
- LLM request failure.
- LLM response that is not valid JSON or lacks required location fields.
- 1024proxy token/API failure.
- Unsupported or unmatched country/state.
- City mismatch when nearest-city fallback is disabled or impossible.
- Proxy validation timeout, HTTP failure, or retry exhaustion.

Errors should include the operation that failed and enough context to troubleshoot without leaking API keys or passwords.

## Testing

Tests should be written before implementation.

Coverage must include:

- YAML config loading and environment-variable expansion.
- LLM response parsing and validation.
- 1024proxy country/state and city request construction.
- 1024proxy response normalization using representative fixtures.
- Country/state/city matching rules.
- `sid` format and username generation.
- Validation mode decisions for `strict`, `state`, `distance`, and `off`.
- Retry behavior when `ipinfo` returns mismatched locations.
- CLI happy path using mocked LLM, platform API, and `ipinfo` responses.

No automated test should depend on live 1024proxy, live LLM, or live `ipinfo.io` calls.

## Non-Goals For First Version

- No HTTP API server.
- No persistent database.
- No background synchronization of platform dictionaries.
- No UI.
- No production-grade geocoder integration unless required to complete nearest-city fallback.
- No support for platforms other than 1024proxy.
