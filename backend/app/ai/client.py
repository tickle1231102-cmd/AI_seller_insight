from __future__ import annotations

import os
from typing import TypeVar

from pydantic import BaseModel, ValidationError


TModel = TypeVar("TModel", bound=BaseModel)


class LLMClientError(RuntimeError):
    """Normalized AI-provider failure that must not leak provider exceptions."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class OpenAIStructuredClient:
    """Small OpenAI Responses API adapter with structured-output validation."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: float | None = None,
        client: object | None = None,
    ) -> None:
        # OPENAI_API_KEY is the preferred name. LLM_API_KEY keeps compatibility
        # with the current TECH_SPEC while B finalizes shared environment names.
        self.api_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
        self.model = model or os.getenv("LLM_MODEL") or "gpt-6-luna"
        self.timeout_seconds = (
            timeout_seconds
            if timeout_seconds is not None
            else float(os.getenv("LLM_TIMEOUT_SECONDS") or 30)
        )
        self._client = client

    def _get_client(self) -> object:
        if self._client is not None:
            return self._client

        if not self.api_key:
            raise LLMClientError(
                "missing_api_key",
                "OPENAI_API_KEY (or LLM_API_KEY) is not configured.",
            )

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise LLMClientError(
                "missing_dependency",
                "The 'openai' Python package is not installed.",
            ) from exc

        self._client = OpenAI(
            api_key=self.api_key,
            timeout=self.timeout_seconds,
            max_retries=0,
        )
        return self._client

    def generate_structured(
        self,
        *,
        schema: type[TModel],
        instructions: str,
        input_text: str,
        max_output_tokens: int = 600,
    ) -> TModel:
        """Return a Pydantic-validated structured response.

        JSON/validation failures are retried once. Provider/network failures are
        normalized immediately so the backend can keep KPI responses alive.
        """

        client = self._get_client()
        last_validation_error: Exception | None = None

        for _attempt in range(2):
            try:
                response = client.responses.parse(
                    model=self.model,
                    instructions=instructions,
                    input=input_text,
                    text_format=schema,
                    max_output_tokens=max_output_tokens,
                )
                parsed = response.output_parsed
                if parsed is None:
                    raise ValueError("OpenAI returned no parsed structured output.")
                if not isinstance(parsed, schema):
                    parsed = schema.model_validate(parsed)
                return parsed
            except (ValidationError, ValueError, TypeError) as exc:
                last_validation_error = exc
                continue
            except Exception as exc:
                raise LLMClientError(
                    "provider_error",
                    "OpenAI request failed.",
                ) from exc

        raise LLMClientError(
            "invalid_structured_output",
            "OpenAI returned invalid structured output after one retry.",
        ) from last_validation_error
