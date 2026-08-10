"""Core annotation logic for SkillPrimitives."""

from __future__ import annotations

import json
import os
from typing import Any, cast

from skill_primitives.core.base import SkillPrimitive
from skill_primitives.core.registry import PrimitiveRegistry
from skill_primitives.utils.config import load_config
from skill_primitives.utils.logging import get_logger

logger = get_logger(__name__)


class PrimitiveAnnotator:
    """Annotates skill primitives with metadata using LLM providers."""

    def __init__(
        self,
        provider: str = "ollama",
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self.provider = provider
        self.model = model
        self.api_key = api_key or os.getenv(f"{provider.upper()}_API_KEY")
        self.base_url = base_url
        self._client: Any = None
        self._config = load_config()

    def annotate(self, primitive: SkillPrimitive) -> dict[str, Any]:
        """Annotate a single primitive with metadata."""
        prompt = self._build_prompt(primitive)
        response = self._call_llm(prompt)
        return self._parse_response(response)

    def annotate_batch(self, primitives: list[SkillPrimitive]) -> list[dict[str, Any]]:
        """Annotate multiple primitives."""
        return [self.annotate(p) for p in primitives]

    def annotate_from_registry(self, registry: PrimitiveRegistry) -> dict[str, dict[str, Any]]:
        """Annotate all primitives in a registry."""
        results = {}
        for name, primitive in registry.items():
            results[name] = self.annotate(primitive)
        return results

    def _get_client(self) -> Any:
        """Initialize and return the LLM client."""
        if self._client is not None:
            return self._client

        if self.provider == "ollama":
            try:
                import ollama

                self._client = ollama
            except ImportError as err:
                raise ImportError("Ollama not installed. Install with: pip install ollama") from err

        elif self.provider == "groq":
            try:
                from groq import Groq

                self._client = Groq(api_key=self.api_key)
            except ImportError as err:
                raise ImportError("Groq SDK not installed. Install with: pip install groq") from err

        elif self.provider == "openai":
            try:
                from openai import OpenAI

                self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            except ImportError as err:
                raise ImportError(
                    "OpenAI SDK not installed. Install with: pip install openai"
                ) from err

        else:
            raise ValueError(f"Unknown provider: {self.provider}. Supported: ollama, groq, openai")

        return self._client

    def _build_prompt(self, primitive: dict[str, Any]) -> str:
        """Build a prompt for LLM annotation."""
        return f"""Analyze this skill primitive and provide structured metadata.

Primitive Name: {primitive.get("name", "Unknown")}
Description: {primitive.get("description", "No description provided")}
Parameters: {json.dumps(primitive.get("parameters", {}), indent=2)}

Provide output as JSON with these fields:
- summary: Brief description of what this primitive does
- category: Functional category (e.g., "data_processing", "api_call", "validation")
- complexity: "simple", "moderate", or "complex"
- dependencies: List of other primitives or external resources needed
- examples: List of usage examples
"""

    def _call_llm(self, prompt: str) -> str:
        """Call the LLM with the given prompt."""
        client = self._get_client()
        model = self.model or self._config.get("default_model", "llama3.1")

        if self.provider == "ollama":
            response = client.chat(
                model=model,
                messages=[{"role": "user", "content": prompt}],
            )
            return cast(str, response["message"]["content"])

        elif self.provider in ("groq", "openai"):
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )
            return cast(str, response.choices[0].message.content)

        raise ValueError(f"Unsupported provider: {self.provider}")

    def _parse_response(self, response: str) -> dict[str, Any]:
        """Parse LLM response into structured metadata."""
        try:
            # Try to extract JSON from markdown code blocks
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response.strip()

            return cast(dict[str, Any], json.loads(json_str))
        except (json.JSONDecodeError, IndexError) as err:
            logger.warning(f"Failed to parse LLM response as JSON: {err}")
            return {"raw_response": response, "parse_error": str(err)}


# Backward-compatible aliases for mypy and import compatibility
Annotator = PrimitiveAnnotator


def annotate_primitives(
    primitives: list[SkillPrimitive],
    provider: str = "ollama",
    model: str | None = None,
    api_key: str | None = None,
) -> list[dict[str, Any]]:
    """Convenience function to annotate a list of primitives."""
    annotator = PrimitiveAnnotator(provider=provider, model=model, api_key=api_key)
    return annotator.annotate_batch(primitives)
