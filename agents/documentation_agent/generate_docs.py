from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from meta_agent.utils import ensure_dir, write_text, write_json, log
from meta_agent.llm_interface import BaseLLM
from meta_agent.context_manager import MCPContext


# System prompt for documentation/specification generation
DOC_SYSTEM_PROMPT = """You are an expert software architect and technical writer.
Generate comprehensive API contracts and specifications that will be used by
both frontend and backend teams to ensure consistency.
Return ONLY valid JSON, no markdown or explanations."""


def generate_docs(prompt: str, ctx: MCPContext, out_dir: Path, llm: BaseLLM) -> Dict[str, str]:
    """
    Generate API contracts and documentation FIRST.
    This output is used by frontend and backend agents to ensure consistency.
    
    Returns:
        Dict[str, str]: Key-value pairs where key is file path and value is file content
    """
    docs_dir = out_dir
    ensure_dir(docs_dir)
    
    generated_files: Dict[str, str] = {}
    
    # 1. Generate API Contract specification
    log.info("Generating API contract specification...")
    api_contract = _generate_api_contract(prompt, llm)
    
    # Store API contract in context for other agents
    ctx.set_api_contract(api_contract)
    
    # 2. Generate data models/types specification
    log.info("Generating data models specification...")
    data_models = _generate_data_models(prompt, api_contract, llm)
    
    # 3. Generate project structure specification
    log.info("Generating project structure...")
    project_structure = _generate_project_structure(prompt, api_contract, llm)
    
    # Create specification files
    
    # API Contract JSON
    api_contract_path = "api-contract.json"
    api_contract_content = json.dumps(api_contract, indent=2)
    generated_files[api_contract_path] = api_contract_content
    write_text(docs_dir / api_contract_path, api_contract_content)
    
    # Data Models JSON
    data_models_path = "data-models.json"
    data_models_content = json.dumps(data_models, indent=2)
    generated_files[data_models_path] = data_models_content
    write_text(docs_dir / data_models_path, data_models_content)
    
    # Project Structure JSON
    project_structure_path = "project-structure.json"
    project_structure_content = json.dumps(project_structure, indent=2)
    generated_files[project_structure_path] = project_structure_content
    write_text(docs_dir / project_structure_path, project_structure_content)
    
    # Generate README documentation
    readme_content = _generate_readme(prompt, api_contract, data_models, project_structure)
    generated_files["README.md"] = readme_content
    write_text(docs_dir / "README.md", readme_content)
    
    # Generate API documentation
    api_docs_content = _generate_api_documentation(api_contract)
    generated_files["API.md"] = api_docs_content
    write_text(docs_dir / "API.md", api_docs_content)
    
    # Store generated files in context
    ctx.set_generated_files("documentation", generated_files)
    ctx.add_artifact("documentation", docs_dir)
    
    log.info(f"Documentation generated at: {docs_dir}")
    log.info(f"Generated {len(generated_files)} files: {list(generated_files.keys())}")
    
    return generated_files


def _generate_api_contract(prompt: str, llm: BaseLLM) -> Dict[str, Any]:
    """Generate comprehensive API contract specification."""
    
    contract_prompt = f"""Based on this application requirement, generate a comprehensive API contract.

Requirement: {prompt}

Return a JSON object with this EXACT structure:
{{
  "api_version": "1.0.0",
  "base_url": "/api",
  "authentication": {{
    "type": "jwt",
    "header": "Authorization",
    "prefix": "Bearer"
  }},
  "endpoints": [
    {{
      "method": "GET|POST|PUT|DELETE",
      "path": "/exact/path",
      "name": "descriptiveName",
      "description": "What this endpoint does",
      "auth_required": true|false,
      "request": {{
        "params": {{"paramName": "type"}},
        "query": {{"queryParam": "type"}},
        "body": {{"fieldName": "type"}}
      }},
      "response": {{
        "success": {{"status": 200, "body": {{"fieldName": "type"}}}},
        "errors": [{{"status": 400, "message": "Error description"}}]
      }}
    }}
  ],
  "models": ["ModelName1", "ModelName2"]
}}

IMPORTANT:
- Include ALL necessary endpoints for the application
- Be specific about request/response structures
- Include proper error responses
- Always include health check endpoint
- Include authentication endpoints if user management is needed

Return ONLY valid JSON."""

    response = llm.generate_code(
        contract_prompt,
        system=DOC_SYSTEM_PROMPT,
        temperature=0.2,
        max_tokens=8192
    )
    
    return _parse_json_response(response, _default_api_contract())


