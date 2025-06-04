from typing import Dict, Optional
from dataclasses import dataclass, asdict
import json

@dataclass
class Context:
    namespace: str = "default"
    service: Optional[str] = None
    environment: str = "prod"
    last_resource: Optional[str] = None
    current_operation: Optional[str] = None

class ContextManager:
    def __init__(self):
        self.context = Context()
        self.history: List[Dict] = []
    
    def update_context(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self.context, key):
                setattr(self.context, key, value)
    
    def get_context(self) -> Context:
        return self.context
    
    def add_to_history(self, command: str, result: str):
        self.history.append({
            "command": command,
            "result": result,
            "context": asdict(self.context)
        })