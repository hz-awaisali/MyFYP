"""AI provider abstraction.

The application-writing assistant depends only on the ``AIProvider`` interface
so vendors can be swapped via configuration. OpenRouter is the default; Groq is
available for free-tier usage; a mock provider runs offline without any key.

Concrete request/response handling (and ai_requests persistence) is wired up in
Phase 2; the interface and provider selection live here so the seam exists now.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass

from app.core.config import settings


@dataclass
class GeneratedApplication:
    subject: str
    body: str
    structured_description: str


class AIProvider(abc.ABC):
    """Generates a formal application from a student's natural-language prompt."""

    @abc.abstractmethod
    async def generate_application(self, prompt: str, *, context: dict | None = None) -> GeneratedApplication:
        ...


class OpenRouterProvider(AIProvider):
    """Default provider using OpenRouter's OpenAI-compatible chat API."""

    base_url = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(self) -> None:
        self.api_key = settings.OPENROUTER_API_KEY
        self.model = settings.OPENROUTER_MODEL

    async def generate_application(self, prompt: str, *, context: dict | None = None) -> GeneratedApplication:
        raise NotImplementedError("OpenRouter generation is implemented in Phase 2")


class GroqProvider(AIProvider):
    """Groq provider (free tier friendly), OpenAI-compatible chat API."""

    base_url = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(self) -> None:
        self.api_key = settings.GROQ_API_KEY
        self.model = settings.GROQ_MODEL

    async def generate_application(self, prompt: str, *, context: dict | None = None) -> GeneratedApplication:
        raise NotImplementedError("Groq generation is implemented in Phase 2")


class MockProvider(AIProvider):
    """Deterministic offline provider for demos/tests without an API key."""

    async def generate_application(self, prompt: str, *, context: dict | None = None) -> GeneratedApplication:
        snippet = prompt.strip()
        return GeneratedApplication(
            subject="Application Request",
            body=(
                "Respected Sir/Madam,\n\n"
                f"I am writing to formally request the following: {snippet}.\n\n"
                "I would be grateful for your kind consideration.\n\nYours sincerely,"
            ),
            structured_description=snippet,
        )


def get_ai_provider() -> AIProvider:
    provider = settings.AI_DEFAULT_PROVIDER.lower()
    if provider == "groq":
        return GroqProvider()
    if provider == "mock":
        return MockProvider()
    return OpenRouterProvider()
