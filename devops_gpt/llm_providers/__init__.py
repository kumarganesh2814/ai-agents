"""
DevOpsGPT LLM (Language Model) Provider Abstraction Layer
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, Any
import logging
import os
import openai
import requests

logger = logging.getLogger(__name__)

class LLMProvider(ABC):
    """Base class for LLM providers"""
    
    @abstractmethod
    async def generate_response(self, prompt: str, max_tokens: int = None) -> str:
        """Generate a response from the LLM"""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Get provider name"""
        pass

class OpenAIProvider(LLMProvider):
    """OpenAI API provider"""
    
    def __init__(self, api_key: str, model: str = "gpt-4"):
        self.api_key = api_key
        self.model = model
        openai.api_key = api_key
    
    async def generate_response(self, prompt: str, max_tokens: int = None) -> str:
        try:
            client = openai.Client(api_key=self.api_key)
            response = await client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise
    
    def get_name(self) -> str:
        return "openai"

class OllamaProvider(LLMProvider):
    """Ollama local LLM provider"""
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama2"):
        self.base_url = base_url.rstrip("/")
        self.model = model
    
    async def generate_response(self, prompt: str, max_tokens: int = None) -> str:
        try:
            # First try to pull the model if it's not already available
            try:
                requests.post(
                    f"{self.base_url}/api/pull",
                    json={"name": self.model}
                ).raise_for_status()
            except Exception as e:
                logger.warning(f"Failed to pull model: {e}")
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "system": "You are an AI assistant helping with DevOps tasks.",
                    "stream": False,
                    "raw": True,
                    "options": {"num_predict": max_tokens if max_tokens else 100}
                }
            )
            response.raise_for_status()
            return response.json()["response"]
        except Exception as e:
            logger.error(f"Ollama API error: {str(e)}")
            raise

    def get_name(self) -> str:
        return "ollama"

class FallbackLLMProvider(LLMProvider):
    """Provider that falls back to a secondary provider if primary fails"""
    
    def __init__(self, primary: LLMProvider, secondary: LLMProvider):
        self.primary = primary
        self.secondary = secondary
    
    async def generate_response(self, prompt: str, max_tokens: int = None) -> str:
        try:
            return await self.primary.generate_response(prompt, max_tokens)
        except Exception as e:
            logger.warning(f"Primary LLM failed: {e}, falling back to secondary")
            return await self.secondary.generate_response(prompt, max_tokens)
    
    def get_name(self) -> str:
        return f"{self.primary.get_name()}+{self.secondary.get_name()}"

def create_llm_provider(config: Dict[str, Any]) -> LLMProvider:
    """Factory function to create LLM provider based on config"""
    provider = config.get("provider", "openai").lower()
    fallback = config.get("fallback_provider", False)
    
    # Create OpenAI provider if configured
    openai_provider = None
    if provider == "openai" or fallback:
        api_key = config.get("api_key") or os.getenv("OPENAI_API_KEY")
        if api_key:
            openai_provider = OpenAIProvider(api_key, config.get("model", "gpt-4"))
    
    # Create Ollama provider if configured
    ollama_provider = None
    if provider == "ollama" or fallback:
        ollama_provider = OllamaProvider(
            config.get("base_url", "http://localhost:11434"),
            config.get("ollama_model", "llama2")
        )
    
    # Set up provider based on configuration
    if provider == "openai" and openai_provider:
        return FallbackLLMProvider(openai_provider, ollama_provider) if fallback else openai_provider
    elif provider == "ollama" and ollama_provider:
        return ollama_provider
    elif fallback and ollama_provider:
        return ollama_provider
    else:
        raise ValueError(f"No valid LLM provider configured. Provider: {provider}, Fallback: {fallback}")
