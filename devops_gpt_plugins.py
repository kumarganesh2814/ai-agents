#!/usr/bin/env python3
"""
DevOpsGPT Plugin System
Cloud Provider Plugins and Configuration Management
"""

import json
import boto3
from azure.identity import DefaultAzureCredential
from azure.mgmt.compute import ComputeManagementClient
from google.cloud import compute_v1
import kubernetes
from kubernetes import client, config
import yaml
import os
from typing import Dict, List, Any
from dataclasses import dataclass
from devops_gpt_core import BasePlugin, TaskCategory, Command, ExecutionResult

@dataclass
class CloudConfig:
    """Cloud provider configuration"""
    provider: str  # aws, azure, gcp
    region: str
    credentials: Dict[str, Any]
    default_tags: Dict[str, str] = None

class ConfigManager:
    """Manages DevOpsGPT configuration"""
    
    def __init__(self, config_path: str = "devops_gpt_config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        default_config = {
            "cloud_providers": {
                "aws": {
                    "region": "us-east-1",
                    "profile": "default"
                },
                "azure": {
                    "subscription_id": "",
                    "resource_group": "devops-gpt-rg"
                },
                "gcp": {
                    "project_id": "",
                    "zone": "us-central1-a"
                }
            },
            "kubernetes": {
                "context": "default",
                "namespace": "default"
            },
            "security": {
                "require_confirmation": True,
                "dry_run_by_default": True,
                "audit_logging": True
            },
            "monitoring": {
                "prometheus_url": "http://localhost:9090",
                "grafana_url": "http://localhost:3000"
            }
        }
        
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    user_config = yaml.safe_load(f)
                    # Merge with defaults
                    default_config.update(user_config)
            else:
                # Create default config file
                with open(self.config_path, 'w') as f:
                    yaml.dump(default_config, f, default_flow_style=False)
        except Exception as e:
            print(f"Warning: Could not load config: {e}")
        
        return default_config
    
    def get_cloud_config(self, provider: str) -> CloudConfig:
        """Get cloud provider configuration"""
        provider_config = self.config.get("cloud_providers", {}).get(provider, {})
        return CloudConfig(
            provider=provider,
            region=provider_config.get("region", "us-east-1"),
            credentials=provider_config,
            default_tags={"CreatedBy": "DevOpsGPT", "Purpose": "Automation"}
        )

