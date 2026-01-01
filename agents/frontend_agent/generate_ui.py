from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from meta_agent.utils import ensure_dir, write_text, write_json, log
from meta_agent.llm_interface import BaseLLM
from meta_agent.context_manager import MCPContext


# System prompt for frontend generation
FRONTEND_SYSTEM_PROMPT = """You are an expert React TypeScript developer. 
Generate clean, production-ready code following these rules:
- Use TypeScript with proper type definitions
- Use Tailwind CSS for styling
- Follow React best practices (hooks, functional components)
- Include proper error handling
- Make components reusable and modular
- Return ONLY code, no explanations or markdown code blocks"""


def generate_ui(prompt: str, ctx: MCPContext, out_dir: Path, llm: BaseLLM) -> None:
    """Generate a modular React+TypeScript frontend using Vite and Tailwind CSS."""
    project_dir = out_dir
    
    # Create industry-standard folder structure
    _create_folder_structure(project_dir)
    
    # 1. Analyze requirements and determine what to generate
    log.info("Analyzing frontend requirements...")
    structure = _analyze_requirements(prompt, llm)
    log.info(f"Detected components: {structure.get('components', [])}")
    log.info(f"Detected pages: {structure.get('pages', [])}")
    
    # 2. Generate static config files
    log.info("Generating configuration files...")
    _generate_config_files(project_dir, structure)
    
    # 3. Generate types/interfaces
    log.info("Generating TypeScript types...")
    _generate_types(prompt, project_dir, llm, structure)
    
    # 4. Generate utility functions and hooks
    log.info("Generating hooks and utilities...")
    _generate_hooks(prompt, project_dir, llm, structure)
    _generate_utils(prompt, project_dir, llm, structure)
    
    # 5. Generate components
    log.info("Generating components...")
    _generate_components(prompt, project_dir, llm, structure)
    
    # 6. Generate pages
    log.info("Generating pages...")
    _generate_pages(prompt, project_dir, llm, structure)
    
    # 7. Generate main App with routing
    log.info("Generating App and main entry...")
    _generate_app(prompt, project_dir, llm, structure)
    _generate_main_entry(project_dir)
    
    # 8. Generate tests
    log.info("Generating tests...")
    _generate_tests(project_dir, llm, structure)

    ctx.add_artifact("frontend", project_dir)
    log.info(f"Frontend generated at: {project_dir}")


def _create_folder_structure(project_dir: Path) -> None:
    """Create industry-standard React project folder structure."""
    folders = [
        "src",
        "src/components",
        "src/components/common",
        "src/components/layout",
        "src/hooks",
        "src/pages",
        "src/types",
        "src/utils",
        "src/services",
        "src/context",
        "src/assets",
        "public",
    ]
    for folder in folders:
        ensure_dir(project_dir / folder)


def _analyze_requirements(prompt: str, llm: BaseLLM) -> Dict[str, Any]:
    """Use LLM to analyze prompt and determine what components/pages are needed."""
    analysis_prompt = f"""Analyze this application requirement and return a JSON structure.

Requirement: {prompt}

Return a JSON object with this exact structure:
{{
  "app_name": "kebab-case-name",
  "description": "Brief description",
  "components": [
    {{"name": "ComponentName", "purpose": "What it does", "props": ["prop1", "prop2"]}}
  ],
  "pages": [
    {{"name": "PageName", "route": "/path", "purpose": "What it shows"}}
  ],
  "hooks": [
    {{"name": "useHookName", "purpose": "What it does"}}
  ],
  "types": [
    {{"name": "TypeName", "fields": {{"field1": "string", "field2": "number"}}}}
  ],
  "features": ["feature1", "feature2"],
  "api_endpoints": ["/api/endpoint1"],
  "has_auth": false,
  "has_routing": true
}}

Be thorough - identify ALL components, pages, and hooks needed for this application.
Return ONLY valid JSON, no explanations."""

    response = llm.generate_code(
        analysis_prompt, 
        system=FRONTEND_SYSTEM_PROMPT,
        temperature=0.3, 
        max_tokens=2048
    )
    
    # Parse JSON from response
    try:
        # Try to extract JSON from response
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            parsed = json.loads(json_match.group())
            # Validate required fields
            if "components" in parsed and "pages" in parsed:
                return parsed
    except json.JSONDecodeError as e:
        log.warning(f"Failed to parse LLM response as JSON: {e}")
    
    # Fallback with sensible defaults based on prompt keywords
    return _generate_fallback_structure(prompt)


