from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List

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
- Return ONLY code, no explanations or markdown code blocks
- Do NOT wrap code in markdown code fences"""

# Higher token limits for larger generations
DEFAULT_MAX_TOKENS = 16384
COMPONENT_MAX_TOKENS = 8192
ANALYSIS_MAX_TOKENS = 4096


def generate_ui(prompt: str, ctx: MCPContext, out_dir: Path, llm: BaseLLM) -> None:
    """Generate a modular React+TypeScript frontend using Vite and Tailwind CSS.
    
    The structure is fully dynamic - only files needed for the application are created.
    No hardcoded/compulsory files beyond the essential Vite config.
    """
    project_dir = out_dir
    
    # 1. Analyze requirements FIRST to determine what to generate
    log.info("Analyzing frontend requirements...")
    structure = _analyze_requirements(prompt, llm)
    log.info(f"App: {structure.get('app_name')}")
    log.info(f"Components to generate: {[c.get('name') for c in structure.get('components', [])]}")
    log.info(f"Pages to generate: {[p.get('name') for p in structure.get('pages', [])]}")
    log.info(f"Hooks to generate: {[h.get('name') for h in structure.get('hooks', [])]}")
    
    # 2. Create ONLY the folders that will be used
    _create_dynamic_folder_structure(project_dir, structure)
    
    # 3. Generate essential Vite config files (these are always needed)
    log.info("Generating Vite configuration...")
    _generate_vite_config(project_dir, structure)
    
    # 4. Generate types ONLY if there are types defined
    if structure.get("types"):
        log.info("Generating TypeScript types...")
        _generate_types(prompt, project_dir, llm, structure)
    
    # 5. Generate hooks ONLY if there are hooks defined
    if structure.get("hooks"):
        log.info("Generating custom hooks...")
        _generate_hooks(prompt, project_dir, llm, structure)
    
    # 6. Generate services ONLY if API endpoints exist
    if structure.get("api_endpoints"):
        log.info("Generating API services...")
        _generate_services(prompt, project_dir, llm, structure)
    
    # 7. Generate components
    if structure.get("components"):
        log.info("Generating components...")
        _generate_components(prompt, project_dir, llm, structure)
    
    # 8. Generate pages
    if structure.get("pages"):
        log.info("Generating pages...")
        _generate_pages(prompt, project_dir, llm, structure)
    
    # 9. Generate App and main entry (always needed)
    log.info("Generating App entry point...")
    _generate_app(prompt, project_dir, llm, structure)
    _generate_main_entry(project_dir, structure)

    ctx.add_artifact("frontend", project_dir)
    log.info(f"Frontend generated at: {project_dir}")


def _create_dynamic_folder_structure(project_dir: Path, structure: Dict[str, Any]) -> None:
    """Create ONLY the folders that will actually contain files."""
    # Always needed for Vite
    ensure_dir(project_dir / "src")
    ensure_dir(project_dir / "public")
    
    # Conditional folders based on what's being generated
    if structure.get("components"):
        ensure_dir(project_dir / "src/components")
        
        # Check if we need layout/ui subdirs
        component_names = [c.get("name", "") for c in structure.get("components", [])]
        layout_keywords = ["Header", "Footer", "Sidebar", "Layout", "Navbar", "Navigation"]
        ui_keywords = ["Button", "Input", "Card", "Modal", "Loader", "Spinner"]
        
        if any(name in layout_keywords for name in component_names):
            ensure_dir(project_dir / "src/components/layout")
        if any(name in ui_keywords for name in component_names):
            ensure_dir(project_dir / "src/components/ui")
    
    if structure.get("pages"):
        ensure_dir(project_dir / "src/pages")
    
    if structure.get("hooks"):
        ensure_dir(project_dir / "src/hooks")
    
    if structure.get("types"):
        ensure_dir(project_dir / "src/types")
    
    if structure.get("api_endpoints"):
        ensure_dir(project_dir / "src/services")
    
    if structure.get("has_auth"):
        ensure_dir(project_dir / "src/context")


def _analyze_requirements(prompt: str, llm: BaseLLM) -> Dict[str, Any]:
    """Use LLM to analyze prompt and determine exactly what files to generate."""
    analysis_prompt = f"""Analyze this application requirement and return a JSON structure describing EXACTLY what needs to be built.