class AWSPlugin(BasePlugin):
    """AWS cloud operations plugin"""
    
    def __init__(self, config_manager: ConfigManager):
        super().__init__("aws", TaskCategory.CLOUD_PROVISIONING)
        self.config = config_manager.get_cloud_config("aws")
        self.session = boto3.Session(
            profile_name=self.config.credentials.get("profile", "default"),
            region_name=self.config.region
        )
        self.register_patterns()
    
    def register_patterns(self):
        self.register_pattern(r"create.*ec2.*instance", "create_ec2_instance")
        self.register_pattern(r"list.*ec2.*instances", "list_ec2_instances")
        self.register_pattern(r"terminate.*instance.*(?P<instance_id>i-\w+)", "terminate_instance")
        self.register_pattern(r"show.*cost.*(?P<service>\w+)", "analyze_cost")
    
    async def can_handle(self, command: Command) -> bool:
        aws_intents = ["create_ec2_instance", "list_ec2_instances", "terminate_instance", "analyze_cost"]
        return command.intent in aws_intents or "ec2" in command.raw_input.lower()
    
    async def execute(self, command: Command) -> ExecutionResult:
        """Execute AWS operations"""
        try:
            if command.intent == "create_ec2_instance":
                return await self._create_ec2_instance(command)
            elif command.intent == "list_ec2_instances":
                return await self._list_ec2_instances(command)
            elif command.intent == "terminate_instance":
                return await self._terminate_instance(command)
            elif command.intent == "analyze_cost":
                return await self._analyze_cost(command)
            else:
                return ExecutionResult(
                    success=False,
                    output="Unknown AWS command",
                    error=f"Intent '{command.intent}' not supported"
                )
        except Exception as e:
            return ExecutionResult(
                success=False,
                output="",
                error=f"AWS operation failed: {str(e)}"
            )
    
    async def _create_ec2_instance(self, command: Command) -> ExecutionResult:
        """Create EC2 instance"""
        ec2 = self.session.client('ec2')
        
        # Default instance configuration
        instance_config = {
            'ImageId': 'ami-0c02fb55956c7d316',  # Amazon Linux 2 AMI
            'InstanceType': command.parameters.get('instance_type', 't2.micro'),
            'MinCount': 1,
            'MaxCount': 1,
            'KeyName': command.parameters.get('key_name', 'my-key'),
            'TagSpecifications': [{
                'ResourceType': 'instance',
                'Tags': [
                    {'Key': 'Name', 'Value': command.parameters.get('name', 'DevOpsGPT-Instance')},
                    {'Key': 'CreatedBy', 'Value': 'DevOpsGPT'},
                    {'Key': 'Purpose', 'Value': 'Automation'}
                ]
            }]
        }
        
        if command.dry_run:
            return ExecutionResult(
                success=True,
                output=f"[DRY RUN] Would create EC2 instance:\n{json.dumps(instance_config, indent=2)}",
                command_executed="ec2.run_instances()"
            )
        
        # Execute instance creation
        response = ec2.run_instances(**instance_config)
        instance_id = response['Instances'][0]['InstanceId']
        
        return ExecutionResult(
            success=True,
            output=f"✅ EC2 instance created successfully!\nInstance ID: {instance_id}",
            metadata={'instance_id': instance_id, 'response': response}
        )
    
    async def _list_ec2_instances(self, command: Command) -> ExecutionResult:
        """List EC2 instances"""
        ec2 = self.session.client('ec2')
        
        if command.dry_run:
            return ExecutionResult(
                success=True,
                output="[DRY RUN] Would list all EC2 instances",
                command_executed="ec2.describe_instances()"
            )
        
        response = ec2.describe_instances()
        instances = []
        
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                name = next((tag['Value'] for tag in instance.get('Tags', []) if tag['Key'] == 'Name'), 'Unnamed')
                instances.append({
                    'InstanceId': instance['InstanceId'],
                    'Name': name,
                    'State': instance['State']['Name'],
                    'InstanceType': instance['InstanceType'],
                    'PublicIpAddress': instance.get('PublicIpAddress', 'N/A')
                })
        
        output = "📋 EC2 Instances:\n"
        for inst in instances:
            output += f"  • {inst['Name']} ({inst['InstanceId']}) - {inst['State']} - {inst['InstanceType']}\n"
        
        return ExecutionResult(
            success=True,
            output=output,
            metadata={'instances': instances}
        )

