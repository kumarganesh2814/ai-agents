#!/usr/bin/env python3
"""
DevOpsGPT - AI-Powered SRE/DevOps Agent
Core Architecture and Plugin Framework
"""

import asyncio
import json
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
import subprocess
import yaml

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TaskCategory(Enum):
    TROUBLESHOOTING = "troubleshooting"
    CICD = "cicd"
    CLOUD_PROVISIONING = "cloud_provisioning"
    COST_USAGE = "cost_usage"
    SECURITY_COMPLIANCE = "security_compliance"
    MONITORING_ALERTS = "monitoring_alerts"

class ExecutionMode(Enum):
    DRY_RUN = "dry_run"
    CONFIRM = "confirm"
    EXECUTE = "execute"

@dataclass
class Command:
    """Represents a parsed command with intent and parameters"""
    intent: str
    category: TaskCategory
    parameters: Dict[str, Any]
    raw_input: str
    confidence: float
    dry_run: bool = True

@dataclass
class ExecutionResult:
    """Result of command execution"""
    success: bool
    output: str
    error: Optional[str] = None
    execution_time: float = 0.0
    command_executed: Optional[str] = None
    metadata: Dict[str, Any] = None

class BasePlugin(ABC):
    """Base class for all DevOpsGPT plugins"""
    
    def __init__(self, name: str, category: TaskCategory):
        self.name = name
        self.category = category
        self.command_patterns = []
        self.required_permissions = []
    
    @abstractmethod
    async def can_handle(self, command: Command) -> bool:
        """Check if this plugin can handle the given command"""
        pass
    
    @abstractmethod
    async def execute(self, command: Command) -> ExecutionResult:
        """Execute the command and return result"""
        pass
    
    def register_pattern(self, pattern: str, intent: str):
        """Register a command pattern this plugin can handle"""
        self.command_patterns.append({
            'pattern': re.compile(pattern, re.IGNORECASE),
            'intent': intent
        })

class CommandParser:
    """Natural language command parser using pattern matching and LLM"""
    
    def __init__(self):
        self.intent_patterns = {
            # Troubleshooting patterns
            r"show.*logs.*from.*(?P<service>\w+)": {
                "intent": "show_logs",
                "category": TaskCategory.TROUBLESHOOTING
            },
            r"restart.*(?P<service>\w+)": {
                "intent": "restart_service", 
                "category": TaskCategory.TROUBLESHOOTING
            },
            r"health.*check.*(?P<service>\w+)": {
                "intent": "health_check",
                "category": TaskCategory.TROUBLESHOOTING
            },
            
            # CI/CD patterns
            r"trigger.*(?P<pipeline>\w+).*pipeline": {
                "intent": "trigger_pipeline",
                "category": TaskCategory.CICD
            },
            r"rollback.*(?P<service>\w+)": {
                "intent": "rollback_deployment",
                "category": TaskCategory.CICD
            },
            
            # Cloud provisioning
            r"create.*(?P<resource_type>ec2|vm|instance)": {
                "intent": "create_instance",
                "category": TaskCategory.CLOUD_PROVISIONING
            },
            
            # Cost analysis
            r"show.*cost.*(?P<service>\w+)": {
                "intent": "analyze_cost",
                "category": TaskCategory.COST_USAGE
            },
            
            # Security
            r"check.*(?P<security_type>ports|cve|vulnerabilities)": {
                "intent": "security_scan",
                "category": TaskCategory.SECURITY_COMPLIANCE
            }
        }
    
    async def parse(self, user_input: str) -> Command:
        """Parse natural language input into a structured command"""
        user_input = user_input.strip().lower()
        
        for pattern, config in self.intent_patterns.items():
            match = re.search(pattern, user_input)
            if match:
                parameters = match.groupdict()
                return Command(
                    intent=config["intent"],
                    category=config["category"],
                    parameters=parameters,
                    raw_input=user_input,
                    confidence=0.8,
                    dry_run=True
                )
        
        # Default fallback
        return Command(
            intent="unknown",
            category=TaskCategory.TROUBLESHOOTING,
            parameters={},
            raw_input=user_input,
            confidence=0.1
        )

