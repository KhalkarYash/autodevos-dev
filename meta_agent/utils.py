from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from rich.logging import RichHandler  # type: ignore
    RICH_AVAILABLE = True
except Exception:
    RICH_AVAILABLE = False


def setup_logger(name: str = "autodevos", level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(level)
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    if RICH_AVAILABLE:
        handler = RichHandler(rich_tracebacks=True, show_time=False)
        handler.setFormatter(fmt)
    else:
        handler = logging.StreamHandler()
        handler.setFormatter(fmt)
    logger.addHandler(handler)
    return logger


log = setup_logger()


def ensure_dir(path: os.PathLike | str) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def write_text(path: os.PathLike | str, content: str) -> None:
    p = Path(path)
    ensure_dir(p.parent)
    p.write_text(content, encoding="utf-8")
    log.debug(f"Wrote file: {p}")


def read_text(path: os.PathLike | str) -> str:
    return Path(path).read_text(encoding="utf-8")


def write_json(path: os.PathLike | str, data: Dict[str, Any], indent: int = 2) -> None:
    ensure_dir(Path(path).parent)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent)
    log.debug(f"Wrote JSON file: {path}")


def file_exists(path: os.PathLike | str) -> bool:
    return Path(path).exists()


def sha1(data: str) -> str:
    return hashlib.sha1(data.encode("utf-8")).hexdigest()


def env(name: str, default: Optional[str] = None) -> Optional[str]:
    return os.environ.get(name, default)


def merge_files(base_content: str, new_content: str, strategy: str = "append") -> str:
    """
    Merge two file contents using specified strategy.
    
    Args:
        base_content: Existing file content
        new_content: New content to merge
        strategy: Merge strategy - "append", "replace", or "smart"
    
    Returns:
        Merged content
    """
    if strategy == "replace":
        return new_content
    
    elif strategy == "append":
        if base_content and not base_content.endswith("\n"):
            return base_content + "\n" + new_content
        return base_content + new_content
    
    elif strategy == "smart":
        # Smart merge: detect duplicates and merge intelligently
        # For now, simple line-based deduplication
        base_lines = set(base_content.splitlines())
        new_lines = new_content.splitlines()
        
        merged_lines = list(base_content.splitlines())
        for line in new_lines:
            if line not in base_lines:
                merged_lines.append(line)
        
        return "\n".join(merged_lines)
    
    else:
        raise ValueError(f"Unknown merge strategy: {strategy}")


def detect_conflicts(base_content: str, new_content: str) -> list[str]:
    """
    Detect potential conflicts between base and new content.
    
    Returns:
        List of conflict descriptions
    """
    conflicts = []
    
    # Check for duplicate function/class definitions
    import re
    
    base_funcs = set(re.findall(r'(?:def|class)\s+(\w+)', base_content))
    new_funcs = set(re.findall(r'(?:def|class)\s+(\w+)', new_content))
    
    duplicates = base_funcs & new_funcs
    if duplicates:
        conflicts.append(f"Duplicate definitions: {', '.join(duplicates)}")
    
    return conflicts


def format_code(content: str, language: str = "python") -> str:
    """
    Format code using language-specific formatters.
    
    Args:
        content: Code content to format
        language: Programming language (python, typescript, etc.)
    
    Returns:
        Formatted code content
    """
    if language == "python":
        try:
            import black
            return black.format_str(content, mode=black.Mode())
        except ImportError:
            log.debug("black not installed, skipping formatting")
            return content
        except Exception as e:
            log.warning(f"Failed to format Python code: {e}")
            return content
    
    elif language in ("typescript", "javascript"):
        # TODO: Integrate with prettier or eslint
        log.debug(f"Formatting not yet implemented for {language}")
        return content
    
    else:
        return content


def validate_json_schema(data: Dict[str, Any], schema: Dict[str, Any]) -> tuple[bool, list[str]]:
    """
    Validate JSON data against a schema.
    
    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []
    
    # Simple validation - check required fields
    required = schema.get("required", [])
    for field in required:
        if field not in data:
            errors.append(f"Missing required field: {field}")
    
    # Check field types if specified
    properties = schema.get("properties", {})
    for field, field_schema in properties.items():
        if field in data:
            expected_type = field_schema.get("type")
            if expected_type:
                actual_value = data[field]
                type_map = {
                    "string": str,
                    "number": (int, float),
                    "integer": int,
                    "boolean": bool,
                    "array": list,
                    "object": dict,
                }
                expected_python_type = type_map.get(expected_type)
                if expected_python_type and not isinstance(actual_value, expected_python_type):
                    errors.append(f"Field '{field}' has incorrect type. Expected {expected_type}, got {type(actual_value).__name__}")
    
    return (len(errors) == 0, errors)