class KubernetesPlugin(BasePlugin):
    """Kubernetes operations plugin"""
    
    def __init__(self, config_manager: ConfigManager):
        super().__init__("kubernetes", TaskCategory.TROUBLESHOOTING)
        self.config = config_manager.config.get("kubernetes", {})
        self._load_kube_config()
        self.register_patterns()
    
    def _load_kube_config(self):
        """Load Kubernetes configuration"""
        try:
            config.load_kube_config(context=self.config.get("context"))
            self.v1 = client.CoreV1Api()
            self.apps_v1 = client.AppsV1Api()
        except Exception as e:
            print(f"Warning: Could not load Kubernetes config: {e}")
            self.v1 = None
            self.apps_v1 = None
    
    def register_patterns(self):
        self.register_pattern(r"get.*pods.*(?P<namespace>\w+)?", "get_pods")
        self.register_pattern(r"describe.*pod.*(?P<pod_name>\w+)", "describe_pod")
        self.register_pattern(r"scale.*deployment.*(?P<deployment>\w+).*(?P<replicas>\d+)", "scale_deployment")
        self.register_pattern(r"create.*namespace.*(?P<namespace>\w+)", "create_namespace")
    
    async def can_handle(self, command: Command) -> bool:
        k8s_keywords = ["pod", "deployment", "service", "namespace", "kubectl"]
        return any(keyword in command.raw_input.lower() for keyword in k8s_keywords)
    
    async def execute(self, command: Command) -> ExecutionResult:
        """Execute Kubernetes operations"""
        if not self.v1:
            return ExecutionResult(
                success=False,
                output="",
                error="Kubernetes client not configured"
            )
        
        try:
            if "pods" in command.raw_input.lower():
                return await self._get_pods(command)
            elif "describe" in command.raw_input.lower():
                return await self._describe_pod(command)
            elif "scale" in command.raw_input.lower():
                return await self._scale_deployment(command)
            elif "namespace" in command.raw_input.lower():
                return await self._create_namespace(command)
            else:
                return ExecutionResult(
                    success=False,
                    output="Unknown Kubernetes command",
                    error=f"Could not parse: {command.raw_input}"
                )
        except Exception as e:
            return ExecutionResult(
                success=False,
                output="",
                error=f"Kubernetes operation failed: {str(e)}"
            )
    
    async def _get_pods(self, command: Command) -> ExecutionResult:
        """Get pods in namespace"""
        namespace = command.parameters.get('namespace', self.config.get('namespace', 'default'))
        
        if command.dry_run:
            return ExecutionResult(
                success=True,
                output=f"[DRY RUN] Would list pods in namespace: {namespace}",
                command_executed=f"kubectl get pods -n {namespace}"
            )
        
        pods = self.v1.list_namespaced_pod(namespace=namespace)
        
        output = f"🚀 Pods in namespace '{namespace}':\n"
        for pod in pods.items:
            status = pod.status.phase
            output += f"  • {pod.metadata.name} - {status}\n"
        
        return ExecutionResult(
            success=True,
            output=output,
            metadata={'pod_count': len(pods.items)}
        )
    
    async def _scale_deployment(self, command: Command) -> ExecutionResult:
        """Scale deployment"""
        deployment = command.parameters.get('deployment', 'unknown')
        replicas = int(command.parameters.get('replicas', 1))
        namespace = self.config.get('namespace', 'default')
        
        if command.dry_run:
            return ExecutionResult(
                success=True,
                output=f"[DRY RUN] Would scale deployment {deployment} to {replicas} replicas",
                command_executed=f"kubectl scale deployment {deployment} --replicas={replicas}"
            )
        
        # Scale the deployment
        body = {'spec': {'replicas': replicas}}
        self.apps_v1.patch_namespaced_deployment_scale(
            name=deployment,
            namespace=namespace,
            body=body
        )
        
        return ExecutionResult(
            success=True,
            output=f"✅ Scaled deployment '{deployment}' to {replicas} replicas",
            metadata={'deployment': deployment, 'replicas': replicas}
        )

