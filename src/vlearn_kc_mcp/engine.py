from __future__ import annotations

from importlib.resources import files
import os
from pathlib import Path

from vlearn_kc.pipeline import KCPipeline
from vlearn_kc.providers import GatewayJsonGenerator, GeminiEmbedder


class ProviderPipelineRunner:
    """Create isolated provider clients for each background KC job."""

    def __init__(
        self,
        *,
        generation_api_key: str,
        gemini_api_keys: list[str],
        generation_base_url: str = "https://api.openai.com/v1",
        generation_model: str = "gpt-5.6-luna",
        reasoning_effort: str = "high",
        gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        embedding_model: str = "gemini-embedding-2",
    ) -> None:
        if not generation_api_key.strip():
            raise ValueError("OPENAI_API_KEY is required")
        keys = [key.strip() for key in gemini_api_keys if key.strip()]
        if not keys:
            raise ValueError("GEMINI_API_KEYS or GEMINI_API_KEY is required")
        self.generation_api_key = generation_api_key
        self.gemini_api_keys = keys
        self.generation_base_url = generation_base_url
        self.generation_model = generation_model
        self.reasoning_effort = reasoning_effort
        self.gemini_base_url = gemini_base_url
        self.embedding_model = embedding_model

    @classmethod
    def from_environment(cls) -> "ProviderPipelineRunner":
        keys_value = os.getenv("GEMINI_API_KEYS", "").strip()
        if not keys_value:
            keys_value = os.getenv("GEMINI_API_KEY", "").strip()
        return cls(
            generation_api_key=os.getenv("OPENAI_API_KEY", ""),
            gemini_api_keys=[value.strip() for value in keys_value.split(",")],
            generation_base_url=os.getenv(
                "VLEARN_KC_GENERATION_BASE_URL", "https://api.openai.com/v1"
            ),
            generation_model=os.getenv(
                "VLEARN_KC_GENERATION_MODEL", "gpt-5.6-luna"
            ),
            reasoning_effort=os.getenv("VLEARN_KC_REASONING_EFFORT", "high"),
            gemini_base_url=os.getenv(
                "VLEARN_KC_GEMINI_BASE_URL",
                "https://generativelanguage.googleapis.com/v1beta",
            ),
            embedding_model=os.getenv(
                "VLEARN_KC_EMBEDDING_MODEL", "gemini-embedding-2"
            ),
        )

    def run(self, *, input_dir: Path, output_dir: Path) -> None:
        generator = GatewayJsonGenerator(
            api_key=self.generation_api_key,
            model=self.generation_model,
            base_url=self.generation_base_url,
            reasoning_effort=self.reasoning_effort,
        )
        embedder = GeminiEmbedder(
            api_keys=self.gemini_api_keys,
            model=self.embedding_model,
            base_url=self.gemini_base_url,
            cache_path=output_dir / "embedding-cache.json",
        )
        try:
            pipeline = KCPipeline(
                generator=generator,
                embedder=embedder,
                extraction_prompt=files("vlearn_kc.prompts")
                .joinpath("kc-extraction.md")
                .read_text(encoding="utf-8"),
                refinement_prompt=files("vlearn_kc.prompts")
                .joinpath("parent-refinement.md")
                .read_text(encoding="utf-8"),
            )
            pipeline.run(input_dir=input_dir, output_dir=output_dir)
        finally:
            embedder.close()
