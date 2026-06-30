"""
Log Follower Agent – tracks all agent activities and writes execution logs.
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import config

# Module-level list of log entries (thread-safe with lock)
_entries: list[dict] = []
_lock = threading.Lock()
_file_logger = logging.getLogger("execution")


def _setup_file_logger() -> None:
    if _file_logger.handlers:
        return
    _file_logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler(config.LOG_FILE, mode="w", encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-8s | %(message)s"))
    _file_logger.addHandler(fh)


_setup_file_logger()


class LogFollowerAgent:
    """
    Centralised logging agent.
    All other agents call `log()` to record their actions.
    """

    def log(
        self,
        agent_name: str,
        action: str,
        input_summary: str = "",
        output_summary: str = "",
        error: Optional[str] = None,
        retry: int = 0,
        node_info: Optional[dict] = None,
    ) -> None:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": agent_name,
            "action": action,
            "input": input_summary,
            "output": output_summary,
            "error": error,
            "retry": retry,
            "node": node_info,
        }
        with _lock:
            _entries.append(entry)

        level = logging.ERROR if error else logging.INFO
        msg = (
            f"[{agent_name}] {action}"
            + (f" | in: {input_summary[:120]}" if input_summary else "")
            + (f" | out: {output_summary[:120]}" if output_summary else "")
            + (f" | ERR: {error}" if error else "")
        )
        _file_logger.log(level, msg)

    def save(self) -> None:
        """Flush log entries to execution_log.json."""
        config.OUTPUT_DIR.mkdir(exist_ok=True)
        with _lock:
            snapshot = list(_entries)
        config.LOG_JSON.write_text(
            json.dumps(snapshot, indent=2, default=str),
            encoding="utf-8",
        )
        _file_logger.info("Execution log saved (%d entries)", len(snapshot))

    def summary(self) -> dict:
        with _lock:
            snapshot = list(_entries)
        errors = [e for e in snapshot if e.get("error")]
        agents = list({e["agent"] for e in snapshot})
        return {
            "total_events": len(snapshot),
            "errors": len(errors),
            "agents_active": agents,
        }
