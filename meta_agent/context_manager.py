from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .utils import ensure_dir, write_text, log


@dataclass
class MCPContext:
    """
    Minimal simulation of MCP-style shared context for agent collaboration.
    """
    project_name: str
    storage_dir: Path
    data: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value
        log.debug(f"Context set: {key} -> {type(value)}")

    def get(self, key: str, default: Optional[Any] = None) -> Any:
        return self.data.get(key, default)

    def append_event(self, kind: str, payload: Dict[str, Any]) -> None:
        evt = {"kind": kind, "payload": payload}
        self.events.append(evt)
        log.info(f"CTX[{kind}]: {payload}")

    def add_artifact(self, agent: str, path: Path) -> None:
        artifacts = self.data.setdefault("artifacts", [])
        artifacts.append({"agent": agent, "path": str(path)})
        self.append_event("artifact", {"agent": agent, "path": str(path)})

    def save(self) -> None:
        ensure_dir(self.storage_dir)
        write_text(self.storage_dir / "context.json", json.dumps({
            "project_name": self.project_name,
            "data": self.data,
            "events": self.events,
        }, indent=2))
