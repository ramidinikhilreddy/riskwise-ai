from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests


@dataclass
class GithubMetrics:
    commits: int
    open_issues: int
    closed_issues: int
    merged_prs: int
    churn_additions: int
    churn_deletions: int
    velocity_14d: int


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def _headers(token: Optional[str]) -> Dict[str, str]:
    h = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "RiskWise/1.0",
    }
    if token:
        # PAT format: "ghp_..."; GitHub accepts "token" scheme for classic PATs.
        h["Authorization"] = f"token {token.strip()}"
    return h


def _paginate_count(url: str, headers: Dict[str, str], params: Dict[str, Any], max_pages: int = 10) -> Tuple[int, List[Dict[str, Any]]]:
    """Return (count, items) using basic pagination.

    GitHub's API uses Link headers; we keep it simple and cap pages.
    """
    items: List[Dict[str, Any]] = []
    page = 1
    while page <= max_pages:
        p = dict(params)
        p.update({"per_page": 100, "page": page})
        r = requests.get(url, headers=headers, params=p, timeout=30)
        if r.status_code >= 400:
            raise RuntimeError(f"GitHub API error {r.status_code}: {r.text}")
        batch = r.json() or []
        if not isinstance(batch, list):
            # some endpoints return dict
            break
        items.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return len(items), items


def fetch_metrics(repo_full_name: str, token: Optional[str] = None, days: int = 30) -> GithubMetrics:
    """Fetch lightweight repo activity metrics for the given time window.

    Notes:
    - This is intentionally conservative (caps pagination and commit-detail requests)
      to avoid rate-limits.
    - Token is strongly recommended; unauthenticated requests are heavily rate-limited.
    """

    if "/" not in repo_full_name:
        raise ValueError("repo_full_name must be like 'owner/repo'")

    owner, repo = repo_full_name.split("/", 1)
    base = f"https://api.github.com/repos/{owner}/{repo}"
    h = _headers(token)

    now = datetime.now(timezone.utc)
    since = now - timedelta(days=max(1, int(days)))
    since_iso = _iso(since)

    # Commits (count only)
    commits_url = f"{base}/commits"
    commits_count, commits_items = _paginate_count(commits_url, h, {"since": since_iso}, max_pages=10)

    # Issues: GitHub issues endpoint includes PRs; filter out those with 'pull_request'
    issues_url = f"{base}/issues"

    open_count, open_items = _paginate_count(issues_url, h, {"state": "open"}, max_pages=10)
    open_issues = sum(1 for it in open_items if "pull_request" not in it)

    all_count, all_items = _paginate_count(issues_url, h, {"state": "closed", "since": since_iso}, max_pages=10)
    closed_issues = sum(1 for it in all_items if "pull_request" not in it)

    # PRs merged in window
    pulls_url = f"{base}/pulls"
    _, pulls_items = _paginate_count(pulls_url, h, {"state": "closed", "sort": "updated", "direction": "desc"}, max_pages=10)

    merged_prs = 0
    for pr in pulls_items:
        merged_at = pr.get("merged_at")
        if not merged_at:
            continue
        try:
            merged_dt = datetime.fromisoformat(merged_at.replace("Z", "+00:00"))
        except Exception:
            continue
        if merged_dt >= since:
            merged_prs += 1

    # Code churn (approx): sum additions/deletions from up to first 30 commits in window
    churn_add = 0
    churn_del = 0
    for c in (commits_items or [])[:30]:
        sha = (c.get("sha") or "").strip()
        if not sha:
            continue
        d = requests.get(f"{base}/commits/{sha}", headers=h, timeout=30)
        if d.status_code >= 400:
            # ignore one-off failures
            continue
        stats = (d.json() or {}).get("stats") or {}
        churn_add += int(stats.get("additions") or 0)
        churn_del += int(stats.get("deletions") or 0)

    # Velocity proxy (last 14 days): closed issues + merged PRs in that window
    since_14 = now - timedelta(days=14)
    since_14_iso = _iso(since_14)
    _, closed14_items = _paginate_count(issues_url, h, {"state": "closed", "since": since_14_iso}, max_pages=10)
    closed_issues_14 = sum(1 for it in closed14_items if "pull_request" not in it)

    merged_prs_14 = 0
    for pr in pulls_items:
        merged_at = pr.get("merged_at")
        if not merged_at:
            continue
        try:
            merged_dt = datetime.fromisoformat(merged_at.replace("Z", "+00:00"))
        except Exception:
            continue
        if merged_dt >= since_14:
            merged_prs_14 += 1

    velocity_14d = closed_issues_14 + merged_prs_14

    return GithubMetrics(
        commits=commits_count,
        open_issues=open_issues,
        closed_issues=closed_issues,
        merged_prs=merged_prs,
        churn_additions=churn_add,
        churn_deletions=churn_del,
        velocity_14d=velocity_14d,
    )
