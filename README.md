# Address To Proxy

Address To Proxy resolves a free-form postal address into proxy connection details for supported proxy platforms.

First version scope:

- CLI entrypoint: `address-to-proxy resolve`.
- LLM-assisted address parsing through a configured OpenAI-compatible endpoint.
- 1024proxy country/state/city dictionary lookup.
- 1024proxy username generation.
- Configurable proxy location validation through `ipinfo.io/json`.

## Usage

```bash
address-to-proxy resolve "123 Example St,Example City,North Carolina,28214, US" \
  --config config.yaml \
  --platform 1024proxy \
  --output json
```

## Configuration

Start from `config.example.yaml` and provide secrets through environment variables.

```bash
export ADDRESS_TO_PROXY_LLM_API_KEY="..."
export ADDRESS_TO_PROXY_1024_TOKEN="..."
export ADDRESS_TO_PROXY_1024_PASSWORD="..."
```

The 1024proxy token is used only for platform dictionary API calls. The account ID and password are used only for connecting to the generated proxy.

## Development

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest -q
```
