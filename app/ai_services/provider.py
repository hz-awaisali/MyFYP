"""AI provider abstraction.

The application-writing assistant depends only on the ``AIProvider`` interface
so vendors can be swapped via configuration. OpenRouter is the default; Groq is
available for free-tier usage; a mock provider runs offline without any key.
"""

from __future__ import annotations

import abc
import json
from dataclasses import dataclass
import httpx

from app.core.config import settings
from app.core.exceptions import ValidationError


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


async def _call_openai_compatible_api(
    base_url: str,
    api_key: str,
    model: str,
    prompt: str,
    context: dict | None = None,
    extra_headers: dict | None = None,
) -> GeneratedApplication:
    if not api_key:
        raise ValidationError("AI Provider API key is missing. Please configure it in your settings.")

    system_prompt = (
        "You are an AI assistant helping a student write a formal university application.\n"
        "Based on the student's prompt and the target form fields, generate a formal application.\n"
        "You MUST respond with a JSON object containing the following keys:\n"
        "- 'subject': A brief, formal subject line for the application.\n"
        "- 'body': The full, formal body text of the application.\n"
        "- 'responses': A JSON object mapping field keys to appropriate values. "
        "For each field in the provided list, extract or generate a value that matches its label, type, options, and constraints.\n"
        "Example format:\n"
        "{\n"
        "  \"subject\": \"Request for Semester Freeze\",\n"
        "  \"body\": \"Respected Sir,\\n\\nI am writing to formally request...\",\n"
        "  \"responses\": {\n"
        "    \"reason\": \"Medical issues\",\n"
        "    \"semester\": \"5\"\n"
        "  }\n"
        "}"
    )

    fields = context.get("fields", []) if context else []
    fields_desc = "\n".join([
        f"- Key: '{f['key']}', Label: '{f['label']}', Type: '{f['type']}', Options: {f.get('options')}"
        for f in fields
    ])

    user_content = (
        f"Student prompt: {prompt}\n\n"
        f"Target form fields:\n{fields_desc}\n\n"
        "Generate the subject, body, and field responses matching the format specified."
    )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if extra_headers:
        headers.update(extra_headers)

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.2,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(base_url, headers=headers, json=payload)
            if response.status_code != 200:
                raise ValidationError(f"AI Provider error: {response.text}")
            
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            subject = parsed.get("subject", "Application Request")
            body = parsed.get("body", "")
            responses_dict = parsed.get("responses", {})

            return GeneratedApplication(
                subject=subject,
                body=body,
                structured_description=json.dumps(responses_dict),
            )
    except httpx.RequestError as exc:
        raise ValidationError(f"HTTP request to AI Provider failed: {exc}")
    except (KeyError, IndexError, json.JSONDecodeError) as exc:
        raise ValidationError(f"Failed to parse AI output: {exc}")


class OpenRouterProvider(AIProvider):
    """Default provider using OpenRouter's OpenAI-compatible chat API."""

    base_url = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(self) -> None:
        self.api_key = settings.OPENROUTER_API_KEY
        self.model = settings.OPENROUTER_MODEL

    async def generate_application(self, prompt: str, *, context: dict | None = None) -> GeneratedApplication:
        extra_headers = {
            "HTTP-Referer": "https://github.com/hz-awaisali/MyFYP",
            "X-Title": "SUMS",
        }
        return await _call_openai_compatible_api(
            self.base_url,
            self.api_key,
            self.model,
            prompt,
            context=context,
            extra_headers=extra_headers,
        )


class GroqProvider(AIProvider):
    """Groq provider (free tier friendly), OpenAI-compatible chat API."""

    base_url = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(self) -> None:
        self.api_key = settings.GROQ_API_KEY
        self.model = settings.GROQ_MODEL

    async def generate_application(self, prompt: str, *, context: dict | None = None) -> GeneratedApplication:
        return await _call_openai_compatible_api(
            self.base_url,
            self.api_key,
            self.model,
            prompt,
            context=context,
        )


class MockProvider(AIProvider):
    """Deterministic offline provider for demos/tests without an API key."""

    async def generate_application(self, prompt: str, *, context: dict | None = None) -> GeneratedApplication:
        snippet = prompt.strip()
        fields = context.get("fields", []) if context else []
        responses = {}
        # Simple mock mapping: map snippet to the first text/textarea field, or fill placeholders
        for f in fields:
            if f["type"] in ("text", "textarea"):
                responses[f["key"]] = snippet
                break
            elif f["type"] == "number":
                responses[f["key"]] = "1"
            elif f["type"] == "email":
                responses[f["key"]] = "student@university.edu"
            elif f["type"] == "phone":
                responses[f["key"]] = "+923001234567"
            elif f["type"] == "date":
                responses[f["key"]] = "2026-07-15"
            elif f["type"] in ("dropdown", "radio") and f.get("options"):
                responses[f["key"]] = str(f["options"][0])

        return GeneratedApplication(
            subject="Application Request",
            body=(
                "Respected Sir/Madam,\n\n"
                f"I am writing to formally request the following: {snippet}.\n\n"
                "I would be grateful for your kind consideration.\n\nYours sincerely,"
            ),
            structured_description=json.dumps(responses),
        )


def get_ai_provider() -> AIProvider:
    provider = settings.AI_DEFAULT_PROVIDER.lower()
    if provider == "groq":
        return GroqProvider()
    if provider == "mock":
        return MockProvider()
    return OpenRouterProvider()