def _generate_fallback_structure(prompt: str) -> Dict[str, Any]:
    """Generate fallback structure when LLM analysis fails."""
    prompt_lower = prompt.lower()
    
    components = [
        {"name": "Header", "purpose": "Navigation header", "props": []},
        {"name": "Footer", "purpose": "Page footer", "props": []},
    ]
    pages = [
        {"name": "HomePage", "route": "/", "purpose": "Main landing page"},
    ]
    hooks = []
    types = []
    
    # Detect common patterns
    if any(word in prompt_lower for word in ["list", "items", "products", "posts"]):
        components.append({"name": "ItemList", "purpose": "Display list of items", "props": ["items"]})
        components.append({"name": "ItemCard", "purpose": "Single item display", "props": ["item"]})
        types.append({"name": "Item", "fields": {"id": "string", "title": "string", "description": "string"}})
        hooks.append({"name": "useItems", "purpose": "Fetch and manage items"})
    
    if any(word in prompt_lower for word in ["form", "create", "add", "submit"]):
        components.append({"name": "ItemForm", "purpose": "Form for creating/editing", "props": ["onSubmit", "initialData"]})
        components.append({"name": "FormInput", "purpose": "Reusable input field", "props": ["label", "value", "onChange"]})
    
    if any(word in prompt_lower for word in ["search", "filter"]):
        components.append({"name": "SearchBar", "purpose": "Search input", "props": ["onSearch"]})
        hooks.append({"name": "useSearch", "purpose": "Handle search logic"})
    
    if any(word in prompt_lower for word in ["detail", "view", "single"]):
        pages.append({"name": "DetailPage", "route": "/detail/:id", "purpose": "Show item details"})
    
    if any(word in prompt_lower for word in ["dashboard", "admin"]):
        pages.append({"name": "DashboardPage", "route": "/dashboard", "purpose": "Dashboard view"})
        components.append({"name": "StatsCard", "purpose": "Display statistics", "props": ["title", "value"]})
    
    if any(word in prompt_lower for word in ["auth", "login", "signup"]):
        pages.append({"name": "LoginPage", "route": "/login", "purpose": "User login"})
        components.append({"name": "LoginForm", "purpose": "Login form", "props": ["onLogin"]})
        hooks.append({"name": "useAuth", "purpose": "Authentication state"})
    
    return {
        "app_name": "autodevos-app",
        "description": prompt[:100],
        "components": components,
        "pages": pages,
        "hooks": hooks,
        "types": types,
        "features": [],
        "api_endpoints": ["/api/items"],
        "has_auth": "auth" in prompt_lower or "login" in prompt_lower,
        "has_routing": len(pages) > 1
    }


