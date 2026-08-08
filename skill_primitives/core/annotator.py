"""LLM-based natural language annotation of skill primitives.

Annotates segmented primitives with natural language descriptions
using local or API-based language models.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import ollama

try:
    import ollama
except ImportError:
    ollama = None


class Annotator:
    """Annotate primitives with natural language descriptions.

    Supports multiple LLM providers:
    - "ollama": Local models via Ollama (default, no API key needed)
    - "groq": Groq API (fast, requires GROQ_API_KEY)
    - "openai": OpenAI API (requires OPENAI_API_KEY)

    Falls back to template-based descriptions if no LLM is available.
    """

    # Default natural language templates for each primitive type
    TEMPLATES: dict[str, str] = {
        "reach": "reach toward the target object",
        "grasp": "grasp the object firmly",
        "lift": "lift the object vertically",
        "transport": "transport the object to the destination",
        "place": "place the object gently",
    }

    def __init__(
        self,
        provider: str = "ollama",
        model: str = "llama3.1",
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        """Initialize the annotator.

        Args:
            provider: LLM provider name ("ollama", "groq", "openai").
            model: Model name for the provider.
            api_key: API key for the provider. If None, reads from env var.
            base_url: Custom base URL for the API (e.g., local OpenAI-compatible server).
        """
        self.provider = provider.lower()
        self.model = model
        self.api_key = api_key or self._get_api_key()
        self.base_url = base_url
        self._client: Any | None = None

    def _get_api_key(self) -> str | None:
        """Get API key from environment variable based on provider."""
        env_vars = {
            "groq": "GROQ_API_KEY",
            "openai": "OPENAI_API_KEY",
            "ollama": None,
        }
        var = env_vars.get(self.provider)
        return os.environ.get(var) if var else None

    def _get_client(self) -> Any:
        """Lazy-load the LLM client."""
        if self._client is not None:
            return self._client

        if self.provider == "ollama":
            try:
                import ollama

                self._client = ollama
            except ImportError as err:
                raise ImportError(
                    "Ollama not installed. Install with: pip install ollama "
                    "or use --provider groq/openai"
                ) from err

        elif self.provider == "groq":
            try:
                from groq import Groq

                self._client = Groq(api_key=self.api_key)
            except ImportError as err:
                raise ImportError("Groq SDK not installed. Install with: pip install groq") from err

        elif self.provider == "openai":
            try:
                from openai import OpenAI  # type: ignore[import-not-found]

                kwargs = {"api_key": self.api_key}
                if self.base_url:
                    kwargs["base_url"] = self.base_url
                self._client = OpenAI(**kwargs)
            except ImportError as err:
                raise ImportError(
                    "OpenAI SDK not installed. Install with: pip install openai"
                ) from err

        else:
            raise ValueError(
                f"Unknown provider: {self.provider}. " "Supported: ollama, groq, openai"
            )

        return self._client

    def _build_prompt(self, primitive: dict[str, Any]) -> str:
        """Build a prompt for the LLM to describe a primitive.

        Args:
            primitive: Dict with at least a 'type' key.

        Returns:
            Prompt string for the LLM.
        """
        ptype = primitive.get("type", "unknown")
        start = primitive.get("start", 0)
        end = primitive.get("end", 0)
        confidence = primitive.get("confidence", 0.0)

        prompt = f"""You are a robot motion descriptor. Given a robot manipulation primitive, generate a concise natural language command (5-10 words) that a human could use to instruct a robot.

Primitive type: {ptype}
Frame range: {start} to {end}
Confidence: {confidence:.2f}

Rules:
- Use imperative mood (e.g., "reach toward", "grasp firmly")
- Be specific about the action
- Keep it under 10 words
- Do not explain, only output the command

Command:"""
        return prompt

    def _call_llm(self, prompt: str) -> str:
        """Call the LLM with a prompt and return the response text.

        Args:
            prompt: The prompt string.

        Returns:
            Generated text from the LLM.
        """
        client = self._get_client()

        if self.provider == "ollama":
            response = client.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.3, "num_predict": 30},
            )
            return response["message"]["content"].strip()  # type: ignore[no-any-return]

        elif self.provider == "groq" or self.provider == "openai":
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=30,
            )
            return response.choices[0].message.content.strip()  # type: ignore[no-any-return]

        return ""

    def annotate(self, primitive: dict[str, Any]) -> str:
        """Generate a natural language description for a single primitive.

        Tries LLM first, falls back to template if LLM fails.

        Args:
            primitive: Dict with at least a 'type' key.

        Returns:
            Natural language command string.
        """
        ptype = primitive.get("type", "unknown")

        # Try LLM annotation
        try:
            prompt = self._build_prompt(primitive)
            description = self._call_llm(prompt)
            if description:
                return description
        except Exception:
            # LLM failed (not installed, no API key, model not available)
            pass

        # Fallback to template
        return self.TEMPLATES.get(ptype, f"perform {ptype}")

    def annotate_batch(
        self,
        primitives: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Annotate a batch of primitives with natural language descriptions.

        Args:
            primitives: List of primitive dicts.

        Returns:
            List of primitive dicts with added "description" key.
        """
        annotated = []
        for _i, primitive in enumerate(primitives):
            desc = self.annotate(primitive)
            annotated_primitive = dict(primitive)
            annotated_primitive["description"] = desc
            annotated.append(annotated_primitive)

        return annotated


def annotate_primitives(
    primitives: list[dict[str, Any]],
    provider: str = "ollama",
    model: str = "llama3.1",
) -> list[dict[str, Any]]:
    """Convenience function to annotate a list of primitives.

    Args:
        primitives: List of primitive dicts.
        provider: LLM provider name.
        model: Model name.

    Returns:
        List of annotated primitive dicts.
    """
    annotator = Annotator(provider=provider, model=model)
    return annotator.annotate_batch(primitives)
