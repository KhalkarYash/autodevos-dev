from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from meta_agent.utils import ensure_dir, write_text, write_json, log
from meta_agent.llm_interface import BaseLLM
from meta_agent.context_manager import MCPContext


# System prompt for backend generation
BACKEND_SYSTEM_PROMPT = """You are an expert Node.js/Express/TypeScript developer.
Generate clean, production-ready backend code following these rules:
- Use TypeScript with proper type definitions
- Follow Express best practices
- Include proper error handling
- Use Prisma for database operations
- Return ONLY code, no explanations or markdown code blocks
- Do NOT wrap code in markdown code fences
- STRICTLY follow the API contract provided - do not deviate from it"""


def generate_api(prompt: str, ctx: MCPContext, out_dir: Path, llm: BaseLLM) -> Dict[str, str]:
    """Generate a Node.js + Express + TypeScript backend based on API contract.
    
    Uses API contract from documentation agent to ensure consistency with frontend.
    
    Returns:
        Dict[str, str]: Key-value pairs where key is file path and value is file content
    """
    project_dir = out_dir
    ensure_dir(project_dir / "src")
    ensure_dir(project_dir / "src/routes")
    ensure_dir(project_dir / "src/controllers")
    ensure_dir(project_dir / "src/lib")
    ensure_dir(project_dir / "src/models")
    ensure_dir(project_dir / "src/types")
    ensure_dir(project_dir / "tests")
    ensure_dir(project_dir / "prisma")
    
    # Track all generated files
    generated_files: Dict[str, str] = {}
    
    # Get API contract from documentation agent
    api_contract = ctx.get_api_contract()
    if api_contract:
        log.info(f"Using API contract with {len(api_contract.get('endpoints', []))} endpoints")
    else:
        log.warning("No API contract found - generating with default contract")
        api_contract = _default_api_contract()
    
    # 1. Generate package.json
    pkg_files = _generate_package_json(project_dir)
    generated_files.update(pkg_files)
    
    # 2. Generate TypeScript config
    ts_files = _generate_tsconfig(project_dir)
    generated_files.update(ts_files)
    
    # 3. Generate Prisma schema from API contract
    prisma_files = _generate_prisma_schema(project_dir, api_contract, llm, prompt)
    generated_files.update(prisma_files)
    
    # 4. Generate environment files
    env_files = _generate_env_files(project_dir)
    generated_files.update(env_files)
    
    # 5. Generate lib files (db, jwt)
    lib_files = _generate_lib_files(project_dir, api_contract)
    generated_files.update(lib_files)
    
    # 6. Generate models/types from API contract
    model_files = _generate_models(project_dir, api_contract)
    generated_files.update(model_files)
    
    # 7. Generate controllers from API contract
    controller_files = _generate_controllers(project_dir, api_contract, llm, prompt)
    generated_files.update(controller_files)
    
    # 8. Generate routes from API contract
    route_files = _generate_routes(project_dir, api_contract)
    generated_files.update(route_files)
    
    # 9. Generate main app.ts and server.ts
    app_files = _generate_app_files(project_dir, api_contract)
    generated_files.update(app_files)
    
    # 10. Generate tests
    test_files = _generate_tests(project_dir, api_contract)
    generated_files.update(test_files)
    
    # 11. Generate additional config files
    config_files = _generate_config_files(project_dir)
    generated_files.update(config_files)
    
    # Store generated files in context
    ctx.set_generated_files("backend", generated_files)
    ctx.add_artifact("backend", project_dir)
    
    log.info(f"Backend generated at: {project_dir}")
    log.info(f"Generated {len(generated_files)} files")
    
    return generated_files


def _default_api_contract() -> Dict[str, Any]:
    """Default API contract if none provided."""
    return {
        "api_version": "1.0.0",
        "base_url": "/api",
        "authentication": {"type": "jwt", "header": "Authorization", "prefix": "Bearer"},
        "endpoints": [
            {"method": "GET", "path": "/health", "name": "healthCheck", "auth_required": False},
            {"method": "POST", "path": "/auth/register", "name": "register", "auth_required": False},
            {"method": "POST", "path": "/auth/login", "name": "login", "auth_required": False},
            {"method": "GET", "path": "/items", "name": "listItems", "auth_required": True},
            {"method": "POST", "path": "/items", "name": "createItem", "auth_required": True},
            {"method": "PUT", "path": "/items/:id", "name": "updateItem", "auth_required": True},
            {"method": "DELETE", "path": "/items/:id", "name": "deleteItem", "auth_required": True}
        ],
        "models": ["User", "Item"]
    }


