from __future__ import annotations

from pathlib import Path

from meta_agent.utils import ensure_dir, write_text, write_json, log
from meta_agent.llm_interface import BaseLLM
from meta_agent.context_manager import MCPContext


def generate_api(prompt: str, ctx: MCPContext, out_dir: Path, llm: BaseLLM) -> None:
    """Generate a Node.js + Express + TypeScript backend with a simple items API."""
    project_dir = out_dir
    ensure_dir(project_dir / "src")
    ensure_dir(project_dir / "tests")

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
            "jest": "^29.7.0",
            "supertest": "^7.0.0",
            "ts-jest": "^29.3.4",
            "ts-node": "^10.9.2",
            "ts-node-dev": "^2.0.0",
            "typescript": "^5.6.3",
            "prisma": "^5.22.0"
        }
    }
    write_json(project_dir / "package.json", pkg)

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
    write_json(project_dir / "tsconfig.json", tsconfig)

    jest_cfg = (
        "import type { Config } from 'jest'\n\nconst config: Config = {\n  testEnvironment: 'node',\n  transform: {\n    '^.+\\.(ts)$': ['ts-jest', { tsconfig: 'tsconfig.json' }],\n  },\n  moduleFileExtensions: ['ts', 'js'],\n}\n\nexport default config\n"
    )
    write_text(project_dir / "jest.config.ts", jest_cfg)

    app_ts = (
        "import 'dotenv/config'\n"
        "import express from 'express'\n"
        "import cors from 'cors'\n"
        "import authRouter from './routes/auth'\n"
        "import itemsRouter from './routes/items'\n\n"
        "const app = express()\n"
        "app.use(cors())\n"
        "app.use(express.json())\n"
        "app.get('/api/health', (_req, res) => res.json({ status: 'ok' }))\n"
        "app.use('/api/auth', authRouter)\n"
        "app.use('/api/items', itemsRouter)\n\n"
        "export default app\n"
    )
    write_text(project_dir / "src/app.ts", app_ts)

    server_ts = (
        "import app from './app'\n\nconst port = process.env.PORT || 3000\napp.listen(port, () => {\n  console.log(`[backend] listening on :${port}`)\n})\n"
    )
    write_text(project_dir / "src/server.ts", server_ts)

    # Prisma schema
    prisma_schema = (
        "generator client {\n"
        "  provider = \"prisma-client-js\"\n"
        "}\n\n"
        "datasource db {\n"
        "  provider = \"sqlite\"\n"
        "  url      = env(\"DATABASE_URL\")\n"
        "}\n\n"
        "model User {\n"
        "  id        String   @id @default(uuid())\n"
        "  email     String   @unique\n"
        "  password  String\n"
        "  name      String?\n"
        "  createdAt DateTime @default(now())\n"
        "  updatedAt DateTime @updatedAt\n"
        "  items     Item[]\n"
        "}\n\n"
        "model Item {\n"
        "  id        String   @id @default(uuid())\n"
        "  name      String\n"
        "  completed Boolean  @default(false)\n"
        "  userId    String\n"
        "  user      User     @relation(fields: [userId], references: [id], onDelete: Cascade)\n"
        "  createdAt DateTime @default(now())\n"
        "  updatedAt DateTime @updatedAt\n"
        "}\n"
    )
    ensure_dir(project_dir / "prisma")
    write_text(project_dir / "prisma/schema.prisma", prisma_schema)

    # .env file
    env_content = (
        "# Database\n"
        "DATABASE_URL=\"file:./dev.db\"\n\n"
        "# JWT\n"
        "JWT_SECRET=your-secret-key-change-in-production\n"
        "JWT_EXPIRES_IN=7d\n\n"
        "# Server\n"
        "PORT=3000\n"
        "NODE_ENV=development\n"
    )
    write_text(project_dir / ".env", env_content)
    write_text(project_dir / ".env.example", env_content.replace("your-secret-key-change-in-production", "your-secret-key-here"))

    model_ts = (
        "export interface Item { id: string; name: string; completed: boolean; userId: string; }\n"
        "export interface User { id: string; email: string; name?: string; }\n"
    )
    write_text(project_dir / "src/models/item.ts", model_ts)

    # Database client
    db_client = (
        "import { PrismaClient } from '@prisma/client'\n\n"
        "const globalForPrisma = globalThis as unknown as { prisma: PrismaClient }\n\n"
        "export const prisma = globalForPrisma.prisma || new PrismaClient()\n\n"
        "if (process.env.NODE_ENV !== 'production') globalForPrisma.prisma = prisma\n"
    )
    ensure_dir(project_dir / "src/lib")
    write_text(project_dir / "src/lib/db.ts", db_client)

    # JWT utilities
    jwt_util = (
        "import jwt from 'jsonwebtoken'\n"
        "import { Request, Response, NextFunction } from 'express'\n\n"
        "const JWT_SECRET = process.env.JWT_SECRET || 'fallback-secret'\n"
        "const JWT_EXPIRES_IN = process.env.JWT_EXPIRES_IN || '7d'\n\n"
        "export interface JWTPayload { userId: string; email: string; }\n\n"
        "export const generateToken = (payload: JWTPayload): string => {\n"
        "  return jwt.sign(payload, JWT_SECRET, { expiresIn: JWT_EXPIRES_IN })\n"
        "}\n\n"
        "export const verifyToken = (token: string): JWTPayload => {\n"
        "  return jwt.verify(token, JWT_SECRET) as JWTPayload\n"
        "}\n\n"
        "export const authMiddleware = (req: Request, res: Response, next: NextFunction) => {\n"
        "  const authHeader = req.headers.authorization\n"
        "  if (!authHeader || !authHeader.startsWith('Bearer ')) {\n"
        "    return res.status(401).json({ error: 'No token provided' })\n"
        "  }\n"
        "  const token = authHeader.substring(7)\n"
        "  try {\n"
        "    const decoded = verifyToken(token)\n"
        "    req.user = decoded\n"
        "    next()\n"
        "  } catch (error) {\n"
        "    return res.status(401).json({ error: 'Invalid token' })\n"
        "  }\n"
        "}\n"
    )
    write_text(project_dir / "src/lib/jwt.ts", jwt_util)

    # Auth controller
    auth_controller = (
        "import { Request, Response } from 'express'\n"
        "import bcrypt from 'bcryptjs'\n"
        "import { prisma } from '../lib/db'\n"
        "import { generateToken } from '../lib/jwt'\n\n"
        "export const register = async (req: Request, res: Response) => {\n"
        "  const { email, password, name } = req.body\n"
        "  if (!email || !password) return res.status(400).json({ error: 'Email and password required' })\n"
        "  try {\n"
        "    const hashedPassword = await bcrypt.hash(password, 10)\n"
        "    const user = await prisma.user.create({ data: { email, password: hashedPassword, name } })\n"
        "    const token = generateToken({ userId: user.id, email: user.email })\n"
        "    return res.status(201).json({ user: { id: user.id, email: user.email, name: user.name }, token })\n"
        "  } catch (error: any) {\n"
        "    if (error.code === 'P2002') return res.status(400).json({ error: 'Email already exists' })\n"
        "    return res.status(500).json({ error: 'Registration failed' })\n"
        "  }\n"
        "}\n\n"
        "export const login = async (req: Request, res: Response) => {\n"
        "  const { email, password } = req.body\n"
        "  if (!email || !password) return res.status(400).json({ error: 'Email and password required' })\n"
        "  try {\n"
        "    const user = await prisma.user.findUnique({ where: { email } })\n"
        "    if (!user) return res.status(401).json({ error: 'Invalid credentials' })\n"
        "    const valid = await bcrypt.compare(password, user.password)\n"
        "    if (!valid) return res.status(401).json({ error: 'Invalid credentials' })\n"
        "    const token = generateToken({ userId: user.id, email: user.email })\n"
        "    return res.json({ user: { id: user.id, email: user.email, name: user.name }, token })\n"
        "  } catch (error) {\n"
        "    return res.status(500).json({ error: 'Login failed' })\n"
        "  }\n"
        "}\n"
    )
    write_text(project_dir / "src/controllers/authController.ts", auth_controller)

    items_controller = (
        "import { Request, Response } from 'express'\n"
        "import { prisma } from '../lib/db'\n\n"
        "export const list = async (req: Request, res: Response) => {\n"
        "  try {\n"
        "    const userId = req.user?.userId\n"
        "    if (!userId) return res.status(401).json({ error: 'Unauthorized' })\n"
        "    const items = await prisma.item.findMany({ where: { userId } })\n"
        "    return res.json(items)\n"
        "  } catch (error) {\n"
        "    return res.status(500).json({ error: 'Failed to fetch items' })\n"
        "  }\n"
        "}\n\n"
        "export const create = async (req: Request, res: Response) => {\n"
        "  const { name } = req.body\n"
        "  if (!name) return res.status(400).json({ error: 'name required' })\n"
        "  try {\n"
        "    const userId = req.user?.userId\n"
        "    if (!userId) return res.status(401).json({ error: 'Unauthorized' })\n"
        "    const item = await prisma.item.create({ data: { name, userId } })\n"
        "    return res.status(201).json(item)\n"
        "  } catch (error) {\n"
        "    return res.status(500).json({ error: 'Failed to create item' })\n"
        "  }\n"
        "}\n\n"
        "export const update = async (req: Request, res: Response) => {\n"
        "  const { id } = req.params\n"
        "  const { name, completed } = req.body\n"
        "  try {\n"
        "    const userId = req.user?.userId\n"
        "    if (!userId) return res.status(401).json({ error: 'Unauthorized' })\n"
        "    const item = await prisma.item.update({ where: { id, userId }, data: { name, completed } })\n"
        "    return res.json(item)\n"
        "  } catch (error) {\n"
        "    return res.status(404).json({ error: 'Item not found' })\n"
        "  }\n"
        "}\n\n"
        "export const remove = async (req: Request, res: Response) => {\n"
        "  const { id } = req.params\n"
        "  try {\n"
        "    const userId = req.user?.userId\n"
        "    if (!userId) return res.status(401).json({ error: 'Unauthorized' })\n"
        "    await prisma.item.delete({ where: { id, userId } })\n"
        "    return res.status(204).send()\n"
        "  } catch (error) {\n"
        "    return res.status(404).json({ error: 'Item not found' })\n"
        "  }\n"
        "}\n"
    )
    ensure_dir(project_dir / "src/controllers")
    write_text(project_dir / "src/controllers/itemsController.ts", items_controller)

    # Auth routes
    auth_routes = (
        "import { Router } from 'express'\n"
        "import * as ctrl from '../controllers/authController'\n\n"
        "const router = Router()\n"
        "router.post('/register', ctrl.register)\n"
        "router.post('/login', ctrl.login)\n\n"
        "export default router\n"
    )
    ensure_dir(project_dir / "src/routes")
    write_text(project_dir / "src/routes/auth.ts", auth_routes)

    # Item routes
    routes_ts = (
        "import { Router } from 'express'\n"
        "import * as ctrl from '../controllers/itemsController'\n"
        "import { authMiddleware } from '../lib/jwt'\n\n"
        "const router = Router()\n"
        "router.use(authMiddleware)\n"
        "router.get('/', ctrl.list)\n"
        "router.post('/', ctrl.create)\n"
        "router.put('/:id', ctrl.update)\n"
        "router.delete('/:id', ctrl.remove)\n\n"
        "export default router\n"
    )
    write_text(project_dir / "src/routes/items.ts", routes_ts)

    # Type declarations for Express
    types_declaration = (
        "declare global {\n"
        "  namespace Express {\n"
        "    interface Request {\n"
        "      user?: { userId: string; email: string; };\n"
        "    }\n"
        "  }\n"
        "}\n\n"
        "export {};\n"
    )
    write_text(project_dir / "src/types/express.d.ts", types_declaration)

    test_api = (
        "import request from 'supertest'\n"
        "import app from '../src/app'\n\n"
        "describe('API Health', () => {\n"
        "  it('health check responds', async () => {\n"
        "    const res = await request(app).get('/api/health')\n"
        "    expect(res.status).toBe(200)\n"
        "    expect(res.body.status).toBe('ok')\n"
        "  })\n"
        "})\n\n"
        "describe('Auth API', () => {\n"
        "  it('allows registration', async () => {\n"
        "    const res = await request(app).post('/api/auth/register').send({\n"
        "      email: `test${Date.now()}@example.com`,\n"
        "      password: 'password123',\n"
        "      name: 'Test User'\n"
        "    })\n"
        "    expect(res.status).toBe(201)\n"
        "    expect(res.body.token).toBeDefined()\n"
        "    expect(res.body.user.email).toBeDefined()\n"
        "  })\n"
        "})\n"
    )
    write_text(project_dir / "tests/api.test.ts", test_api)

    # Add .gitignore
    gitignore_content = (
        "node_modules/\n"
        "dist/\n"
        ".env\n"
        "*.db\n"
        "*.db-journal\n"
        ".DS_Store\n"
        "coverage/\n"
        ".vscode/\n"
        ".idea/\n"
    )
    write_text(project_dir / ".gitignore", gitignore_content)

    # Add README
    readme_content = (
        "# AutoDevOS Backend\n\n"
        "Generated Express + TypeScript + Prisma backend with JWT authentication.\n\n"
        "## Setup\n\n"
        "```bash\n"
        "npm install\n"
        "npm run db:generate\n"
        "npm run db:push\n"
        "```\n\n"
        "## Development\n\n"
        "```bash\n"
        "npm run dev\n"
        "```\n\n"
        "## API Endpoints\n\n"
        "- `POST /api/auth/register` - Register new user\n"
        "- `POST /api/auth/login` - Login user\n"
        "- `GET /api/items` - List items (requires auth)\n"
        "- `POST /api/items` - Create item (requires auth)\n"
        "- `PUT /api/items/:id` - Update item (requires auth)\n"
        "- `DELETE /api/items/:id` - Delete item (requires auth)\n\n"
        "## Testing\n\n"
        "```bash\n"
        "npm test\n"
        "```\n"
    )
    write_text(project_dir / "README.md", readme_content)

    # Use LLM to propose additional routes (not strictly necessary)
    _ = llm.generate_code(f"Suggest additional REST endpoints for an item model based on: {prompt}")

    ctx.add_artifact("backend", project_dir)
    log.info(f"Backend generated at: {project_dir}")
