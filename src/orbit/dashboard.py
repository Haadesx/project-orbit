# SPDX-License-Identifier: MIT
"""HTML dashboard generator — single-file command center."""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

TEMPLATE_HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Orbit · command center</title>
<meta http-equiv="refresh" content="60">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0c0f16;color:#d1d5db;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;font-size:13px;line-height:1.5;padding:20px 24px;min-height:100vh}
h1{font-size:16px;font-weight:600;letter-spacing:-.02em;color:#f3f4f6}
h2{font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.08em;color:#6b7280;margin-bottom:10px}
header{display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;flex-wrap:wrap;gap:8px}
header .r{display:flex;align-items:center;gap:10px;font-size:11px;color:#6b7280}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px;margin-bottom:16px}
.card{background:linear-gradient(135deg,#131620,#0f1219);border:1px solid #1f2330;border-radius:10px;padding:14px 16px}
.val{font-size:22px;font-weight:600;letter-spacing:-.04em;line-height:1.2;font-variant-numeric:tabular-nums}
.lbl{font-size:10px;color:#6b7280;margin-top:1px}
.tag{font-size:10px;color:#6b7280;background:#181c28;border:1px solid #1f2330;border-radius:5px;padding:2px 8px}
.proj{background:linear-gradient(135deg,#131620,#0f1219);border:1px solid #1f2330;border-radius:10px;padding:14px 16px;margin-bottom:8px}
.proj-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:6px}
.proj-name{font-weight:600;font-size:14px;color:#e5e7eb}
.proj-type{font-size:10px;color:#6b7280;background:#181c28;border:1px solid #1f2330;border-radius:4px;padding:1px 6px}
.proj-detail{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin:6px 0;font-size:11px;color:#9ca3af}
.proj-reason{font-size:10px;color:#f59e0b;padding:2px 0}
.score{font-size:20px;font-weight:700;text-align:right}
.score.critical{color:#ef4444}
.score.high{color:#f59e0b}
.score.medium{color:#3b82f6}
.score.low{color:#6b7280}
.status-dot{display:inline-block;width:6px;height:6px;border-radius:50%}
.status-dot.dirty{background:#f59e0b}
.status-dot.clean{background:#22c55e}
.status-dot.unknown{background:#6b7280}
footer{font-size:10px;color:#374151;text-align:center;padding-top:10px;border-top:1px solid #161a24;margin-top:16px}
@media(max-width:600px){body{padding:12px}.proj-detail{grid-template-columns:1fr 1fr}}
</style>
</head>
<body>
"""

TEMPLATE_TAIL = """</body></html>"""


def generate_dashboard(priority: list[dict], state: dict, output_path: Optional[Path] = None) -> str:
    """Generate a self-contained HTML dashboard from scan state + priority.

    Args:
        priority: Output from prioritize().
        state: Raw scan state from scan_projects().
        output_path: Where to write the HTML file.

    Returns:
        The HTML string.
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    proj_count = state.get("project_count", 0)

    # Count states
    critical = [p for p in priority if p["priority_label"] == "critical"]
    high = [p for p in priority if p["priority_label"] == "high"]
    medium = [p for p in priority if p["priority_label"] == "medium"]
    low = [p for p in priority if p["priority_label"] == "low"]

    html = TEMPLATE_HEAD
    html += f"""<header>
<div><h1>Orbit</h1><div class="tag" style="margin-top:2px">{proj_count} projects · {now}</div></div>
<div class="r"></div>
</header>

<div class="grid">
<div class="card"><div class="val" style="color:#ef4444">{len(critical)}</div><div class="lbl">critical</div></div>
<div class="card"><div class="val" style="color:#f59e0b">{len(high)}</div><div class="lbl">high</div></div>
<div class="card"><div class="val" style="color:#3b82f6">{len(medium)}</div><div class="lbl">medium</div></div>
<div class="card"><div class="val" style="color:#6b7280">{len(low)}</div><div class="lbl">low</div></div>
</div>
"""

    for p in priority:
        name = p["name"]
        label = p["priority_label"]
        score = p["priority_score"]
        proj_type = p["type"]
        git = p.get("git", {})
        files = p.get("files", {})
        reasons = p.get("reasons", [])

        dirty_dot = ""
        if git.get("has_git"):
            dirty_dot = '<span class="status-dot dirty" title="uncommitted changes"></span>' if git.get("dirty") else '<span class="status-dot clean" title="clean"></span>'

        # Project details
        days_since = git.get("days_since_commit", "?")
        total_files = files.get("total_files", "?")
        size_kb = files.get("size_kb", "?")

        reasons_html = ""
        if reasons:
            reasons_html = '<div class="proj-reason">' + " · ".join(reasons[:3]) + "</div>"

        html += f"""<div class="proj">
<div class="proj-header">
<div><span class="proj-name">{dirty_dot}&nbsp;{name}</span> <span class="proj-type">{proj_type}</span></div>
<div class="score {label}">{score}</div>
</div>
<div class="proj-detail">
<div>{total_files} files</div>
<div>{size_kb} KB</div>
<div>{days_since}d since commit</div>
</div>
{reasons_html}
</div>
"""

    if proj_count == 0:
        html += '<p style="color:#6b7280;text-align:center;padding:40px">No projects found. Run <code>orbit init</code> first.</p>'

    html += f"<footer>Project Orbit · {now} · refresh every 60s</footer>"
    html += TEMPLATE_TAIL

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html)

    return html
