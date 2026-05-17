# Address To Proxy

Address To Proxy resolves a free-form postal address into proxy connection details for supported proxy platforms.

First version scope:

- CLI entrypoint: `address-to-proxy resolve`.
- LLM-assisted address parsing through a configured OpenAI-compatible endpoint.
- 1024proxy country/state/city dictionary lookup.
- 1024proxy username generation.
- Configurable proxy location validation through `ipinfo.io/json`.

## Usage

Install dependencies:

```bash
./install.sh
```

Create your local config once:

```bash
cp config.example.yaml config.yaml
```

Edit `config.yaml` and set the required environment variables:

```bash
export ADDRESS_TO_PROXY_LLM_API_KEY="..."
export ADDRESS_TO_PROXY_1024_TOKEN="..."
export ADDRESS_TO_PROXY_1024_PASSWORD="..."
```

Run:

```bash
./run.py "123 Example St,Example City,North Carolina,28214, US"
```

If you installed the package entrypoint, this command is equivalent:

```bash
address-to-proxy resolve "123 Example St,Example City,North Carolina,28214, US"
```

By default, the CLI reads `config.yaml` from the current working directory. Use `--config path/to/config.yaml` only when you want to load a different file.
It also selects the first supported proxy platform found in `platforms`; use `--platform 1024proxy` only when you want to override that selection.

Output defaults to JSON. Other formats are available:

```bash
./run.py "123 Example St,Example City,North Carolina,28214, US" --output text
./run.py "123 Example St,Example City,North Carolina,28214, US" --output curl
```

`text` prints `proxy_host`, `username`, `password`, and `validated` as simple key/value lines. `curl` prints a ready-to-run `curl -x ... -U ... https://ipinfo.io/json` command.

## Configuration

Start from `config.example.yaml` and provide secrets through environment variables.

```bash
export ADDRESS_TO_PROXY_LLM_API_KEY="..."
export ADDRESS_TO_PROXY_1024_TOKEN="..."
export ADDRESS_TO_PROXY_1024_PASSWORD="..."
```

The 1024proxy token is used only for platform dictionary API calls. The account ID and password are used only for connecting to the generated proxy.

## Development

For normal local use, run the installer:

```bash
./install.sh
```

It creates `.venv`, upgrades pip, and installs this project in editable mode.

For manual setup:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
```

Run the test suite:

```bash
.venv/bin/python -m pytest -q
```

Verify the CLI entrypoint:

```bash
.venv/bin/address-to-proxy --help
.venv/bin/address-to-proxy resolve --help
```

Create a local runtime config:

```bash
cp config.example.yaml config.yaml
```

Then edit `config.yaml` for non-secret values such as `llm.base_url`, `llm.model`, `platforms.1024proxy.account_id`, `platforms.1024proxy.proxy_host`, `platforms.1024proxy.ttl_minutes`, and `validation.*`. Keep secrets in environment variables:

```bash
export ADDRESS_TO_PROXY_LLM_API_KEY="your-llm-api-key"
export ADDRESS_TO_PROXY_1024_TOKEN="your-1024proxy-api-token"
export ADDRESS_TO_PROXY_1024_PASSWORD="your-fake-proxy-password"
```

Run a real resolve request:

```bash
.venv/bin/address-to-proxy resolve \
  "123 Example St,Example City,North Carolina,28214, US"
```

Equivalent direct-script command:

```bash
.venv/bin/python run.py \
  "123 Example St,Example City,North Carolina,28214, US"
```

To use a config file outside the current directory:

```bash
.venv/bin/address-to-proxy resolve \
  "123 Example St,Example City,North Carolina,28214, US" \
  --config path/to/config.yaml \
  --platform 1024proxy
```

For development without making a real proxy validation request, set:

```yaml
validation:
  mode: "off"
  max_retries: 1
  distance_km: 100
```

Use `strict` when you want the tool to verify that `ipinfo.io/json` returns the same country, state, and city requested in the generated proxy username.
