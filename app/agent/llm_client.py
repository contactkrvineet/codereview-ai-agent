"""
Pluggable LLM client supporting multiple backends.

Why this exists: LLM providers change pricing, capabilities, and APIs frequently.
The agent code shouldn't care which backend is used — that's separable.
Each provider implements the same `complete()` interface.
"""

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

import requests


@dataclass
class LLMResponse:
    """Normalized response from any LLM provider."""

    text: str
    provider: str
    model: str
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None


class LLMClient(ABC):
    """Base class for all LLM providers."""

    @abstractmethod
    def complete(self, system_prompt: str, user_prompt: str, max_tokens: int = 2000) -> LLMResponse:
        """Execute an LLM call and return normalized response."""
        ...


class OllamaClient(LLMClient):
    """
    Local Ollama backend. No API key needed.

    Setup:
        curl -fsSL https://ollama.com/install.sh | sh
        ollama pull qwen2.5-coder:7b
    """

    def __init__(self, model: str = "qwen2.5-coder:7b", host: str = "http://localhost:11434"):
        self.model = model
        self.host = host

    def complete(self, system_prompt: str, user_prompt: str, max_tokens: int = 2000) -> LLMResponse:
        response = requests.post(
            f"{self.host}/api/chat",
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "stream": False,
                "options": {"num_predict": max_tokens, "temperature": 0.2},
            },
            timeout=120,
        )
        response.raise_for_status()
        data = response.json()
        return LLMResponse(
            text=data["message"]["content"],
            provider="ollama",
            model=self.model,
            prompt_tokens=data.get("prompt_eval_count"),
            completion_tokens=data.get("eval_count"),
        )


class GeminiClient(LLMClient):
    """
    Google Gemini backend. Free tier available.

    Setup:
        Get API key: https://aistudio.google.com/apikey
        export GEMINI_API_KEY=your_key_here
    """

    def __init__(self, model: str = "gemini-2.5-flash", api_key: Optional[str] = None):
        self.model = model
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not set in environment")

    def complete(self, system_prompt: str, user_prompt: str, max_tokens: int = 2000) -> LLMResponse:
        # Using direct REST API to avoid SDK version coupling
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent?key={self.api_key}"
        )
        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": 0.2,
                "responseMimeType": "application/json",
            },
        }
        import time as _time
        import logging as _logging
        _log = _logging.getLogger(__name__)
        response = None
        for attempt in range(3):  # up to 3 attempts (2 retries on 429)
            response = requests.post(url, json=payload, timeout=60)
            if response.status_code == 429:
                # Parse retryDelay from Gemini response body, else default to 65s
                wait = 65
                try:
                    details = response.json().get("error", {}).get("details", [])
                    for d in details:
                        delay = d.get("retryDelay", "")
                        if delay and delay.endswith("s"):
                            wait = int(delay[:-1]) + 5
                            break
                except Exception:
                    pass
                _log.warning("Gemini 429 rate limit — waiting %ds before retry (attempt %d/3)", wait, attempt + 1)
                _time.sleep(wait)
                continue
            break
        response.raise_for_status()
        data = response.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        usage = data.get("usageMetadata", {})
        return LLMResponse(
            text=text,
            provider="gemini",
            model=self.model,
            prompt_tokens=usage.get("promptTokenCount"),
            completion_tokens=usage.get("candidatesTokenCount"),
        )


class OpenAIClient(LLMClient):
    """OpenAI backend. Paid (cheap for review-sized prompts)."""

    def __init__(self, model: str = "gpt-4o-mini", api_key: Optional[str] = None):
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not set in environment")

    def complete(self, system_prompt: str, user_prompt: str, max_tokens: int = 2000) -> LLMResponse:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "max_tokens": max_tokens,
                "temperature": 0.2,
                "response_format": {"type": "json_object"},
            },
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        return LLMResponse(
            text=data["choices"][0]["message"]["content"],
            provider="openai",
            model=self.model,
            prompt_tokens=data["usage"]["prompt_tokens"],
            completion_tokens=data["usage"]["completion_tokens"],
        )


class ClaudeClient(LLMClient):
    """Anthropic Claude backend. Paid."""

    def __init__(self, model: str = "claude-sonnet-4-6", api_key: Optional[str] = None):
        self.model = model
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not set in environment")

    def complete(self, system_prompt: str, user_prompt: str, max_tokens: int = 2000) -> LLMResponse:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": self.model,
                "max_tokens": max_tokens,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_prompt}],
            },
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        return LLMResponse(
            text=data["content"][0]["text"],
            provider="anthropic",
            model=self.model,
            prompt_tokens=data["usage"]["input_tokens"],
            completion_tokens=data["usage"]["output_tokens"],
        )


def get_client(provider: str, model: Optional[str] = None, **kwargs) -> LLMClient:
    """
    Factory for LLM clients. Lets the CLI/agent layer stay provider-agnostic.

        client = get_client("ollama", model="qwen2.5-coder:7b")
        client = get_client("gemini")  # uses default model and env var for key
    """
    providers = {
        "ollama": OllamaClient,
        "gemini": GeminiClient,
        "openai": OpenAIClient,
        "anthropic": ClaudeClient,
        "claude": ClaudeClient,
    }
    if provider not in providers:
        raise ValueError(
            f"Unknown provider '{provider}'. Available: {', '.join(providers.keys())}"
        )
    kwargs = {k: v for k, v in kwargs.items() if v is not None}
    if model is not None:
        kwargs["model"] = model
    return providers[provider](**kwargs)
