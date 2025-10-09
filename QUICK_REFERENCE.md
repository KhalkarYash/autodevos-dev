# AutoDevOS Quick Reference Guide

## 🚀 Common Commands

### Generate Application
```bash
# Basic generation
python3 main.py --prompt "Build a Todo app"

# With custom output directory
python3 main.py --prompt "Your prompt" --output my_output

# Full demo with all steps
python3 scripts/demo_full.py --prompt "Your prompt"
```

### Run Tests
```bash
# All tests
pytest

# Unit tests only
pytest tests/unit

# Integration tests only
pytest tests/integration

# With coverage
pytest --cov=meta_agent --cov=agents
```

### Docker
```bash
# Build image
docker build -t autodevos -f docker/Dockerfile .

# Run full workflow
docker run -e DEMO_PROMPT="Your prompt" -p 3000:3000 -p 5173:5173 autodevos

# Run specific command
docker run autodevos generate
docker run autodevos test
docker run autodevos bash
```

### Development
```bash
# Format code
black meta_agent agents tests

# Lint code
flake8 meta_agent agents tests

# Type check
mypy meta_agent agents
```

## 📁 Project Structure

```
AutoDevOS/
├── meta_agent/              # Core orchestration
│   ├── orchestrator.py      # Dynamic planning + DAG execution
│   ├── dag_scheduler.py     # Task scheduler
│   ├── context_manager.py   # Thread-safe MCP context
│   ├── llm_interface.py     # Gemini + MockLLM
│   └── utils.py             # Utilities
│
├── agents/                  # Specialized agents
│   ├── frontend_agent/      # React + TS + Tailwind
│   ├── backend_agent/       # Express + Prisma + JWT
│   ├── testing_agent/       # PyTest
│   └── documentation_agent/ # Docs generator
│
├── tests/                   # Test suite
│   ├── unit/               # Unit tests
│   └── integration/        # Integration tests
│
├── docker/                  # Docker config
│   ├── Dockerfile          # Multi-stage build
│   └── entrypoint.sh       # Entrypoint script
│
├── scripts/                 # Utility scripts
│   └── demo_full.py        # End-to-end demo
│
├── .github/workflows/       # CI/CD
│   └── ci.yml              # GitHub Actions
│
└── output/                  # Generated artifacts (gitignored)
```

## 🔧 Configuration

### Environment Variables
```bash
# LLM Configuration
export GEMINI_API_KEY="your-api-key"

# Demo Prompt (Docker)
export DEMO_PROMPT="Your prompt here"
```

### Config Files
- **`config.yaml`** - Orchestrator settings
- **`pyproject.toml`** - Python tool configuration
- **`pytest.ini`** - Test configuration
- **`.env.example`** - Environment template

## 📝 Generated Backend API

Every generated backend includes:

```bash
# Authentication
POST /api/auth/register    # Register new user
POST /api/auth/login       # Login user

# Items (requires authentication)
GET    /api/items          # List items
POST   /api/items          # Create item
PUT    /api/items/:id      # Update item
DELETE /api/items/:id      # Delete item

# Health
GET /api/health            # Health check
```

### Authentication Flow
```bash
# 1. Register
curl -X POST http://localhost:3000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password123","name":"User"}'

# Response: { "user": {...}, "token": "jwt-token" }

# 2. Use token for protected routes
curl -X GET http://localhost:3000/api/items \
  -H "Authorization: Bearer jwt-token"
```

## 🧪 Testing Workflow

### Run Generated App Tests
```bash
# Backend tests
cd output/backend/app
npm test

# Frontend tests
cd output/frontend/app
npm test
```

### Run Platform Tests
```bash
# Quick smoke test
pytest tests/unit/test_context_manager.py -v

# Full test suite
pytest -v

# With coverage report
pytest --cov --cov-report=html
open htmlcov/index.html  # View coverage
```

## 🐛 Debugging

### Enable Debug Logging
```python
# In your code
from meta_agent.utils import setup_logger
import logging

log = setup_logger(level=logging.DEBUG)
```

### View Context State
```python
from meta_agent.context_manager import MCPContext
from pathlib import Path

ctx = MCPContext.load("project_name", Path("output/.ctx"))
print(ctx.data)
print(ctx.events)
```

### Inspect DAG Execution
```python
# Check execution summary
summary = await orch.run(prompt, ctx)
print(f"Completed: {summary['completed']}")
print(f"Failed: {summary['failed']}")
print(f"Details: {summary['tasks']}")
```

## 🚨 Troubleshooting

### Issue: LLM Timeout
**Solution:** Increase timeout in `llm_interface.py`:
```python
llm = GeminiLLM(timeout=120.0)  # 2 minutes
```

### Issue: Database Locked (SQLite)
**Solution:** Restart backend or use PostgreSQL:
```prisma
datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}
```

### Issue: Port Already in Use
**Solution:** Change ports in generated `server.ts`:
```typescript
const port = process.env.PORT || 3001;  // Use 3001
```

### Issue: Tests Failing
**Solution:** Check test output and run with verbose:
```bash
pytest -vv --tb=long
```

## 📊 Performance Tuning

### Parallel Task Execution
```python
# Increase parallelism
orch = Orchestrator(max_parallel=8)  # Default: 4
```

### LLM Response Speed
```python
# Use streaming for long responses
for chunk in llm.generate_streaming(prompt):
    print(chunk, end='')
```

### Docker Build Speed
```bash
# Use buildkit cache
docker buildx build --cache-from=type=local,src=/tmp/cache .
```

## 🔐 Security Best Practices

1. **Never commit secrets**
   - Use `.env` for local development
   - Use secrets managers for production

2. **Rotate JWT secrets regularly**
   ```bash
   # Generate new secret
   openssl rand -hex 32
   ```

3. **Use HTTPS in production**
   ```typescript
   // Add helmet middleware
   import helmet from 'helmet';
   app.use(helmet());
   ```

4. **Validate all inputs**
   ```typescript
   // Already included in generated code
   if (!name) return res.status(400).json({ error: 'name required' });
   ```

## 🎯 Quick Examples

### Example 1: Simple CRUD App
```bash
python3 main.py --prompt "Build a blog with posts and comments"
```

### Example 2: Auth System
```bash
python3 main.py --prompt "Build a user management system with roles"
```

### Example 3: API Only (No Frontend)
```python
# In orchestrator.py, customize plan
def _custom_plan(self):
    return [
        {"id": "backend", "name": "Generate Backend", "depends_on": []},
        {"id": "testing", "name": "Generate Tests", "depends_on": ["backend"]},
        {"id": "docs", "name": "Generate Docs", "depends_on": ["backend"]},
    ]
```

## 📚 Additional Resources

- **Main Docs:** `README.md`
- **Architecture:** `ARCHITECTURE.md`
- **Quick Start:** `QUICKSTART.md`
- **Development Status:** `DEVELOPMENT_STATUS.md`
- **Implementation Details:** `IMPLEMENTATION_COMPLETE.md`

## 💡 Pro Tips

1. **Use descriptive prompts:** "Build a task tracker with user auth and real-time updates"
2. **Check context after generation:** `cat output/.ctx/context.json | jq`
3. **Run tests before deploying:** Always validate generated code
4. **Use Docker for isolation:** Keeps your system clean
5. **Leverage CI/CD:** Push to GitHub and let automation handle testing

---

**Need help?** Check the full documentation or open an issue!
