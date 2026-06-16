# SPDX-License-Identifier: MIT
"""Interactive HTML dashboard — single-file, zero deps, rich project explorer."""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional


def generate_dashboard(priority: list[dict], state: dict, output_path: Optional[Path] = None) -> str:
    """Generate an interactive self-contained HTML dashboard."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    projects = state.get("projects", {})
    proj_count = state.get("project_count", 0)

    # Build project data as JSON blob for JS
    proj_data = []
    for p in priority:
        name = p["name"]
        info = projects.get(name, {})
        git = p.get("git", {}) or info.get("git", {})
        files = p.get("files", {}) or info.get("files", {})

        proj_data.append({
            "name": name,
            "type": p.get("type", info.get("type", "?")),
            "path": p.get("path", info.get("path", "")),
            "score": p["priority_score"],
            "label": p["priority_label"],
            "reasons": p.get("reasons", []),
            "days_since_commit": git.get("days_since_commit"),
            "last_commit": git.get("last_commit", ""),
            "dirty": git.get("dirty", False),
            "uncommitted": git.get("uncommitted_files", 0),
            "branches": git.get("branches", 0),
            "total_files": files.get("total_files", 0),
            "size_kb": files.get("size_kb", 0),
            "by_type": files.get("by_type", {}),
            "days_since_modified": info.get("days_since_modified"),
        })

    data_json = json.dumps(proj_data)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Orbit · project explorer</title>
<style>
:root {{
  --bg: #0a0c10;
  --surface: #111318;
  --border: #1e2028;
  --text: #c8ccd4;
  --text-dim: #6b7084;
  --text-bright: #e8ecf4;
  --accent: #4f8cff;
  --critical: #f54336;
  --high: #f9a825;
  --medium: #4f8cff;
  --low: #6b7084;
  --green: #34a853;
  --red: #ea4335;
  --radius: 10px;
}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,'SF Pro Display','Segoe UI',system-ui,sans-serif;font-size:14px;line-height:1.5;min-height:100vh;overflow-x:hidden}}
::selection{{background:rgba(79,140,255,0.2)}}

/* ── Layout ── */
.app{{display:grid;grid-template-columns:280px 1fr;min-height:100vh}}
@media(max-width:800px){{.app{{grid-template-columns:1fr}}}}

/* ── Sidebar ── */
.sidebar{{background:var(--surface);border-right:1px solid var(--border);padding:24px 20px;display:flex;flex-direction:column;gap:20px}}
.sidebar h1{{font-size:15px;font-weight:600;color:var(--text-bright);letter-spacing:-.02em}}
.sidebar h1 span{{color:var(--accent)}}
.sidebar .meta{{font-size:11px;color:var(--text-dim);line-height:1.6}}
.stat-group{{display:grid;grid-template-columns:1fr 1fr;gap:8px}}
.stat{{background:var(--bg);border-radius:8px;padding:10px 12px}}
.stat .num{{font-size:18px;font-weight:600;color:var(--text-bright);font-variant-numeric:tabular-nums}}
.stat .lbl{{font-size:10px;color:var(--text-dim);text-transform:uppercase;letter-spacing:.04em;margin-top:1px}}
.stat .num.critical{{color:var(--critical)}}
.stat .num.high{{color:var(--high)}}
.stat .num.medium{{color:var(--medium)}}
.filter-group{{display:flex;flex-direction:column;gap:4px}}
.filter-btn{{background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:7px 12px;font-size:12px;color:var(--text-dim);cursor:pointer;text-align:left;transition:all .15s}}
.filter-btn:hover{{border-color:var(--accent);color:var(--text-bright)}}
.filter-btn.active{{border-color:var(--accent);color:var(--accent);font-weight:500}}
.filter-btn .count{{float:right;opacity:.5}}

/* ── Main ── */
.main{{padding:24px 28px;max-width:1100px}}
.main-header{{display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;flex-wrap:wrap;gap:10px}}
.search-box{{background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:8px 14px;font-size:13px;color:var(--text-bright);width:260px;outline:none;transition:border-color .15s}}
.search-box:focus{{border-color:var(--accent)}}
.search-box::placeholder{{color:var(--text-dim)}}
.proj-count{{font-size:12px;color:var(--text-dim)}}

/* ── Project Cards ── */
.proj-list{{display:flex;flex-direction:column;gap:8px}}
.proj{{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);overflow:hidden;cursor:pointer;transition:border-color .15s}}
.proj:hover{{border-color:var(--accent)}}
.proj-header{{display:flex;align-items:center;padding:14px 18px;gap:12px}}
.proj-score{{width:40px;height:40px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:15px;font-weight:700;flex-shrink:0}}
.proj-score.critical{{background:rgba(245,67,54,0.12);color:var(--critical)}}
.proj-score.high{{background:rgba(249,168,37,0.12);color:var(--high)}}
.proj-score.medium{{background:rgba(79,140,255,0.12);color:var(--medium)}}
.proj-score.low{{background:rgba(107,112,132,0.12);color:var(--low)}}
.proj-info{{flex:1;min-width:0}}
.proj-name{{font-size:14px;font-weight:600;color:var(--text-bright);display:flex;align-items:center;gap:6px}}
.proj-meta{{font-size:11px;color:var(--text-dim);margin-top:2px;display:flex;gap:10px;flex-wrap:wrap}}
.proj-meta span{{display:inline-flex;align-items:center;gap:3px}}
.proj-type-badge{{font-size:9px;padding:1px 6px;border-radius:4px;background:var(--bg);color:var(--text-dim);text-transform:uppercase;letter-spacing:.04em}}
.dirty-dot{{width:6px;height:6px;border-radius:50%;display:inline-block;flex-shrink:0}}
.dirty-dot.yes{{background:var(--high)}}
.dirty-dot.no{{background:var(--green)}}
.proj-arrow{{color:var(--text-dim);font-size:16px;transition:transform .2s}}
.proj-arrow.open{{transform:rotate(90deg)}}

/* ── Expanded Details ── */
.proj-detail{{max-height:0;overflow:hidden;transition:max-height .3s ease}}
.proj-detail.open{{max-height:600px}}
.proj-detail-inner{{padding:0 18px 16px;border-top:1px solid var(--border);margin:0 18px 0 68px;padding-top:12px}}
.detail-grid{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:10px}}
.detail-item{{font-size:11px}}
.detail-item .dlbl{{color:var(--text-dim);font-size:10px;text-transform:uppercase;letter-spacing:.04em}}
.detail-item .dval{{color:var(--text-bright);font-weight:500}}
.detail-item .dval.dirty{{color:var(--high)}}
.detail-item .dval.clean{{color:var(--green)}}
.reason-list{{display:flex;flex-wrap:wrap;gap:4px;margin-bottom:10px}}
.reason-tag{{font-size:10px;padding:2px 8px;border-radius:4px;background:rgba(249,168,37,0.1);color:var(--high);border:1px solid rgba(249,168,37,0.15)}}
.file-bars{{display:grid;grid-template-columns:1fr 1fr;gap:4px;margin-top:6px}}
.file-bar{{font-size:10px;display:flex;align-items:center;gap:6px}}
.file-bar .bar-fill{{height:6px;border-radius:3px;background:var(--accent);min-width:2px;flex-shrink:0}}
.file-bar .bar-label{{color:var(--text-dim);white-space:nowrap;min-width:30px}}
.file-bar .bar-count{{color:var(--text-bright);font-weight:500}}

/* ── Empty ── */
.empty{{text-align:center;padding:60px 20px;color:var(--text-dim)}}
.empty h3{{font-size:16px;margin-bottom:4px;color:var(--text-bright)}}
</style>
</head>
<body>
<div class="app">
<aside class="sidebar">
<div><h1>Orbit<span>.</span></h1><div class="meta">{now} · {proj_count} projects</div></div>

<div class="stat-group" id="stats">
<div class="stat"><div class="num critical" id="cnt-critical">0</div><div class="lbl">critical</div></div>
<div class="stat"><div class="num high" id="cnt-high">0</div><div class="lbl">high</div></div>
<div class="stat"><div class="num medium" id="cnt-medium">0</div><div class="lbl">medium</div></div>
<div class="stat"><div class="num low" id="cnt-low">0</div><div class="lbl">low</div></div>
</div>

<div class="filter-group">
<button class="filter-btn active" data-filter="all">All projects <span class="count" id="f-all">0</span></button>
<button class="filter-btn" data-filter="critical">Critical <span class="count" id="f-critical">0</span></button>
<button class="filter-btn" data-filter="high">High <span class="count" id="f-high">0</span></button>
<button class="filter-btn" data-filter="medium">Medium <span class="count" id="f-medium">0</span></button>
<button class="filter-btn" data-filter="low">Low <span class="count" id="f-low">0</span></button>
</div>

<div class="meta" style="font-size:10px;margin-top:auto;padding-top:10px;border-top:1px solid var(--border)">
  Click a project to expand details.<br>
  j/k to navigate · enter to toggle
</div>
</aside>

<main class="main">
<div class="main-header">
<input class="search-box" id="search" placeholder="Search projects..." autofocus>
<span class="proj-count" id="visible-count">Showing {proj_count}</span>
</div>
<div class="proj-list" id="proj-list"></div>
<div class="empty" id="empty" style="display:none">
<h3>No projects match</h3>
<p>Try a different search or filter.</p>
</div>
</main>
</div>

<script>
const DATA = {data_json};
let activeIdx = 0;
let filter = 'all';
let searchTerm = '';

function esc(t) {{ return t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;') }}

function render() {{
  const filtered = DATA.filter(p => {{
    if (filter !== 'all' && p.label !== filter) return false;
    if (searchTerm && !p.name.toLowerCase().includes(searchTerm.toLowerCase())) return false;
    return true;
  }});
  document.getElementById('visible-count').textContent = 'Showing ' + filtered.length;
  document.getElementById('empty').style.display = filtered.length ? 'none' : 'block';

  const list = document.getElementById('proj-list');
  list.innerHTML = filtered.map((p, i) => {{
    const isOpen = activeIdx === i;
    const dirtyClass = p.dirty ? 'yes' : 'no';
    const reasons = p.reasons || [];
    const byType = p.by_type || {{}};
    const typeEntries = Object.entries(byType).sort((a,b) => b[1]-a[1]).slice(0,8);
    const maxType = typeEntries.length ? typeEntries[0][1] : 1;
    return `<div class="proj" data-idx="${{i}}" onclick="toggle(${{i}})">
      <div class="proj-header">
        <div class="proj-score ${{p.label}}">${{p.score}}</div>
        <div class="proj-info">
          <div class="proj-name">
            <span class="dirty-dot ${{dirtyClass}}"></span>
            ${{esc(p.name)}}
            <span class="proj-type-badge">${{p.type}}</span>
          </div>
          <div class="proj-meta">
            <span>${{p.total_files}} files</span>
            <span>${{p.size_kb}} KB</span>
            <span>${{p.days_since_commit !== null ? p.days_since_commit + 'd since commit' : ''}}</span>
            ${{p.dirty ? '<span style="color:var(--high)">⚡ ' + p.uncommitted + ' uncommitted</span>' : ''}}
          </div>
        </div>
        <div class="proj-arrow ${{isOpen ? 'open' : ''}}">▶</div>
      </div>
      <div class="proj-detail ${{isOpen ? 'open' : ''}}">
        <div class="proj-detail-inner">
          ${{reasons.length ? '<div class="reason-list">' + reasons.map(r => '<span class="reason-tag">' + esc(r) + '</span>').join('') + '</div>' : ''}}
          <div class="detail-grid">
            <div class="detail-item"><div class="dlbl">Path</div><div class="dval" style="font-size:10px;word-break:break-all">${{esc(p.path)}}</div></div>
            <div class="detail-item"><div class="dlbl">Last commit</div><div class="dval" style="font-size:10px">${{esc(p.last_commit || '—')}}</div></div>
            <div class="detail-item"><div class="dlbl">Branches</div><div class="dval">${{p.branches || '—'}}</div></div>
            <div class="detail-item"><div class="dlbl">Modified</div><div class="dval ${{p.days_since_modified > 30 ? 'dirty' : 'clean'}}">${{p.days_since_modified !== null ? p.days_since_modified + 'd ago' : '—'}}</div></div>
            <div class="detail-item"><div class="dlbl">Status</div><div class="dval ${{p.dirty ? 'dirty' : 'clean'}}">${{p.dirty ? 'Dirty (' + p.uncommitted + ' files)' : 'Clean'}}</div></div>
            <div class="detail-item"><div class="dlbl">Type</div><div class="dval">${{p.type}}</div></div>
          </div>
          ${{typeEntries.length ? '<div style="font-size:10px;color:var(--text-dim);text-transform:uppercase;letter-spacing:.04em;margin-bottom:4px">File types</div><div class="file-bars">' + typeEntries.map(([ext, count]) => `<div class="file-bar"><span class="bar-label">${{esc(ext)}}</span><span class="bar-fill" style="width:${{Math.max(4, count/maxType*80)}}px"></span><span class="bar-count">${{count}}</span></div>`).join('') + '</div>' : ''}}
        </div>
      </div>
    </div>`;
  }}).join('');

  updateStats(filtered);
}}

function updateStats(filtered) {{
  const all = DATA;
  document.getElementById('cnt-critical').textContent = all.filter(p => p.label === 'critical').length;
  document.getElementById('cnt-high').textContent = all.filter(p => p.label === 'high').length;
  document.getElementById('cnt-medium').textContent = all.filter(p => p.label === 'medium').length;
  document.getElementById('cnt-low').textContent = all.filter(p => p.label === 'low').length;
  document.getElementById('f-all').textContent = all.length;
  document.getElementById('f-critical').textContent = all.filter(p=>p.label==='critical').length;
  document.getElementById('f-high').textContent = all.filter(p=>p.label==='high').length;
  document.getElementById('f-medium').textContent = all.filter(p=>p.label==='medium').length;
  document.getElementById('f-low').textContent = all.filter(p=>p.label==='low').length;
}}

function toggle(idx) {{
  activeIdx = activeIdx === idx ? -1 : idx;
  render();
}}

document.querySelectorAll('.filter-btn').forEach(btn => {{
  btn.addEventListener('click', () => {{
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    filter = btn.dataset.filter;
    activeIdx = -1;
    render();
  }});
}});

document.getElementById('search').addEventListener('input', (e) => {{
  searchTerm = e.target.value;
  activeIdx = -1;
  render();
}});

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {{
  if (e.target === document.getElementById('search')) return;
  const items = document.querySelectorAll('.proj');
  if (e.key === 'j' || e.key === 'ArrowDown') {{
    e.preventDefault();
    activeIdx = Math.min((activeIdx < 0 ? 0 : activeIdx) + 1, items.length - 1);
    render();
    items[activeIdx]?.scrollIntoView({{block:'nearest'}});
  }}
  if (e.key === 'k' || e.key === 'ArrowUp') {{
    e.preventDefault();
    activeIdx = Math.max((activeIdx < 0 ? 0 : activeIdx) - 1, 0);
    render();
    items[activeIdx]?.scrollIntoView({{block:'nearest'}});
  }}
  if (e.key === 'Enter' && activeIdx >= 0) {{
    e.preventDefault();
    toggle(activeIdx);
  }}
}});

render();
</script>
</body>
</html>"""

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html)

    return html
