"""Timeline aggregation and heatmap data."""

from collections import defaultdict
from datetime import datetime, timedelta


def aggregate_timeline(commits: list, granularity: str = "daily") -> dict:
    """
    Aggregate commits by time bucket.

    Granularity: daily, weekly, monthly, yearly.
    Returns per-bucket commit counts, additions, deletions, authors.
    """
    buckets = defaultdict(lambda: {
        "commits": 0, "additions": 0, "deletions": 0,
        "authors": set(), "files": set(),
    })

    for commit in commits:
        bucket = _bucket_date(commit.date, granularity)
        b = buckets[bucket]
        b["commits"] += 1
        b["additions"] += commit.total_additions
        b["deletions"] += commit.total_deletions
        b["authors"].add(commit.author_key)
        for f in commit.files:
            b["files"].add(f.path)

    result = {}
    for bucket, b in sorted(buckets.items()):
        result[bucket] = {
            "commits": b["commits"],
            "additions": b["additions"],
            "deletions": b["deletions"],
            "net": b["additions"] - b["deletions"],
            "authors": len(b["authors"]),
            "files": len(b["files"]),
        }
    return result


def _bucket_date(dt: datetime, granularity: str) -> str:
    """Bucket a datetime into a string key."""
    if granularity == "daily":
        return dt.strftime("%Y-%m-%d")
    elif granularity == "weekly":
        # ISO week: year-Wweek
        iso = dt.isocalendar()
        return f"{iso[0]}-W{iso[1]:02d}"
    elif granularity == "monthly":
        return dt.strftime("%Y-%m")
    elif granularity == "yearly":
        return dt.strftime("%Y")
    else:
        return dt.strftime("%Y-%m-%d")


def build_heatmap(commits: list, weeks: int = 52) -> dict:
    """
    Build a GitHub-style contribution heatmap.

    Returns a 2D structure: columns (weeks) x rows (days 0-6),
    each cell has date, count, level (0-4).
    """
    if not commits:
        return {"weeks": [], "max_count": 0, "total": 0}

    # Count commits per day
    daily_counts = defaultdict(int)
    for commit in commits:
        day = commit.date.strftime("%Y-%m-%d")
        daily_counts[day] += 1

    # Find the most recent Sunday
    latest = max(c.date for c in commits)
    # Go back to start of week (Sunday)
    days_since_sunday = (latest.weekday() + 1) % 7  # Sunday=0
    end_date = latest - timedelta(days=days_since_sunday)
    start_date = end_date - timedelta(weeks=weeks - 1)

    # Build columns
    columns = []
    max_count = max(daily_counts.values()) if daily_counts else 0

    current = start_date
    while current <= end_date:
        week_data = []
        for day_offset in range(7):
            cell_date = current + timedelta(days=day_offset)
            date_str = cell_date.strftime("%Y-%m-%d")
            count = daily_counts.get(date_str, 0)
            level = _heatmap_level(count, max_count)
            week_data.append({
                "date": date_str,
                "count": count,
                "level": level,
            })
        columns.append(week_data)
        current += timedelta(weeks=1)

    return {
        "weeks": columns,
        "max_count": max_count,
        "total": sum(daily_counts.values()),
        "start": start_date.strftime("%Y-%m-%d"),
        "end": end_date.strftime("%Y-%m-%d"),
    }


def _heatmap_level(count: int, max_count: int) -> int:
    """Map commit count to 0-4 intensity level."""
    if count == 0:
        return 0
    if max_count == 0:
        return 1
    ratio = count / max_count
    if ratio <= 0.25:
        return 1
    elif ratio <= 0.5:
        return 2
    elif ratio <= 0.75:
        return 3
    else:
        return 4


def get_busiest_periods(commits: list, top_n: int = 10) -> list:
    """Find the busiest days/periods by commit count."""
    daily = defaultdict(int)
    for commit in commits:
        daily[commit.date.strftime("%Y-%m-%d")] += 1
    busiest = sorted(daily.items(), key=lambda x: x[1], reverse=True)
    return [{"date": d, "commits": c} for d, c in busiest[:top_n]]


def get_hourly_distribution(commits: list) -> dict:
    """Get commit distribution by hour of day (0-23)."""
    hourly = defaultdict(int)
    for commit in commits:
        hourly[commit.date.hour] += 1
    return {str(h): hourly.get(h, 0) for h in range(24)}


def get_weekday_distribution(commits: list) -> dict:
    """Get commit distribution by day of week."""
    names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    weekday = defaultdict(int)
    for commit in commits:
        weekday[names[commit.date.weekday()]] += 1
    return {name: weekday.get(name, 0) for name in names}
