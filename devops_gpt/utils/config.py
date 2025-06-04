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
        
        # OpenAI Configuration
        self.openai_api_key = os.getenv('OPENAI_API_KEY', '').strip()
        logger.debug("api_key", present=bool(self.openai_api_key), 
                    length=len(self.openai_api_key) if self.openai_api_key else 0)
        
        # Logging Configuration
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        
        # Application Configuration
        self.dry_run_default = os.getenv('DRY_RUN_DEFAULT', 'true').lower() == 'true'
        
        # Model Configuration
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4.5-preview')
        
    @property
    def validate(self) -> bool:
        """Validate configuration"""
        if not self.openai_api_key:
            logger.error("config.validation_failed", error="OpenAI API key not set")
            return False
            
        if not self.openai_api_key.startswith('sk-'):
            logger.error("config.validation_failed", error="Invalid OpenAI API key format")
            return False
            
        logger.info("config.validated", status="success")
        return True