def _generate_package_json(project_dir: Path) -> Dict[str, str]:
    """Generate package.json."""
    pkg = {
        "name": "autodevos-backend",
        "private": True,
        "version": "0.1.0",
        "type": "module",
        "scripts": {
            "dev": "ts-node-dev --respawn --transpile-only src/server.ts",
            "build": "tsc -p .",
            "start": "node dist/server.js",
            "test": "jest --runInBand",
            "db:generate": "prisma generate",
            "db:push": "prisma db push",
            "db:migrate": "prisma migrate dev"
        },
        "dependencies": {
            "express": "^4.21.1",
            "cors": "^2.8.5",
            "@prisma/client": "^5.22.0",
            "bcryptjs": "^2.4.3",
            "jsonwebtoken": "^9.0.2",
            "dotenv": "^16.4.5"
        },
        "devDependencies": {
            "@types/express": "^4.17.21",
            "@types/jest": "^29.5.14",
            "@types/node": "^22.7.5",
            "@types/supertest": "^6.0.3",
            "@types/bcryptjs": "^2.4.6",
            "@types/jsonwebtoken": "^9.0.7",
            "@types/cors": "^2.8.17",
            "jest": "^29.7.0",
            "supertest": "^7.0.0",
            "ts-jest": "^29.3.4",
            "ts-node": "^10.9.2",
            "ts-node-dev": "^2.0.0",
            "typescript": "^5.6.3",
            "prisma": "^5.22.0"
        }
    }
    content = json.dumps(pkg, indent=2)
    write_json(project_dir / "package.json", pkg)
    return {"package.json": content}


def _generate_tsconfig(project_dir: Path) -> Dict[str, str]:
    """Generate TypeScript config."""
    tsconfig = {
        "compilerOptions": {
            "target": "ES2020",
            "module": "ESNext",
            "moduleResolution": "Bundler",
            "outDir": "dist",
            "rootDir": "src",
            "strict": True,
            "esModuleInterop": True,
            "skipLibCheck": True,
            "forceConsistentCasingInFileNames": True
        },
        "include": ["src", "jest.config.ts", "tests"]
    }
    content = json.dumps(tsconfig, indent=2)
    write_json(project_dir / "tsconfig.json", tsconfig)
    
    # Jest config
    jest_cfg = """import type { Config } from 'jest'

const config: Config = {
  testEnvironment: 'node',
  transform: {
    '^.+\\.(ts)$': ['ts-jest', { tsconfig: 'tsconfig.json' }],
  },
  moduleFileExtensions: ['ts', 'js'],
}

export default config
"""
    write_text(project_dir / "jest.config.ts", jest_cfg)
    
    return {
        "tsconfig.json": content,
        "jest.config.ts": jest_cfg
    }


def _generate_prisma_schema(project_dir: Path, api_contract: Dict[str, Any], llm: BaseLLM, prompt: str) -> Dict[str, str]:
    """Generate Prisma schema based on API contract."""
    models = api_contract.get("models", ["User", "Item"])
    
    # Generate schema using LLM based on contract
    schema_prompt = f"""Generate a Prisma schema for these models: {models}

Application requirement: {prompt}

API Contract endpoints:
{json.dumps(api_contract.get('endpoints', []), indent=2)}

Requirements:
- Use SQLite as provider for simplicity
- Include proper relations between models
- Add timestamps (createdAt, updatedAt) to all models
- User should have: id, email, password, name, timestamps
- Other models should relate to User with userId foreign key
- Use @id @default(uuid()) for IDs

Return ONLY the Prisma schema code, no markdown."""

    schema_code = llm.generate_code(
        schema_prompt,
        system=BACKEND_SYSTEM_PROMPT,
        temperature=0.2,
        max_tokens=2048
    )
    
    # Clean and validate
    schema_code = _clean_code_response(schema_code)
    
    # Ensure minimum valid schema
    if "generator client" not in schema_code:
        schema_code = f"""generator client {{
  provider = "prisma-client-js"
}}

datasource db {{
  provider = "sqlite"
  url      = env("DATABASE_URL")
}}

{schema_code}"""
    
    write_text(project_dir / "prisma/schema.prisma", schema_code)
    return {"prisma/schema.prisma": schema_code}