def _generate_data_models(prompt: str, api_contract: Dict[str, Any], llm: BaseLLM) -> Dict[str, Any]:
    """Generate data models specification based on API contract."""
    
    models_prompt = f"""Based on this application requirement and API contract, generate data model specifications.

Requirement: {prompt}

API Contract Models: {json.dumps(api_contract.get('models', []))}

Return a JSON object with this EXACT structure:
{{
  "models": [
    {{
      "name": "ModelName",
      "description": "What this model represents",
      "fields": [
        {{
          "name": "fieldName",
          "type": "string|number|boolean|Date|ModelName|ModelName[]",
          "required": true|false,
          "description": "Field description",
          "validation": "optional validation rules"
        }}
      ],
      "relationships": [
        {{"type": "hasMany|hasOne|belongsTo", "model": "RelatedModel", "foreignKey": "keyName"}}
      ]
    }}
  ],
  "enums": [
    {{
      "name": "EnumName",
      "values": ["VALUE1", "VALUE2"],
      "description": "What this enum represents"
    }}
  ]
}}

Return ONLY valid JSON."""

    response = llm.generate_code(
        models_prompt,
        system=DOC_SYSTEM_PROMPT,
        temperature=0.2,
        max_tokens=4096
    )
    
    return _parse_json_response(response, _default_data_models())


def _generate_project_structure(prompt: str, api_contract: Dict[str, Any], llm: BaseLLM) -> Dict[str, Any]:
    """Generate project structure specification."""
    
    structure_prompt = f"""Based on this application requirement, generate project structure specifications.

Requirement: {prompt}

Return a JSON object with this EXACT structure:
{{
  "app_name": "kebab-case-name",
  "description": "One line description",
  "frontend": {{
    "framework": "react",
    "pages": ["PageName"],
    "components": ["ComponentName"],
    "hooks": ["useHookName"],
    "services": ["serviceName"]
  }},
  "backend": {{
    "framework": "express",
    "routes": ["routeName"],
    "controllers": ["controllerName"],
    "middleware": ["middlewareName"],
    "services": ["serviceName"]
  }},
  "features": ["feature1", "feature2"]
}}

Return ONLY valid JSON."""

    response = llm.generate_code(
        structure_prompt,
        system=DOC_SYSTEM_PROMPT,
        temperature=0.2,
        max_tokens=2048
    )
    
    return _parse_json_response(response, _default_project_structure())


def _parse_json_response(response: str, fallback: Dict[str, Any]) -> Dict[str, Any]:
    """Parse JSON from LLM response with fallback."""
    try:
        # Clean markdown code blocks
        cleaned = re.sub(r'^```(?:json)?\s*\n?', '', response, flags=re.MULTILINE)
        cleaned = re.sub(r'\n?```\s*$', '', cleaned, flags=re.MULTILINE)
        
        json_match = re.search(r'\{[\s\S]*\}', cleaned)
        if json_match:
            return json.loads(json_match.group())
    except json.JSONDecodeError as e:
        log.warning(f"Failed to parse LLM response as JSON: {e}")
    
    log.info("Using fallback specification")
    return fallback


