import os
import importlib
import pkgutil
import traceback
from typing import Optional, Dict, Any
from rich.console import Console
import structlog
import yaml
from devops_gpt.plugins.base import BasePlugin
from devops_gpt.utils.config import Config
from devops_gpt.llm_providers import create_llm_provider, LLMProvider

# Initialize logger
logger = structlog.get_logger()
console = Console()

class DevOpsGPT:
    def __init__(self, config_path: str = None):
        self.config = Config()  # Initialize configuration
        self.plugins: Dict[str, BasePlugin] = {}
        self.context = {}  # For storing conversation context
        self.llm_provider: Optional[LLMProvider] = None
        self.setup()
        
    def setup(self):
        """Initialize the agent with required configurations"""
        try:
            # Validate configuration
            if not self.config.validate:
                raise ValueError("Invalid configuration")
                
            # Setup LLM provider
            self.llm_provider = create_llm_provider(self.config.llm)
            logger.info("llm.provider.initialized", provider=self.llm_provider.get_name())
            
            # Initialize plugins
            self._load_plugins()
            logger.info("agent.initialized", status="success")
            
        except Exception as e:
            logger.error("agent.initialization_failed", error=str(e))
            raise
            
    def _load_plugins(self):
        """Load all available plugins"""
        try:
            # Get plugin directory path
            plugin_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'plugins')
            logger.info(f"Loading plugins from: {plugin_dir}")
            
            # Get list of plugin files
            plugin_files = [f for f in os.listdir(plugin_dir) 
                          if f.endswith('.py') and f != '__init__.py' and f != 'base.py']
            
            for plugin_file in plugin_files:
                try:
                    # Convert filename to module name
                    module_name = f"devops_gpt.plugins.{plugin_file[:-3]}"
                    
                    # Import the module
                    module = importlib.import_module(module_name)
                    
                    # Find plugin classes (subclasses of BasePlugin)
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (isinstance(attr, type) and 
                            issubclass(attr, BasePlugin) and 
                            attr != BasePlugin and 
                            not attr.__abstractmethods__):
                            
                            # Instantiate and register plugin
                            plugin = attr()
                            self.plugins[plugin.name] = plugin
                            logger.info(f"plugin.loaded", name=plugin.name)
                            
                except Exception as e:
                    logger.error(f"plugin.load_failed", 
                               name=plugin_file, 
                               error=str(e),
                               traceback=traceback.format_exc())
                    
        except Exception as e:
            logger.error("plugins.load_failed", error=str(e))

    async def execute_command(self, command: str, dry_run: bool = True) -> Dict[str, Any]:
        """Execute a command and return the result"""
        try:
            # Log command execution
            logger.info("command.executing", command=command, dry_run=dry_run)
            
            # Parse command using GPT
            intent = await self._parse_command(command)
            
            # Check security restrictions
            if not self._is_action_allowed(intent):
                return {
                    "success": False,
                    "error": "Action not allowed by security policy"
                }
            
            # Find appropriate plugin
            plugin = self._get_plugin_for_intent(intent)
            if not plugin:
                return {
                    "success": False,
                    "error": "No plugin found to handle this command"
                }
            
            # Execute through plugin
            result = await plugin.execute(intent, dry_run=dry_run)
            result["command"] = command
            logger.info("command.executed", **result)
            return result
            
        except Exception as e:
            error = {
                "success": False,
                "command": command,
                "error": str(e)
            }
            logger.error("command.failed", **error)
            return error
            
    async def _parse_command(self, command: str) -> Dict[str, Any]:
        """Parse command using LLM to determine intent and parameters"""
        try:
            prompt = """You are a DevOps command parser.
Parse the command into a structured format with:
- action: The main action to perform
- category: One of [troubleshooting, cicd, cloud, cost, security, monitoring]
- parameters: Key-value pairs of relevant parameters
- context: Any relevant context for the command

Example output format:
{
    "action": "fetch_logs",
    "category": "troubleshooting",
    "parameters": {
        "service": "frontend",
        "environment": "production",
        "time_range": "last_hour"
    },
    "context": {
        "current_namespace": "default"
    }
}

Command to parse: """ + command
            
            response = await self.llm_provider.generate_response(
                prompt=prompt,
                max_tokens=500
            )
            
            if not response:
                raise ValueError("No response from LLM provider")
            
            try:
                # Parse the response content as a Python dictionary
                content = response.strip()
                return eval(content)
            except Exception as e:
                logger.error("command.parse_failed", error=f"Failed to parse response: {str(e)}")
                raise ValueError(f"Invalid response format: {content}")
            
        except Exception as e:
            logger.error("command.parse_failed", error=str(e))
            raise
            
    def _get_plugin_for_intent(self, intent: Dict[str, Any]) -> Optional[BasePlugin]:
        """Find the appropriate plugin to handle the intent"""
        category = intent.get("category", "").lower()
        for plugin in self.plugins.values():
            if plugin.can_handle(category):
                return plugin
        return None
        
    def _is_action_allowed(self, intent: Dict[str, Any]) -> bool:
        """Check if the action is allowed by security policy"""
        action = intent.get("action", "").lower()
        allowed_actions = self.config.get('security', {}).get('allowed_actions', [])
        restricted_actions = self.config.get('security', {}).get('restricted_actions', [])
        
        if action in restricted_actions:
            return False
            
        return not allowed_actions or action in allowed_actions