"""
LLM Integration Module
Handles communication with LLM providers (Ollama and OpenAI) with fallback support
"""
import openai
import requests
import logging
from typing import Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential
from config import settings
import time

logger = logging.getLogger(__name__)


class LLMClient:
    """Client for interacting with LLM providers"""

    def __init__(self):
        self.primary_provider = settings.LLM_PROVIDER
        self.ollama_url = settings.OLLAMA_URL
        self.ollama_model = settings.LLM_MODEL
        self.openai_model = settings.OPENAI_MODEL

        if settings.OPENAI_API_KEY:
            openai.api_key = settings.OPENAI_API_KEY

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def generate_thought(self, prompt: str, context: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate an LLM thought based on prompt and context

        Args:
            prompt: The main prompt/question for the LLM
            context: Optional context to include

        Returns:
            Dictionary with thought, model used, tokens, and processing time
        """
        start_time = time.time()

        # Construct full prompt
        full_prompt = self._construct_prompt(prompt, context)

        try:
            # Try primary provider
            if self.primary_provider == "ollama":
                result = self._call_ollama(full_prompt)
            else:
                result = self._call_openai(full_prompt)

        except Exception as e:
            logger.warning(f"Primary LLM provider failed: {e}. Trying fallback...")

            # Fallback to alternative provider
            try:
                if self.primary_provider == "ollama":
                    result = self._call_openai(full_prompt)
                    result['model_used'] = f"openai-{self.openai_model}"
                else:
                    result = self._call_ollama(full_prompt)
                    result['model_used'] = f"ollama-{self.ollama_model}"
            except Exception as fallback_error:
                logger.error(f"Fallback LLM provider also failed: {fallback_error}")
                raise

        processing_time = int((time.time() - start_time) * 1000)
        result['processing_time_ms'] = processing_time

        return result

    def _construct_prompt(self, prompt: str, context: Optional[str] = None) -> str:
        """Construct the full prompt with context and instructions"""
        system_instruction = """You are an AI analyst for cryptocurrency token monitoring.
Your task is to analyze events related to token activity (price changes, large transfers, news, etc.)
and provide insights on potential impacts, risks, and market implications.
Be concise, analytical, and focus on actionable insights."""

        if context:
            full_prompt = f"""{system_instruction}

Previous Context:
{context}

New Event:
{prompt}

Analyze this event in the context of previous information. Provide insights on:
1. Immediate impact on token value/sentiment
2. Potential risks or opportunities
3. Recommended monitoring focus areas
"""
        else:
            full_prompt = f"""{system_instruction}

Event to Analyze:
{prompt}

Provide analysis on:
1. Immediate impact on token value/sentiment
2. Potential risks or opportunities
3. Recommended monitoring focus areas
"""

        return full_prompt

    def _call_ollama(self, prompt: str) -> Dict[str, Any]:
        """Call Ollama API"""
        url = f"{self.ollama_url}/api/generate"

        payload = {
            "model": self.ollama_model,
            "prompt": prompt,
            "stream": False
        }

        response = requests.post(
            url,
            json=payload,
            timeout=settings.LLM_TIMEOUT
        )
        response.raise_for_status()

        data = response.json()

        return {
            'thought': data.get('response', ''),
            'model_used': f"ollama-{self.ollama_model}",
            'tokens_used': data.get('eval_count', 0)
        }

    def _call_openai(self, prompt: str) -> Dict[str, Any]:
        """Call OpenAI API"""
        if not settings.OPENAI_API_KEY:
            raise ValueError("OpenAI API key not configured")

        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

        response = client.chat.completions.create(
            model=self.openai_model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            timeout=settings.LLM_TIMEOUT
        )

        return {
            'thought': response.choices[0].message.content,
            'model_used': f"openai-{self.openai_model}",
            'tokens_used': response.usage.total_tokens if response.usage else 0
        }


# Global LLM client instance
llm_client = LLMClient()
