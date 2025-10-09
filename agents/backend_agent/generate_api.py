from __future__ import annotations

from pathlib import Path

from meta_agent.utils import ensure_dir, write_text, write_json, log
from meta_agent.llm_interface import BaseLLM
from meta_agent.context_manager import MCPContext


def generate_api(prompt: str, ctx: MCPContext, out_dir: Path, llm: BaseLLM) -> None:
    """Generate a Node.js + Express + TypeScript backend with a simple items API."""
    project_dir = out_dir / "app"
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
            "test": "jest --runInBand"
        },
        "dependencies": {
            "express": "^4.21.1",
            "cors": "^2.8.5"
        },
        "devDependencies": {
            "@types/express": "^4.17.21",
            "@types/jest": "^29.5.14",
            "@types/node": "^22.7.5",
            "@types/supertest": "^6.0.3",
            "jest": "^29.7.0",
            "supertest": "^7.0.0",
            "ts-jest": "^29.3.4",
            "ts-node": "^10.9.2",
            "ts-node-dev": "^2.0.0",
            "typescript": "^5.6.3"
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
        "import express from 'express'\n"
        "import cors from 'cors'\n"
        "import itemsRouter from './routes/items'\n\n"
        "const app = express()\n"
        "app.use(cors())\n"
        "app.use(express.json())\n"
        "app.get('/api/health', (_req, res) => res.json({ status: 'ok' }))\n"
        "app.use('/api/items', itemsRouter)\n\n"
        "export default app\n"
    )
    write_text(project_dir / "src/app.ts", app_ts)

    server_ts = (
        "import app from './app'\n\nconst port = process.env.PORT || 3000\napp.listen(port, () => {\n  console.log(`[backend] listening on :${port}`)\n})\n"
    )
    write_text(project_dir / "src/server.ts", server_ts)

    model_ts = (
        "export interface Item { id: string; name: string; }\n"
    )
    write_text(project_dir / "src/models/item.ts", model_ts)

    repo_ts = (
        "import { Item } from '../models/item'\n"
        "const store: Item[] = []\n"
        "export const list = () => store\n"
        "export const add = (name: string): Item => {\n  const item: Item = { id: String(Date.now()), name }\n  store.push(item)\n  return item\n}\n"
    )
    ensure_dir(project_dir / "src/repository")
    write_text(project_dir / "src/repository/inMemoryStore.ts", repo_ts)

    items_controller = (
        "import { Request, Response } from 'express'\n"
        "import * as repo from '../repository/inMemoryStore'\n\n"
        "export const list = (_req: Request, res: Response) => {\n  return res.json(repo.list())\n}\n\nexport const create = (req: Request, res: Response) => {\n  const { name } = req.body\n  if (!name) return res.status(400).json({ error: 'name required' })\n  const item = repo.add(name)\n  return res.status(201).json(item)\n}\n"
    )
    ensure_dir(project_dir / "src/controllers")
    write_text(project_dir / "src/controllers/itemsController.ts", items_controller)

    routes_ts = (
        "import { Router } from 'express'\n"
        "import * as ctrl from '../controllers/itemsController'\n\n"
        "const router = Router()\n"
        "router.get('/', ctrl.list)\n"
        "router.post('/', ctrl.create)\n\n"
        "export default router\n"
    )
    ensure_dir(project_dir / "src/routes")
    write_text(project_dir / "src/routes/items.ts", routes_ts)

    test_api = (
        "import request from 'supertest'\n"
        "import app from '../src/app'\n\n"
        "describe('items api', () => {\n  it('lists empty initially', async () => {\n    const res = await request(app).get('/api/items')\n    expect(res.status).toBe(200)\n    expect(res.body).toEqual([])\n  })\n\n  it('creates an item', async () => {\n    const res = await request(app).post('/api/items').send({ name: 'Sample' })\n    expect(res.status).toBe(201)\n    expect(res.body.name).toBe('Sample')\n  })\n})\n"
    )
    write_text(project_dir / "tests/items.test.ts", test_api)

    # Use LLM to propose additional routes (not strictly necessary)
    _ = llm.generate_code(f"Suggest additional REST endpoints for an item model based on: {prompt}")

    ctx.add_artifact("backend", project_dir)
    log.info(f"Backend generated at: {project_dir}")