class TroubleshootingPlugin(BasePlugin):
    """Plugin for troubleshooting operations"""
    
    def __init__(self):
        super().__init__("troubleshooting", TaskCategory.TROUBLESHOOTING)
        self.register_patterns()
    
    def register_patterns(self):
        self.register_pattern(r"show.*logs", "show_logs")
        self.register_pattern(r"restart.*service", "restart_service")
        self.register_pattern(r"health.*check", "health_check")
    
    async def can_handle(self, command: Command) -> bool:
        return command.category == TaskCategory.TROUBLESHOOTING
    
    async def execute(self, command: Command) -> ExecutionResult:
        """Execute troubleshooting commands"""
        start_time = datetime.now()
        
        try:
            if command.intent == "show_logs":
                return await self._show_logs(command)
            elif command.intent == "restart_service":
                return await self._restart_service(command)
            elif command.intent == "health_check":
                return await self._health_check(command)
            else:
                return ExecutionResult(
                    success=False,
                    output="Unknown troubleshooting command",
                    error=f"Intent '{command.intent}' not supported"
                )
        except Exception as e:
            logger.error(f"Error executing command: {e}")
            return ExecutionResult(
                success=False,
                output="",
                error=str(e)
            )
    
    async def _show_logs(self, command: Command) -> ExecutionResult:
        service = command.parameters.get('service', 'unknown')
        
        if command.dry_run:
            cmd = f"kubectl logs -l app={service} --tail=50"
            return ExecutionResult(
                success=True,
                output=f"[DRY RUN] Would execute: {cmd}",
                command_executed=cmd
            )
        
        # In real implementation, execute kubectl or docker logs
        cmd = f"kubectl logs -l app={service} --tail=50"
        result = await self._execute_shell_command(cmd)
        return result
    
    async def _restart_service(self, command: Command) -> ExecutionResult:
        service = command.parameters.get('service', 'unknown')
        
        if command.dry_run:
            cmd = f"kubectl rollout restart deployment/{service}"
            return ExecutionResult(
                success=True,
                output=f"[DRY RUN] Would execute: {cmd}",
                command_executed=cmd
            )
        
        cmd = f"kubectl rollout restart deployment/{service}"
        result = await self._execute_shell_command(cmd)
        return result
    
    async def _health_check(self, command: Command) -> ExecutionResult:
        service = command.parameters.get('service', 'unknown')
        
        if command.dry_run:
            cmd = f"kubectl get pods -l app={service}"
            return ExecutionResult(
                success=True,
                output=f"[DRY RUN] Would execute: {cmd}",
                command_executed=cmd
            )
        
        cmd = f"kubectl get pods -l app={service}"
        result = await self._execute_shell_command(cmd)
        return result
    
    async def _execute_shell_command(self, cmd: str) -> ExecutionResult:
        """Execute shell command safely"""
        try:
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            return ExecutionResult(
                success=process.returncode == 0,
                output=stdout.decode() if stdout else "",
                error=stderr.decode() if stderr else None,
                command_executed=cmd
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                output="",
                error=str(e),
                command_executed=cmd
            )

class SessionContext:
    """Maintains session context for conversation continuity"""
    
    def __init__(self):
        self.namespace = "default"
        self.current_service = None
        self.cloud_provider = None
        self.history = []
    
    def update_context(self, command: Command, result: ExecutionResult):
        """Update context based on executed command"""
        self.history.append({
            'timestamp': datetime.now(),
            'command': command,
            'result': result
        })
        
        # Extract context from parameters
        if 'service' in command.parameters:
            self.current_service = command.parameters['service']

