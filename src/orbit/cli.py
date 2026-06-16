# SPDX-License-Identifier: MIT
"""CLI entry point for Project Orbit."""

import argparse
import json
import sys
import webbrowser
from pathlib import Path

from . import __version__
from .config import load_config, init_config
from .scanner import scan_projects
from .priority import prioritize
from .dashboard import generate_dashboard

STATE_FILE = ".orbit_state.json"
DASHBOARD_FILE = "orbit_dashboard.html"


def main():
    parser = argparse.ArgumentParser(
        prog="orbit",
        description="Project Orbit — local-first project convergence layer",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # init
    p_init = sub.add_parser("init", help="Create orbit.json in current directory")
    p_init.add_argument("--dir", type=Path, default=Path.cwd(), help="Target directory")

    # scan
    p_scan = sub.add_parser("scan", help="Scan all projects")
    p_scan.add_argument("--json", action="store_true", help="Output raw JSON")
    p_scan.add_argument("--output", type=Path, help="Write state JSON to file")

    # priority
    p_pri = sub.add_parser("priority", help="Calculate priority queue")
    p_pri.add_argument("--json", action="store_true", help="Output raw JSON")
    p_pri.add_argument("--top", type=int, default=5, help="Show top N projects")

    # dashboard
    p_dash = sub.add_parser("dashboard", help="Generate HTML command center")
    p_dash.add_argument("--open", action="store_true", help="Open in browser")
    p_dash.add_argument("--output", type=Path, default=Path(DASHBOARD_FILE), help="Output path")

    # status
    p_st = sub.add_parser("status", help="Quick summary of all projects")

    # run (full cycle)
    p_run = sub.add_parser("run", help="Full allocator cycle (scan → priority → dashboard)")
    p_run.add_argument("--open", action="store_true", help="Open dashboard after run")

    args = parser.parse_args()

    if args.command == "init":
        return cmd_init(args)
    elif args.command == "scan":
        return cmd_scan(args)
    elif args.command == "priority":
        return cmd_priority(args)
    elif args.command == "dashboard":
        return cmd_dashboard(args)
    elif args.command == "status":
        return cmd_status(args)
    elif args.command == "run":
        return cmd_run(args)


def _get_state(config: dict) -> dict:
    """Run scan and return state dict."""
    projects_dir = config.get("projects_dir", ".")
    ignore = config.get("ignore_patterns", [])
    return scan_projects(projects_dir, ignore)


def _save_state(state: dict):
    """Persist state to JSON."""
    try:
        Path(STATE_FILE).write_text(json.dumps(state, indent=2, default=str))
    except OSError:
        pass


def cmd_init(args):
    path = init_config(args.dir)
    print(f"Orbit initialized at {path}")
    return 0


def cmd_scan(args):
    config = load_config()
    state = _get_state(config)
    _save_state(state)

    if args.output:
        args.output.write_text(json.dumps(state, indent=2, default=str))

    if args.json:
        print(json.dumps(state, indent=2, default=str))
        return 0

    count = state.get("project_count", 0)
    projects = state.get("projects", {})

    print(f"Scanned {count} project{'s' if count != 1 else ''}:")
    for name, info in sorted(projects.items()):
        files = info.get("files", {})
        total = files.get("total_files", "?")
        ptype = info.get("type", "?")
        git = info.get("git", {})
        dirty = " ⚡" if git.get("dirty") else ""
        days = git.get("days_since_commit")
        age = f" · {days}d stale" if days and days > 7 else ""
        print(f"  {'✓' if not git.get('dirty') else '⚡'} {name} ({ptype}, {total} files{age}){dirty}")

    return 0


def cmd_priority(args):
    config = load_config()

    # Try cached state first
    state = None
    if Path(STATE_FILE).exists():
        try:
            state = json.loads(Path(STATE_FILE).read_text())
        except: pass

    if not state or not state.get("projects"):
        state = _get_state(config)
        _save_state(state)

    staleness = config.get("staleness_days", 7)
    priority = prioritize(state, staleness)

    if args.json:
        print(json.dumps(priority, indent=2, default=str))
        return 0

    print(f"Priority Queue ({len(priority)} projects):")
    print()
    for p in priority[:args.top]:
        label = p["priority_label"]
        score = p["priority_score"]
        reasons = p.get("reasons", [])
        reason_str = " — " + ", ".join(reasons[:2]) if reasons else ""
        print(f"  {score:3d}/100 [{label:8s}] {p['name']}{reason_str}")

    print()
    if priority:
        top = priority[0]
        print(f"Next action: {top['name']} ({top['priority_score']}/100, {top['priority_label']})")
        if top.get("reasons"):
            print(f"  Why: {'; '.join(top['reasons'][:3])}")
    else:
        print("No projects need attention.")

    return 0


def cmd_dashboard(args):
    config = load_config()

    # Try to load cached state first
    state = None
    if Path(STATE_FILE).exists():
        try:
            state = json.loads(Path(STATE_FILE).read_text())
        except: pass

    if not state or not state.get("projects"):
        state = _get_state(config)
        _save_state(state)

    staleness = config.get("staleness_days", 7)
    priority = prioritize(state, staleness)

    output = args.output
    generate_dashboard(priority, state, output)
    print(f"Dashboard written to {output} ({len(priority)} projects)")

    if args.open:
        webbrowser.open(str(output.absolute()))

    return 0


def cmd_status(args):
    config = load_config()

    # Try cached state first
    state = None
    if Path(STATE_FILE).exists():
        try:
            state = json.loads(Path(STATE_FILE).read_text())
        except: pass

    if not state or not state.get("projects"):
        state = _get_state(config)
        _save_state(state)

    projects = state.get("projects", {})
    print(f"Project Orbit — {state.get('project_count', 0)} projects in {state.get('projects_dir', '.')}")
    print()

    for name, info in sorted(projects.items()):
        ptype = info.get("type", "?")
        git = info.get("git", {})
        files = info.get("files", {})
        dirty = "⚡" if git.get("dirty") else "✓"
        days = git.get("days_since_commit", "?")
        print(f"  {dirty} {name:30s} {ptype:15s} {files.get('total_files', 0):>4d} files · {days}d since commit")

    return 0


def cmd_run(args):
    """Full allocator cycle."""
    config = load_config()
    state = _get_state(config)
    _save_state(state)

    staleness = config.get("staleness_days", 7)
    priority = prioritize(state, staleness)

    # Generate dashboard
    output = Path(DASHBOARD_FILE)
    generate_dashboard(priority, state, output)

    if args.open:
        webbrowser.open(str(output.absolute()))

    # Print summary
    top = priority[0] if priority else None
    critical = [p for p in priority if p["priority_label"] == "critical"]
    high = [p for p in priority if p["priority_label"] == "high"]

    print(f"Orbit cycle complete — {state.get('project_count', 0)} projects")
    print(f"  {len(critical)} critical · {len(high)} high · {output}")
    if top:
        print(f"  Top: {top['name']} ({top['priority_score']}/100)")
        if top.get("reasons"):
            print(f"  Why: {'; '.join(top['reasons'][:3])}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
