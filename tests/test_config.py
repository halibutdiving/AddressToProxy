import pytest

from address_to_proxy.config import ConfigError, load_config


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


def test_load_config_fails_for_missing_environment_variable(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
llm:
  base_url: "https://llm.example/v1"
  api_key: "${MISSING_LLM_KEY}"
  model: "fast-model"
platforms: {}
validation:
  mode: "strict"
  max_retries: 5
""",
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="MISSING_LLM_KEY"):
        load_config(config_file)


def test_load_config_rejects_unknown_validation_mode(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
llm:
  base_url: "https://llm.example/v1"
  api_key: "key"
  model: "fast-model"
platforms: {}
validation:
  mode: "unsupported"
  max_retries: 5
""",
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="validation"):
        load_config(config_file)
