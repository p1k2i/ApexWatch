"""
LLM Integration Module
Handles communication with OpenAI-compatible API providers
"""
import openai
import logging
from typing import Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential
from config import settings
import time

logger = logging.getLogger(__name__)


class LLMClient:
    """Client for interacting with OpenAI-compatible API"""

    def __init__(self):
        self.api_url = settings.OPENAI_API_URL
        self.api_key = settings.OPENAI_API_KEY
        self.model = settings.OPENAI_API_MODEL

        if not self.api_key:
            logger.warning("OPENAI_API_KEY not set. LLM functionality may be limited.")

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

        # Call OpenAI-compatible API
        result = self._call_openai_compatible(full_prompt)

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

    def _call_openai_compatible(self, prompt: str) -> Dict[str, Any]:
        """Call OpenAI-compatible API"""
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not configured")

        client = openai.OpenAI(
            api_key=self.api_key,
            base_url=self.api_url
        )

        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            timeout=settings.LLM_TIMEOUT
        )

        return {
            'thought': response.choices[0].message.content,
            'model_used': self.model,
            'tokens_used': response.usage.total_tokens if response.usage else 0
        }


# Global LLM client instance
llm_client = LLMClient()
