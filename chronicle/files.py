"""File change statistics and hotspots."""

from collections import defaultdict


def analyze_files(commits: list) -> dict:
    """
    Analyze file-level change statistics.

    Returns per-file stats: commit count, additions, deletions,
    last changed date, authors who touched it, churn rate.
    """
    files = defaultdict(lambda: {
        "commits": 0,
        "additions": 0,
        "deletions": 0,
        "last_changed": None,
        "authors": set(),
        "renames": [],
    })

    for commit in commits:
        for f in commit.files:
            entry = files[f.path]
            entry["commits"] += 1
            entry["additions"] += f.additions
            entry["deletions"] += f.deletions
            if entry["last_changed"] is None or commit.date > entry["last_changed"]:
                entry["last_changed"] = commit.date
            entry["authors"].add(commit.author_key)

    result = {}
    for path, entry in files.items():
        total = entry["additions"] + entry["deletions"]
        result[path] = {
            "path": path,
            "commits": entry["commits"],
            "additions": entry["additions"],
            "deletions": entry["deletions"],
            "total_changes": total,
            "churn": round(total / max(entry["commits"], 1), 1),
            "last_changed": entry["last_changed"].isoformat() if entry["last_changed"] else None,
            "authors_count": len(entry["authors"]),
            "authors": sorted(entry["authors"]),
        }

    return result


def rank_files(file_stats: dict, by: str = "commits", top_n: int = 50) -> list:
    """Rank files by a metric."""
    valid = {"commits", "additions", "deletions", "total_changes", "churn", "authors_count"}
    if by not in valid:
        by = "commits"
    ranked = sorted(file_stats.values(), key=lambda x: x.get(by, 0), reverse=True)
    return ranked[:top_n]


def get_file_extensions(file_stats: dict) -> dict:
    """Aggregate statistics by file extension."""
    exts = defaultdict(lambda: {"files": 0, "commits": 0, "additions": 0, "deletions": 0})
    for path, stats in file_stats.items():
        if "." in path:
            ext = "." + path.rsplit(".", 1)[-1].lower()
        else:
            ext = "(no extension)"
        exts[ext]["files"] += 1
        exts[ext]["commits"] += stats["commits"]
        exts[ext]["additions"] += stats["additions"]
        exts[ext]["deletions"] += stats["deletions"]
    return dict(sorted(exts.items(), key=lambda x: x[1]["commits"], reverse=True))


def get_directory_stats(file_stats: dict, depth: int = 1) -> dict:
    """Aggregate statistics by top-level directory."""
    dirs = defaultdict(lambda: {"files": 0, "commits": 0, "additions": 0, "deletions": 0})
    for path, stats in file_stats.items():
        parts = path.replace("\\", "/").split("/")
        if len(parts) > depth:
            d = "/".join(parts[:depth])
        else:
            d = "(root)"
        dirs[d]["files"] += 1
        dirs[d]["commits"] += stats["commits"]
        dirs[d]["additions"] += stats["additions"]
        dirs[d]["deletions"] += stats["deletions"]
    return dict(sorted(dirs.items(), key=lambda x: x[1]["commits"], reverse=True))


def get_hotspots(file_stats: dict, threshold: int = 10) -> list:
    """Identify hotspots: files changed in many commits."""
    return [
        stats for stats in file_stats.values()
        if stats["commits"] >= threshold
    ]
