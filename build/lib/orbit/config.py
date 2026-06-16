# SPDX-License-Identifier: MIT
"""Configuration handling for Project Orbit."""

import json
import os
from pathlib import Path
from typing import Optional

DEFAULT_CONFIG = {
    "projects_dir": ".",
    "ignore_patterns": [
        "node_modules", "__pycache__", ".git", ".venv", "venv",
        ".egg-info", "dist", "build", ".DS_Store", "*.pyc",
    ],
    "staleness_days": 7,
    "max_depth": 3,
    "bridges": {
        "git_health": True,
        "staleness_alerts": True,
    },
    "hooks": {},
}

CONFIG_FILENAME = "orbit.json"


def find_config(start_dir: Optional[Path] = None) -> Optional[Path]:
    """Walk up from start_dir looking for orbit.json."""
    if start_dir is None:
        start_dir = Path.cwd()
    for parent in [start_dir] + list(start_dir.parents):
        candidate = parent / CONFIG_FILENAME
        if candidate.exists():
            return candidate
    return None


def load_config(config_path: Optional[Path] = None) -> dict:
    """Load orbit.json, merging with defaults."""
    config = dict(DEFAULT_CONFIG)

    if config_path is None:
        config_path = find_config()

    if config_path and config_path.exists():
        try:
            user_config = json.loads(config_path.read_text())
            config.update(user_config)
        except (json.JSONDecodeError, OSError):
            pass

    # Resolve projects_dir relative to config location
    if config_path:
        config_dir = config_path.parent.resolve()
        projects_dir = config.get("projects_dir", ".")
        # If relative, resolve against config dir
        if not os.path.isabs(projects_dir):
            config["projects_dir"] = str((config_dir / projects_dir).resolve())
        config["_config_path"] = str(config_path)

    return config


def init_config(target_dir: Optional[Path] = None) -> Path:
    """Create a default orbit.json in the target directory."""
    if target_dir is None:
        target_dir = Path.cwd()

    config_path = target_dir / CONFIG_FILENAME
    if config_path.exists():
        return config_path

    config = dict(DEFAULT_CONFIG)
    config["projects_dir"] = str(target_dir.resolve())
    config_path.write_text(json.dumps(config, indent=2) + "\n")
    return config_path