def _generate_env_files(project_dir: Path) -> Dict[str, str]:
    """Generate environment files."""
    env_content = """# Database
DATABASE_URL="file:./dev.db"

# JWT
JWT_SECRET=your-secret-key-change-in-production
JWT_EXPIRES_IN=7d

# Server
PORT=3000
NODE_ENV=development
"""
    write_text(project_dir / ".env", env_content)
    
    env_example = env_content.replace("your-secret-key-change-in-production", "your-secret-key-here")
    write_text(project_dir / ".env.example", env_example)
    
    return {
        ".env": env_content,
        ".env.example": env_example
    }


def _generate_lib_files(project_dir: Path, api_contract: Dict[str, Any]) -> Dict[str, str]:
    """Generate lib files (db client, jwt utils)."""
    generated_files: Dict[str, str] = {}
    
    # Database client
    db_client = """import { PrismaClient } from '@prisma/client'

const globalForPrisma = globalThis as unknown as { prisma: PrismaClient }

export const prisma = globalForPrisma.prisma || new PrismaClient()

if (process.env.NODE_ENV !== 'production') globalForPrisma.prisma = prisma
"""
    write_text(project_dir / "src/lib/db.ts", db_client)
    generated_files["src/lib/db.ts"] = db_client
    
    # JWT utilities (only if auth endpoints exist)
    auth = api_contract.get("authentication", {})
    if auth.get("type") == "jwt":
        jwt_util = """import jwt from 'jsonwebtoken'
import { Request, Response, NextFunction } from 'express'

const JWT_SECRET = process.env.JWT_SECRET || 'fallback-secret'
const JWT_EXPIRES_IN = process.env.JWT_EXPIRES_IN || '7d'

export interface JWTPayload {
  userId: string
  email: string
}

export const generateToken = (payload: JWTPayload): string => {
  return jwt.sign(payload, JWT_SECRET, { expiresIn: JWT_EXPIRES_IN })
}

export const verifyToken = (token: string): JWTPayload => {
  return jwt.verify(token, JWT_SECRET) as JWTPayload
}

export const authMiddleware = (req: Request, res: Response, next: NextFunction) => {
  const authHeader = req.headers.authorization
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return res.status(401).json({ error: 'No token provided' })
  }
  const token = authHeader.substring(7)
  try {
    const decoded = verifyToken(token)
    req.user = decoded
    next()
  } catch (error) {
    return res.status(401).json({ error: 'Invalid token' })
  }
}
"""
        write_text(project_dir / "src/lib/jwt.ts", jwt_util)
        generated_files["src/lib/jwt.ts"] = jwt_util
    
    return generated_files


def _generate_models(project_dir: Path, api_contract: Dict[str, Any]) -> Dict[str, str]:
    """Generate TypeScript model interfaces from API contract."""
    generated_files: Dict[str, str] = {}
    
    # Generate type declarations for Express
    types_declaration = """declare global {
  namespace Express {
    interface Request {
      user?: { userId: string; email: string }
    }
  }
}

export {}
"""
    write_text(project_dir / "src/types/express.d.ts", types_declaration)
    generated_files["src/types/express.d.ts"] = types_declaration
    
    # Generate model interfaces
    models = api_contract.get("models", ["User", "Item"])
    model_content = """// Auto-generated model interfaces from API contract

export interface User {
  id: string
  email: string
  name?: string
  createdAt: Date
  updatedAt: Date
}

export interface Item {
  id: string
  name: string
  completed: boolean
  userId: string
  createdAt: Date
  updatedAt: Date
}

// DTOs
export interface CreateUserDTO {
  email: string
  password: string
  name?: string
}

export interface LoginDTO {
  email: string
  password: string
}

export interface CreateItemDTO {
  name: string
}

export interface UpdateItemDTO {
  name?: string
  completed?: boolean
}
"""
    write_text(project_dir / "src/models/index.ts", model_content)
    generated_files["src/models/index.ts"] = model_content
    
    return generated_files


