from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time
from typing import Any, Protocol

import httpx
from json_repair import repair_json
from openai import OpenAI


class JsonGenerator(Protocol):
    def generate(
        self, *, prompt: str, request: dict[str, Any], stage: str
    ) -> tuple[dict[str, Any], dict[str, Any]]: ...


class Embedder(Protocol):
    def embed(
        self, texts: list[str], *, kind: str
    ) -> tuple[list[list[float]], dict[str, Any]]: ...


class StableEmbeddingCache:
    def __init__(self, path: Path | str, *, namespace: str) -> None:
        self.path = Path(path)
        self.namespace = namespace
        self._items = self._load()

    def _key(self, *, kind: str, text: str) -> str:
        value = f"{self.namespace}\0{kind}\0{text}".encode("utf-8")
        return "sha256:" + hashlib.sha256(value).hexdigest()

    def get(self, *, kind: str, text: str) -> list[float] | None:
        value = self._items.get(self._key(kind=kind, text=text))
        return list(value) if value is not None else None

    def put(self, *, kind: str, text: str, vector: list[float]) -> None:
        self._items[self._key(kind=kind, text=text)] = [float(value) for value in vector]

    def flush(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(
                {
                    "schema_version": "stable_embedding_cache_v1",
                    "namespace": self.namespace,
                    "items": self._items,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def _load(self) -> dict[str, list[float]]:
        if not self.path.is_file():
            return {}
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        if payload.get("namespace") != self.namespace:
            return {}
        items = payload.get("items")
        if not isinstance(items, dict):
            return {}
        return {
            str(key): [float(value) for value in vector]
            for key, vector in items.items()
            if isinstance(vector, list)
        }


class GeminiEmbedder:
    def __init__(
        self,
        *,
        api_keys: list[str],
        model: str = "gemini-embedding-2",
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        cache_path: Path | str,
        timeout: float = 120.0,
        max_retries: int = 2,
        client: Any | None = None,
    ) -> None:
        keys = [value.strip() for value in api_keys if value.strip()]
        if not keys:
            raise ValueError("at least one Gemini API key is required")
        self.api_keys = keys
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max(0, max_retries)
        self.client = client or httpx.Client()
        self._owns_client = client is None
        self._key_index = 0
        self.cache = StableEmbeddingCache(
            cache_path,
            namespace=f"gemini:{model}:dim:default",
        )

    def _next_key(self) -> str:
        value = self.api_keys[self._key_index % len(self.api_keys)]
        self._key_index += 1
        return value

    def _embed_text(self, text: str) -> tuple[list[float], int]:
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self.client.post(
                    f"{self.base_url}/models/{self.model}:embedContent",
                    headers={
                        "Content-Type": "application/json",
                        "x-goog-api-key": self._next_key(),
                    },
                    json={
                        "model": f"models/{self.model}",
                        "content": {"parts": [{"text": text}]},
                    },
                    timeout=self.timeout,
                )
                response.raise_for_status()
                payload = response.json()
                embedding = payload.get("embedding") or {}
                values = embedding.get("values") or payload.get("values")
                if not isinstance(values, list) or not values:
                    raise ValueError("Gemini response contains no embedding vector")
                usage = payload.get("usageMetadata") or {}
                tokens = int(
                    usage.get("promptTokenCount")
                    or usage.get("totalTokenCount")
                    or 0
                )
                return [float(value) for value in values], tokens
            except Exception as exc:  # noqa: BLE001 - provider transports vary.
                last_error = exc
                if attempt >= self.max_retries:
                    raise
                time.sleep(0.5 * (attempt + 1))
        assert last_error is not None
        raise last_error

    def embed(
        self, texts: list[str], *, kind: str
    ) -> tuple[list[list[float]], dict[str, Any]]:
        started = time.perf_counter()
        vectors: list[list[float]] = []
        cache_hits = 0
        embedded_items = 0
        input_tokens = 0
        for text in texts:
            cached = self.cache.get(kind=kind, text=text)
            if cached is not None:
                cache_hits += 1
                vectors.append(cached)
                continue
            vector, tokens = self._embed_text(text)
            self.cache.put(kind=kind, text=text, vector=vector)
            vectors.append(vector)
            embedded_items += 1
            input_tokens += tokens
        self.cache.flush()
        return vectors, {
            "provider": "gemini",
            "model": self.model,
            "embedded_items": embedded_items,
            "cache_hits": cache_hits,
            "input_tokens": input_tokens,
            "latency_seconds": round(time.perf_counter() - started, 3),
            "estimated_cost_usd": round(input_tokens * 0.20 / 1_000_000, 10),
        }

    def close(self) -> None:
        if self._owns_client:
            self.client.close()


class GatewayJsonGenerator:
    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gpt-5.6-luna",
        base_url: str = "https://api.openai.com/v1",
        reasoning_effort: str = "high",
        max_tokens: int = 20_000,
        client: Any | None = None,
    ) -> None:
        if not api_key.strip():
            raise ValueError("generation API key is required")
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.max_tokens = max_tokens
        self.base_url = base_url.rstrip("/")
        self.client = client or OpenAI(
            api_key=api_key,
            base_url=self.base_url,
            timeout=300.0,
            max_retries=1,
        )

    @staticmethod
    def _parse(value: str) -> dict[str, Any]:
        try:
            result = json.loads(value)
        except json.JSONDecodeError:
            result = json.loads(repair_json(value))
        if not isinstance(result, dict):
            raise TypeError("model response must be a JSON object")
        return result

    def generate(
        self, *, prompt: str, request: dict[str, Any], stage: str
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        started = time.perf_counter()
        token_limit = (
            {"max_completion_tokens": self.max_tokens}
            if self.base_url == "https://api.openai.com/v1"
            else {"max_tokens": self.max_tokens}
        )
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": prompt},
                {
                    "role": "user",
                    "content": json.dumps(
                        request,
                        ensure_ascii=False,
                        separators=(",", ":"),
                    ),
                },
            ],
            response_format={"type": "json_object"},
            reasoning_effort=self.reasoning_effort,
            **token_limit,
        )
        content = response.choices[0].message.content
        if not isinstance(content, str) or not content.strip():
            raise ValueError("generation provider response has no content")
        body = response.model_dump()
        usage = body.get("usage") or {}
        prompt_details = usage.get("prompt_tokens_details") or {}
        completion_details = usage.get("completion_tokens_details") or {}
        input_tokens = int(usage.get("prompt_tokens") or 0)
        cached_tokens = int(prompt_details.get("cached_tokens") or 0)
        output_tokens = int(usage.get("completion_tokens") or 0)
        reasoning_tokens = int(completion_details.get("reasoning_tokens") or 0)
        return self._parse(content), {
            "stage": stage,
            "provider": (
                "openai"
                if self.base_url == "https://api.openai.com/v1"
                else "openai_compatible"
            ),
            "base_url": self.base_url,
            "model": body.get("model") or self.model,
            "reasoning_effort": self.reasoning_effort,
            "api_calls": 1,
            "latency_seconds": round(time.perf_counter() - started, 3),
            "usage": {
                "input_tokens": input_tokens,
                "cached_input_tokens": cached_tokens,
                "output_tokens": output_tokens,
                "reasoning_tokens": reasoning_tokens,
                "total_tokens": int(usage.get("total_tokens") or 0),
            },
        }
