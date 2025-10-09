# AutoDevOS Quick Start Guide

## 🚀 What You Just Built

You now have a **fully functional multi-agent autonomous software development platform** that:
- ✅ Accepts natural language prompts
- ✅ Generates complete React + TypeScript frontends
- ✅ Generates Node.js + Express + TypeScript backends
- ✅ Creates comprehensive test suites
- ✅ Auto-generates documentation
- ✅ Orchestrates everything via async task DAG

## 📁 Project Structure

```
AutoDevOS/
├── meta_agent/              # Orchestration layer
│   ├── orchestrator.py      # Task DAG & parallel execution
│   ├── context_manager.py   # MCP-based shared context
│   ├── llm_interface.py     # Modular LLM (Gemini/Mock)
│   └── utils.py             # Logging & file operations
│
├── agents/                  # Specialized agents
│   ├── frontend_agent/      # React + TS + Tailwind + Jest
│   ├── backend_agent/       # Express + TS + Jest
│   ├── testing_agent/       # PyTest integration tests
│   └── documentation_agent/ # Auto-generated docs
│
├── output/                  # Generated artifacts (gitignored)
│   ├── frontend/app/        # Complete React app
│   ├── backend/app/         # Complete Express API
│   ├── testing/python/      # Integration tests
│   └── documentation/docs/  # Project docs
│
├── docker/                  # Containerization
│   └── Dockerfile           # All-in-one deployment
│
├── main.py                  # Entry point
├── demo.py                  # Demo script
├── README.md                # Main documentation
├── ARCHITECTURE.md          # System design
└── requirements.txt         # Python dependencies
```

## 🎯 Usage

### Option 1: Local Development

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Generate an application:**
   ```bash
   python3 main.py --prompt "Build a Blog platform with posts and comments"
   ```

3. **Install & run the generated backend:**
   ```bash
   cd output/backend/app
   npm install
   npm run dev  # Runs on http://localhost:3000
   ```

4. **Install & run the generated frontend:**
   ```bash
   cd output/frontend/app
   npm install
   npm run dev  # Runs on http://localhost:5173
   ```

### Option 2: Use Concurrently (from root)

```bash
npm install
npm run dev  # Runs both frontend and backend
```

### Option 3: Docker (All-in-One)

```bash
docker build -t autodevos:latest -f docker/Dockerfile .
docker run -e DEMO_PROMPT="Build an E-commerce store" -p 3000:3000 -p 5173:5173 autodevos:latest
```

## 🔑 Using Gemini LLM (Optional)

By default, AutoDevOS uses a MockLLM for offline testing. To use Gemini:

1. Get API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Set environment variable:
   ```bash
   export GEMINI_API_KEY="your-api-key-here"
   ```
3. Run as normal:
   ```bash
   python3 main.py --prompt "Your prompt here"
   ```

## 📝 Example Prompts

Try these to see AutoDevOS in action:

```bash
# Simple CRUD app
python3 main.py --prompt "Build a Todo app with create, read, update, delete"

# Blog platform
python3 main.py --prompt "Build a blog with posts, comments, and user authentication"

# E-commerce
python3 main.py --prompt "Build an online store with product catalog and shopping cart"

# Task tracker
python3 main.py --prompt "Build a project management tool with tasks and status tracking"
```

## 🧪 Testing Generated Code

### Backend Tests
```bash
cd output/backend/app
npm test
```

### Frontend Tests
```bash
cd output/frontend/app
npm test
```

### Integration Tests
```bash
pip install pytest
pytest output/testing/python/
```

## 🔍 Generated API Endpoints

Every backend includes these by default:

```
GET  /api/health          → { status: 'ok' }
GET  /api/items           → List all items
POST /api/items           → Create new item (body: { name: string })
```

## 🎨 Frontend Stack

- **Framework:** React 18
- **Language:** TypeScript (strict mode)
- **Build Tool:** Vite
- **Styling:** Tailwind CSS
- **Testing:** Jest + Testing Library

## 🔧 Backend Stack

- **Runtime:** Node.js
- **Framework:** Express
- **Language:** TypeScript
- **Architecture:** MVC (Models, Controllers, Routes, Repository)
- **Testing:** Jest + Supertest

## 🏗️ How It Works

1. **User provides natural language prompt**
2. **Orchestrator creates task DAG:**
   - Level 0: Frontend + Backend (parallel)
   - Level 1: Testing (after 0)
   - Level 2: Documentation (after 1)
3. **Agents execute tasks:**
   - Each agent uses LLM to generate code
   - Artifacts stored in `output/`
   - Context shared via MCP protocol
4. **Complete app ready to run**

## 🔄 Extending AutoDevOS

### Add a New Agent

1. Create `agents/new_agent/generate_task.py`
2. Implement signature:
   ```python
   def generate_task(prompt: str, ctx: MCPContext, out_dir: Path, llm: BaseLLM) -> None:
       # Your logic here
       pass
   ```
3. Register in `orchestrator.py`:
   ```python
   Task(id="newtask", name="New Task", agent="new_agent", 
        fn=self._wrap_sync(generate_task), depends_on=["frontend"])
   ```

### Add a New LLM Provider

1. Extend `BaseLLM` in `llm_interface.py`:
   ```python
   class GPT4LLM(BaseLLM):
       def generate_code(self, prompt, system, temperature, max_tokens):
           # OpenAI API call
           pass
   ```

## 🐛 Troubleshooting

**Issue:** `GEMINI_API_KEY not set`
- **Solution:** This is expected. MockLLM is used as fallback.

**Issue:** `npm: command not found`
- **Solution:** Install Node.js 18+

**Issue:** Generated app won't run
- **Solution:** Run `npm install` in the generated app directory first

**Issue:** Port already in use
- **Solution:** Change ports in generated code or kill existing process

## 📚 Learn More

- **README.md** - Overview and setup
- **ARCHITECTURE.md** - System design and internals
- **output/documentation/docs/** - Generated project docs

## 🎉 Success!

You've successfully set up AutoDevOS! The system is ready to generate production-quality applications from natural language prompts.

**Next Steps:**
1. Try different prompts
2. Examine generated code quality
3. Extend with custom agents
4. Deploy generated apps to production

Happy building! 🚀