def _generate_config_files(project_dir: Path, structure: Dict[str, Any]) -> None:
    """Generate static config files."""
    app_name = structure.get("app_name", "autodevos-frontend")
    has_routing = structure.get("has_routing", True)
    
    # package.json
    dependencies = {
        "react": "^18.3.1",
        "react-dom": "^18.3.1",
        "react-icons": "^5.5.0",
    }
    
    if has_routing:
        dependencies["react-router-dom"] = "^6.22.0"
    
    pkg = {
        "name": app_name,
        "private": True,
        "version": "0.1.0",
        "type": "module",
        "scripts": {
            "dev": "vite",
            "build": "tsc -b && vite build",
            "preview": "vite preview",
            "lint": "eslint src --ext ts,tsx",
            "test": "jest --passWithNoTests"
        },
        "dependencies": dependencies,
        "devDependencies": {
            "@types/react": "^18.3.5",
            "@types/react-dom": "^18.3.0",
            "@vitejs/plugin-react": "^4.3.3",
            "autoprefixer": "^10.4.20",
            "postcss": "^8.4.47",
            "tailwindcss": "^3.4.14",
            "typescript": "^5.6.3",
            "vite": "^5.4.8",
            "jest": "^29.7.0",
            "ts-jest": "^29.3.4",
            "@types/jest": "^29.5.14",
            "@testing-library/react": "^16.0.1",
            "@testing-library/jest-dom": "^6.6.3",
            "jest-environment-jsdom": "^29.7.0"
        }
    }
    write_json(project_dir / "package.json", pkg)

    # tsconfig.json
    tsconfig = {
        "compilerOptions": {
            "target": "ES2020",
            "useDefineForClassFields": True,
            "lib": ["ES2020", "DOM", "DOM.Iterable"],
            "module": "ESNext",
            "skipLibCheck": True,
            "jsx": "react-jsx",
            "moduleResolution": "Bundler",
            "resolveJsonModule": True,
            "isolatedModules": True,
            "noEmit": True,
            "esModuleInterop": True,
            "allowJs": False,
            "strict": True,
            "forceConsistentCasingInFileNames": True,
            "types": ["jest", "@testing-library/jest-dom"],
            "baseUrl": ".",
            "paths": {
                "@/*": ["src/*"],
                "@components/*": ["src/components/*"],
                "@pages/*": ["src/pages/*"],
                "@hooks/*": ["src/hooks/*"],
                "@types/*": ["src/types/*"],
                "@utils/*": ["src/utils/*"],
                "@services/*": ["src/services/*"]
            }
        },
        "include": ["src", "vite.config.ts", "jest.config.ts", "setupTests.ts"]
    }
    write_json(project_dir / "tsconfig.json", tsconfig)

    # vite.config.ts with path aliases
    vite_cfg = '''import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@components': path.resolve(__dirname, './src/components'),
      '@pages': path.resolve(__dirname, './src/pages'),
      '@hooks': path.resolve(__dirname, './src/hooks'),
      '@types': path.resolve(__dirname, './src/types'),
      '@utils': path.resolve(__dirname, './src/utils'),
      '@services': path.resolve(__dirname, './src/services'),
    },
  },
})
'''
    write_text(project_dir / "vite.config.ts", vite_cfg)

    # index.html
    index_html = f'''<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="description" content="{structure.get('description', 'AutoDevOS Frontend')}" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <title>{app_name.replace('-', ' ').title()}</title>
  </head>
  <body class="min-h-screen bg-gray-50 text-slate-900 antialiased">
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
'''
    write_text(project_dir / "index.html", index_html)

    # postcss.config.js
    postcss = '''export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
'''
    write_text(project_dir / "postcss.config.js", postcss)

    # tailwind.config.js
    tailwind = '''/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#eff6ff',
          100: '#dbeafe',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
        },
      },
    },
  },
  plugins: [],
}
'''
    write_text(project_dir / "tailwind.config.js", tailwind)

    # src/index.css
    css = '''@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  html {
    @apply scroll-smooth;
  }
  body {
    @apply font-sans;
  }
}

@layer components {
  .btn {
    @apply px-4 py-2 rounded-lg font-medium transition-colors duration-200;
  }
  .btn-primary {
    @apply bg-primary-600 text-white hover:bg-primary-700;
  }
  .btn-secondary {
    @apply bg-gray-200 text-gray-800 hover:bg-gray-300;
  }
  .input {
    @apply w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent;
  }
  .card {
    @apply bg-white rounded-xl shadow-md p-6;
  }
}
'''
    write_text(project_dir / "src/index.css", css)

    # Jest config
    jest_cfg = '''import type { Config } from 'jest'

const config: Config = {
  testEnvironment: 'jsdom',
  transform: {
    '^.+\\.(ts|tsx)$': ['ts-jest', { tsconfig: 'tsconfig.json' }],
  },
  moduleFileExtensions: ['ts', 'tsx', 'js'],
  setupFilesAfterEnv: ['<rootDir>/setupTests.ts'],
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1',
    '^@components/(.*)$': '<rootDir>/src/components/$1',
    '^@pages/(.*)$': '<rootDir>/src/pages/$1',
    '^@hooks/(.*)$': '<rootDir>/src/hooks/$1',
    '^@types/(.*)$': '<rootDir>/src/types/$1',
    '^@utils/(.*)$': '<rootDir>/src/utils/$1',
  },
}

export default config
'''
    write_text(project_dir / "jest.config.ts", jest_cfg)

    # Setup tests
    setup_tests = "import '@testing-library/jest-dom'\n"
    write_text(project_dir / "setupTests.ts", setup_tests)

    # .gitignore
    gitignore = '''# Dependencies
node_modules
.pnp
.pnp.js

# Build
dist
build

# IDE
.idea
.vscode
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Environment
.env
.env.local
.env.*.local

# Logs
*.log
npm-debug.log*

# Testing
coverage
'''
    write_text(project_dir / ".gitignore", gitignore)


