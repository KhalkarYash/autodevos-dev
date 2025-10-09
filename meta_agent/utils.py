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
