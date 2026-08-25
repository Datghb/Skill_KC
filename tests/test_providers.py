from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from vlearn_kc.providers import (
    GatewayJsonGenerator,
    GeminiEmbedder,
    StableEmbeddingCache,
)


class FakeResponse:
    def __init__(self, vector: list[float]) -> None:
        self._vector = vector

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {
            "embedding": {"values": self._vector},
            "usageMetadata": {"promptTokenCount": 3},
        }


class FakeHttpClient:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def post(self, url: str, **kwargs):
        self.calls.append({"url": url, **kwargs})
        return FakeResponse([0.1, 0.2, 0.3])

    def close(self) -> None:
        return None


def test_stable_embedding_cache_round_trips_vectors(tmp_path: Path) -> None:
    path = tmp_path / "cache.json"
    cache = StableEmbeddingCache(path, namespace="test:model")
    cache.put(kind="document", text="hello", vector=[1.0, 2.0])
    cache.flush()

    loaded = StableEmbeddingCache(path, namespace="test:model")

    assert loaded.get(kind="document", text="hello") == [1.0, 2.0]


def test_gemini_embedder_uses_explicit_key_and_cache(tmp_path: Path) -> None:
    client = FakeHttpClient()
    embedder = GeminiEmbedder(
        api_keys=["test-key"],
        model="gemini-embedding-2",
        cache_path=tmp_path / "cache.json",
        client=client,
    )

    first, first_meta = embedder.embed(["hello"], kind="document")
    second, second_meta = embedder.embed(["hello"], kind="document")

    assert first == second == [[0.1, 0.2, 0.3]]
    assert len(client.calls) == 1
    assert client.calls[0]["headers"]["x-goog-api-key"] == "test-key"
    assert first_meta["embedded_items"] == 1
    assert second_meta["cache_hits"] == 1


class FakeGatewayCompletions:
    def __init__(self, *, content: object, body: dict) -> None:
        self.content = content
        self.body = body
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self.content))],
            model_dump=lambda: self.body,
        )


def _gateway_client(*, content: object, body: dict | None = None):
    completions = FakeGatewayCompletions(
        content=content,
        body=body or {"model": "served-model", "usage": {}},
    )
    return SimpleNamespace(
        chat=SimpleNamespace(completions=completions),
        completions_spy=completions,
    )


def test_gateway_generator_returns_json_and_complete_usage_telemetry() -> None:
    client = _gateway_client(
        content='{"knowledge_items": []}',
        body={
            "model": "served-model",
            "usage": {
                "prompt_tokens": 11,
                "completion_tokens": 7,
                "total_tokens": 18,
                "prompt_tokens_details": {"cached_tokens": 3},
                "completion_tokens_details": {"reasoning_tokens": 2},
            },
        },
    )
    generator = GatewayJsonGenerator(
        api_key="secret",
        model="requested-model",
        base_url="https://gateway.example/v1/",
        reasoning_effort="medium",
        max_tokens=321,
        client=client,
    )

    result, telemetry = generator.generate(
        prompt="system prompt",
        request={"lesson": "Bài 1"},
        stage="kc_extraction",
    )

    assert result == {"knowledge_items": []}
    assert telemetry["stage"] == "kc_extraction"
    assert telemetry["base_url"] == "https://gateway.example/v1"
    assert telemetry["model"] == "served-model"
    assert telemetry["usage"] == {
        "input_tokens": 11,
        "cached_input_tokens": 3,
        "output_tokens": 7,
        "reasoning_tokens": 2,
        "total_tokens": 18,
    }
    call = client.completions_spy.calls[0]
    assert call["model"] == "requested-model"
    assert call["response_format"] == {"type": "json_object"}
    assert call["reasoning_effort"] == "medium"
    assert call["max_tokens"] == 321
    assert call["messages"][0] == {"role": "system", "content": "system prompt"}
    assert '"lesson":"Bài 1"' in call["messages"][1]["content"]


def test_gateway_generator_repairs_nearly_valid_json() -> None:
    generator = GatewayJsonGenerator(
        api_key="secret",
        client=_gateway_client(content="{'answer': 42,}"),
    )

    result, _ = generator.generate(prompt="p", request={}, stage="repair")

    assert result == {"answer": 42}


@pytest.mark.parametrize("content", [None, "", "   "])
def test_gateway_generator_rejects_empty_content(content: object) -> None:
    generator = GatewayJsonGenerator(
        api_key="secret",
        client=_gateway_client(content=content),
    )

    with pytest.raises(ValueError, match="no content"):
        generator.generate(prompt="p", request={}, stage="error")


def test_gateway_generator_rejects_non_object_json() -> None:
    generator = GatewayJsonGenerator(
        api_key="secret",
        client=_gateway_client(content="[1, 2, 3]"),
    )

    with pytest.raises(TypeError, match="JSON object"):
        generator.generate(prompt="p", request={}, stage="error")


def test_gateway_generator_requires_non_blank_api_key() -> None:
    with pytest.raises(ValueError, match="generation API key"):
        GatewayJsonGenerator(api_key="  ", client=object())


def test_generator_defaults_to_direct_openai_api() -> None:
    client = _gateway_client(content='{"ok": true}')

    generator = GatewayJsonGenerator(api_key="secret", client=client)

    assert generator.base_url == "https://api.openai.com/v1"
    assert generator.model == "gpt-5.6-luna"


def test_direct_openai_uses_max_completion_tokens() -> None:
    client = _gateway_client(content='{"ok": true}')
    generator = GatewayJsonGenerator(
        api_key="secret",
        max_tokens=456,
        client=client,
    )

    generator.generate(prompt="p", request={}, stage="direct_openai")

    call = client.completions_spy.calls[0]
    assert call["max_completion_tokens"] == 456
    assert "max_tokens" not in call