def _default_api_contract() -> Dict[str, Any]:
    """Default API contract structure."""
    return {
        "api_version": "1.0.0",
        "base_url": "/api",
        "authentication": {
            "type": "jwt",
            "header": "Authorization",
            "prefix": "Bearer"
        },
        "endpoints": [
            {
                "method": "GET",
                "path": "/health",
                "name": "healthCheck",
                "description": "Health check endpoint",
                "auth_required": False,
                "request": {},
                "response": {
                    "success": {"status": 200, "body": {"status": "string"}},
                    "errors": []
                }
            },
            {
                "method": "POST",
                "path": "/auth/register",
                "name": "register",
                "description": "Register a new user",
                "auth_required": False,
                "request": {
                    "body": {"email": "string", "password": "string", "name": "string"}
                },
                "response": {
                    "success": {"status": 201, "body": {"user": "User", "token": "string"}},
                    "errors": [{"status": 400, "message": "Email already exists"}]
                }
            },
            {
                "method": "POST",
                "path": "/auth/login",
                "name": "login",
                "description": "Login user",
                "auth_required": False,
                "request": {
                    "body": {"email": "string", "password": "string"}
                },
                "response": {
                    "success": {"status": 200, "body": {"user": "User", "token": "string"}},
                    "errors": [{"status": 401, "message": "Invalid credentials"}]
                }
            },
            {
                "method": "GET",
                "path": "/items",
                "name": "listItems",
                "description": "Get all items for authenticated user",
                "auth_required": True,
                "request": {},
                "response": {
                    "success": {"status": 200, "body": {"items": "Item[]"}},
                    "errors": [{"status": 401, "message": "Unauthorized"}]
                }
            },
            {
                "method": "POST",
                "path": "/items",
                "name": "createItem",
                "description": "Create a new item",
                "auth_required": True,
                "request": {
                    "body": {"name": "string"}
                },
                "response": {
                    "success": {"status": 201, "body": {"item": "Item"}},
                    "errors": [{"status": 400, "message": "Name required"}]
                }
            },
            {
                "method": "PUT",
                "path": "/items/:id",
                "name": "updateItem",
                "description": "Update an item",
                "auth_required": True,
                "request": {
                    "params": {"id": "string"},
                    "body": {"name": "string", "completed": "boolean"}
                },
                "response": {
                    "success": {"status": 200, "body": {"item": "Item"}},
                    "errors": [{"status": 404, "message": "Item not found"}]
                }
            },
            {
                "method": "DELETE",
                "path": "/items/:id",
                "name": "deleteItem",
                "description": "Delete an item",
                "auth_required": True,
                "request": {
                    "params": {"id": "string"}
                },
                "response": {
                    "success": {"status": 204, "body": {}},
                    "errors": [{"status": 404, "message": "Item not found"}]
                }
            }
        ],
        "models": ["User", "Item"]
    }


def _default_data_models() -> Dict[str, Any]:
    """Default data models structure."""
    return {
        "models": [
            {
                "name": "User",
                "description": "User account",
                "fields": [
                    {"name": "id", "type": "string", "required": True, "description": "Unique identifier"},
                    {"name": "email", "type": "string", "required": True, "description": "User email"},
                    {"name": "name", "type": "string", "required": False, "description": "Display name"},
                    {"name": "createdAt", "type": "Date", "required": True, "description": "Creation timestamp"},
                    {"name": "updatedAt", "type": "Date", "required": True, "description": "Last update timestamp"}
                ],
                "relationships": [
                    {"type": "hasMany", "model": "Item", "foreignKey": "userId"}
                ]
            },
            {
                "name": "Item",
                "description": "Task/item owned by a user",
                "fields": [
                    {"name": "id", "type": "string", "required": True, "description": "Unique identifier"},
                    {"name": "name", "type": "string", "required": True, "description": "Item name"},
                    {"name": "completed", "type": "boolean", "required": True, "description": "Completion status"},
                    {"name": "userId", "type": "string", "required": True, "description": "Owner user ID"},
                    {"name": "createdAt", "type": "Date", "required": True, "description": "Creation timestamp"},
                    {"name": "updatedAt", "type": "Date", "required": True, "description": "Last update timestamp"}
                ],
                "relationships": [
                    {"type": "belongsTo", "model": "User", "foreignKey": "userId"}
                ]
            }
        ],
        "enums": []
    }


def _default_project_structure() -> Dict[str, Any]:
    """Default project structure."""
    return {
        "app_name": "my-app",
        "description": "Generated application",
        "frontend": {
            "framework": "react",
            "pages": ["HomePage", "LoginPage"],
            "components": ["Header", "ItemList", "ItemForm"],
            "hooks": ["useAuth", "useItems"],
            "services": ["api", "auth"]
        },
        "backend": {
            "framework": "express",
            "routes": ["auth", "items"],
            "controllers": ["authController", "itemsController"],
            "middleware": ["authMiddleware"],
            "services": ["db", "jwt"]
        },
        "features": ["authentication", "item-management"]
    }