def _generate_types(prompt: str, project_dir: Path, llm: BaseLLM, structure: Dict[str, Any]) -> None:
    """Generate TypeScript type definitions."""
    types_dir = project_dir / "src/types"
    
    # Generate index.ts that exports all types
    types_list = structure.get("types", [])
    
    if not types_list:
        # Generate types based on prompt
        types_prompt = f"""Generate TypeScript type definitions for this application:

Application: {prompt}
Features: {structure.get('features', [])}
API endpoints: {structure.get('api_endpoints', [])}

Create interfaces and types for:
1. Data models (items, users, etc.)
2. API response types
3. Component prop types
4. Form data types

Use proper TypeScript conventions. Export all types.
Return ONLY TypeScript code."""

        types_code = llm.generate_code(
            types_prompt,
            system=FRONTEND_SYSTEM_PROMPT,
            temperature=0.3,
            max_tokens=2048
        )
        
        # Clean up response
        types_code = _clean_code_response(types_code, "typescript")
        write_text(types_dir / "index.ts", types_code)
    else:
        # Generate from structure
        type_definitions = []
        for type_def in types_list:
            name = type_def.get("name", "Unknown")
            fields = type_def.get("fields", {})
            
            field_strs = [f"  {k}: {v};" for k, v in fields.items()]
            type_definitions.append(f"export interface {name} {{\n" + "\n".join(field_strs) + "\n}")
        
        # Add common types
        common_types = '''
// Common utility types
export type ID = string | number;

export interface ApiResponse<T> {
  data: T;
  success: boolean;
  message?: string;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  pageSize: number;
}

export interface FormState {
  isSubmitting: boolean;
  errors: Record<string, string>;
}
'''
        
        full_types = "\n\n".join(type_definitions) + common_types
        write_text(types_dir / "index.ts", full_types)


