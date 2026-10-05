"""Code size and evolution trend analysis."""

from collections import defaultdict
from datetime import datetime, timedelta


def compute_loc_trend(commits: list, granularity: str = "monthly") -> dict:
    """
    Compute lines-of-code evolution over time.

    Uses cumulative additions - deletions to estimate total LOC.
    This is an approximation (doesn't account for file renames/deletions
    perfectly), but gives a good trend indicator.

    Returns per-bucket: total_additions, total_deletions, estimated_loc,
    commits, active_files.
    """
    if not commits:
        return {}

    # Sort by date
    sorted_commits = sorted(commits, key=lambda c: c.date)

    buckets = defaultdict(lambda: {
        "additions": 0, "deletions": 0, "commits": 0, "files": set(),
    })

    cumulative_add = 0
    cumulative_del = 0

    for commit in sorted_commits:
        bucket = _bucket(commit.date, granularity)
        b = buckets[bucket]
        b["additions"] += commit.total_additions
        b["deletions"] += commit.total_deletions
        b["commits"] += 1
        for f in commit.files:
            b["files"].add(f.path)

    result = {}
    running_add = 0
    running_del = 0
    for bucket in sorted(buckets.keys()):
        b = buckets[bucket]
        running_add += b["additions"]
        running_del += b["deletions"]
        result[bucket] = {
            "additions": b["additions"],
            "deletions": b["deletions"],
            "net": b["additions"] - b["deletions"],
            "cumulative_additions": running_add,
            "cumulative_deletions": running_del,
            "estimated_loc": running_add - running_del,
            "commits": b["commits"],
            "active_files": len(b["files"]),
        }

    return result


def _bucket(dt: datetime, granularity: str) -> str:
    if granularity == "daily":
        return dt.strftime("%Y-%m-%d")
    elif granularity == "weekly":
        iso = dt.isocalendar()
        return f"{iso[0]}-W{iso[1]:02d}"
    elif granularity == "monthly":
        return dt.strftime("%Y-%m")
    elif granularity == "yearly":
        return dt.strftime("%Y")
    return dt.strftime("%Y-%m")


def compute_growth_rate(loc_trend: dict) -> dict:
    """Compute period-over-period growth rate."""
    if len(loc_trend) < 2:
        return {}

    buckets = sorted(loc_trend.keys())
    rates = {}
    for i in range(1, len(buckets)):
        prev = loc_trend[buckets[i - 1]]["estimated_loc"]
        curr = loc_trend[buckets[i]]["estimated_loc"]
        if prev != 0:
            rate = round((curr - prev) / abs(prev) * 100, 2)
        else:
            rate = 0.0 if curr == 0 else 100.0
        rates[buckets[i]] = {
            "growth_rate_pct": rate,
            "absolute_change": curr - prev,
        }
    return rates


def get_major_milestones(commits: list, top_n: int = 10) -> list:
    """Identify major commits by total lines changed."""
    ranked = sorted(
        commits,
        key=lambda c: c.total_additions + c.total_deletions,
        reverse=True,
    )
    return [
        {
            "sha": c.short_sha,
            "full_sha": c.sha,
            "author": c.author_name,
            "date": c.date.isoformat(),
            "subject": c.subject,
            "additions": c.total_additions,
            "deletions": c.total_deletions,
            "total": c.total_additions + c.total_deletions,
            "files_changed": len(c.files),
        }
        for c in ranked[:top_n]
    ]


def get_commit_size_distribution(commits: list) -> dict:
    """Distribution of commit sizes (small/medium/large/huge)."""
    bins = {
        "tiny (1-10)": 0,
        "small (11-50)": 0,
        "medium (51-200)": 0,
        "large (201-1000)": 0,
        "huge (1000+)": 0,
    }
    for commit in commits:
        total = commit.total_additions + commit.total_deletions
        if total <= 10:
            bins["tiny (1-10)"] += 1
        elif total <= 50:
            bins["small (11-50)"] += 1
        elif total <= 200:
            bins["medium (51-200)"] += 1
        elif total <= 1000:
            bins["large (201-1000)"] += 1
        else:
            bins["huge (1000+)"] += 1
    return bins


def get_productivity_metrics(commits: list) -> dict:
    """Compute overall productivity metrics."""
    if not commits:
        return {"total_commits": 0}

    total_add = sum(c.total_additions for c in commits)
    total_del = sum(c.total_deletions for c in commits)
    dates = [c.date for c in commits]
    span_days = max((max(dates) - min(dates)).days, 1)

    authors = set(c.author_key for c in commits)
    active_days = set(d.strftime("%Y-%m-%d") for d in dates)

    return {
        "total_commits": len(commits),
        "total_additions": total_add,
        "total_deletions": total_del,
        "net_lines": total_add - total_del,
        "avg_lines_per_commit": round((total_add + total_del) / len(commits), 1),
        "authors": len(authors),
        "active_days": len(active_days),
        "span_days": span_days,
        "commits_per_day": round(len(commits) / span_days, 2),
        "commits_per_active_day": round(len(commits) / max(len(active_days), 1), 2),
        "first_commit": min(dates).isoformat(),
        "last_commit": max(dates).isoformat(),
        "files_touched": len(set(f.path for c in commits for f in c.files)),
    }
