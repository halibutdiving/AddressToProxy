import json
from typing import Any

import httpx
from pydantic import ValidationError as PydanticValidationError

from address_to_proxy.config import LlmConfig
from address_to_proxy.errors import LlmParseError
from address_to_proxy.matching import match_city
from address_to_proxy.models import City, ParsedAddress


class LlmAddressParser:
    def __init__(
        self,
        config: LlmConfig,
        client: httpx.Client | None = None,
        timeout: float = 20.0,
    ) -> None:
        self.config = config
        self.client = client or httpx.Client(timeout=timeout)

    def parse(self, address: str) -> ParsedAddress:
        payload = self._chat(
            [
                {
                    "role": "system",
                    "content": (
                        "Extract a postal address into strict JSON with keys "
                        "country, state, city, postal_code, street, confidence. "
                        "Use postal codes and abbreviations to infer missing state "
                        "or city when the input provides enough evidence. Return "
                        "only JSON."
                    ),
                },
                {"role": "user", "content": address},
            ]
        )
        content = _extract_content(payload)
        try:
            data = json.loads(_strip_code_fence(content))
        except json.JSONDecodeError as exc:
            raise LlmParseError("LLM response content was not valid JSON") from exc

        try:
            return ParsedAddress.model_validate(data)
        except PydanticValidationError as exc:
            raise LlmParseError(f"LLM response missing required address fields: {exc}") from exc

    def choose_nearest_city(self, parsed: ParsedAddress, cities: list[City]) -> City:
        payload = self._chat(
            [
                {
                    "role": "system",
                    "content": (
                        "Choose the physically nearest supported proxy city for the "
                        "parsed address. Return strict JSON with exactly one key: city. "
                        "The city value must be copied from the supported city list."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "parsed_address": parsed.model_dump(exclude_none=True),
                            "supported_cities": [city.name for city in cities],
                        },
                        ensure_ascii=False,
                    ),
                },
            ]
        )
        content = _extract_content(payload)
        try:
            data = json.loads(_strip_code_fence(content))
        except json.JSONDecodeError as exc:
            raise LlmParseError("LLM nearest-city response content was not valid JSON") from exc
        city_name = data.get("city")
        if not isinstance(city_name, str):
            raise LlmParseError("LLM nearest-city response must include a city string")
        return match_city(city_name, cities)

    def _chat(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        url = self.config.base_url.rstrip("/") + "/chat/completions"
        try:
            response = self.client.post(
                url,
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.config.model,
                    "messages": messages,
                    "temperature": 0,
                },
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise LlmParseError(f"LLM request failed: {exc}") from exc

        return response.json()


def _extract_content(payload: dict[str, Any]) -> str:
    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LlmParseError("LLM response did not include choices[0].message.content") from exc
    if not isinstance(content, str) or not content.strip():
        raise LlmParseError("LLM response content was empty")
    return content


def _strip_code_fence(content: str) -> str:
    stripped = content.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()