class MonitoringPlugin(BasePlugin):
    """Monitoring and alerting plugin"""
    
    def __init__(self, config_manager: ConfigManager):
        super().__init__("monitoring", TaskCategory.MONITORING_ALERTS)
        self.config = config_manager.config.get("monitoring", {})
        self.prometheus_url = self.config.get("prometheus_url")
        self.grafana_url = self.config.get("grafana_url")
        self.register_patterns()
    
    def register_patterns(self):
        self.register_pattern(r"show.*metrics.*(?P<service>\w+)", "show_metrics")
        self.register_pattern(r"check.*alerts", "check_alerts")
        self.register_pattern(r"cpu.*usage.*(?P<service>\w+)", "cpu_usage")
    
    async def can_handle(self, command: Command) -> bool:
        monitoring_keywords = ["metrics", "alerts", "cpu", "memory", "prometheus", "grafana"]
        return any(keyword in command.raw_input.lower() for keyword in monitoring_keywords)
    
    async def execute(self, command: Command) -> ExecutionResult:
        """Execute monitoring operations"""
        try:
            if "metrics" in command.raw_input.lower():
                return await self._show_metrics(command)
            elif "alerts" in command.raw_input.lower():
                return await self._check_alerts(command)
            elif "cpu" in command.raw_input.lower():
                return await self._cpu_usage(command)
            else:
                return ExecutionResult(
                    success=False,
                    output="Unknown monitoring command"
                )
        except Exception as e:
            return ExecutionResult(
                success=False,
                output="",
                error=f"Monitoring operation failed: {str(e)}"
            )
    
    async def _show_metrics(self, command: Command) -> ExecutionResult:
        """Show service metrics"""
        service = command.parameters.get('service', 'unknown')
        
        if command.dry_run:
            query = f'up{{job="{service}"}}'
            return ExecutionResult(
                success=True,
                output=f"[DRY RUN] Would query Prometheus: {query}",
                command_executed=f"prometheus_query: {query}"
            )
        
        # Mock metrics data (in real implementation, query Prometheus)
        metrics = {
            'service': service,
            'uptime': '99.9%',
            'response_time': '120ms',
            'error_rate': '0.1%',
            'cpu_usage': '45%',
            'memory_usage': '60%',
            'request_rate': '1250 req/min'
        }
        
        output = f"📊 Metrics for service '{service}':\n"
        for key, value in metrics.items():
            if key != 'service':
                output += f"  • {key.replace('_', ' ').title()}: {value}\n"
        
        return ExecutionResult(
            success=True,
            output=output,
            metadata={'metrics': metrics}
        )
    
    async def _check_alerts(self, command: Command) -> ExecutionResult:
        """Check active alerts"""
        if command.dry_run:
            return ExecutionResult(
                success=True,
                output="[DRY RUN] Would check Prometheus/Grafana alerts",
                command_executed="alertmanager_api/alerts"
            )
        
        # Mock alert data (in real implementation, query Alertmanager)
        alerts = [
            {'service': 'payment-api', 'severity': 'warning', 'message': 'High response time'},
            {'service': 'database', 'severity': 'critical', 'message': 'Connection pool exhausted'}
        ]
        
        if not alerts:
            return ExecutionResult(
                success=True,
                output="✅ No active alerts found"
            )
        
        output = "🚨 Active Alerts:\n"
        for alert in alerts:
            emoji = "🔴" if alert['severity'] == 'critical' else "🟡"
            output += f"  {emoji} {alert['service']}: {alert['message']} ({alert['severity']})\n"
        
        return ExecutionResult(
            success=True,
            output=output,
            metadata={'alert_count': len(alerts), 'alerts': alerts}
        )