def _generate_controllers(project_dir: Path, api_contract: Dict[str, Any], llm: BaseLLM, prompt: str) -> Dict[str, str]:
    """Generate controllers based on API contract."""
    generated_files: Dict[str, str] = {}
    endpoints = api_contract.get("endpoints", [])
    
    # Group endpoints by route prefix
    auth_endpoints = [ep for ep in endpoints if "/auth" in ep.get("path", "")]
    item_endpoints = [ep for ep in endpoints if "/items" in ep.get("path", "")]
    
    # Auth controller
    if auth_endpoints:
        auth_controller = """import { Request, Response } from 'express'
import bcrypt from 'bcryptjs'
import { prisma } from '../lib/db'
import { generateToken } from '../lib/jwt'

export const register = async (req: Request, res: Response) => {
  const { email, password, name } = req.body
  if (!email || !password) {
    return res.status(400).json({ error: 'Email and password required' })
  }
  try {
    const hashedPassword = await bcrypt.hash(password, 10)
    const user = await prisma.user.create({
      data: { email, password: hashedPassword, name }
    })
    const token = generateToken({ userId: user.id, email: user.email })
    return res.status(201).json({
      user: { id: user.id, email: user.email, name: user.name },
      token
    })
  } catch (error: any) {
    if (error.code === 'P2002') {
      return res.status(400).json({ error: 'Email already exists' })
    }
    return res.status(500).json({ error: 'Registration failed' })
  }
}

export const login = async (req: Request, res: Response) => {
  const { email, password } = req.body
  if (!email || !password) {
    return res.status(400).json({ error: 'Email and password required' })
  }
  try {
    const user = await prisma.user.findUnique({ where: { email } })
    if (!user) {
      return res.status(401).json({ error: 'Invalid credentials' })
    }
    const valid = await bcrypt.compare(password, user.password)
    if (!valid) {
      return res.status(401).json({ error: 'Invalid credentials' })
    }
    const token = generateToken({ userId: user.id, email: user.email })
    return res.json({
      user: { id: user.id, email: user.email, name: user.name },
      token
    })
  } catch (error) {
    return res.status(500).json({ error: 'Login failed' })
  }
}
"""
        write_text(project_dir / "src/controllers/authController.ts", auth_controller)
        generated_files["src/controllers/authController.ts"] = auth_controller
    
    # Items controller
    if item_endpoints:
        items_controller = """import { Request, Response } from 'express'
import { prisma } from '../lib/db'

export const list = async (req: Request, res: Response) => {
  try {
    const userId = req.user?.userId
    if (!userId) return res.status(401).json({ error: 'Unauthorized' })
    const items = await prisma.item.findMany({ where: { userId } })
    return res.json(items)
  } catch (error) {
    return res.status(500).json({ error: 'Failed to fetch items' })
  }
}

export const create = async (req: Request, res: Response) => {
  const { name } = req.body
  if (!name) return res.status(400).json({ error: 'Name required' })
  try {
    const userId = req.user?.userId
    if (!userId) return res.status(401).json({ error: 'Unauthorized' })
    const item = await prisma.item.create({ data: { name, userId } })
    return res.status(201).json(item)
  } catch (error) {
    return res.status(500).json({ error: 'Failed to create item' })
  }
}

export const update = async (req: Request, res: Response) => {
  const { id } = req.params
  const { name, completed } = req.body
  try {
    const userId = req.user?.userId
    if (!userId) return res.status(401).json({ error: 'Unauthorized' })
    const item = await prisma.item.update({
      where: { id, userId },
      data: { name, completed }
    })
    return res.json(item)
  } catch (error) {
    return res.status(404).json({ error: 'Item not found' })
  }
}

export const remove = async (req: Request, res: Response) => {
  const { id } = req.params
  try {
    const userId = req.user?.userId
    if (!userId) return res.status(401).json({ error: 'Unauthorized' })
    await prisma.item.delete({ where: { id, userId } })
    return res.status(204).send()
  } catch (error) {
    return res.status(404).json({ error: 'Item not found' })
  }
}
"""
        write_text(project_dir / "src/controllers/itemsController.ts", items_controller)
        generated_files["src/controllers/itemsController.ts"] = items_controller
    
    return generated_files


def _generate_routes(project_dir: Path, api_contract: Dict[str, Any]) -> Dict[str, str]:
    """Generate routes based on API contract."""
    generated_files: Dict[str, str] = {}
    endpoints = api_contract.get("endpoints", [])
    
    # Auth routes
    auth_endpoints = [ep for ep in endpoints if "/auth" in ep.get("path", "")]
    if auth_endpoints:
        auth_routes = """import { Router } from 'express'
import * as ctrl from '../controllers/authController'

const router = Router()
router.post('/register', ctrl.register)
router.post('/login', ctrl.login)

export default router
"""
        write_text(project_dir / "src/routes/auth.ts", auth_routes)
        generated_files["src/routes/auth.ts"] = auth_routes
    
    # Items routes
    item_endpoints = [ep for ep in endpoints if "/items" in ep.get("path", "")]
    if item_endpoints:
        items_routes = """import { Router } from 'express'
import * as ctrl from '../controllers/itemsController'
import { authMiddleware } from '../lib/jwt'

const router = Router()
router.use(authMiddleware)
router.get('/', ctrl.list)
router.post('/', ctrl.create)
router.put('/:id', ctrl.update)
router.delete('/:id', ctrl.remove)

export default router
"""
        write_text(project_dir / "src/routes/items.ts", items_routes)
        generated_files["src/routes/items.ts"] = items_routes
    
    return generated_files


