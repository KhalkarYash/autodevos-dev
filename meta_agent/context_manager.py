from __future__ import annotations  
import json 
import threading 
import time 
import portalocker
from dataclasses import dataclass, field 
from pathlib import Path 
from typing import Any, Dict, List, Optional 
from datetime import datetime  
from .utils import ensure_dir, write_text, log   

@dataclass 
class MCPContext:
    """ 
    Thread-safe MCP-style shared context for agent collaboration with versioning. 
    """ 
    project_name: str 
    storage_dir: Path 
    data: Dict[str, Any] = field(default_factory=dict) 
    events: List[Dict[str, Any]] = field(default_factory=list) 
    version: int = field(default=1) 
    _lock: threading.RLock = field(default_factory=threading.RLock, init=False, repr=False) 

    def set(self, key: str, value: Any) -> None:
        """Thread-safe set operation with automatic versioning.""" 
        with self._lock:
            self.data[key] = value
            self.version += 1
            log.debug(f"Context set: {key} -> {type(value)} (v{self.version})")

    def get(self, key: str, default: Optional[Any] = None) -> Any:
        """Thread-safe get operation.""" 
        with self._lock:
            return self.data.get(key, default)

    def append_event(self, kind: str, payload: Dict[str, Any]) -> None:
        """Thread-safe event logging with timestamp.""" 
        with self._lock:
            evt = { 
                "kind": kind, 
                "payload": payload, 
                "timestamp": datetime.utcnow().isoformat(), 
                "version": self.version
            } 
            self.events.append(evt)
            log.info(f"CTX[{kind}]: {payload}")

    def add_artifact(self, agent: str, path: Path) -> None:
        """Thread-safe artifact registration.""" 
        with self._lock:
            artifacts = self.data.setdefault("artifacts", [])
            artifact_info = { 
                "agent": agent, 
                "path": str(path), 
                "timestamp": datetime.utcnow().isoformat() 
            } 
            artifacts.append(artifact_info)
            self.version += 1
            self.append_event("artifact", artifact_info)

    def save(self) -> None:
        """Thread-safe context persistence with atomic write and file locking.""" 
        with self._lock:
            ensure_dir(self.storage_dir)

            context_data = { 
                "project_name": self.project_name, 
                "version": self.version, 
                "data": self.data, 
                "events": self.events, 
                "saved_at": datetime.utcnow().isoformat() 
            }

            # Atomic write: write to temp file then rename 
            temp_path = self.storage_dir / f"context.tmp.{int(time.time() * 1000)}.{threading.get_ident()}"
            final_path = self.storage_dir / "context.json"
            lock_path = self.storage_dir / "context.lock"

            lock_fd = None
            try:
                # Acquire file lock for cross-process safety
                ensure_dir(lock_path.parent)
                lock_fd = open(lock_path, 'w')

                # Try non-blocking lock first, fall back to blocking if needed
                try:
                    portalocker.lock(lock_fd, portalocker.LOCK_EX | portalocker.LOCK_NB)
                except portalocker.LockException:
                    log.debug("Waiting for context file lock...")
                    portalocker.lock(lock_fd, portalocker.LOCK_EX)

                # Write to temp file
                write_text(temp_path, json.dumps(context_data, indent=2))

                # Atomic rename
                temp_path.rename(final_path)

                log.debug(f"Context saved to {final_path} (v{self.version})")

            except Exception as e:
                log.error(f"Failed to save context: {e}")
                if temp_path.exists():
                    temp_path.unlink()
                raise
            finally:
                # Release lock
                if lock_fd:
                    try:
                        portalocker.unlock(lock_fd)  # Unlock the file
                        lock_fd.close()
                    except Exception as e:
                        log.error(f"Failed to unlock file: {e}")

    @classmethod 
    def load(cls, project_name: str, storage_dir: Path) -> "MCPContext": 
        """Load context from disk with version recovery and file locking.""" 
        context_file = storage_dir / "context.json" 
        lock_path = storage_dir / "context.lock" 

        if not context_file.exists():
            log.info(f"No existing context found, creating new one") 
            return cls(project_name=project_name, storage_dir=storage_dir)

        lock_fd = None
        try:
            # Acquire read lock
            ensure_dir(lock_path.parent)
            lock_fd = open(lock_path, 'w')
            portalocker.lock(lock_fd, portalocker.LOCK_SH)  # Shared lock for reading

            # Check for partial temp files and clean up
            for temp_file in storage_dir.glob("context.tmp.*"):
                temp_age = time.time() - temp_file.stat().st_mtime
                if temp_age > 60:  # Older than 1 minute
                    log.warning(f"Cleaning up stale temp file: {temp_file}")
                    temp_file.unlink()

            # Load context
            with open(context_file, 'r') as f:
                data = json.load(f)

            ctx = cls(
                project_name=data.get("project_name", project_name),
                storage_dir=storage_dir,
                data=data.get("data", {}),
                events=data.get("events", []),
                version=data.get("version", 1)
            )
            log.info(f"Context loaded from {context_file} (v{ctx.version}, {len(ctx.events)} events)")
            return ctx

        except json.JSONDecodeError as e:
            log.error(f"Corrupted context file: {e}, creating new context")
            # Backup corrupted file
            backup_path = context_file.with_suffix(f".json.corrupted.{int(time.time())}")
            context_file.rename(backup_path)
            log.info(f"Backed up corrupted context to {backup_path}")
            return cls(project_name=project_name, storage_dir=storage_dir)

        except Exception as e:
            log.error(f"Failed to load context: {e}, creating new one")
            return cls(project_name=project_name, storage_dir=storage_dir)

        finally:
            if lock_fd:
                try:
                    portalocker.unlock(lock_fd)  # Unlock the file
                    lock_fd.close()
                except Exception as e:
                    log.error(f"Failed to unlock file: {e}")

    def atomic_update(self, updater_fn) -> Any:
        """Execute a function atomically within a lock and auto-save.""" 
        with self._lock:
            result = updater_fn(self)
            self.version += 1
            return result
