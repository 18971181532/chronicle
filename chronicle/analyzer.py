"""Main analysis orchestrator — runs all analyses and produces a full report."""

import json
from typing import Optional

from chronicle import git_reader, authors, files, timeline, network, trend


class AnalysisResult:
    """Container for all analysis results."""

    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self.repo_info = {}
        self.commits = []
        self.author_stats = {}
        self.file_stats = {}
        self.timeline_daily = {}
        self.timeline_weekly = {}
        self.timeline_monthly = {}
        self.heatmap = {}
        self.collab_network = {}
        self.centrality = {}
        self.clusters = []
        self.loc_trend = {}
        self.milestones = []
        self.productivity = {}
        self.branches = []
        self.tags = []

    def to_dict(self) -> dict:
        return {
            "repo": self.repo_info,
            "summary": self.productivity,
            "commits_count": len(self.commits),
            "authors": self.author_stats,
            "files": self.file_stats,
            "timeline": {
                "daily": self.timeline_daily,
                "weekly": self.timeline_weekly,
                "monthly": self.timeline_monthly,
            },
            "heatmap": self.heatmap,
            "network": self.collab_network,
            "centrality": self.centrality,
            "clusters": self.clusters,
            "loc_trend": self.loc_trend,
            "milestones": self.milestones,
            "branches": self.branches,
            "tags": self.tags,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False, default=str)


def analyze_repo(repo_path: str, max_commits: Optional[int] = None,
                 since: Optional[str] = None, until: Optional[str] = None,
                 include_network: bool = True) -> AnalysisResult:
    """
    Run full analysis on a git repository.

    Args:
        repo_path: Path to the git repository
        max_commits: Maximum number of commits to analyze (None = all)
        since: Only analyze commits after this date (git --since format)
        until: Only analyze commits before this date
        include_network: Whether to compute collaboration network (can be slow for large repos)

    Returns:
        AnalysisResult with all computed metrics
    """
    result = AnalysisResult(repo_path)

    # Basic repo info
    result.repo_info = git_reader.get_repo_info(repo_path)
    result.branches = git_reader.get_branches(repo_path)
    try:
        result.tags = git_reader.get_tags(repo_path)
    except Exception:
        result.tags = []

    # Parse commits
    result.commits = git_reader.parse_commits(
        repo_path, max_count=max_commits, since=since, until=until,
    )

    if not result.commits:
        result.productivity = trend.get_productivity_metrics([])
        return result

    # Author analysis
    result.author_stats = authors.analyze_authors(result.commits)

    # File analysis
    result.file_stats = files.analyze_files(result.commits)

    # Timeline
    result.timeline_daily = timeline.aggregate_timeline(result.commits, "daily")
    result.timeline_weekly = timeline.aggregate_timeline(result.commits, "weekly")
    result.timeline_monthly = timeline.aggregate_timeline(result.commits, "monthly")
    result.heatmap = timeline.build_heatmap(result.commits)

    # Collaboration network
    if include_network:
        result.collab_network = network.build_collaboration_network(result.commits)
        result.centrality = network.compute_centrality(result.collab_network)
        result.clusters = network.find_clusters(result.collab_network)

    # Trends
    result.loc_trend = trend.compute_loc_trend(result.commits, "monthly")
    result.milestones = trend.get_major_milestones(result.commits)
    result.productivity = trend.get_productivity_metrics(result.commits)

    return result


def quick_summary(result: AnalysisResult) -> str:
    """Generate a human-readable quick summary."""
    p = result.productivity
    lines = []
    lines.append(f"Repository: {result.repo_info.get('root', result.repo_path)}")
    lines.append(f"Branch: {result.repo_info.get('branch', 'unknown')}")
    lines.append("")
    lines.append(f"Commits: {p.get('total_commits', 0)}")
    lines.append(f"Authors: {p.get('authors', 0)}")
    lines.append(f"Files touched: {p.get('files_touched', 0)}")
    lines.append(f"Active days: {p.get('active_days', 0)}")
    lines.append(f"Span: {p.get('span_days', 0)} days")
    lines.append("")
    lines.append(f"Total additions: {p.get('total_additions', 0):,}")
    lines.append(f"Total deletions: {p.get('total_deletions', 0):,}")
    lines.append(f"Net lines: {p.get('net_lines', 0):,}")
    lines.append(f"Avg lines/commit: {p.get('avg_lines_per_commit', 0)}")
    lines.append("")

    # Top authors
    ranked = authors.rank_authors(result.author_stats, "commits")
    if ranked:
        lines.append("Top contributors:")
        for i, (key, stats) in enumerate(ranked[:5], 1):
            lines.append(f"  {i}. {stats['name']} — {stats['commits']} commits, "
                         f"+{stats['additions']:,}/-{stats['deletions']:,}")
        lines.append("")

    # Top files
    top_files = files.rank_files(result.file_stats, "commits", 5)
    if top_files:
        lines.append("Most modified files:")
        for i, f in enumerate(top_files, 1):
            lines.append(f"  {i}. {f['path']} — {f['commits']} commits, "
                         f"{f['total_changes']:,} changes")

    return "\n".join(lines)