def _generate_readme(prompt: str, api_contract: Dict[str, Any], 
                     data_models: Dict[str, Any], project_structure: Dict[str, Any]) -> str:
    """Generate comprehensive README documentation."""
    
    app_name = project_structure.get("app_name", "my-app")
    description = project_structure.get("description", "Generated application")
    
    endpoints_doc = []
    for ep in api_contract.get("endpoints", []):
        auth_badge = "🔒" if ep.get("auth_required") else "🔓"
        endpoints_doc.append(f"- `{ep['method']} {ep['path']}` {auth_badge} - {ep.get('description', '')}")
    
    models_doc = []
    for model in data_models.get("models", []):
        fields = ", ".join([f["name"] for f in model.get("fields", [])])
        models_doc.append(f"- **{model['name']}**: {model.get('description', '')} ({fields})")
    
    return f"""# {app_name}

{description}

## Original Requirement

> {prompt}

## Project Structure

### Frontend (React + TypeScript + Vite)

- **Pages**: {', '.join(project_structure.get('frontend', {}).get('pages', []))}
- **Components**: {', '.join(project_structure.get('frontend', {}).get('components', []))}
- **Hooks**: {', '.join(project_structure.get('frontend', {}).get('hooks', []))}
- **Services**: {', '.join(project_structure.get('frontend', {}).get('services', []))}

### Backend (Node.js + Express + TypeScript)

- **Routes**: {', '.join(project_structure.get('backend', {}).get('routes', []))}
- **Controllers**: {', '.join(project_structure.get('backend', {}).get('controllers', []))}
- **Middleware**: {', '.join(project_structure.get('backend', {}).get('middleware', []))}

## API Endpoints

🔒 = Requires authentication | 🔓 = Public

{chr(10).join(endpoints_doc)}

## Data Models

{chr(10).join(models_doc)}

## Running Locally

### Backend
```bash
cd output/backend
npm install
npm run db:generate
npm run db:push
npm run dev
```

### Frontend
```bash
cd output/frontend
npm install
npm run dev
```

## API Contract

See [api-contract.json](api-contract.json) for the full API specification.
See [data-models.json](data-models.json) for data model definitions.
"""


def _generate_api_documentation(api_contract: Dict[str, Any]) -> str:
    """Generate detailed API documentation."""
    
    docs = ["# API Documentation\n"]
    docs.append(f"**Version**: {api_contract.get('api_version', '1.0.0')}\n")
    docs.append(f"**Base URL**: `{api_contract.get('base_url', '/api')}`\n\n")
    
    auth = api_contract.get("authentication", {})
    docs.append("## Authentication\n")
    docs.append(f"- **Type**: {auth.get('type', 'jwt')}")
    docs.append(f"- **Header**: `{auth.get('header', 'Authorization')}: {auth.get('prefix', 'Bearer')} <token>`\n\n")
    
    docs.append("## Endpoints\n")
    
    for ep in api_contract.get("endpoints", []):
        docs.append(f"### {ep.get('name', 'Unnamed')}\n")
        docs.append(f"**{ep['method']}** `{ep['path']}`\n")
        docs.append(f"{ep.get('description', '')}\n")
        
        if ep.get("auth_required"):
            docs.append("🔒 **Authentication required**\n")
        
        request = ep.get("request", {})
        if request.get("params"):
            docs.append("\n**URL Parameters**:")
            for name, type_ in request["params"].items():
                docs.append(f"- `{name}`: {type_}")
        
        if request.get("query"):
            docs.append("\n**Query Parameters**:")
            for name, type_ in request["query"].items():
                docs.append(f"- `{name}`: {type_}")
        
        if request.get("body"):
            docs.append("\n**Request Body**:")
            docs.append("```json")
            docs.append(json.dumps(request["body"], indent=2))
            docs.append("```")
        
        response = ep.get("response", {})
        if response.get("success"):
            success = response["success"]
            docs.append(f"\n**Success Response** ({success.get('status', 200)}):")
            docs.append("```json")
            docs.append(json.dumps(success.get("body", {}), indent=2))
            docs.append("```")
        
        if response.get("errors"):
            docs.append("\n**Error Responses**:")
            for err in response["errors"]:
                docs.append(f"- `{err.get('status', 400)}`: {err.get('message', '')}")
        
        docs.append("\n---\n")
    
    return "\n".join(docs)
