import os
import structlog
from typing import Optional
from dotenv import load_dotenv

logger = structlog.get_logger(__name__)

class Config:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initialize configuration"""
        # Load environment variables from .env file
        load_dotenv()
        
        # Log environment status
        env_path = os.path.join(os.getcwd(), '.env')
        logger.debug("env_file", path=env_path, exists=os.path.exists(env_path))
        
        # Load LLM configuration
        self.llm = {
            'provider': os.getenv('LLM_PROVIDER', 'ollama').lower(),
            'base_url': os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434'),
            'model': os.getenv('OLLAMA_MODEL', 'llama2'),
            'max_tokens': int(os.getenv('MAX_TOKENS', '500')),
            'openai_api_key': os.getenv('OPENAI_API_KEY', '').strip(),
            'openai_model': os.getenv('OPENAI_MODEL', 'gpt-4.5-preview'),
            'fallback_provider': os.getenv('FALLBACK_PROVIDER', 'false').lower() == 'true'
        }
        
        logger.debug("llm_config", provider=self.llm['provider'])
        
        # Logging Configuration
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        
        # Application Configuration
        self.dry_run_default = os.getenv('DRY_RUN_DEFAULT', 'true').lower() == 'true'
        
    @property
    def validate(self) -> bool:
        """Validate configuration"""
        if self.llm['provider'] == 'openai':
            if not self.llm['openai_api_key']:
                logger.error("config.validation_failed", error="OpenAI API key not set")
                return False
            if not self.llm['openai_api_key'].startswith('sk-'):
                logger.error("config.validation_failed", error="Invalid OpenAI API key format")
                return False
        elif self.llm['provider'] == 'ollama':
            # Basic validation for Ollama configuration
            if not self.llm['base_url']:
                logger.error("config.validation_failed", error="Ollama base URL not set")
                return False
            if not self.llm['model']:
                logger.error("config.validation_failed", error="Ollama model not set")
                return False
                
            # If fallback is enabled, validate OpenAI config
            if self.llm['fallback_provider']:
                if not self.llm['openai_api_key'] or not self.llm['openai_model']:
                    logger.error("config.validation_failed", error="OpenAI fallback configuration incomplete")
                    return False
        else:
            logger.error("config.validation_failed", error=f"Unknown provider: {self.llm['provider']}")
            return False
            
        logger.info("config.validated", status="success")
        return True
