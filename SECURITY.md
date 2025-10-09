# Security and Secrets Management Guide

## Overview

This document provides security best practices and secrets management guidance for the AutoDevOS project.

## API Keys and Secrets

### Gemini API Key

The Gemini API key is the primary secret used in this application.

**Loading Priority:**

1. Environment variable `GEMINI_API_KEY`
2. `.env` file (local development only)
3. Secrets manager (production)

**Best Practices:**

- ✅ DO: Store in environment variables or secrets manager
- ✅ DO: Rotate keys regularly (every 90 days)
- ✅ DO: Use different keys for dev/staging/prod
- ❌ DON'T: Commit keys to git
- ❌ DON'T: Share keys in chat or email
- ❌ DON'T: Hardcode keys in source code

### Local Development

1. Copy `.env.example` to `.env`:

   ```bash
   cp .env.example .env
   ```

2. Add your Gemini API key to `.env`:

   ```
   GEMINI_API_KEY=your_actual_key_here
   ```

3. Ensure `.env` is in `.gitignore` (already configured)

### Production Deployment

**Option 1: Environment Variables**

```bash
export GEMINI_API_KEY="your-production-key"
python main.py
```

**Option 2: Docker Secrets**

```bash
# Create secret file
echo "your-production-key" > gemini_api_key.txt

# Run with secret
docker run --rm \
  --secret gemini_api_key,target=/run/secrets/gemini_api_key \
  autodevos:latest
```

**Option 3: Cloud Secrets Manager**

For AWS:

```python
import boto3

def get_secret():
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId='autodevos/gemini-api-key')
    return response['SecretString']
```

For Azure:

```python
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

def get_secret():
    credential = DefaultAzureCredential()
    client = SecretClient(vault_url="https://<vault-name>.vault.azure.net/", credential=credential)
    return client.get_secret("gemini-api-key").value
```

For GCP:

```python
from google.cloud import secretmanager

def get_secret():
    client = secretmanager.SecretManagerServiceClient()
    name = "projects/<project-id>/secrets/gemini-api-key/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")
```

## Security Checklist

### Code Security

- [x] No hardcoded secrets
- [x] Input validation in all agents
- [x] LLM prompt injection prevention
- [x] Error messages don't leak sensitive info
- [x] Dependency vulnerability scanning (CI)
- [x] Non-root Docker user
- [ ] TODO: Add rate limiting for LLM calls
- [ ] TODO: Add output sanitization

### Infrastructure Security

- [x] Multi-stage Docker builds
- [x] Minimal base images
- [x] Non-root container user
- [x] Health checks
- [ ] TODO: Container image scanning
- [ ] TODO: Network policies
- [ ] TODO: Resource limits

### CI/CD Security

- [x] Secrets stored in GitHub Secrets
- [x] Security scanning with Bandit
- [x] Dependency vulnerability checks with Safety
- [x] Code quality checks
- [ ] TODO: SAST/DAST integration
- [ ] TODO: Container scanning
- [ ] TODO: License compliance checks

## Vulnerability Management

### Regular Scans

Run security scans regularly:

```bash
# Python dependency vulnerabilities
pip install safety
safety check

# Code security issues
pip install bandit
bandit -r meta_agent agents

# Update dependencies
pip list --outdated
```

### Dependency Updates

Update dependencies quarterly or when critical CVEs are announced:

```bash
# Check for updates
pip list --outdated

# Update specific package
pip install --upgrade google-generativeai

# Regenerate lockfile
pip freeze > requirements.txt
```

## Incident Response

If a secret is compromised:

1. **Immediately revoke** the compromised key
2. **Generate** a new key
3. **Update** all deployments with the new key
4. **Review** access logs for unauthorized usage
5. **Audit** git history if key was committed
6. **Document** the incident

## Audit Logging

Enable audit logging for production:

```python
# In config.yaml
logging:
  level: INFO
  audit: true
  sensitive_fields:
    - api_key
    - password
    - token
```

## Network Security

### Firewall Rules

- Only expose necessary ports (3000, 5173)
- Use TLS for all external communication
- Implement rate limiting
- Use API gateways for production

### API Security

- Implement authentication/authorization
- Use API keys or OAuth tokens
- Rate limit API endpoints
- Validate all inputs
- Sanitize all outputs

## Compliance

### Data Privacy

- Don't log user prompts containing PII
- Implement data retention policies
- Support GDPR/CCPA compliance if applicable
- Encrypt data at rest and in transit

### License Compliance

- Review all dependencies for license compatibility
- Document all third-party licenses
- Ensure generated code complies with licenses

## Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CIS Docker Benchmark](https://www.cisecurity.org/benchmark/docker)
- [Google Cloud Security Best Practices](https://cloud.google.com/security/best-practices)
- [GitHub Security Best Practices](https://docs.github.com/en/code-security)

## Contact

For security issues, please email: security@autodevos.example.com
(Do not create public GitHub issues for security vulnerabilities)
