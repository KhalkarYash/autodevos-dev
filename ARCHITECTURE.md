# AutoDevOS Architecture

## Overview

AutoDevOS is a production-grade, multi-agent autonomous software development platform that generates complete applications from natural language prompts.

## System Architecture

### Meta-Agent Layer (`meta_agent/`)

The orchestration layer that coordinates all specialized agents:

#### 1. `orchestrator.py`
- **Responsibilities:**
  - Parse natural language prompts
  - Create task DAG with dependencies
  - Spawn and coordinate specialized agents
  - Execute tasks in parallel when independent, sequentially when dependent
  - Collect and integrate outputs

- **Task Execution Flow:**
  ```
  Level 0 (Parallel): Frontend + Backend
  Level 1 (After 0): Testing
  Level 2 (After 1): Documentation
  ```

#### 2. `context_manager.py`
- **MCP-based Context System:**
  - Shared state across all agents
  - Event logging for audit trail
  - Artifact tracking
  - JSON-serializable context storage

#### 3. `llm_interface.py`
- **Modular LLM Integration:**
  - `BaseLLM` interface for swappable models
  - `GeminiLLM` with automatic fallback to `MockLLM`
  - Environment-based configuration
  - Error handling and graceful degradation

#### 4. `utils.py`
- Logging with Rich integration
- File operations (ensure_dir, write_text, write_json)
- Environment variable helpers
- Hash utilities

### Specialized Agents (`agents/`)

#### Frontend Agent (`frontend_agent/`)
Generates React + TypeScript applications:
- **Stack:** Vite + React 18 + TypeScript + Tailwind CSS
- **Testing:** Jest + Testing Library + jsdom
- **Features:**
  - Complete project scaffolding
  - Responsive UI with Tailwind
  - Type-safe components
  - Test setup included

#### Backend Agent (`backend_agent/`)
Generates Node.js + Express + TypeScript APIs:
- **Architecture:** MVC pattern
  - Models: Data structures
  - Controllers: Business logic
  - Routes: API endpoints
  - Repository: Data access layer
- **Features:**
  - RESTful API design
  - CORS enabled
  - In-memory data store (extensible to DB)
  - Jest + Supertest integration tests

#### Testing Agent (`testing_agent/`)
Creates cross-cutting integration tests:
- **Python PyTest** for system-level validation
- Verifies artifact generation
- Can be extended for E2E testing

#### Documentation Agent (`documentation_agent/`)
Generates comprehensive documentation:
- Project README
- API documentation
- Setup instructions
- Architecture overview

## Data Flow

```
User Prompt
    ↓
Orchestrator.plan()
    ↓
Task DAG Creation
    ↓
Parallel Execution (Frontend + Backend)
    ↓
Sequential Execution (Testing)
    ↓
Sequential Execution (Documentation)
    ↓
Context Save + Artifact Collection
```

## MCP Context Protocol

The `MCPContext` provides a shared memory space for agents:

```python
ctx.set("key", value)          # Store data
ctx.get("key")                 # Retrieve data
ctx.add_artifact(agent, path)  # Register output
ctx.append_event(kind, data)   # Log events
ctx.save()                     # Persist to disk
```

## LLM Integration Strategy

### Current: Gemini
- Model: `gemini-1.5-flash`
- API: `google-generativeai`
- Auth: `GEMINI_API_KEY` environment variable

### Fallback: MockLLM
- Deterministic template-based responses
- Enables offline development
- No external dependencies

### Future Extensions
To add GPT-4/5 or other models:
```python
class GPT4LLM(BaseLLM):
    def generate_code(self, prompt, system, temperature, max_tokens):
        # Implement OpenAI API call
        pass
```

## Deployment

### Local Development
```bash
# Install Python dependencies
pip install -r requirements.txt

# Generate application
python main.py --prompt "Build a Todo app"

# Install and run generated apps
npm --prefix output/frontend/app ci && npm run dev
npm --prefix output/backend/app ci && npm run dev
```

### Docker
```bash
docker build -t autodevos:latest -f docker/Dockerfile .
docker run -e DEMO_PROMPT="Your prompt" -p 3000:3000 -p 5173:5173 autodevos:latest
```

## Code Quality Standards

### Python
- Type hints with `from __future__ import annotations`
- Docstrings for public functions
- Logging at appropriate levels
- Exception handling with graceful degradation

### Generated TypeScript
- Strict mode enabled
- ESLint-compatible patterns
- Comprehensive test coverage
- Modular, maintainable structure

## Extensibility

### Adding New Agents
1. Create `agents/new_agent/generate_task.py`
2. Implement function signature: `def generate_task(prompt, ctx, out_dir, llm) -> None`
3. Register in `orchestrator.py` task list
4. Define dependencies in Task object

### Adding New LLM Providers
1. Extend `BaseLLM` in `llm_interface.py`
2. Implement `generate_code()` method
3. Update `make_llm()` factory function
4. Configure via environment variables

## Security Considerations

- **Secrets:** All sensitive data via environment variables
- **LLM API Keys:** Never committed to source control
- **Generated Code:** Sandboxed execution recommended
- **Docker:** Non-root user recommended for production

## Performance

- **Parallel Execution:** Independent agents run concurrently
- **Async I/O:** Python asyncio for orchestration
- **Caching:** Context persisted to avoid regeneration
- **Resource Limits:** Configurable via LLM max_tokens

## Monitoring & Logging

- **Rich Console:** Colorized, structured logging
- **Event Stream:** All agent actions logged to context
- **Artifacts:** All outputs tracked with agent attribution
- **Context JSON:** Complete audit trail persisted

## Testing Strategy

1. **Unit Tests:** Each agent function testable independently
2. **Integration Tests:** PyTest validates artifact generation
3. **Generated Tests:** Frontend/Backend include Jest test suites
4. **Manual Verification:** Docker demo validates end-to-end flow

## Future Roadmap

- [ ] Database agent (PostgreSQL/MongoDB schemas)
- [ ] DevOps agent (CI/CD pipelines, Kubernetes manifests)
- [ ] Advanced DAG scheduler with retries
- [ ] Web UI for prompt submission
- [ ] Multi-project workspace management
- [ ] Version control integration (git commit automation)
- [ ] Code review agent with quality metrics
