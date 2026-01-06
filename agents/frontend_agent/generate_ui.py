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
- Return ONLY code, no explanations or markdown code blocks
- Do NOT wrap code in markdown code fences
- STRICTLY follow the API contract provided - do not deviate from it"""

# Higher token limits for larger generations
DEFAULT_MAX_TOKENS = 16384
COMPONENT_MAX_TOKENS = 8192
ANALYSIS_MAX_TOKENS = 4096


def generate_ui(prompt: str, ctx: MCPContext, out_dir: Path, llm: BaseLLM) -> Dict[str, str]:
    """Generate a modular React+TypeScript frontend using Vite and Tailwind CSS.
    
    Uses API contract from documentation agent to ensure consistency with backend.
    
    Returns:
        Dict[str, str]: Key-value pairs where key is file path and value is file content
    """
    project_dir = out_dir
    
    # Get API contract from documentation agent
    api_contract = ctx.get_api_contract()
    if api_contract:
        log.info(f"Using API contract with {len(api_contract.get('endpoints', []))} endpoints")
    else:
        log.warning("No API contract found - generating without contract constraints")
    
    # Track all generated files for key-value output
    generated_files: Dict[str, str] = {}
    
    # 1. Analyze requirements using API contract
    log.info("Analyzing frontend requirements...")
    structure = _analyze_requirements_with_contract(prompt, llm, api_contract)
    log.info(f"App: {structure.get('app_name')}")
    log.info(f"Components to generate: {[c.get('name') for c in structure.get('components', [])]}")
    log.info(f"Pages to generate: {[p.get('name') for p in structure.get('pages', [])]}")
    log.info(f"Hooks to generate: {[h.get('name') for h in structure.get('hooks', [])]}")
    
    # 2. Create ONLY the folders that will be used
    _create_dynamic_folder_structure(project_dir, structure)
    
    # 3. Generate essential Vite config files (these are always needed)
    log.info("Generating Vite configuration...")
    config_files = _generate_vite_config(project_dir, structure, api_contract)
    generated_files.update(config_files)
    
    # 4. Generate types ONLY if there are types defined (based on API contract)
    if structure.get("types"):
        log.info("Generating TypeScript types...")
        type_files = _generate_types(prompt, project_dir, llm, structure, api_contract)
        generated_files.update(type_files)
    
    # 5. Generate hooks ONLY if there are hooks defined
    if structure.get("hooks"):
        log.info("Generating custom hooks...")
        hook_files = _generate_hooks(prompt, project_dir, llm, structure, api_contract)
        generated_files.update(hook_files)
    
    # 6. Generate services based on API contract
    if api_contract and api_contract.get("endpoints"):
        log.info("Generating API services from contract...")
        service_files = _generate_services_from_contract(prompt, project_dir, llm, structure, api_contract)
        generated_files.update(service_files)
    
    # 7. Generate components
    if structure.get("components"):
        log.info("Generating components...")
        component_files = _generate_components(prompt, project_dir, llm, structure, api_contract)
        generated_files.update(component_files)
    
    # 8. Generate pages
    if structure.get("pages"):
        log.info("Generating pages...")
        page_files = _generate_pages(prompt, project_dir, llm, structure, api_contract)
        generated_files.update(page_files)
    
    # 9. Generate App and main entry (always needed)
    log.info("Generating App entry point...")
    app_files = _generate_app(prompt, project_dir, llm, structure, api_contract)
    generated_files.update(app_files)
    main_files = _generate_main_entry(project_dir, structure)
    generated_files.update(main_files)

    # Store generated files in context for other agents
    ctx.set_generated_files("frontend", generated_files)
    ctx.add_artifact("frontend", project_dir)
    
    log.info(f"Frontend generated at: {project_dir}")
    log.info(f"Generated {len(generated_files)} files")
    
    return generated_files


def _analyze_requirements_with_contract(prompt: str, llm: BaseLLM, api_contract: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Use LLM to analyze prompt and API contract to determine exactly what files to generate."""
    
    # Extract info from API contract if available
    contract_endpoints = []
    contract_models = []
    if api_contract:
        contract_endpoints = api_contract.get("endpoints", [])
        contract_models = api_contract.get("models", [])
    
    analysis_prompt = f"""Analyze this application requirement and API contract to determine what frontend files need to be built.

Requirement: {prompt}

API Contract Endpoints:
{json.dumps(contract_endpoints, indent=2) if contract_endpoints else "No API contract provided"}

API Models to implement:
{json.dumps(contract_models, indent=2) if contract_models else "No models provided"}

Return a JSON object with this EXACT structure. Be SPECIFIC - derive from the API contract:

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
  "api_endpoints": {json.dumps([ep.get("path") for ep in contract_endpoints]) if contract_endpoints else "[]"},
  "has_auth": {"true" if any(ep.get("auth_required") for ep in contract_endpoints) else "false"},
  "has_routing": true,
  "state_management": "context"
}}

IMPORTANT:
- Types MUST match the API contract models exactly
- Components should handle API responses as defined in contract
- Include auth components if API has auth endpoints
- Service functions should match API contract exactly

Return ONLY valid JSON."""

    response = llm.generate_code(
        analysis_prompt, 
        system="You are an expert software architect. Analyze requirements and API contracts precisely.",
        temperature=0.2, 
        max_tokens=ANALYSIS_MAX_TOKENS
    )
    
    # Parse JSON from response
    try:
        cleaned = re.sub(r'^```(?:json)?\s*\n?', '', response, flags=re.MULTILINE)
        cleaned = re.sub(r'\n?```\s*$', '', cleaned, flags=re.MULTILINE)
        
        json_match = re.search(r'\{[\s\S]*\}', cleaned)
        if json_match:
            parsed = json.loads(json_match.group())
            if parsed.get("components") or parsed.get("pages"):
                log.debug(f"Successfully parsed LLM analysis: {len(parsed.get('components', []))} components, {len(parsed.get('pages', []))} pages")
                return parsed
    except json.JSONDecodeError as e:
        log.warning(f"Failed to parse LLM response as JSON: {e}")
    
    # Fallback: generate structure based on API contract
    log.info("Using fallback structure analysis based on API contract")
    return _generate_fallback_structure_from_contract(prompt, api_contract)


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


