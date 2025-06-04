from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import structlog

logger = structlog.get_logger()

class BasePlugin(ABC):
    """Base class for all DevOpsGPT plugins"""
    
    def __init__(self):
        self.name = self.__class__.__name__
        self.logger = logger.bind(plugin=self.name)
        
    @abstractmethod
    async def execute(self, intent: Dict[str, Any], dry_run: bool = True) -> Dict[str, Any]:
        """Execute the plugin's functionality"""
        pass
        
    @abstractmethod
    def get_capabilities(self) -> Dict[str, Any]:
        """Return the plugin's capabilities"""
        return {
            "name": self.name,
            "categories": self.get_categories(),
            "actions": self.get_actions(),
            "parameters": self.get_parameters()
        }
        
    @abstractmethod
    def get_categories(self) -> List[str]:
        """Return categories this plugin can handle"""
        pass
        
    @abstractmethod
    def get_actions(self) -> List[str]:
        """Return actions this plugin can perform"""
        pass
        
    @abstractmethod
    def get_parameters(self) -> Dict[str, Any]:
        """Return parameters this plugin accepts"""
        pass
        
    def can_handle(self, category: str) -> bool:
        """Check if plugin can handle the given category"""
        return category in self.get_categories()
        
    def validate_params(self, params: Dict[str, Any]) -> bool:
        """Validate the parameters for this plugin"""
        required_params = {
            k: v for k, v in self.get_parameters().items()
            if v.get("required", False)
        }
        
        return all(k in params for k in required_params)
        
    def log_execution(self, action: str, params: Dict[str, Any], result: Dict[str, Any]):
        """Log plugin execution details"""
        self.logger.info(
            "plugin.executed",
            action=action,
            params=params,
            success=result.get("success", False)
        )
