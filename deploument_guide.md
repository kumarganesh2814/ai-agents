# 🚀 DevOpsGPT Setup & Deployment Guide

## 📋 Overview
DevOpsGPT is an AI-powered SRE/DevOps agent that automates operational tasks through natural language commands. This guide will help you set up and deploy DevOpsGPT in your environment.

## 🛠️ Prerequisites

### System Requirements
- Python 3.8+
- Docker (optional for containerized deployment)
- Kubernetes cluster access (optional)
- Cloud provider credentials (AWS/Azure/GCP)

### Required Python Packages
```bash
pip install -r requirements.txt
```

Create `requirements.txt`:
```
asyncio
boto3>=1.26.0
azure-identity>=1.12.0
azure-mgmt-compute>=29.0.0
google-cloud-compute>=1.8.0
kubernetes>=25.0.0
pyyaml>=6.0
openai>=1.0.0  # For LLM integration
prometheus-client>=0.15.0
requests>=2.28.0
click>=8.0.0  # For CLI
rich>=13.0.0  # For beautiful CLI output
```

## ⚙️ Configuration

### 1. Create Configuration File
Create `devops_gpt_config.yaml`:

```yaml
# Cloud Provider Configurations
cloud_providers:
  aws:
    region: "us-east-1"
    profile: "default"  # AWS CLI profile
    
  azure:
    subscription_id: "your-subscription-id"
    resource_group: "devops-gpt-rg"
    tenant_id: "your-tenant-id"
    
  gcp:
    project_id: "your-project-id"
    zone: "us-central1-a"
    credentials_path: "/path/to/service-account.json"

# Kubernetes Configuration
kubernetes:
  context: "default"  # kubectl context
  namespace: "default"
  config_path: "~/.kube/config"

# Security Settings
security:
  require_confirmation: true
  dry_run_by_default: true
  audit_logging: true
  allowed_operations:
    - "restart"
    - "scale"
    - "deploy"
    - "rollback"
  restricted_operations:
    - "delete"
    - "terminate"

# Monitoring Integration
monitoring:
  prometheus_url: "http://localhost:9090"
  grafana_url: "http://localhost:3000"
  alertmanager_url: "http://localhost:9093"

# CI/CD Integration
cicd:
  jenkins:
    url: "http://localhost:8080"
    username: "admin"
    token: "your-jenkins-token"
  
  github:
    token: "your-github-token"
    org: "your-org"
  
  gitlab:
    url: "https://gitlab.com"
    token: "your-gitlab-token"

# LLM Configuration (for enhanced NLP)
llm:
  provider: "openai"  # or "anthropic", "local"
  api_key: "your-api-key"
  model: "gpt-4"
  max_tokens: 500

# Logging
logging:
  level: "INFO"
  file: "devops_gpt.log"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Web Interface (optional)
web:
  enabled: true
  host: "0.0.0.0"
  port: 8080
  auth_required: true
```

### 2. Environment Variables
Create `.env` file:
```bash
# AWS Credentials (if not using AWS CLI profiles)
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_DEFAULT_REGION=us-east-1

# Azure Credentials
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
AZURE_TENANT_ID=your-tenant-id

# GCP Credentials
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# OpenAI API Key
OPENAI_API_KEY=your-openai-api-key

# Other API Keys
PROMETHEUS_API_KEY=your-prometheus-key
GRAFANA_API_KEY=your-grafana-key
```

## 🏗️ Installation Methods

### Method 1: Local Development Setup

1. **Clone the Repository**
```bash
git clone https://github.com/kumarganesh2814/ai-agents.git
cd ai-agents
```

2. **Create Virtual Environment**
```bash
python -m venv devops-gpt-env
source devops-gpt-env/bin/activate  # Linux/Mac
# or
devops-gpt-env\Scripts\activate  # Windows
```

3. **Install Dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure Permissions**
```bash
# AWS CLI setup
aws configure

# Kubectl setup
kubectl config current-context

# Test cloud access
python -c "import boto3; print(boto3.client('ec2').describe_instances())"
```

5. **Run DevOpsGPT**
```bash
python devops_gpt_core.py
```

### Method 2: Docker Deployment

1. **Create Dockerfile**
```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install kubectl
RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" \
    && chmod +x kubectl \
    && mv kubectl /usr/local/bin/

# Install AWS CLI
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" \
    && unzip awscliv2.zip \
    && ./aws/install \
    && rm -rf awscliv2.zip aws

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 devops-gpt
USER devops-gpt

# Expose port for web interface
EXPOSE 8080

# Run the application
CMD ["python", "devops_gpt_core.py"]
```

2. **Build and Run Container**
```bash
# Build image
docker build -t devops-gpt:latest .

# Run with environment variables
docker run -d \
  --name devops-gpt \
  -p 8080:8080 \
  -v ~/.kube:/home/devops-gpt/.kube:ro \
  -v ~/.aws:/home/devops-gpt/.aws:ro \
  -e OPENAI_API_KEY=your-api-key \
  devops-gpt:latest
```

### Method 3: Kubernetes Deployment

1. **Create Kubernetes Manifests**

`k8s/namespace.yaml`:
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: devops-gpt
```

`k8s/configmap.yaml`:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: devops-gpt-config
  namespace: devops-gpt
data:
  config.yaml: |
    # Your devops_gpt_config.yaml content here
```

`k8s/secret.yaml`:
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: devops-gpt-secrets
  namespace: devops-gpt
type: Opaque
data:
  openai-api-key: <base64-encoded-key>
  aws-access-key: <base64-encoded-key>
  aws-secret-key: <base64-encoded-key>
