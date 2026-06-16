# SPDX-License-Identifier: MIT
"""Priority engine — scores projects by attention urgency."""

from datetime import datetime, timezone


def prioritize(state: dict, staleness_days: int = 7) -> list[dict]:
    """Score each project 0-100 by urgency.

    Factors:
    - Days since last commit (older = higher, caps at 14 days → 40 points)
    - Days since any file modified (older = higher, caps at 30 days → 30 points)
    - Uncommitted changes (dirty git = 15 points)
    - Project complexity (more files = more to lose, up to 10 points)
    - Branch count (multiple active branches = active development, 5 points)

    Returns sorted list of project evaluations.
    """
    evaluations = []
    projects = state.get("projects", {})

    for name, info in projects.items():
        score = 0
        reasons = []

        # 1. Git staleness (max 40 points)
        git = info.get("git", {})
        if git.get("has_git"):
            days_since = git.get("days_since_commit")
            if days_since is not None:
                staleness_score = min(40, max(0, days_since / staleness_days * 20))
                if days_since > staleness_days:
                    score += staleness_score
                    reasons.append(f"no commit in {days_since}d")

            # 2. Dirty working tree (15 points)
            if git.get("dirty"):
                score += 15
                reasons.append(f"{git.get('uncommitted_files', 0)} uncommitted file(s)")

            # 3. Multiple branches (5 points, active)
            branches = git.get("branches", 0)
            if 2 <= branches <= 5:
                score += 5
            elif branches > 5:
                score += 3  # Too many branches is its own problem

        # 4. File staleness (max 30 points)
        days_mod = info.get("days_since_modified")
        if days_mod is not None and days_mod > staleness_days:
            staleness_file = min(30, days_mod / 30 * 15)
            score += staleness_file
            if days_mod > staleness_days * 2:
                reasons.append(f"stale for {days_mod}d")

        # 5. Project size bonus (max 10 points for large projects)
        files = info.get("files", {})
        total_files = files.get("total_files", 0)
        if total_files > 50:
            score += min(10, total_files / 200 * 5)

        # 6. Type-specific bonuses
        proj_type = info.get("type", "Unknown")
        if proj_type == "Python" and info.get("files", {}).get("by_type", {}).get(".py", 0) > 20:
            score += 5  # Large Python projects need more attention

        # Ensure 0-100
        score = max(0, min(100, int(score)))

        evaluations.append({
            "name": name,
            "type": proj_type,
            "priority_score": score,
            "priority_label": _label(score),
            "reasons": reasons,
            "path": info.get("path", ""),
            "git": info.get("git", {}),
            "files": info.get("files", {}),
        })

    evaluations.sort(key=lambda e: e["priority_score"], reverse=True)
    return evaluations


def _label(score: int) -> str:
    if score >= 50:
        return "critical"
    if score >= 25:
        return "high"
    if score >= 10:
        return "medium"
    return "low"
