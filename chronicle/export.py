"""Export and import analysis results."""

import json
import os
from typing import Optional

from chronicle.analyzer import AnalysisResult


def export_to_json(result: AnalysisResult, output_path: str, indent: int = 2) -> str:
    """Export analysis result to a JSON file."""
    data = result.to_dict()
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, ensure_ascii=False, default=str)
    return output_path


def import_from_json(input_path: str) -> dict:
    """Import analysis result from a JSON file."""
    with open(input_path, "r", encoding="utf-8") as f:
        return json.load(f)


def export_summary_csv(result: AnalysisResult, output_dir: str) -> list:
    """Export key summaries as CSV files."""
    os.makedirs(output_dir, exist_ok=True)
    created = []

    # Authors CSV
    authors_path = os.path.join(output_dir, "authors.csv")
    with open(authors_path, "w", encoding="utf-8") as f:
        f.write("name,email,commits,additions,deletions,net_lines,files_touched,active_days,first_commit,last_commit\n")
        for key, stats in sorted(result.author_stats.items(), key=lambda x: x[1]["commits"], reverse=True):
            f.write(f'"{stats["name"]}","{stats["email"]}",{stats["commits"]},'
                    f'{stats["additions"]},{stats["deletions"]},{stats["net_lines"]},'
                    f'{stats["files_touched"]},{stats["active_days"]},'
                    f'{stats["first_commit"]},{stats["last_commit"]}\n')
    created.append(authors_path)

    # Files CSV
    files_path = os.path.join(output_dir, "files.csv")
    with open(files_path, "w", encoding="utf-8") as f:
        f.write("path,commits,additions,deletions,total_changes,churn,authors_count,last_changed\n")
        for path, stats in sorted(result.file_stats.items(), key=lambda x: x[1]["commits"], reverse=True):
            f.write(f'"{path}",{stats["commits"]},{stats["additions"]},'
                    f'{stats["deletions"]},{stats["total_changes"]},{stats["churn"]},'
                    f'{stats["authors_count"]},{stats["last_changed"]}\n')
    created.append(files_path)

    # Monthly timeline CSV
    timeline_path = os.path.join(output_dir, "timeline_monthly.csv")
    with open(timeline_path, "w", encoding="utf-8") as f:
        f.write("month,commits,additions,deletions,net,authors,files\n")
        for bucket, stats in sorted(result.timeline_monthly.items()):
            f.write(f'{bucket},{stats["commits"]},{stats["additions"]},'
                    f'{stats["deletions"]},{stats["net"]},{stats["authors"]},{stats["files"]}\n')
    created.append(timeline_path)

    return created


def export_markdown_report(result: AnalysisResult, output_path: str) -> str:
    """Export a human-readable Markdown report."""
    p = result.productivity
    lines = []

    lines.append(f"# Chronicle Report: {result.repo_info.get('root', 'Unknown')}")
    lines.append("")
    lines.append(f"**Branch:** {result.repo_info.get('branch', 'unknown')}  ")
    lines.append(f"**Remote:** {result.repo_info.get('remote', 'none')}  ")
    lines.append(f"**Analyzed:** {len(result.commits)} commits")
    lines.append("")

    lines.append("## Overview")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Total commits | {p.get('total_commits', 0):,} |")
    lines.append(f"| Contributors | {p.get('authors', 0)} |")
    lines.append(f"| Files touched | {p.get('files_touched', 0):,} |")
    lines.append(f"| Active days | {p.get('active_days', 0)} |")
    lines.append(f"| Span | {p.get('span_days', 0)} days |")
    lines.append(f"| Additions | {p.get('total_additions', 0):,} |")
    lines.append(f"| Deletions | {p.get('total_deletions', 0):,} |")
    lines.append(f"| Net lines | {p.get('net_lines', 0):,} |")
    lines.append(f"| Avg lines/commit | {p.get('avg_lines_per_commit', 0)} |")
    lines.append(f"| Commits/day | {p.get('commits_per_day', 0)} |")
    lines.append("")

    # Top contributors
    lines.append("## Top Contributors")
    lines.append("")
    lines.append("| # | Author | Commits | Additions | Deletions | Files | Active Days |")
    lines.append("|---|--------|---------|-----------|-----------|-------|-------------|")
    from chronicle.authors import rank_authors
    for i, (key, stats) in enumerate(rank_authors(result.author_stats, "commits")[:10], 1):
        lines.append(f"| {i} | {stats['name']} | {stats['commits']} | "
                     f"+{stats['additions']:,} | -{stats['deletions']:,} | "
                     f"{stats['files_touched']} | {stats['active_days']} |")
    lines.append("")

    # Most modified files
    from chronicle.files import rank_files
    lines.append("## Most Modified Files")
    lines.append("")
    lines.append("| # | File | Commits | Additions | Deletions | Churn | Authors |")
    lines.append("|---|------|---------|-----------|-----------|-------|---------|")
    for i, f in enumerate(rank_files(result.file_stats, "commits", 15), 1):
        lines.append(f"| {i} | `{f['path']}` | {f['commits']} | "
                     f"+{f['additions']:,} | -{f['deletions']:,} | "
                     f"{f['churn']} | {f['authors_count']} |")
    lines.append("")

    # Major milestones
    if result.milestones:
        lines.append("## Major Commits (by size)")
        lines.append("")
        lines.append("| Date | SHA | Author | Subject | +/- | Files |")
        lines.append("|------|-----|--------|---------|-----|-------|")
        for m in result.milestones[:10]:
            lines.append(f"| {m['date'][:10]} | `{m['sha']}` | {m['author']} | "
                         f"{m['subject'][:60]} | +{m['additions']:,}/-{m['deletions']:,} | "
                         f"{m['files_changed']} |")
        lines.append("")

    # Collaboration
    if result.collab_network and result.collab_network["edges"]:
        lines.append("## Collaboration Network")
        lines.append("")
        lines.append(f"- **Nodes:** {result.collab_network['node_count']} authors")
        lines.append(f"- **Edges:** {result.collab_network['edge_count']} connections")
        lines.append(f"- **Clusters:** {len(result.clusters)}")
        lines.append("")
        lines.append("### Strongest collaborations")
        lines.append("")
        lines.append("| Author A | Author B | Shared files |")
        lines.append("|----------|----------|-------------|")
        for edge in result.collab_network["edges"][:10]:
            a = edge["source"].split(" <")[0]
            b = edge["target"].split(" <")[0]
            lines.append(f"| {a} | {b} | {edge['weight']} |")
        lines.append("")

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return output_path