class DevOpsGPT:
    """Main DevOpsGPT Agent class"""
    
    def __init__(self):
        self.parser = CommandParser()
        self.plugins: List[BasePlugin] = []
        self.context = SessionContext()
        self.audit_log = []
        
        # Register default plugins
        self.register_plugin(TroubleshootingPlugin())
    
    def register_plugin(self, plugin: BasePlugin):
        """Register a new plugin"""
        self.plugins.append(plugin)
        logger.info(f"Registered plugin: {plugin.name}")
    
    async def process_command(self, user_input: str, execution_mode: ExecutionMode = ExecutionMode.DRY_RUN) -> ExecutionResult:
        """Process natural language command"""
        # Parse command
        command = await self.parser.parse(user_input)
        command.dry_run = (execution_mode == ExecutionMode.DRY_RUN)
        
        # Log for audit
        self._audit_log(command)
        
        # Find appropriate plugin
        for plugin in self.plugins:
            if await plugin.can_handle(command):
                result = await plugin.execute(command)
                
                # Update context
                self.context.update_context(command, result)
                
                return result
        
        # No plugin found
        return ExecutionResult(
            success=False,
            output="No plugin found to handle this command",
            error=f"Unsupported command: {user_input}"
        )
    
    def _audit_log(self, command: Command):
        """Log command for audit trail"""
        audit_entry = {
            'timestamp': datetime.now().isoformat(),
            'user_input': command.raw_input,
            'intent': command.intent,
            'category': command.category.value,
            'parameters': command.parameters
        }
        self.audit_log.append(audit_entry)
        logger.info(f"Command logged: {command.intent}")

# CLI Interface
class DevOpsGPTCLI:
    """Command-line interface for DevOpsGPT"""
    
    def __init__(self):
        self.agent = DevOpsGPT()
    
    async def run_interactive(self):
        """Run interactive CLI session"""
        print("🤖 DevOpsGPT Agent - AI-Powered SRE Assistant")
        print("Type 'help' for commands, 'quit' to exit")
        print("-" * 50)
        
        while True:
            try:
                user_input = input("\n💬 DevOpsGPT> ").strip()
                
                if user_input.lower() in ['quit', 'exit']:
                    print("👋 Goodbye!")
                    break
                
                if user_input.lower() == 'help':
                    self._show_help()
                    continue
                
                if user_input.lower() == 'execute':
                    print("⚡ Switching to EXECUTE mode for next command")
                    execution_mode = ExecutionMode.EXECUTE
                    continue
                
                # Process command (default dry-run)
                result = await self.agent.process_command(user_input, ExecutionMode.DRY_RUN)
                
                # Display result
                self._display_result(result)
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
    
    def _show_help(self):
        """Show help information"""
        help_text = """
🚀 DevOpsGPT Commands:

📋 Troubleshooting:
  • "show logs from [service]"     - Get service logs
  • "restart [service]"            - Restart service
  • "health check [service]"       - Check service health

🔧 CI/CD:
  • "trigger [pipeline] pipeline"  - Trigger pipeline
  • "rollback [service]"           - Rollback deployment

☁️ Cloud:
  • "create ec2 instance"          - Create cloud instance
  • "show cost for [service]"      - Analyze costs

🔒 Security:
  • "check ports"                  - Security scan
  • "check vulnerabilities"        - CVE scan

⚙️ Controls:
  • "execute"                      - Execute next command (vs dry-run)
  • "help"                         - Show this help
  • "quit"                         - Exit
        """
        print(help_text)
    
    def _display_result(self, result: ExecutionResult):
        """Display execution result"""
        if result.success:
            print(f"✅ Success:")
            print(f"   {result.output}")
            if result.command_executed:
                print(f"   Command: {result.command_executed}")
        else:
            print(f"❌ Failed:")
            if result.error:
                print(f"   Error: {result.error}")
            if result.output:
                print(f"   Output: {result.output}")

# Main entry point
async def main():
    """Main entry point"""
    cli = DevOpsGPTCLI()
    await cli.run_interactive()

if __name__ == "__main__":
    asyncio.run(main())