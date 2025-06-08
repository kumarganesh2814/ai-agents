"""
Ollama LLM provider implementation
"""
import requests
import structlog
from typing import Optional
from .provider import LLMProvider
from .openai_provider import OpenAIProvider

logger = structlog.get_logger(__name__)

class OllamaProvider(LLMProvider):
    """
    Ollama provider for local LLM inference
    """
    def __init__(self, base_url: str, model: str, max_tokens: int,
                 fallback_provider: bool = False,
                 openai_api_key: Optional[str] = None,
                 openai_model: Optional[str] = None):
        """
        Initialize Ollama provider
        
        Args:
            base_url: Ollama API base URL e.g. http://localhost:11434
            model: Model name e.g. llama2
            max_tokens: Maximum tokens for response
            fallback_provider: Whether to enable fallback to OpenAI
            openai_api_key: Optional OpenAI API key for fallback
            openai_model: Optional OpenAI model name for fallback
        """
        super().__init__()
        self.base_url = base_url
        self.model = model
        self.max_tokens = max_tokens
        self.fallback_provider = fallback_provider
        self.openai_api_key = openai_api_key 
        self.openai_model = openai_model
        
        if fallback_provider and (not openai_api_key or not openai_model):
            raise ValueError("OpenAI API key and model required for fallback")
            
        # Initialize fallback provider
        self._fallback = None
        if fallback_provider:
            self._fallback = OpenAIProvider(openai_api_key, openai_model)

    async def _make_request(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        """Make request to Ollama API"""
        response = requests.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": max_tokens or self.max_tokens,
                    "stop": ["}"]  # Stop at JSON closing
                }
            }
        )
        
        if response.status_code != 200:
            error_msg = f"Ollama API error: {response.status_code} {response.reason}"
            if response.text:
                error_msg += f"\nResponse: {response.text}"
                
            if self.fallback_provider:
                return await self._fallback.generate_response(prompt)
            raise Exception(error_msg)
            
        response_json = response.json()
        if "response" not in response_json:
            raise ValueError(f"Unexpected response format: {response_json}")
            
        return response_json["response"]
        
    async def generate_response(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        """Generate response from prompt"""
        try:
            return await self._make_request(prompt, max_tokens)
        except Exception as e:
            if self.fallback_provider:
                # Try fallback on connection error
                return await self._fallback.generate_response(prompt)
            raise e