def _generate_hooks(prompt: str, project_dir: Path, llm: BaseLLM, structure: Dict[str, Any]) -> None:
    """Generate custom React hooks."""
    hooks_dir = project_dir / "src/hooks"
    hooks_list = structure.get("hooks", [])
    
    generated_hooks = []
    
    for hook in hooks_list:
        hook_name = hook.get("name", "useCustomHook")
        hook_purpose = hook.get("purpose", "Custom hook")
        
        hook_prompt = f"""Generate a React custom hook named {hook_name}.

Purpose: {hook_purpose}
Application context: {prompt}
Available types: {[t.get('name') for t in structure.get('types', [])]}
API endpoints: {structure.get('api_endpoints', [])}

Requirements:
- Use TypeScript with proper types
- Handle loading, error, and success states
- Follow React hooks best practices
- Include cleanup in useEffect if needed
- Return an object with state and handlers

Return ONLY the hook code with imports."""

        hook_code = llm.generate_code(
            hook_prompt,
            system=FRONTEND_SYSTEM_PROMPT,
            temperature=0.3,
            max_tokens=1500
        )
        
        hook_code = _clean_code_response(hook_code, "typescript")
        write_text(hooks_dir / f"{hook_name}.ts", hook_code)
        generated_hooks.append(hook_name)
    
    # Generate index.ts for hooks
    if generated_hooks:
        index_content = "\n".join([f"export {{ default as {h} }} from './{h}';" for h in generated_hooks])
        # Also export with named exports
        index_content += "\n\n// Alternative named exports\n"
        index_content += "\n".join([f"export {{ {h} }} from './{h}';" for h in generated_hooks])
        write_text(hooks_dir / "index.ts", index_content)
    else:
        # Create a placeholder
        write_text(hooks_dir / "index.ts", "// Custom hooks will be exported here\nexport {}\n")


def _generate_utils(prompt: str, project_dir: Path, llm: BaseLLM, structure: Dict[str, Any]) -> None:
    """Generate utility functions."""
    utils_dir = project_dir / "src/utils"
    
    utils_prompt = f"""Generate utility functions for this React application:

Application: {prompt}
Features: {structure.get('features', [])}

Create utilities for:
1. API helper functions (fetch wrapper)
2. Form validation helpers
3. Date/string formatting
4. Local storage helpers
5. Any app-specific helpers

Use TypeScript. Export all functions.
Return ONLY the code."""

    utils_code = llm.generate_code(
        utils_prompt,
        system=FRONTEND_SYSTEM_PROMPT,
        temperature=0.3,
        max_tokens=2048
    )
    
    utils_code = _clean_code_response(utils_code, "typescript")
    write_text(utils_dir / "index.ts", utils_code)
    
    # Generate API service
    api_service = '''import { ApiResponse } from '@/types';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

interface RequestOptions extends RequestInit {
  params?: Record<string, string>;
}

class ApiService {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: RequestOptions = {}
  ): Promise<ApiResponse<T>> {
    const { params, ...fetchOptions } = options;
    
    let url = `${this.baseUrl}${endpoint}`;
    if (params) {
      const searchParams = new URLSearchParams(params);
      url += `?${searchParams.toString()}`;
    }

    try {
      const response = await fetch(url, {
        ...fetchOptions,
        headers: {
          'Content-Type': 'application/json',
          ...fetchOptions.headers,
        },
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.message || 'Request failed');
      }

      return { data, success: true };
    } catch (error) {
      return {
        data: null as T,
        success: false,
        message: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }

  async get<T>(endpoint: string, params?: Record<string, string>) {
    return this.request<T>(endpoint, { method: 'GET', params });
  }

  async post<T>(endpoint: string, body: unknown) {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: JSON.stringify(body),
    });
  }

  async put<T>(endpoint: string, body: unknown) {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: JSON.stringify(body),
    });
  }

  async delete<T>(endpoint: string) {
    return this.request<T>(endpoint, { method: 'DELETE' });
  }
}

export const api = new ApiService();
export default ApiService;
'''
    write_text(project_dir / "src/services/api.ts", api_service)


