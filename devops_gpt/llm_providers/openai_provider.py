"""
OpenAI LLM provider implementation
"""
import openai
import structlog
from typing import Optional
from .provider import LLMProvider

logger = structlog.get_logger(__name__)

class OpenAIProvider(LLMProvider):
    """OpenAI provider implementation"""
    
    def __init__(self, api_key: str, model: str = "gpt-4"):
        super().__init__()
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model
        
    async def generate_response(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        """Generate response using OpenAI API"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=0
            )
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error("openai.request_failed", error=str(e))
            raise