def _generate_app_files(project_dir: Path, api_contract: Dict[str, Any]) -> Dict[str, str]:
    """Generate main app.ts and server.ts files."""
    generated_files: Dict[str, str] = {}
    endpoints = api_contract.get("endpoints", [])
    
    # Determine which routes to include
    has_auth = any("/auth" in ep.get("path", "") for ep in endpoints)
    has_items = any("/items" in ep.get("path", "") for ep in endpoints)
    
    imports = ["import 'dotenv/config'", "import express from 'express'", "import cors from 'cors'"]
    routes = []
    
    if has_auth:
        imports.append("import authRouter from './routes/auth'")
        routes.append("app.use('/api/auth', authRouter)")
    
    if has_items:
        imports.append("import itemsRouter from './routes/items'")
        routes.append("app.use('/api/items', itemsRouter)")
    
    app_ts = f"""{chr(10).join(imports)}

const app = express()
app.use(cors())
app.use(express.json())

// Health check
app.get('/api/health', (_req, res) => res.json({{ status: 'ok' }}))

// Routes
{chr(10).join(routes)}

export default app
"""
    write_text(project_dir / "src/app.ts", app_ts)
    generated_files["src/app.ts"] = app_ts
    
    server_ts = """import app from './app'

const port = process.env.PORT || 3000

app.listen(port, () => {
  console.log(`[backend] listening on :${port}`)
})
"""
    write_text(project_dir / "src/server.ts", server_ts)
    generated_files["src/server.ts"] = server_ts
    
    return generated_files


def _generate_tests(project_dir: Path, api_contract: Dict[str, Any]) -> Dict[str, str]:
    """Generate tests based on API contract."""
    generated_files: Dict[str, str] = {}
    
    test_api = """import request from 'supertest'
import app from '../src/app'

describe('API Health', () => {
  it('health check responds', async () => {
    const res = await request(app).get('/api/health')
    expect(res.status).toBe(200)
    expect(res.body.status).toBe('ok')
  })
})

describe('Auth API', () => {
  it('allows registration', async () => {
    const res = await request(app).post('/api/auth/register').send({
      email: `test${Date.now()}@example.com`,
      password: 'password123',
      name: 'Test User'
    })
    expect(res.status).toBe(201)
    expect(res.body.token).toBeDefined()
    expect(res.body.user.email).toBeDefined()
  })
})
"""
    write_text(project_dir / "tests/api.test.ts", test_api)
    generated_files["tests/api.test.ts"] = test_api
    
    return generated_files


def _generate_config_files(project_dir: Path) -> Dict[str, str]:
    """Generate additional config files."""
    generated_files: Dict[str, str] = {}
    
    # .gitignore
    gitignore = """node_modules/
dist/
.env
*.db
*.db-journal
.DS_Store
coverage/
.vscode/
.idea/
"""
    write_text(project_dir / ".gitignore", gitignore)
    generated_files[".gitignore"] = gitignore
    
    # README
    readme = """# AutoDevOS Backend

Generated Express + TypeScript + Prisma backend with JWT authentication.

## Setup

```bash
npm install
npm run db:generate
npm run db:push
```

## Development

```bash
npm run dev
```

## API Endpoints

See the API contract in the documentation folder for full endpoint specifications.

## Testing

```bash
npm test
```
"""
    write_text(project_dir / "README.md", readme)
    generated_files["README.md"] = readme
    
    return generated_files


def _clean_code_response(code: str) -> str:
    """Clean up LLM code response."""
    code = re.sub(r'^```(?:typescript|ts|javascript|js|prisma)?\s*\n?', '', code, flags=re.MULTILINE)
    code = re.sub(r'\n?```\s*$', '', code, flags=re.MULTILINE)
    return code.strip()
