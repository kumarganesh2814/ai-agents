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

def create_llm_provider(config: Dict[str, Any]) -> LLMProvider:
    """Create LLM provider based on configuration"""
    provider_type = config.get('llm', {}).get('provider', 'openai').lower()
    
    if provider_type == 'openai':
        api_key = config.get('llm', {}).get('openai_api_key') or os.getenv('OPENAI_API_KEY')
        model = config.get('llm', {}).get('openai_model', 'gpt-4')
        if not api_key:
            raise ValueError("OpenAI API key required")
        return OpenAIProvider(api_key, model)
        
    elif provider_type == 'ollama':
        base_url = config.get('llm', {}).get('base_url', 'http://localhost:11434')
        model = config.get('llm', {}).get('model', 'llama2')
        max_tokens = config.get('llm', {}).get('max_tokens', 500)
        fallback_provider = config.get('llm', {}).get('fallback_provider', False)
        
        # Optional fallback config
        openai_api_key = None
        openai_model = None
        if fallback_provider:
            openai_api_key = config.get('llm', {}).get('openai_api_key')
            openai_model = config.get('llm', {}).get('openai_model')
            
        return OllamaProvider(
            base_url=base_url,
            model=model, 
            max_tokens=max_tokens,
            fallback_provider=fallback_provider,
            openai_api_key=openai_api_key,
            openai_model=openai_model
        )
        
    else:
        raise ValueError(f"Unknown LLM provider type: {provider_type}")

class OllamaProvider(LLMProvider):
    """Ollama provider for local LLM inference"""
    
    def __init__(self, base_url: str, model: str, max_tokens: int,
                 fallback_provider: bool = False,
                 openai_api_key: Optional[str] = None,
                 openai_model: Optional[str] = None):
        """Initialize Ollama provider"""
        self.base_url = base_url
        self.model = model 
        self.max_tokens = max_tokens
        self.fallback_provider = fallback_provider
        self.openai_api_key = openai_api_key
        self.openai_model = openai_model
        
        # Initialize fallback provider
        self._fallback = None 
        if fallback_provider:
            if not openai_api_key or not openai_model:
                raise ValueError("OpenAI API key and model required for fallback")
            self._fallback = OpenAIProvider(openai_api_key, openai_model)
    
    async def generate_response(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        """Generate response from prompt"""
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "max_tokens": max_tokens or self.max_tokens
                }
            )
            
            if response.status_code != 200:
                if self.fallback_provider:
                    # Try fallback to OpenAI
                    return await self._fallback.generate_response(prompt, max_tokens)
                raise Exception(f"Ollama API error: {response.json()}")
                
            return response.json()["response"]
            
        except Exception as e:
            if self.fallback_provider:
                # Try fallback on connection error
                return await self._fallback.generate_response(prompt, max_tokens)
            raise e
    
    def get_name(self) -> str:
        return "ollama"
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