Requirement: {prompt}

Return a JSON object. Be SPECIFIC - only include what's actually needed for this app:

{{
  "app_name": "kebab-case-name-based-on-app",
  "description": "One line description",
  "components": [
    {{"name": "ExactComponentName", "purpose": "What it does", "props": ["propName"], "category": "layout|ui|feature"}}
  ],
  "pages": [
    {{"name": "PageName", "route": "/exact-path", "purpose": "What this page shows"}}
  ],
  "hooks": [
    {{"name": "useExactHookName", "purpose": "What state/logic it manages"}}
  ],
  "types": [
    {{"name": "TypeName", "purpose": "What data it represents", "fields": {{"fieldName": "type"}}}}
  ],
  "api_endpoints": ["/api/exact-endpoint"],
  "has_auth": true/false,
  "has_routing": true/false,
  "state_management": "local|context|none"
}}

IMPORTANT:
- Only include components/pages/hooks that are ACTUALLY needed
- Use descriptive, specific names (not generic like "ItemList" unless it's really a list of items)
- If the app is simple, keep the structure simple
- Don't add unnecessary complexity

Return ONLY valid JSON."""

    response = llm.generate_code(
        analysis_prompt, 
        system="You are an expert software architect. Analyze requirements precisely.",
        temperature=0.2, 
        max_tokens=ANALYSIS_MAX_TOKENS
    )
    
    # Parse JSON from response
    try:
        # Extract JSON from response (handle markdown code blocks)
        cleaned = re.sub(r'^```(?:json)?\s*\n?', '', response, flags=re.MULTILINE)
        cleaned = re.sub(r'\n?```\s*$', '', cleaned, flags=re.MULTILINE)
        
        json_match = re.search(r'\{[\s\S]*\}', cleaned)
        if json_match:
            parsed = json.loads(json_match.group())
            # Validate we got something useful
            if parsed.get("components") or parsed.get("pages"):
                log.debug(f"Successfully parsed LLM analysis: {len(parsed.get('components', []))} components, {len(parsed.get('pages', []))} pages")
                return parsed
    except json.JSONDecodeError as e:
        log.warning(f"Failed to parse LLM response as JSON: {e}")
    
    # Fallback: generate minimal structure based on keywords
    log.info("Using fallback structure analysis")
    return _generate_fallback_structure(prompt)


def _generate_fallback_structure(prompt: str) -> Dict[str, Any]:
    """Generate minimal structure when LLM analysis fails."""
    prompt_lower = prompt.lower()
    words = prompt_lower.split()
    
    # Extract app name from prompt
    app_name = "-".join(words[:3]) if len(words) >= 3 else "my-app"
    app_name = re.sub(r'[^a-z0-9-]', '', app_name)
    
    components: List[Dict[str, Any]] = []
    pages: List[Dict[str, Any]] = [{"name": "HomePage", "route": "/", "purpose": "Main page", "category": "page"}]
    hooks: List[Dict[str, Any]] = []
    types: List[Dict[str, Any]] = []
    api_endpoints: List[str] = []
    
    # Detect what's actually needed from keywords
    if any(word in prompt_lower for word in ["todo", "task", "list"]):
        components.extend([
            {"name": "TodoList", "purpose": "Display todos", "props": ["todos", "onToggle", "onDelete"], "category": "feature"},
            {"name": "TodoItem", "purpose": "Single todo", "props": ["todo", "onToggle", "onDelete"], "category": "feature"},
            {"name": "AddTodoForm", "purpose": "Add new todo", "props": ["onAdd"], "category": "feature"},
        ])
        types.append({"name": "Todo", "purpose": "Todo item", "fields": {"id": "string", "text": "string", "completed": "boolean"}})
        hooks.append({"name": "useTodos", "purpose": "Manage todo state"})
    
    if any(word in prompt_lower for word in ["blog", "post", "article"]):
        components.extend([
            {"name": "PostList", "purpose": "List of posts", "props": ["posts"], "category": "feature"},
            {"name": "PostCard", "purpose": "Post preview", "props": ["post"], "category": "feature"},
        ])
        pages.append({"name": "PostPage", "route": "/post/:id", "purpose": "Single post view"})
        types.append({"name": "Post", "purpose": "Blog post", "fields": {"id": "string", "title": "string", "content": "string", "createdAt": "string"}})
        api_endpoints.append("/api/posts")
    
    if any(word in prompt_lower for word in ["shop", "store", "product", "cart", "ecommerce"]):
        components.extend([
            {"name": "ProductGrid", "purpose": "Product listing", "props": ["products"], "category": "feature"},
            {"name": "ProductCard", "purpose": "Product display", "props": ["product", "onAddToCart"], "category": "feature"},
            {"name": "Cart", "purpose": "Shopping cart", "props": ["items", "onRemove"], "category": "feature"},
        ])
        pages.append({"name": "ProductPage", "route": "/product/:id", "purpose": "Product details"})
        types.append({"name": "Product", "purpose": "Product item", "fields": {"id": "string", "name": "string", "price": "number", "image": "string"}})
        hooks.append({"name": "useCart", "purpose": "Cart state management"})
        api_endpoints.append("/api/products")
    
    if any(word in prompt_lower for word in ["dashboard", "admin", "analytics"]):
        components.extend([
            {"name": "StatCard", "purpose": "Statistics display", "props": ["title", "value", "change"], "category": "feature"},
            {"name": "Chart", "purpose": "Data visualization", "props": ["data", "type"], "category": "feature"},
        ])
        pages.append({"name": "DashboardPage", "route": "/dashboard", "purpose": "Dashboard view"})
    
    if any(word in prompt_lower for word in ["auth", "login", "signup", "register"]):
        components.extend([
            {"name": "LoginForm", "purpose": "User login", "props": ["onSubmit"], "category": "feature"},
        ])
        pages.append({"name": "LoginPage", "route": "/login", "purpose": "Login page"})
        hooks.append({"name": "useAuth", "purpose": "Authentication state"})
    
    if any(word in prompt_lower for word in ["chat", "message", "conversation"]):
        components.extend([
            {"name": "MessageList", "purpose": "Chat messages", "props": ["messages"], "category": "feature"},
            {"name": "MessageInput", "purpose": "Send message", "props": ["onSend"], "category": "feature"},
        ])
        types.append({"name": "Message", "purpose": "Chat message", "fields": {"id": "string", "text": "string", "sender": "string", "timestamp": "string"}})
        hooks.append({"name": "useMessages", "purpose": "Message handling"})
    
    # Add header if app seems complex enough
    if len(pages) > 1 or len(components) > 2:
        components.insert(0, {"name": "Header", "purpose": "Navigation", "props": [], "category": "layout"})
    
    return {
        "app_name": app_name or "my-app",
        "description": prompt[:100],
        "components": components,
        "pages": pages,
        "hooks": hooks,
        "types": types,
        "api_endpoints": api_endpoints,
        "has_auth": any(word in prompt_lower for word in ["auth", "login"]),
        "has_routing": len(pages) > 1,
        "state_management": "context" if hooks else "local"
    }


def _generate_vite_config(project_dir: Path, structure: Dict[str, Any]) -> None:
    """Generate essential Vite/React config files."""
    app_name = structure.get("app_name", "vite-react-app")
    has_routing = structure.get("has_routing", False)
    
    # Determine dependencies based on what's needed
    dependencies: Dict[str, str] = {
        "react": "^18.3.1",
        "react-dom": "^18.3.1",
    }
    
    if has_routing:
        dependencies["react-router-dom"] = "^6.22.0"
    
    # package.json
    pkg = {
        "name": app_name,
        "private": True,
        "version": "0.1.0",
        "type": "module",
        "scripts": {
            "dev": "vite",
            "build": "tsc -b && vite build",
            "preview": "vite preview"
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
            "vite": "^5.4.8"
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
            "strict": True,
            "baseUrl": ".",
            "paths": {
                "@/*": ["src/*"]
            }
        },
        "include": ["src"]
    }
    write_json(project_dir / "tsconfig.json", tsconfig)

    # vite.config.ts
    vite_cfg = '''import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
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
    <title>{app_name.replace('-', ' ').title()}</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
'''
    write_text(project_dir / "index.html", index_html)

    # postcss.config.js
    write_text(project_dir / "postcss.config.js", '''export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
''')

    # tailwind.config.js
    write_text(project_dir / "tailwind.config.js", '''/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: { extend: {} },
  plugins: [],
}
''')

    # src/index.css
    write_text(project_dir / "src/index.css", '''@tailwind base;
@tailwind components;
@tailwind utilities;
''')


def _generate_types(prompt: str, project_dir: Path, llm: BaseLLM, structure: Dict[str, Any]) -> None:
    """Generate TypeScript types - each type in its own file."""
    types_dir = project_dir / "src/types"
    types_list = structure.get("types", [])
    
    if not types_list:
        return
    
    generated_types = []
    
    for type_def in types_list:
        type_name = type_def.get("name", "Unknown")
        type_purpose = type_def.get("purpose", "")
        type_fields = type_def.get("fields", {})
        
        # Generate type using LLM for better quality
        type_prompt = f"""Generate a TypeScript interface/type for: {type_name}

Purpose: {type_purpose}
Base fields: {type_fields}
Application: {prompt}

Requirements:
- Export the interface
- Add JSDoc comments
- Include any related types (e.g., CreateDTO, UpdateDTO if relevant)
- Use proper TypeScript conventions

Return ONLY TypeScript code, no markdown."""

        type_code = llm.generate_code(
            type_prompt,
            system=FRONTEND_SYSTEM_PROMPT,
            temperature=0.2,
            max_tokens=1024
        )
        
        type_code = _clean_code_response(type_code)
        write_text(types_dir / f"{type_name}.ts", type_code)
        generated_types.append(type_name)
    
    # Generate index.ts that re-exports all types
    if generated_types:
        index_content = "\n".join([f"export * from './{t}';" for t in generated_types])
        write_text(types_dir / "index.ts", index_content + "\n")


def _generate_hooks(prompt: str, project_dir: Path, llm: BaseLLM, structure: Dict[str, Any]) -> None:
    """Generate custom hooks - each hook in its own file."""
    hooks_dir = project_dir / "src/hooks"
    hooks_list = structure.get("hooks", [])
    
    if not hooks_list:
        return
    
    generated_hooks = []
    type_names = [t.get("name") for t in structure.get("types", [])]
    
    for hook in hooks_list:
        hook_name = hook.get("name", "useCustom")
        hook_purpose = hook.get("purpose", "")
        
        hook_prompt = f"""Generate a React custom hook: {hook_name}

Purpose: {hook_purpose}
Application: {prompt}
Available types to import from '@/types': {type_names}
API endpoints: {structure.get('api_endpoints', [])}

Requirements:
- Use TypeScript
- Handle loading, error states if doing async operations
- Follow React hooks rules
- Include proper cleanup
- Export as default and named export

Return ONLY the code, no markdown."""

        hook_code = llm.generate_code(
            hook_prompt,
            system=FRONTEND_SYSTEM_PROMPT,
            temperature=0.3,
            max_tokens=2048
        )
        
        hook_code = _clean_code_response(hook_code)
        
        # Ensure exports
        if f"export default {hook_name}" not in hook_code and "export default" not in hook_code:
            hook_code += f"\n\nexport default {hook_name};\n"
        
        write_text(hooks_dir / f"{hook_name}.ts", hook_code)
        generated_hooks.append(hook_name)
    
    # Generate index
    if generated_hooks:
        index_lines = [f"export {{ default as {h} }} from './{h}';" for h in generated_hooks]
        write_text(hooks_dir / "index.ts", "\n".join(index_lines) + "\n")


def _generate_services(prompt: str, project_dir: Path, llm: BaseLLM, structure: Dict[str, Any]) -> None:
    """Generate API service layer."""
    services_dir = project_dir / "src/services"
    endpoints = structure.get("api_endpoints", [])
    type_names = [t.get("name") for t in structure.get("types", [])]
    
    if not endpoints:
        return
    
    service_prompt = f"""Generate an API service module for a React app.

API Endpoints: {endpoints}
Available types from '@/types': {type_names}
Application: {prompt}

Requirements:
- Create a typed API client
- Use fetch or axios pattern
- Handle errors properly
- Export functions for each endpoint (get, create, update, delete as needed)
- Use TypeScript

Return ONLY the code."""

    service_code = llm.generate_code(
        service_prompt,
        system=FRONTEND_SYSTEM_PROMPT,
        temperature=0.3,
        max_tokens=3000
    )
    
    service_code = _clean_code_response(service_code)
    write_text(services_dir / "api.ts", service_code)
    write_text(services_dir / "index.ts", "export * from './api';\n")


def _generate_components(prompt: str, project_dir: Path, llm: BaseLLM, structure: Dict[str, Any]) -> None:
    """Generate React components - each in its own file."""
    components_dir = project_dir / "src/components"
    components_list = structure.get("components", [])
    
    if not components_list:
        return
    
    layout_keywords = ["Header", "Footer", "Sidebar", "Layout", "Navbar", "Navigation", "Nav"]
    ui_keywords = ["Button", "Input", "Card", "Modal", "Loader", "Spinner", "Badge"]
    
    generated: Dict[str, List[str]] = {"root": [], "layout": [], "ui": []}
    type_names = [t.get("name") for t in structure.get("types", [])]
    hook_names = [h.get("name") for h in structure.get("hooks", [])]
    
    for component in components_list:
        comp_name = component.get("name", "Component")
        comp_purpose = component.get("purpose", "")
        comp_props = component.get("props", [])
        comp_category = component.get("category", "feature")
        
        # Determine target directory
        if comp_name in layout_keywords or comp_category == "layout":
            target_dir = components_dir / "layout"
            category_key = "layout"
        elif comp_name in ui_keywords or comp_category == "ui":
            target_dir = components_dir / "ui"
            category_key = "ui"
        else:
            target_dir = components_dir
            category_key = "root"
        
        ensure_dir(target_dir)
        
        comp_prompt = f"""Generate a React component: {comp_name}

Purpose: {comp_purpose}
Props: {comp_props}
Application context: {prompt}

Available imports:
- Types from '@/types': {type_names}
- Hooks from '@/hooks': {hook_names}

Requirements:
- TypeScript with Props interface
- Tailwind CSS for styling
- Functional component
- Handle edge cases (empty, loading if applicable)
- Accessibility attributes where needed
- Export as default

Return ONLY the component code, no markdown code blocks."""

        comp_code = llm.generate_code(
            comp_prompt,
            system=FRONTEND_SYSTEM_PROMPT,
            temperature=0.4,
            max_tokens=COMPONENT_MAX_TOKENS
        )
        
        comp_code = _clean_code_response(comp_code)
        
        if "export default" not in comp_code:
            comp_code += f"\n\nexport default {comp_name};\n"
        
        write_text(target_dir / f"{comp_name}.tsx", comp_code)
        generated[category_key].append(comp_name)
        log.debug(f"Generated component: {comp_name} in {category_key}")
    
    # Generate index files
    for category, names in generated.items():
        if not names:
            continue
        
        if category == "root":
            target_dir = components_dir
        else:
            target_dir = components_dir / category
        
        index_lines = [f"export {{ default as {n} }} from './{n}';" for n in names]
        write_text(target_dir / "index.ts", "\n".join(index_lines) + "\n")
    
    # Main components index
    main_exports = []
    if generated["root"]:
        main_exports.extend([f"export {{ {n} }} from './{n}';" for n in generated["root"]])
    if generated["layout"]:
        main_exports.append("export * from './layout';")
    if generated["ui"]:
        main_exports.append("export * from './ui';")
    
    if main_exports:
        write_text(components_dir / "index.ts", "\n".join(main_exports) + "\n")


def _generate_pages(prompt: str, project_dir: Path, llm: BaseLLM, structure: Dict[str, Any]) -> None:
    """Generate page components."""
    pages_dir = project_dir / "src/pages"
    pages_list = structure.get("pages", [])
    
    if not pages_list:
        return
    
    component_names = [c.get("name") for c in structure.get("components", [])]
    hook_names = [h.get("name") for h in structure.get("hooks", [])]
    type_names = [t.get("name") for t in structure.get("types", [])]
    
    generated_pages = []
    
    for page in pages_list:
        page_name = page.get("name", "Page")
        page_route = page.get("route", "/")
        page_purpose = page.get("purpose", "")
        
        page_prompt = f"""Generate a React page component: {page_name}

Route: {page_route}
Purpose: {page_purpose}
Application: {prompt}

Available imports:
- Components from '@/components': {component_names}
- Hooks from '@/hooks': {hook_names}
- Types from '@/types': {type_names}

Requirements:
- TypeScript
- Use available components and hooks
- Tailwind CSS layout
- Handle loading/error/empty states
- Proper page structure
- Export as default

Return ONLY the code."""

        page_code = llm.generate_code(
            page_prompt,
            system=FRONTEND_SYSTEM_PROMPT,
            temperature=0.4,
            max_tokens=COMPONENT_MAX_TOKENS
        )
        
        page_code = _clean_code_response(page_code)
        
        if "export default" not in page_code:
            page_code += f"\n\nexport default {page_name};\n"
        
        write_text(pages_dir / f"{page_name}.tsx", page_code)
        generated_pages.append(page_name)
    
    # Generate pages index
    if generated_pages:
        index_lines = [f"export {{ default as {p} }} from './{p}';" for p in generated_pages]
        write_text(pages_dir / "index.ts", "\n".join(index_lines) + "\n")


def _generate_app(prompt: str, project_dir: Path, llm: BaseLLM, structure: Dict[str, Any]) -> None:
    """Generate the main App.tsx."""
    pages = structure.get("pages", [])
    components = structure.get("components", [])
    has_routing = structure.get("has_routing", False)
    
    page_routes = [(p.get("name"), p.get("route", "/")) for p in pages]
    layout_components = [c.get("name") for c in components if c.get("category") == "layout" or c.get("name") in ["Header", "Footer", "Navbar", "Layout"]]
    
    app_prompt = f"""Generate App.tsx for this React application.

Application: {prompt}
Uses routing: {has_routing}
Pages and routes: {page_routes}
Layout components available: {layout_components}

Requirements:
- Import pages from '@/pages'
- Import layout components from '@/components' if available
{"- Use BrowserRouter, Routes, Route from react-router-dom" if has_routing else "- Render the main page directly"}
- Wrap with layout components if available (Header, Footer)
- TypeScript
- Tailwind CSS

Return ONLY the code."""

    app_code = llm.generate_code(
        app_prompt,
        system=FRONTEND_SYSTEM_PROMPT,
        temperature=0.3,
        max_tokens=3000
    )
    
    app_code = _clean_code_response(app_code)
    
    if "export default" not in app_code:
        app_code += "\n\nexport default App;\n"
    
    write_text(project_dir / "src/App.tsx", app_code)


def _generate_main_entry(project_dir: Path, structure: Dict[str, Any]) -> None:
    """Generate main.tsx entry point."""
    # Simple main.tsx - routing is handled in App.tsx
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


def _clean_code_response(code: str) -> str:
    """Clean up LLM code response."""
    # Remove markdown code blocks
    code = re.sub(r'^```(?:typescript|tsx|ts|javascript|jsx|js|json)?\s*\n?', '', code, flags=re.MULTILINE)
    code = re.sub(r'\n?```\s*$', '', code, flags=re.MULTILINE)
    code = code.strip()
    
    # Organize imports at top
    lines = code.split('\n')
    imports = []
    other = []
    
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('import ') or stripped.startswith('import{'):
            imports.append(line)
        else:
            other.append(line)
    
    if imports:
        # Remove duplicate imports
        imports = list(dict.fromkeys(imports))
        return '\n'.join(imports) + '\n\n' + '\n'.join(other).strip()
    
    return code
