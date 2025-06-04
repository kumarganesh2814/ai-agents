import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict, field
import os
import logging
from enum import Enum
from threading import Lock
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StateChangeEvent(Enum):
    CONTEXT_UPDATED = "context_updated"
    COMMAND_EXECUTED = "command_executed"
    SESSION_STARTED = "session_started"
    SESSION_ENDED = "session_ended"
    ERROR_OCCURRED = "error_occurred"

@dataclass
class AgentState:
    """Maintains agent's operational state"""
    # Core state
    current_context: str
    last_command: Optional[str]
    environment: str
    session_start: str
    execution_history: List[Dict[str, Any]] = field(default_factory=list)
    
    # Enhanced state tracking
    active_services: List[str] = field(default_factory=list)
    resource_states: Dict[str, Any] = field(default_factory=dict)
    error_count: int = 0
    last_error: Optional[str] = None
    
    # Session metrics
    successful_commands: int = 0
    failed_commands: int = 0
    total_execution_time: float = 0.0
    
    # Plugin states
    plugin_states: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentState':
        """Create state from dictionary"""
        return cls(**data)

class StateManager:
    def __init__(self, state_file: str = "agent_state.json", backup_dir: str = "state_backups"):
        self.state_file = state_file
        self.backup_dir = backup_dir
        self._lock = Lock()
        self._observers: Dict[StateChangeEvent, List[callable]] = {event: [] for event in StateChangeEvent}
        
        # Ensure backup directory exists
        Path(backup_dir).mkdir(parents=True, exist_ok=True)
        
        # Load or create initial state
        self.state = self._load_state()

    def _load_state(self) -> AgentState:
        """Load state from file with fallback to backup"""
        try:
            # Try loading from main file
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    return AgentState.from_dict(data)
            
            # Try loading from latest backup
            latest_backup = self._get_latest_backup()
            if latest_backup:
                logger.info(f"Loading state from backup: {latest_backup}")
                with open(latest_backup, 'r') as f:
                    data = json.load(f)
                    return AgentState.from_dict(data)
            
            return self._create_initial_state()
            
        except Exception as e:
            logger.error(f"Error loading state: {e}")
            return self._create_initial_state()

    def _create_initial_state(self) -> AgentState:
        """Create fresh initial state"""
        return AgentState(
            current_context="default",
            last_command=None,
            environment="development",
            session_start=datetime.now().isoformat()
        )

    def register_observer(self, event: StateChangeEvent, callback: callable):
        """Register observer for state changes"""
        self._observers[event].append(callback)

    def _notify_observers(self, event: StateChangeEvent, data: Any = None):
        """Notify observers of state change"""
        for callback in self._observers[event]:
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Error in observer callback: {e}")

    def save_state(self):
        """Save state to file and create backup"""
        with self._lock:
            try:
                # Save to main file
                with open(self.state_file, 'w') as f:
                    json.dump(self.state.to_dict(), f, indent=2)
                
                # Create backup
                backup_file = os.path.join(
                    self.backup_dir, 
                    f"state_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                )
                with open(backup_file, 'w') as f:
                    json.dump(self.state.to_dict(), f, indent=2)
                
                # Cleanup old backups (keep last 5)
                self._cleanup_old_backups()
                
            except Exception as e:
                logger.error(f"Error saving state: {e}")
                self._notify_observers(StateChangeEvent.ERROR_OCCURRED, str(e))

    def _get_latest_backup(self) -> Optional[str]:
        """Get path to latest backup file"""
        try:
            backups = sorted(
                Path(self.backup_dir).glob("state_backup_*.json"),
                key=os.path.getctime
            )
            return str(backups[-1]) if backups else None
        except Exception:
            return None

    def _cleanup_old_backups(self, keep_last: int = 5):
        """Remove old backup files"""
        try:
            backups = sorted(
                Path(self.backup_dir).glob("state_backup_*.json"),
                key=os.path.getctime
            )
            for backup in backups[:-keep_last]:
                backup.unlink()
        except Exception as e:
            logger.error(f"Error cleaning up backups: {e}")

    def update_context(self, context: str):
        """Update current context"""
        with self._lock:
            self.state.current_context = context
            self.save_state()
            self._notify_observers(StateChangeEvent.CONTEXT_UPDATED, context)

    def record_command(self, command: str, success: bool, execution_time: float):
        """Record command execution"""
        with self._lock:
            self.state.last_command = command
            self.state.total_execution_time += execution_time
            
            if success:
                self.state.successful_commands += 1
            else:
                self.state.failed_commands += 1
            
            self.state.execution_history.append({
                'timestamp': datetime.now().isoformat(),
                'command': command,
                'success': success,
                'execution_time': execution_time
            })
            
            self.save_state()
            self._notify_observers(StateChangeEvent.COMMAND_EXECUTED, {
                'command': command,
                'success': success
            })

    def record_error(self, error: str):
        """Record error occurrence"""
        with self._lock:
            self.state.error_count += 1
            self.state.last_error = error
            self.save_state()
            self._notify_observers(StateChangeEvent.ERROR_OCCURRED, error)

    def update_plugin_state(self, plugin_name: str, state_data: Dict[str, Any]):
        """Update plugin-specific state"""
        with self._lock:
            self.state.plugin_states[plugin_name] = state_data
            self.save_state()

    def get_plugin_state(self, plugin_name: str) -> Dict[str, Any]:
        """Get plugin-specific state"""
        return self.state.plugin_states.get(plugin_name, {})