def _generate_components(prompt: str, project_dir: Path, llm: BaseLLM, structure: Dict[str, Any]) -> None:
    """Generate React components using separate LLM calls for each."""
    components_dir = project_dir / "src/components"
    common_dir = components_dir / "common"
    layout_dir = components_dir / "layout"
    
    components_list = structure.get("components", [])
    generated_components = []
    
    # Categorize components
    layout_components = ["Header", "Footer", "Sidebar", "Layout", "Navbar", "Navigation"]
    common_components = ["Button", "Input", "Card", "Modal", "Loader", "FormInput", "SearchBar"]
    
    for component in components_list:
        comp_name = component.get("name", "Component")
        comp_purpose = component.get("purpose", "")
        comp_props = component.get("props", [])
        
        # Determine which folder
        if comp_name in layout_components:
            target_dir = layout_dir
        elif comp_name in common_components:
            target_dir = common_dir
        else:
            target_dir = components_dir
        
        component_prompt = f"""Generate a React TypeScript component named {comp_name}.

Purpose: {comp_purpose}
Props: {comp_props}
Application context: {prompt}

Requirements:
- Use TypeScript with a Props interface
- Use Tailwind CSS for styling
- Make it functional and reusable
- Include proper accessibility attributes
- Handle edge cases (loading, empty, error states if applicable)
- Use React.FC or function component syntax

Structure:
1. Imports
2. Props interface
3. Component function
4. Default export

Return ONLY the component code."""

        component_code = llm.generate_code(
            component_prompt,
            system=FRONTEND_SYSTEM_PROMPT,
            temperature=0.4,
            max_tokens=2048
        )
        
        component_code = _clean_code_response(component_code, "tsx")
        
        # Ensure proper export
        if "export default" not in component_code and "export {" not in component_code:
            component_code += f"\n\nexport default {comp_name};\n"
        
        write_text(target_dir / f"{comp_name}.tsx", component_code)
        generated_components.append({"name": comp_name, "dir": target_dir.name})
        log.debug(f"Generated component: {comp_name}")
    
    # Generate index files for each component directory
    _generate_component_index(components_dir, generated_components)
    _generate_component_index(common_dir, [c for c in generated_components if c["dir"] == "common"])
    _generate_component_index(layout_dir, [c for c in generated_components if c["dir"] == "layout"])


def _generate_component_index(dir_path: Path, components: List[Dict]) -> None:
    """Generate index.ts for a components directory."""
    if not components:
        write_text(dir_path / "index.ts", "// Components will be exported here\nexport {}\n")
        return
    
    exports = []
    for comp in components:
        name = comp["name"]
        exports.append(f"export {{ default as {name} }} from './{name}';")
    
    write_text(dir_path / "index.ts", "\n".join(exports) + "\n")


def _generate_pages(prompt: str, project_dir: Path, llm: BaseLLM, structure: Dict[str, Any]) -> None:
    """Generate page components."""
    pages_dir = project_dir / "src/pages"
    pages_list = structure.get("pages", [])
    generated_pages = []
    
    # Get component names for imports
    component_names = [c.get("name") for c in structure.get("components", [])]
    hook_names = [h.get("name") for h in structure.get("hooks", [])]
    
    for page in pages_list:
        page_name = page.get("name", "Page")
        page_route = page.get("route", "/")
        page_purpose = page.get("purpose", "")
        
        page_prompt = f"""Generate a React TypeScript page component named {page_name}.

Route: {page_route}
Purpose: {page_purpose}
Application context: {prompt}

Available components to import from '@components': {component_names}
Available hooks to import from '@hooks': {hook_names}

Requirements:
- Use TypeScript
- Import and use relevant components from the list above
- Use Tailwind CSS for layout and styling
- Handle loading, error, and empty states
- Include proper page structure (header area, main content, etc.)
- Use hooks for data fetching if needed

Return ONLY the page component code."""

        page_code = llm.generate_code(
            page_prompt,
            system=FRONTEND_SYSTEM_PROMPT,
            temperature=0.4,
            max_tokens=3000
        )
        
        page_code = _clean_code_response(page_code, "tsx")
        
        if "export default" not in page_code:
            page_code += f"\n\nexport default {page_name};\n"
        
        write_text(pages_dir / f"{page_name}.tsx", page_code)
        generated_pages.append(page_name)
        log.debug(f"Generated page: {page_name}")
    
    # Generate pages index
    exports = [f"export {{ default as {p} }} from './{p}';" for p in generated_pages]
    write_text(pages_dir / "index.ts", "\n".join(exports) + "\n" if exports else "export {}\n")


