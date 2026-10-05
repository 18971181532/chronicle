"""Author / contributor analysis."""

from collections import defaultdict
from datetime import datetime
from typing import Optional


def analyze_authors(commits: list) -> dict:
    """
    Analyze contributor statistics from a list of commits.

    Returns per-author stats: commit count, additions, deletions,
    files touched, first/last commit date, active days, hourly distribution.
    """
    authors = defaultdict(lambda: {
        "name": "",
        "email": "",
        "commits": 0,
        "additions": 0,
        "deletions": 0,
        "files_touched": set(),
        "first_commit": None,
        "last_commit": None,
        "active_days": set(),
        "hourly": defaultdict(int),
        "weekday": defaultdict(int),
        "subjects": [],
    })

    for commit in commits:
        key = commit.author_key
        a = authors[key]
        a["name"] = commit.author_name
        a["email"] = commit.author_email
        a["commits"] += 1
        a["additions"] += commit.total_additions
        a["deletions"] += commit.total_deletions
        for f in commit.files:
            a["files_touched"].add(f.path)
        if a["first_commit"] is None or commit.date < a["first_commit"]:
            a["first_commit"] = commit.date
        if a["last_commit"] is None or commit.date > a["last_commit"]:
            a["last_commit"] = commit.date
        a["active_days"].add(commit.date.strftime("%Y-%m-%d"))
        a["hourly"][commit.date.hour] += 1
        a["weekday"][commit.date.strftime("%A")] += 1
        if len(a["subjects"]) < 5:
            a["subjects"].append(commit.subject)

    # Convert to serializable format
    result = {}
    for key, a in authors.items():
        result[key] = {
            "name": a["name"],
            "email": a["email"],
            "commits": a["commits"],
            "additions": a["additions"],
            "deletions": a["deletions"],
            "net_lines": a["additions"] - a["deletions"],
            "files_touched": len(a["files_touched"]),
            "first_commit": a["first_commit"].isoformat() if a["first_commit"] else None,
            "last_commit": a["last_commit"].isoformat() if a["last_commit"] else None,
            "active_days": len(a["active_days"]),
            "avg_commits_per_day": round(
                a["commits"] / max(len(a["active_days"]), 1), 2
            ),
            "hourly": dict(sorted(a["hourly"].items())),
            "weekday": dict(a["weekday"]),
            "recent_subjects": a["subjects"],
        }

    return result


def rank_authors(author_stats: dict, by: str = "commits") -> list:
    """Rank authors by a metric. Returns sorted list of (key, stats)."""
    valid_keys = {"commits", "additions", "deletions", "net_lines", "files_touched", "active_days"}
    if by not in valid_keys:
        by = "commits"
    return sorted(author_stats.items(), key=lambda x: x[1].get(by, 0), reverse=True)


def get_author_timeline(commits: list, author_key: str, granularity: str = "daily") -> dict:
    """Get commit activity timeline for a specific author."""
    counts = defaultdict(int)
    additions = defaultdict(int)
    deletions = defaultdict(int)

    for commit in commits:
        if commit.author_key != author_key:
            continue
        if granularity == "daily":
            bucket = commit.date.strftime("%Y-%m-%d")
        elif granularity == "weekly":
            bucket = commit.date.strftime("%Y-W%W")
        elif granularity == "monthly":
            bucket = commit.date.strftime("%Y-%m")
        else:
            bucket = commit.date.strftime("%Y-%m-%d")
        counts[bucket] += 1
        additions[bucket] += commit.total_additions
        deletions[bucket] += commit.total_deletions

    return {
        "author": author_key,
        "granularity": granularity,
        "commits": dict(sorted(counts.items())),
        "additions": dict(sorted(additions.items())),
        "deletions": dict(sorted(deletions.items())),
    }