```

`k8s/deployment.yaml`:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: devops-gpt
  namespace: devops-gpt
spec:
  replicas: 1
  selector:
    matchLabels:
      app: devops-gpt
  template:
    metadata:
      labels:
        app: devops-gpt
    spec:
      serviceAccountName: devops-gpt
      containers:
      - name: devops-gpt
        image: devops-gpt:latest
        ports:
        - containerPort: 8080
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: devops-gpt-secrets
              key: openai-api-key
        volumeMounts:
        - name: config
          mountPath: /app/devops_gpt_config.yaml
          subPath: config.yaml
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
      volumes:
      - name: config
        configMap:
          name: devops-gpt-config
```

`k8s/rbac.yaml`:
```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: devops-gpt
  namespace: devops-gpt
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: devops-gpt
rules:
- apiGroups: [""]
  resources: ["pods", "services", "endpoints", "persistentvolumeclaims"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: ["apps"]
  resources: ["deployments", "replicasets"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: ["extensions"]
  resources: ["deployments", "replicasets"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: devops-gpt
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: devops-gpt
subjects:
- kind: ServiceAccount
  name: devops-gpt
  namespace: devops-gpt
```

2. **Deploy to Kubernetes**
```bash
kubectl apply -f k8s/
```

## 🧪 Testing & Validation

### 1. Basic Functionality Test
```bash
# Test CLI interface
python devops_gpt_core.py

# Test specific commands
echo "show logs from frontend" | python devops_gpt_core.py
echo "list ec2 instances" | python devops_gpt_core.py
echo "get pods in default namespace" | python devops_gpt_core.py
```

### 2. Plugin Testing
```python
# Create test_plugins.py
import asyncio
from devops_gpt_plugins import ExtendedDevOpsGPT

async def test_plugins():
    agent = ExtendedDevOpsGPT()
    
    test_commands = [
        "show logs from payment service",
        "create ec2 instance",
        "check vulnerabilities",
        "trigger build pipeline",
        "show metrics for api"
    ]
    
    for cmd in test_commands:
        print(f"Testing: {cmd}")
        result = await agent.process_command(cmd, "dry_run")
        print(f"Result: {result.success}")
        print(f"Output: {result.output[:100]}...")
        print("-" * 50)

if __name__ == "__main__":
    asyncio.run(test_plugins())
```

### 3. Integration Tests
```bash
# Test cloud provider integration
python -c "
from devops_gpt_plugins import AWSPlugin, ConfigManager
import asyncio

async def test_aws():
    config = ConfigManager()
    plugin = AWSPlugin(config)
    print('AWS Plugin initialized successfully')

asyncio.run(test_aws())
"
```

## 🔒 Security Best Practices

### 1. Principle of Least Privilege
- Grant only necessary permissions to DevOpsGPT
- Use IAM roles instead of long-term credentials
- Regularly rotate API keys and tokens

### 2. Audit & Monitoring
- Enable comprehensive logging
- Monitor all DevOpsGPT activities
- Set up alerts for sensitive operations

### 3. Input Validation
- Sanitize all user inputs
- Validate commands before execution
- Implement command whitelisting

### 4. Network Security
- Use VPN or private networks
- Enable TLS for all communications
- Restrict access to management interfaces

## 📊 Monitoring & Observability

### 1. Metrics Collection
```python
# Add to devops_gpt_core.py
from prometheus_client import Counter, Histogram, start_http_server

COMMAND_COUNTER = Counter('devops_gpt_commands_total', 'Total commands processed', ['status'])
COMMAND_DURATION = Histogram('devops_gpt_command_duration_seconds', 'Command execution time')

# Start metrics server
start_http_server(9090)
```

### 2. Logging Configuration
```python
import structlog

logger = structlog.get_logger()
logger.info("Command executed", command=command.intent, user="admin", result=result.success)
```

### 3. Health Checks
```python
# Add health check endpoint
@app.route('/health')
def health_check():
    return {'status': 'healthy', 'timestamp': datetime.now().isoformat()}
```

## 🚀 Production Deployment Checklist

- [ ] Configuration files secured and encrypted
- [ ] Cloud credentials properly configured
- [ ] RBAC permissions set up correctly
- [ ] Monitoring and logging enabled
- [ ] Health checks implemented
- [ ] Backup and recovery procedures tested
- [ ] Security scanning completed
- [ ] Performance testing done
- [ ] Documentation updated
- [ ] Team training completed

## 🆘 Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Verify cloud credentials
   - Check IAM permissions
   - Validate API keys

2. **Kubernetes Connection Issues**
   - Check kubectl context
   - Verify cluster connectivity
   - Validate service account permissions

3. **Plugin Loading Failures**
   - Check dependencies installation
   - Verify configuration files
   - Review error logs

### Debug Mode
```bash
# Run with debug logging
export LOG_LEVEL=DEBUG
python devops_gpt_core.py
```

### Support
- Create issues on GitHub repository
- Check documentation wiki
- Join community Discord/Slack

## 🔄 Updates & Maintenance

### Regular Tasks
- Update dependencies monthly
- Rotate credentials quarterly
- Review audit logs weekly
- Test disaster recovery procedures

### Version Updates
```bash
# Update to latest version
git pull origin main
pip install -r requirements.txt --upgrade
python devops_gpt_core.py --version
```

---

**🎉 Congratulations!** You now have DevOpsGPT set up and ready to automate your operational tasks. Start with simple commands and gradually expand to more complex workflows as you become familiar with the system.