def _generate_app(prompt: str, project_dir: Path, llm: BaseLLM, structure: Dict[str, Any]) -> None:
    """Generate the main App component with routing."""
    pages = structure.get("pages", [])
    components = structure.get("components", [])
    has_routing = structure.get("has_routing", len(pages) > 1)
    
    # Get layout components
    layout_names = [c.get("name") for c in components if c.get("name") in ["Header", "Footer", "Navbar", "Sidebar", "Layout"]]
    page_names = [p.get("name") for p in pages]
    routes = [(p.get("name"), p.get("route", "/")) for p in pages]
    
    app_prompt = f"""Generate the main App.tsx for a React application.

Application: {prompt}
Has routing: {has_routing}
Pages and routes: {routes}
Layout components available: {layout_names}

Requirements:
- Import pages from '@pages'
- Import layout components from '@components/layout' if available
- {"Use React Router for routing with BrowserRouter, Routes, and Route" if has_routing else "Render the main page directly"}
- Include a layout wrapper with Header/Footer if available
- Use Tailwind CSS
- TypeScript with proper types

Return ONLY the App.tsx code."""

    app_code = llm.generate_code(
        app_prompt,
        system=FRONTEND_SYSTEM_PROMPT,
        temperature=0.3,
        max_tokens=2048
    )
    
    app_code = _clean_code_response(app_code, "tsx")
    
    if "export default" not in app_code:
        app_code += "\n\nexport default App;\n"
    
    write_text(project_dir / "src/App.tsx", app_code)


def _generate_main_entry(project_dir: Path) -> None:
    """Generate main.tsx entry point."""
    main_tsx = '''import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
'''
    write_text(project_dir / "src/main.tsx", main_tsx)


def _generate_tests(project_dir: Path, llm: BaseLLM, structure: Dict[str, Any]) -> None:
    """Generate test files for components."""
    components = structure.get("components", [])[:3]  # Limit to avoid too many LLM calls
    
    for component in components:
        comp_name = component.get("name", "Component")
        
        test_prompt = f"""Generate Jest + React Testing Library tests for a React component named {comp_name}.

Purpose: {component.get('purpose', '')}
Props: {component.get('props', [])}

Include:
1. Render test (component renders without crashing)
2. Snapshot test or content test
3. User interaction test if applicable
4. Props test

Use TypeScript. Import from '@testing-library/react'.
Return ONLY the test code."""

        test_code = llm.generate_code(
            test_prompt,
            system=FRONTEND_SYSTEM_PROMPT,
            temperature=0.3,
            max_tokens=1500
        )
        
        test_code = _clean_code_response(test_code, "tsx")
        write_text(project_dir / f"src/components/{comp_name}.test.tsx", test_code)
    
    # Generate App test
    app_test = '''import { render, screen } from '@testing-library/react'
import React from 'react'
import App from './App'

describe('App', () => {
  it('renders without crashing', () => {
    render(<App />)
  })

  it('displays main content', () => {
    render(<App />)
    // App should render some content
    expect(document.body).toBeInTheDocument()
  })
})
'''
    write_text(project_dir / "src/App.test.tsx", app_test)


def _clean_code_response(code: str, lang: str = "typescript") -> str:
    """Clean up LLM code response by removing markdown code blocks."""
    # Remove markdown code blocks
    code = re.sub(r'^```(?:typescript|tsx|ts|javascript|jsx|js)?\s*\n?', '', code, flags=re.MULTILINE)
    code = re.sub(r'\n?```\s*$', '', code, flags=re.MULTILINE)
    code = code.strip()
    
    # Ensure imports are at the top
    lines = code.split('\n')
    imports = []
    other = []
    
    for line in lines:
        if line.strip().startswith('import ') or line.strip().startswith('import{'):
            imports.append(line)
        else:
            other.append(line)
    
    if imports:
        return '\n'.join(imports) + '\n\n' + '\n'.join(other).strip()
    
    return code