def _generate_fallback_structure_from_contract(prompt: str, api_contract: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate structure based on API contract when LLM analysis fails."""
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
    has_auth = False
    
    # Build from API contract if available
    if api_contract:
        endpoints = api_contract.get("endpoints", [])
        models = api_contract.get("models", [])
        
        # Extract endpoints
        api_endpoints = [ep.get("path") for ep in endpoints if ep.get("path")]
        
        # Check for auth
        has_auth = any(ep.get("auth_required") for ep in endpoints)
        auth_endpoints = [ep for ep in endpoints if "/auth" in ep.get("path", "")]
        
        # Add types from models
        for model in models:
            types.append({
                "name": model,
                "purpose": f"{model} data type from API",
                "fields": {}
            })
        
        # Add auth components if needed
        if auth_endpoints or has_auth:
            components.extend([
                {"name": "LoginForm", "purpose": "User login", "props": ["onSubmit"], "category": "feature"},
                {"name": "RegisterForm", "purpose": "User registration", "props": ["onSubmit"], "category": "feature"},
            ])
            pages.append({"name": "LoginPage", "route": "/login", "purpose": "Login page"})
            pages.append({"name": "RegisterPage", "route": "/register", "purpose": "Registration page"})
            hooks.append({"name": "useAuth", "purpose": "Authentication state management"})
        
        # Add components for resource endpoints
        resource_endpoints = [ep for ep in endpoints if ep.get("method") in ["GET", "POST"] and "/auth" not in ep.get("path", "")]
        for ep in resource_endpoints:
            path = ep.get("path", "")
            resource_name = path.split("/")[-1].replace(":", "").title()
            if resource_name and resource_name not in ["Health"]:
                components.append({
                    "name": f"{resource_name}List",
                    "purpose": f"Display {resource_name.lower()} items",
                    "props": ["items", "onRefresh"],
                    "category": "feature"
                })
                components.append({
                    "name": f"{resource_name}Form",
                    "purpose": f"Create/edit {resource_name.lower()}",
                    "props": ["onSubmit", "initialData"],
                    "category": "feature"
                })
                hooks.append({
                    "name": f"use{resource_name}",
                    "purpose": f"Manage {resource_name.lower()} state and API calls"
                })
    
    # Add common layout components
    components.insert(0, {"name": "Header", "purpose": "Navigation header", "props": [], "category": "layout"})
    
    return {
        "app_name": app_name or "my-app",
        "description": prompt[:100],
        "components": components,
        "pages": pages,
        "hooks": hooks,
        "types": types,
        "api_endpoints": api_endpoints,
        "has_auth": has_auth,
        "has_routing": len(pages) > 1,
        "state_management": "context" if hooks else "local"
    }


def _generate_vite_config(project_dir: Path, structure: Dict[str, Any], api_contract: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    """Generate essential Vite/React config files. Returns generated files as key-value pairs."""
    app_name = structure.get("app_name", "vite-react-app")
    has_routing = structure.get("has_routing", False)
    
    generated_files: Dict[str, str] = {}
    
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
    pkg_content = json.dumps(pkg, indent=2)
    write_json(project_dir / "package.json", pkg)
    generated_files["package.json"] = pkg_content

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
    tsconfig_content = json.dumps(tsconfig, indent=2)
    write_json(project_dir / "tsconfig.json", tsconfig)
    generated_files["tsconfig.json"] = tsconfig_content

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
    generated_files["vite.config.ts"] = vite_cfg

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
    generated_files["index.html"] = index_html

    # postcss.config.js
    postcss_cfg = '''export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
'''
    write_text(project_dir / "postcss.config.js", postcss_cfg)
    generated_files["postcss.config.js"] = postcss_cfg

    # tailwind.config.js
    tailwind_cfg = '''/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: { extend: {} },
  plugins: [],
}
'''
    write_text(project_dir / "tailwind.config.js", tailwind_cfg)
    generated_files["tailwind.config.js"] = tailwind_cfg

    # src/index.css
    index_css = '''@tailwind base;
@tailwind components;
@tailwind utilities;
'''
    write_text(project_dir / "src/index.css", index_css)
    generated_files["src/index.css"] = index_css
    
    return generated_files


def _generate_types(prompt: str, project_dir: Path, llm: BaseLLM, structure: Dict[str, Any], api_contract: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    """Generate TypeScript types - each type in its own file. Returns files as key-value pairs."""
    types_dir = project_dir / "src/types"
    types_list = structure.get("types", [])
    generated_files: Dict[str, str] = {}
    
    if not types_list:
        return generated_files
    
    generated_types = []
    
    # Get model definitions from API contract if available
    contract_models = {}
    if api_contract:
        for ep in api_contract.get("endpoints", []):
            response = ep.get("response", {})
            if response.get("success"):
                body = response["success"].get("body", {})
                contract_models.update(body)
    
    for type_def in types_list:
        type_name = type_def.get("name", "Unknown")
        type_purpose = type_def.get("purpose", "")
        type_fields = type_def.get("fields", {})
        
        # Generate type using LLM with API contract context
        type_prompt = f"""Generate a TypeScript interface/type for: {type_name}

Purpose: {type_purpose}
Base fields: {type_fields}
Application: {prompt}
API Contract context: {json.dumps(contract_models) if contract_models else "None"}

Requirements:
- Export the interface
- Add JSDoc comments
- Include any related types (e.g., CreateDTO, UpdateDTO if relevant)
- Use proper TypeScript conventions
- Types MUST be compatible with the API contract

Return ONLY TypeScript code, no markdown."""

        type_code = llm.generate_code(
            type_prompt,
            system=FRONTEND_SYSTEM_PROMPT,
            temperature=0.2,
            max_tokens=1024
        )
        
        type_code = _clean_code_response(type_code)
        file_path = f"src/types/{type_name}.ts"
        write_text(types_dir / f"{type_name}.ts", type_code)
        generated_files[file_path] = type_code
        generated_types.append(type_name)
    
    # Generate index.ts that re-exports all types
    if generated_types:
        index_content = "\n".join([f"export * from './{t}';" for t in generated_types]) + "\n"
        write_text(types_dir / "index.ts", index_content)
        generated_files["src/types/index.ts"] = index_content
    
    return generated_files


def _generate_hooks(prompt: str, project_dir: Path, llm: BaseLLM, structure: Dict[str, Any], api_contract: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    """Generate custom hooks - each hook in its own file. Returns files as key-value pairs."""
    hooks_dir = project_dir / "src/hooks"
    hooks_list = structure.get("hooks", [])
    generated_files: Dict[str, str] = {}
    
    if not hooks_list:
        return generated_files
    
    generated_hooks = []
    type_names = [t.get("name") for t in structure.get("types", [])]
    api_endpoints = []
    if api_contract:
        api_endpoints = [{"method": ep.get("method"), "path": ep.get("path"), "name": ep.get("name")} 
                        for ep in api_contract.get("endpoints", [])]
    
    for hook in hooks_list:
        hook_name = hook.get("name", "useCustom")
        hook_purpose = hook.get("purpose", "")
        
        hook_prompt = f"""Generate a React custom hook: {hook_name}

Purpose: {hook_purpose}
Application: {prompt}
Available types to import from '@/types': {type_names}
API Contract endpoints to use: {json.dumps(api_endpoints) if api_endpoints else structure.get('api_endpoints', [])}

Requirements:
- Use TypeScript
- Handle loading, error states if doing async operations
- Follow React hooks rules
- Include proper cleanup
- Export as default and named export
- MUST use the exact API endpoints from the contract

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
        
        file_path = f"src/hooks/{hook_name}.ts"
        write_text(hooks_dir / f"{hook_name}.ts", hook_code)
        generated_files[file_path] = hook_code
        generated_hooks.append(hook_name)
    
    # Generate index
    if generated_hooks:
        index_lines = [f"export {{ default as {h} }} from './{h}';" for h in generated_hooks]
        index_content = "\n".join(index_lines) + "\n"
        write_text(hooks_dir / "index.ts", index_content)
        generated_files["src/hooks/index.ts"] = index_content
    
    return generated_files


def _generate_services_from_contract(prompt: str, project_dir: Path, llm: BaseLLM, structure: Dict[str, Any], api_contract: Dict[str, Any]) -> Dict[str, str]:
    """Generate API service layer based on API contract. Returns files as key-value pairs."""
    services_dir = project_dir / "src/services"
    ensure_dir(services_dir)
    generated_files: Dict[str, str] = {}
    
    endpoints = api_contract.get("endpoints", [])
    type_names = [t.get("name") for t in structure.get("types", [])]
    base_url = api_contract.get("base_url", "/api")
    auth = api_contract.get("authentication", {})
    
    service_prompt = f"""Generate a TypeScript API service module for a React app based on this EXACT API contract.

API Base URL: {base_url}
Authentication: {json.dumps(auth)}

API Endpoints (MUST implement ALL of these exactly):
{json.dumps(endpoints, indent=2)}

Available types from '@/types': {type_names}
Application: {prompt}

Requirements:
- Create a typed API client
- Use fetch with proper error handling
- Implement EVERY endpoint from the contract exactly as specified
- Export functions matching endpoint names (e.g., healthCheck, login, register, listItems, createItem, etc.)
- Include proper TypeScript types for request/response
- Handle authentication token storage and headers
- Each function should match the exact method, path, and request/response structure from the contract

Return ONLY the code, no markdown."""

    service_code = llm.generate_code(
        service_prompt,
        system=FRONTEND_SYSTEM_PROMPT,
        temperature=0.3,
        max_tokens=4096
    )
    
    service_code = _clean_code_response(service_code)
    write_text(services_dir / "api.ts", service_code)
    generated_files["src/services/api.ts"] = service_code
    
    index_content = "export * from './api';\n"
    write_text(services_dir / "index.ts", index_content)
    generated_files["src/services/index.ts"] = index_content
    
    return generated_files


def _generate_components(prompt: str, project_dir: Path, llm: BaseLLM, structure: Dict[str, Any], api_contract: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    """Generate React components - each in its own file. Returns files as key-value pairs."""
    components_dir = project_dir / "src/components"
    components_list = structure.get("components", [])
    generated_files: Dict[str, str] = {}
    
    if not components_list:
        return generated_files
    
    layout_keywords = ["Header", "Footer", "Sidebar", "Layout", "Navbar", "Navigation", "Nav"]
    ui_keywords = ["Button", "Input", "Card", "Modal", "Loader", "Spinner", "Badge"]
    
    generated: Dict[str, List[str]] = {"root": [], "layout": [], "ui": []}
    type_names = [t.get("name") for t in structure.get("types", [])]
    hook_names = [h.get("name") for h in structure.get("hooks", [])]
    
    # Get API contract info for components
    api_info = ""
    if api_contract:
        api_info = f"API endpoints available: {json.dumps([ep.get('name') for ep in api_contract.get('endpoints', [])])}"
    
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
{api_info}

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
- If using API data, ensure types match the API contract

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
        
        # Determine file path for key-value output
        if category_key == "root":
            file_path = f"src/components/{comp_name}.tsx"
        else:
            file_path = f"src/components/{category_key}/{comp_name}.tsx"
        
        write_text(target_dir / f"{comp_name}.tsx", comp_code)
        generated_files[file_path] = comp_code
        generated[category_key].append(comp_name)
        log.debug(f"Generated component: {comp_name} in {category_key}")
    
    # Generate index files
    for category, names in generated.items():
        if not names:
            continue
        
        if category == "root":
            target_dir = components_dir
            index_path = "src/components/index.ts"
        else:
            target_dir = components_dir / category
            index_path = f"src/components/{category}/index.ts"
        
        index_lines = [f"export {{ default as {n} }} from './{n}';" for n in names]
        index_content = "\n".join(index_lines) + "\n"
        write_text(target_dir / "index.ts", index_content)
        generated_files[index_path] = index_content
    
    # Main components index
    main_exports = []
    if generated["root"]:
        main_exports.extend([f"export {{ {n} }} from './{n}';" for n in generated["root"]])
    if generated["layout"]:
        main_exports.append("export * from './layout';")
    if generated["ui"]:
        main_exports.append("export * from './ui';")
    
    if main_exports:
        main_index_content = "\n".join(main_exports) + "\n"
        write_text(components_dir / "index.ts", main_index_content)
        generated_files["src/components/index.ts"] = main_index_content
    
    return generated_files


def _generate_pages(prompt: str, project_dir: Path, llm: BaseLLM, structure: Dict[str, Any], api_contract: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    """Generate page components. Returns files as key-value pairs."""
    pages_dir = project_dir / "src/pages"
    pages_list = structure.get("pages", [])
    generated_files: Dict[str, str] = {}
    
    if not pages_list:
        return generated_files
    
    component_names = [c.get("name") for c in structure.get("components", [])]
    hook_names = [h.get("name") for h in structure.get("hooks", [])]
    type_names = [t.get("name") for t in structure.get("types", [])]
    
    # Get API info
    api_info = ""
    if api_contract:
        api_info = f"API Contract: {json.dumps([{'name': ep.get('name'), 'method': ep.get('method'), 'path': ep.get('path')} for ep in api_contract.get('endpoints', [])])}"
    
    generated_pages = []
    
    for page in pages_list:
        page_name = page.get("name", "Page")
        page_route = page.get("route", "/")
        page_purpose = page.get("purpose", "")
        
        page_prompt = f"""Generate a React page component: {page_name}

Route: {page_route}
Purpose: {page_purpose}
Application: {prompt}
{api_info}

Available imports:
- Components from '@/components': {component_names}
- Hooks from '@/hooks': {hook_names}
- Types from '@/types': {type_names}
- API services from '@/services': Available

Requirements:
- TypeScript
- Use available components and hooks
- Tailwind CSS layout
- Handle loading/error/empty states
- Proper page structure
- Export as default
- Use API services that match the contract

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
        
        file_path = f"src/pages/{page_name}.tsx"
        write_text(pages_dir / f"{page_name}.tsx", page_code)
        generated_files[file_path] = page_code
        generated_pages.append(page_name)
    
    # Generate pages index
    if generated_pages:
        index_lines = [f"export {{ default as {p} }} from './{p}';" for p in generated_pages]
        index_content = "\n".join(index_lines) + "\n"
        write_text(pages_dir / "index.ts", index_content)
        generated_files["src/pages/index.ts"] = index_content
    
    return generated_files


def _generate_app(prompt: str, project_dir: Path, llm: BaseLLM, structure: Dict[str, Any], api_contract: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    """Generate the main App.tsx. Returns files as key-value pairs."""
    pages = structure.get("pages", [])
    components = structure.get("components", [])
    has_routing = structure.get("has_routing", False)
    generated_files: Dict[str, str] = {}
    
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
    generated_files["src/App.tsx"] = app_code
    
    return generated_files


def _generate_main_entry(project_dir: Path, structure: Dict[str, Any]) -> Dict[str, str]:
    """Generate main.tsx entry point. Returns files as key-value pairs."""
    generated_files: Dict[str, str] = {}
    
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
    generated_files["src/main.tsx"] = main_tsx
    
    return generated_files


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