class SecurityPlugin(BasePlugin):
    """Security and compliance plugin"""
    
    def __init__(self, config_manager: ConfigManager):
        super().__init__("security", TaskCategory.SECURITY_COMPLIANCE)
        self.config = config_manager.config
        self.register_patterns()
    
    def register_patterns(self):
        self.register_pattern(r"scan.*vulnerabilities", "vulnerability_scan")
        self.register_pattern(r"check.*ports", "port_scan")
        self.register_pattern(r"audit.*compliance", "compliance_audit")
        self.register_pattern(r"check.*certificates", "cert_check")
    
    async def can_handle(self, command: Command) -> bool:
        security_keywords = ["scan", "vulnerability", "security", "compliance", "audit", "cve", "ports"]
        return any(keyword in command.raw_input.lower() for keyword in security_keywords)
    
    async def execute(self, command: Command) -> ExecutionResult:
        """Execute security operations"""
        try:
            if "vulnerability" in command.raw_input.lower() or "cve" in command.raw_input.lower():
                return await self._vulnerability_scan(command)
            elif "ports" in command.raw_input.lower():
                return await self._port_scan(command)
            elif "compliance" in command.raw_input.lower():
                return await self._compliance_audit(command)
            elif "certificate" in command.raw_input.lower():
                return await self._cert_check(command)
            else:
                return ExecutionResult(
                    success=False,
                    output="Unknown security command"
                )
        except Exception as e:
            return ExecutionResult(
                success=False,
                output="",
                error=f"Security operation failed: {str(e)}"
            )
    
    async def _vulnerability_scan(self, command: Command) -> ExecutionResult:
        """Run vulnerability scan"""
        target = command.parameters.get('target', 'current-system')
        
        if command.dry_run:
            return ExecutionResult(
                success=True,
                output=f"[DRY RUN] Would run vulnerability scan on: {target}",
                command_executed="trivy image scan / nmap vulnerability scan"
            )
        
        # Mock vulnerability data
        vulnerabilities = [
            {'cve': 'CVE-2023-1234', 'severity': 'HIGH', 'package': 'openssl', 'fixed_version': '1.1.1t'},
            {'cve': 'CVE-2023-5678', 'severity': 'MEDIUM', 'package': 'curl', 'fixed_version': '8.0.1'}
        ]
        
        output = f"🔍 Vulnerability Scan Results for {target}:\n"
        critical_count = sum(1 for v in vulnerabilities if v['severity'] == 'CRITICAL')
        high_count = sum(1 for v in vulnerabilities if v['severity'] == 'HIGH')
        medium_count = sum(1 for v in vulnerabilities if v['severity'] == 'MEDIUM')
        
        output += f"  📊 Summary: {critical_count} Critical, {high_count} High, {medium_count} Medium\n\n"
        
        for vuln in vulnerabilities:
            emoji = "🔴" if vuln['severity'] == 'CRITICAL' else "🟡" if vuln['severity'] == 'HIGH' else "🟢"
            output += f"  {emoji} {vuln['cve']} ({vuln['severity']})\n"
            output += f"     Package: {vuln['package']}, Fix: {vuln['fixed_version']}\n"
        
        return ExecutionResult(
            success=True,
            output=output,
            metadata={'vulnerability_count': len(vulnerabilities), 'vulnerabilities': vulnerabilities}
        )
    
    async def _port_scan(self, command: Command) -> ExecutionResult:
        """Scan for open ports"""
        target = command.parameters.get('target', 'localhost')
        
        if command.dry_run:
            return ExecutionResult(
                success=True,
                output=f"[DRY RUN] Would scan ports on: {target}",
                command_executed=f"nmap -sS {target}"
            )
        
        # Mock port scan data
        open_ports = [
            {'port': 22, 'service': 'SSH', 'state': 'open'},
            {'port': 80, 'service': 'HTTP', 'state': 'open'},
            {'port': 443, 'service': 'HTTPS', 'state': 'open'},
            {'port': 3000, 'service': 'Node.js', 'state': 'open'}
        ]
        
        output = f"🔍 Port Scan Results for {target}:\n"
        for port_info in open_ports:
            status_emoji = "🟢" if port_info['state'] == 'open' else "🔴"
            output += f"  {status_emoji} Port {port_info['port']}: {port_info['service']} ({port_info['state']})\n"
        
        return ExecutionResult(
            success=True,
            output=output,
            metadata={'open_ports': len(open_ports), 'ports': open_ports}
        )

class CICDPlugin(BasePlugin):
    """CI/CD operations plugin"""
    
    def __init__(self, config_manager: ConfigManager):
        super().__init__("cicd", TaskCategory.CICD)
        self.config = config_manager.config
        self.register_patterns()
    
    def register_patterns(self):
        self.register_pattern(r"trigger.*pipeline.*(?P<pipeline>\w+)", "trigger_pipeline")
        self.register_pattern(r"rollback.*(?P<service>\w+)", "rollback_deployment")
        self.register_pattern(r"deploy.*(?P<service>\w+).*(?P<version>\w+)?", "deploy_service")
        self.register_pattern(r"build.*status.*(?P<pipeline>\w+)", "build_status")
    
    async def can_handle(self, command: Command) -> bool:
        cicd_keywords = ["pipeline", "deploy", "build", "rollback", "release", "jenkins", "github", "gitlab"]
        return any(keyword in command.raw_input.lower() for keyword in cicd_keywords)
    
    async def execute(self, command: Command) -> ExecutionResult:
        """Execute CI/CD operations"""
        try:
            if "trigger" in command.raw_input.lower() and "pipeline" in command.raw_input.lower():
                return await self._trigger_pipeline(command)
            elif "rollback" in command.raw_input.lower():
                return await self._rollback_deployment(command)
            elif "deploy" in command.raw_input.lower():
                return await self._deploy_service(command)
            elif "build" in command.raw_input.lower() and "status" in command.raw_input.lower():
                return await self._build_status(command)
            else:
                return ExecutionResult(
                    success=False,
                    output="Unknown CI/CD command"
                )
        except Exception as e:
            return ExecutionResult(
                success=False,
                output="",
                error=f"CI/CD operation failed: {str(e)}"
            )
    
    async def _trigger_pipeline(self, command: Command) -> ExecutionResult:
        """Trigger CI/CD pipeline"""
        pipeline = command.parameters.get('pipeline', 'unknown')
        
        if command.dry_run:
            return ExecutionResult(
                success=True,
                output=f"[DRY RUN] Would trigger pipeline: {pipeline}",
                command_executed=f"jenkins/github actions trigger: {pipeline}"
            )
        
        # Mock pipeline trigger
        build_id = f"#{hash(pipeline) % 1000}"
        
        return ExecutionResult(
            success=True,
            output=f"🚀 Pipeline '{pipeline}' triggered successfully!\nBuild ID: {build_id}\nStatus: Running",
            metadata={'pipeline': pipeline, 'build_id': build_id, 'status': 'running'}
        )
    
    async def _rollback_deployment(self, command: Command) -> ExecutionResult:
        """Rollback service deployment"""
        service = command.parameters.get('service', 'unknown')
        
        if command.dry_run:
            return ExecutionResult(
                success=True,
                output=f"[DRY RUN] Would rollback service: {service}",
                command_executed=f"kubectl rollout undo deployment/{service}"
            )
        
        # Mock rollback operation
        previous_version = "v1.2.3"
        
        return ExecutionResult(
            success=True,
            output=f"⏪ Service '{service}' rolled back successfully!\nReverted to version: {previous_version}",
            metadata={'service': service, 'previous_version': previous_version}
        )

