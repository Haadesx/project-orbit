# SPDX-License-Identifier: MIT
"""Generic project scanner — discovers and inventories projects."""

import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def _git_info(project_path: Path) -> dict:
    """Get git status for a project."""
    info = {"has_git": False}
    git_dir = project_path / ".git"
    if not git_dir.exists():
        return info

    info["has_git"] = True

    try:
        r = subprocess.run(
            ["git", "log", "--oneline", "-1", "--format=%h %s %ar"],
            capture_output=True, text=True, timeout=5,
            cwd=str(project_path),
        )
        if r.returncode == 0 and r.stdout.strip():
            info["last_commit"] = r.stdout.strip()
            # Extract timestamp
            r2 = subprocess.run(
                ["git", "log", "-1", "--format=%at"],
                capture_output=True, text=True, timeout=5,
                cwd=str(project_path),
            )
            if r2.returncode == 0 and r2.stdout.strip():
                ts = int(r2.stdout.strip())
                info["last_commit_utc"] = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
                info["days_since_commit"] = (datetime.now(timezone.utc) - datetime.fromtimestamp(ts, tz=timezone.utc)).days
    except (subprocess.TimeoutExpired, OSError):
        pass

    # Check for uncommitted changes
    try:
        r = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, timeout=5,
            cwd=str(project_path),
        )
        if r.returncode == 0:
            dirty = [line for line in r.stdout.split("\n") if line.strip()]
            info["uncommitted_files"] = len(dirty)
            info["dirty"] = len(dirty) > 0
    except (subprocess.TimeoutExpired, OSError):
        pass

    # Count branches
    try:
        r = subprocess.run(
            ["git", "branch", "--list"],
            capture_output=True, text=True, timeout=5,
            cwd=str(project_path),
        )
        if r.returncode == 0:
            branches = [b.strip() for b in r.stdout.split("\n") if b.strip()]
            info["branches"] = len(branches)
    except (subprocess.TimeoutExpired, OSError):
        pass

    return info


def _project_type(path: Path) -> str:
    """Detect project type from files present."""
    files = {f.name for f in path.iterdir() if f.is_file()}

    if "pyproject.toml" in files or "setup.py" in files or "setup.cfg" in files:
        return "Python"
    if "package.json" in files:
        return "Node.js"
    if "go.mod" in files or "go.sum" in files:
        return "Go"
    if "Cargo.toml" in files:
        return "Rust"
    if "Gemfile" in files or "*.gemspec" in files:
        return "Ruby"
    if "Makefile" in files or "CMakeLists.txt" in files:
        return "C/C++"
    if "composer.json" in files:
        return "PHP"
    if "Project.swift" in files or "Package.swift" in files:
        return "Swift"
    if path.suffix == ".sln" or any(f.endswith(".csproj") for f in files):
        return "C#"
    if "Dockerfile" in files:
        return "Docker"
    if any(f.endswith(".md") for f in files):
        return "Documentation"

    # Check for Python files
    py_files = list(path.glob("*.py"))
    if py_files:
        return "Python"
    js_files = list(path.glob("*.js")) or list(path.glob("*.ts"))
    if js_files:
        return "JavaScript"

    return "Unknown"


def _file_stats(project_path: Path, ignore_patterns: list) -> dict:
    """Count files by type, efficiently."""
    stats = {"total_files": 0, "by_type": {}, "size_kb": 0}
    ignore_set = set(ignore_patterns)

    try:
        for f in project_path.rglob("*"):
            if f.is_file():
                # Check ignore patterns
                rel = f.relative_to(project_path)
                parts = set(rel.parts)
                if parts & ignore_set:
                    continue
                if any(p.startswith(".") for p in rel.parts[:-1]):
                    continue

                stats["total_files"] += 1
                ext = f.suffix or "(no ext)"
                stats["by_type"][ext] = stats["by_type"].get(ext, 0) + 1
                stats["size_kb"] += f.stat().st_size // 1024
    except (PermissionError, OSError):
        pass

    # Limit to avoid memorization
    stats["total_files"] = min(stats["total_files"], 10000)
    return stats


def _find_projects(root_dir: Path, ignore_patterns: list, max_depth: int = 3) -> list[Path]:
    """Find project roots by looking for common markers."""
    markers = {
        ".git", "pyproject.toml", "setup.py", "setup.cfg", "package.json",
        "go.mod", "Cargo.toml", "requirements.txt", "Gemfile",
        "Makefile", "CMakeLists.txt", "composer.json", "Dockerfile",
    }
    projects = []
    ignore_set = set(ignore_patterns)

    try:
        for depth in range(max_depth + 1):
            if depth == 0:
                dirs = [root_dir]
            else:
                # Walk to this depth
                if depth == 1:
                    dirs = [d for d in root_dir.iterdir() if d.is_dir() and d.name not in ignore_set and not d.name.startswith(".")]
                else:
                    continue  # For now, only scan 1 level deep

            for d in dirs:
                if d.name in ignore_set or d.name.startswith("."):
                    continue
                try:
                    contents = {f.name for f in d.iterdir() if f.is_file()}
                    if contents & markers:
                        projects.append(d)
                    elif any(f.suffix == ".py" for f in d.iterdir()):
                        # Python files without project markers — still count as a project
                        projects.append(d)
                except (PermissionError, OSError):
                    pass
    except (PermissionError, OSError):
        pass

    return projects


def scan_projects(projects_dir: str, ignore_patterns: Optional[list] = None, max_depth: int = 3) -> dict:
    """Scan all projects in a directory and return their state.

    Args:
        projects_dir: Root directory to scan for projects.
        ignore_patterns: Directory/file patterns to ignore.
        max_depth: How deep to search for project roots.

    Returns:
        Dict with timestamp and per-project state.
    """
    if ignore_patterns is None:
        ignore_patterns = ["node_modules", "__pycache__", ".git", ".venv", "venv"]

    root = Path(projects_dir).resolve()
    if not root.exists():
        return {"error": f"Directory not found: {root}", "projects": {}}

    project_dirs = _find_projects(root, ignore_patterns, max_depth)
    results = {}

    for proj in sorted(project_dirs):
        name = proj.name
        info = {
            "path": str(proj),
            "type": _project_type(proj),
            "git": _git_info(proj),
            "files": _file_stats(proj, ignore_patterns),
            "scanned_at": datetime.now(timezone.utc).isoformat(),
        }

        # Last modified time of most recent file
        try:
            latest = max(
                (f.stat().st_mtime for f in proj.rglob("*") if f.is_file()),
                default=0,
            )
            info["last_modified_utc"] = datetime.fromtimestamp(latest, tz=timezone.utc).isoformat()
            info["days_since_modified"] = (datetime.now(timezone.utc) - datetime.fromtimestamp(latest, tz=timezone.utc)).days
        except (OSError, ValueError):
            pass

        results[name] = info

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "projects_dir": str(root),
        "project_count": len(results),
        "projects": results,
    }
