"""
Base LLM provider interface
"""
from abc import ABC, abstractmethod
from typing import Optional

class LLMProvider(ABC):
    """Base class for LLM providers"""
    
    @abstractmethod
    async def generate_response(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        """Generate response from prompt"""
        pass

    def get_name(self) -> str:
        """Get provider name"""
        return self.__class__.__name__.lower().replace('provider', '')