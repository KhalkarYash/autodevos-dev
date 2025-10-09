**Project Name:** AutoDevOS – Autonomous Multi-Agent Software Development Platform

**Project Goal:**

Build a **full-fledged AutoDevOS system** — an AI-driven platform that autonomously generates complete applications from high-level natural language prompts. The system should demonstrate **multi-agent orchestration, meta-agent task decomposition, and AI-powered code generation**, with a **production-quality, modular, maintainable, and scalable architecture**.

---

### **Requirements & Features**

#### **1. Meta-Agent / Orchestration Layer**

* Language: **Python**
* Responsibilities:

  * Parse natural language user prompts and extract features.
  * Break tasks into a **task DAG** with dependencies.
  * Spawn specialized agents (Frontend, Backend, Testing, DevOps optional).
  * Collect outputs and integrate modules seamlessly.
  * Maintain **shared project context** using MCP (Model Context Protocol) simulation.
  * Handle error detection, logging, and graceful failure management.
  * Provide a **modular interface for AI calls** (`generateCode(prompt)`) to allow future LLM upgrades.

---

#### **2. Specialized Agents**

* **Frontend Agent**

  * Language: **React + TypeScript**
  * Generate reusable, modular UI components and pages.
  * Use Tailwind CSS or Material UI for styling.
  * Write clean, maintainable, and well-commented code.

* **Backend Agent**

  * Language: **Node.js + Express + TypeScript**
  * Generate REST APIs, database models, authentication (JWT optional).
  * Follow MVC or similar modular architecture.

* **Testing Agent**

  * Language: **Jest (JS/TS) / PyTest (Python)**
  * Generate reusable unit and integration tests for frontend and backend.
  * Include logs to show test coverage.

* **Documentation Agent**

  * Generate **README, API documentation, and usage instructions**.
  * Document folder structure, agent responsibilities, and running instructions.

---

#### **3. LLM Integration**

* All AI code generation inside AutoDevOS should **use Gemini LLM** for now.
* Design a **modular interface** for LLM calls so it can be swapped with GPT-4/5 later.
* Agents should use LLM to generate high-quality, fully-functional code modules.

---

#### **4. Task Orchestration & Communication**

* Lightweight **Python async or threads** for parallel execution.
* Shared **MCP context (JSON or Python dictionary)** for agent collaboration.
* Tasks run **in parallel when independent** and **sequentially when dependent**.

---

#### **5. Deployment**

* Auto-generate **Dockerfile** for local deployment.
* Ready to run application with minimal setup.
* Modular deployment structure for later cloud integration.

---

#### **6. Code Quality Standards**

* **Clean, readable, modular, maintainable, and reusable code**.
* Well-structured folders per agent.
* Proper commenting and documentation in code.
* Avoid hardcoding; use **configurable parameters**.
* Include **logging / console outputs** to track agent workflow.

---

### **7. Deliverables**

1. **AutoDevOS root folder** containing:

   * `meta_agent/` → orchestration code, context manager, utils
   * `agents/` → frontend, backend, testing, documentation
   * `docker/` → Dockerfile for local deployment
   * `README.md` with clear instructions
   * `requirements.txt` and `package.json` for dependencies

2. Fully functioning **meta-agent and specialized agents** integrated.

3. **MCP-based context system** for inter-agent communication.

4. Working demo:

   * Accept a natural language prompt
   * Generate frontend + backend + tests automatically
   * Show integrated application running via Docker

---

### **8. Folder Structure Reference**

```
AutoDevOS/
├── meta_agent/
│   ├── orchestrator.py
│   ├── context_manager.py
│   └── utils.py
├── agents/
│   ├── frontend_agent/
│   │   ├── generate_ui.py
│   │   └── components/
│   ├── backend_agent/
│   │   ├── generate_api.py
│   │   └── models/
│   ├── testing_agent/
│   │   └── generate_tests.py
│   └── documentation_agent/
│       └── generate_docs.py
├── docker/
│   └── Dockerfile
├── README.md
├── requirements.txt
└── package.json
```

---

### **Additional Instructions to Warp**

* **Do not treat this as a prototype** — generate full, production-quality code.
* Ensure **all modules are functional and integrated**.
* Maintain **high code quality and modularity**.
* Generate **self-contained scripts** — running the demo should require minimal setup.
* Include **logging, error handling, and context tracking** for all agents.
