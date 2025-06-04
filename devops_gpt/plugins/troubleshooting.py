from typing import Dict, Any, List
import subprocess
import json
from devops_gpt.plugins.base import BasePlugin

class TroubleshootingPlugin(BasePlugin):
    def __init__(self):
        super().__init__()
        
    async def execute(self, intent: Dict[str, Any], dry_run: bool = True) -> Dict[str, Any]:
        """Execute troubleshooting actions"""
        action = intent.get("action")
        params = intent.get("parameters", {})
        
        if not self.validate_params(params):
            return {
                "success": False,
                "error": "Missing required parameters"
            }
            
        if dry_run:
            return {
                "success": True,
                "action": action,
                "params": params,
                "dry_run": True,
                "message": f"Would execute {action} with params {params}"
            }
            
        try:
            if not hasattr(self, f"_{action}"):
                return {
                    "success": False,
                    "error": f"Action {action} not supported"
                }
                
            result = await getattr(self, f"_{action}")(params)
            return {**result, "action": action, "params": params}
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "action": action,
                "params": params
            }
            
    async def _fetch_logs(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch logs from a pod/service"""
        pod = params.get("pod")
        namespace = params.get("namespace", "default")
        
        try:
            cmd = f"kubectl logs {pod} -n {namespace}"
            output = subprocess.check_output(cmd.split()).decode()
            return {
                "success": True,
                "logs": output
            }
        except subprocess.CalledProcessError as e:
            return {
                "success": False,
                "error": str(e)
            }
            
    def get_categories(self) -> List[str]:
        return ["troubleshooting"]
        
    def get_actions(self) -> List[str]:
        return ["fetch_logs", "analyze_errors", "health_check"]
        
    def get_parameters(self) -> Dict[str, Any]:
        return {
            "pod": {
                "type": "string",
                "required": True,
                "description": "Pod name"
            },
            "namespace": {
                "type": "string",
                "required": False,
                "default": "default",
                "description": "Kubernetes namespace"
            }
        }
        
    def get_capabilities(self) -> Dict[str, Any]:
        """Return plugin capabilities"""
        return {
            "name": self.name,
            "categories": self.get_categories(),
            "actions": self.get_actions(),
            "parameters": self.get_parameters()
        }