# Extended DevOpsGPT with all plugins
class ExtendedDevOpsGPT:
    """Extended DevOpsGPT with all plugin capabilities"""
    
    def __init__(self, config_path: str = "devops_gpt_config.yaml"):
        from devops_gpt_core import DevOpsGPT
        
        self.config_manager = ConfigManager(config_path)
        self.agent = DevOpsGPT()
        
        # Register all plugins
        self._register_plugins()
    
    def _register_plugins(self):
        """Register all available plugins"""
        # Cloud providers
        try:
            aws_plugin = AWSPlugin(self.config_manager)
            self.agent.register_plugin(aws_plugin)
        except Exception as e:
            print(f"Warning: Could not initialize AWS plugin: {e}")
        
        # Kubernetes
        try:
            k8s_plugin = KubernetesPlugin(self.config_manager)
            self.agent.register_plugin(k8s_plugin)
        except Exception as e:
            print(f"Warning: Could not initialize Kubernetes plugin: {e}")
        
        # Monitoring
        monitoring_plugin = MonitoringPlugin(self.config_manager)
        self.agent.register_plugin(monitoring_plugin)
        
        # Security
        security_plugin = SecurityPlugin(self.config_manager)
        self.agent.register_plugin(security_plugin)
        
        # CI/CD
        cicd_plugin = CICDPlugin(self.config_manager)
        self.agent.register_plugin(cicd_plugin)
    
    async def process_command(self, user_input: str, execution_mode: str = "dry_run"):
        """Process command with extended plugin support"""
        from devops_gpt_core import ExecutionMode
        
        mode_map = {
            "dry_run": ExecutionMode.DRY_RUN,
            "confirm": ExecutionMode.CONFIRM,
            "execute": ExecutionMode.EXECUTE
        }
        
        return await self.agent.process_command(user_input, mode_map.get(execution_mode, ExecutionMode.DRY_RUN))

# Example usage and testing
async def demo_extended_devops_gpt():
    """Demo the extended DevOpsGPT capabilities"""
    print("🚀 DevOpsGPT Extended Demo")
    print("=" * 50)
    
    # Initialize extended agent
    agent = ExtendedDevOpsGPT()
    
    # Demo commands
    demo_commands = [
        "show logs from payment service",
        "create ec2 instance",
        "list ec2 instances", 
        "get pods in production",
        "check vulnerabilities",
        "trigger payment pipeline",
        "show metrics for api service",
        "scan ports on localhost",
        "rollback user-service"
    ]
    
    for cmd in demo_commands:
        print(f"\n💬 Command: {cmd}")
        print("-" * 30)
        
        result = await agent.process_command(cmd, "dry_run")
        
        if result.success:
            print(f"✅ {result.output}")
        else:
            print(f"❌ Error: {result.error}")
        
        print()

if __name__ == "__main__":
    import asyncio
    asyncio.run(demo_extended_devops_gpt())