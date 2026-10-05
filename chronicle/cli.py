"""Chronicle CLI — git repository history analysis."""

import argparse
import json
import os
import sys

from chronicle import __version__
from chronicle.analyzer import analyze_repo, quick_summary
from chronicle import authors as authors_mod
from chronicle import files as files_mod
from chronicle import timeline as timeline_mod
from chronicle import network as network_mod
from chronicle import trend as trend_mod
from chronicle import export as export_mod
from chronicle import git_reader


def cmd_analyze(args):
    """Full analysis with summary output."""
    repo = args.repo or os.getcwd()
    if not git_reader.is_git_repo(repo):
        print(f"Error: {repo} is not a git repository", file=sys.stderr)
        sys.exit(1)

    if not args.json:
        print(f"Analyzing {repo}...")
    result = analyze_repo(
        repo, max_commits=args.max, since=args.since, until=args.until,
        include_network=not args.no_network,
    )

    if args.json:
        print(result.to_json())
    elif args.output:
        path = export_mod.export_to_json(result, args.output)
        print(f"Exported to {path}")
    else:
        print()
        print(quick_summary(result))

    return result


def cmd_authors(args):
    """List contributors ranked by commits."""
    repo = args.repo or os.getcwd()
    result = analyze_repo(repo, max_commits=args.max, include_network=False)
    ranked = authors_mod.rank_authors(result.author_stats, args.sort_by)

    print(f"{'#':>3} {'Author':<30} {'Commits':>8} {'+':>10} {'-':>10} {'Files':>7} {'Days':>6}")
    print("-" * 80)
    for i, (key, stats) in enumerate(ranked[:args.limit], 1):
        name = stats["name"][:28]
        print(f"{i:>3} {name:<30} {stats['commits']:>8} "
              f"{stats['additions']:>10,} {stats['deletions']:>10,} "
              f"{stats['files_touched']:>7} {stats['active_days']:>6}")

    if args.json:
        print(json.dumps(dict(ranked), indent=2, ensure_ascii=False, default=str))


def cmd_files(args):
    """List most modified files."""
    repo = args.repo or os.getcwd()
    result = analyze_repo(repo, max_commits=args.max, include_network=False)
    ranked = files_mod.rank_files(result.file_stats, args.sort_by, args.limit)

    print(f"{'#':>3} {'File':<50} {'Commits':>8} {'+':>8} {'-':>8} {'Churn':>7} {'Auth':>5}")
    print("-" * 95)
    for i, f in enumerate(ranked, 1):
        path = f["path"][:48]
        print(f"{i:>3} {path:<50} {f['commits']:>8} "
              f"{f['additions']:>8,} {f['deletions']:>8,} "
              f"{f['churn']:>7} {f['authors_count']:>5}")


def cmd_timeline(args):
    """Show commit timeline."""
    repo = args.repo or os.getcwd()
    result = analyze_repo(repo, max_commits=args.max, include_network=False)
    data = getattr(result, f"timeline_{args.granularity}", result.timeline_monthly)

    print(f"{'Period':<12} {'Commits':>8} {'+':>10} {'-':>10} {'Net':>10} {'Authors':>8} {'Files':>7}")
    print("-" * 75)
    for bucket, stats in list(data.items())[-args.limit:]:
        print(f"{bucket:<12} {stats['commits']:>8} "
              f"{stats['additions']:>10,} {stats['deletions']:>10,} "
              f"{stats['net']:>10,} {stats['authors']:>8} {stats['files']:>7}")


def cmd_network(args):
    """Show collaboration network."""
    repo = args.repo or os.getcwd()
    result = analyze_repo(repo, max_commits=args.max)
    net = result.collab_network

    print(f"Network: {net['node_count']} authors, {net['edge_count']} connections")
    print()

    print("Top collaborations (by shared files):")
    print(f"{'#':>3} {'Author A':<25} {'Author B':<25} {'Shared':>7}")
    print("-" * 65)
    for i, edge in enumerate(net["edges"][:args.limit], 1):
        a = edge["source"].split(" <")[0][:23]
        b = edge["target"].split(" <")[0][:23]
        print(f"{i:>3} {a:<25} {b:<25} {edge['weight']:>7}")

    if result.clusters:
        print()
        print(f"Clusters found: {len(result.clusters)}")
        for i, cluster in enumerate(result.clusters[:5], 1):
            names = [n.split(" <")[0] for n in cluster[:5]]
            extra = f" +{len(cluster)-5}" if len(cluster) > 5 else ""
            print(f"  {i}. ({len(cluster)} authors): {', '.join(names)}{extra}")


def cmd_trend(args):
    """Show code size evolution trend."""
    repo = args.repo or os.getcwd()
    result = analyze_repo(repo, max_commits=args.max, include_network=False)
    loc = result.loc_trend

    print(f"{'Period':<10} {'Commits':>8} {'+':>10} {'-':>10} {'Est. LOC':>12} {'Change':>10}")
    print("-" * 70)
    prev_loc = 0
    for bucket, stats in list(loc.items())[-args.limit:]:
        change = stats["estimated_loc"] - prev_loc
        sign = "+" if change >= 0 else ""
        print(f"{bucket:<10} {stats['commits']:>8} "
              f"{stats['additions']:>10,} {stats['deletions']:>10,} "
              f"{stats['estimated_loc']:>12,} {sign}{change:>9,}")
        prev_loc = stats["estimated_loc"]


def cmd_milestones(args):
    """Show largest commits."""
    repo = args.repo or os.getcwd()
    result = analyze_repo(repo, max_commits=args.max, include_network=False)

    print(f"{'Date':<12} {'SHA':<8} {'Author':<20} {'+':>8} {'-':>8} {'Files':>6}  Subject")
    print("-" * 100)
    for m in result.milestones[:args.limit]:
        print(f"{m['date'][:10]:<12} {m['sha']:<8} {m['author'][:18]:<20} "
              f"{m['additions']:>8,} {m['deletions']:>8,} {m['files_changed']:>6}  "
              f"{m['subject'][:50]}")


def cmd_export(args):
    """Export analysis to JSON/CSV/Markdown."""
    repo = args.repo or os.getcwd()
    result = analyze_repo(repo, max_commits=args.max)

    if args.format == "json":
        path = export_mod.export_to_json(result, args.output)
        print(f"Exported JSON: {path}")
    elif args.format == "csv":
        paths = export_mod.export_summary_csv(result, args.output)
        for p in paths:
            print(f"Exported: {p}")
    elif args.format == "markdown":
        path = export_mod.export_markdown_report(result, args.output)
        print(f"Exported Markdown: {path}")


def cmd_serve(args):
    """Start the web dashboard."""
    from chronicle.server import start_server
    repo = args.repo or os.getcwd()
    if not git_reader.is_git_repo(repo):
        print(f"Error: {repo} is not a git repository", file=sys.stderr)
        sys.exit(1)
    print(f"Chronicle dashboard: http://127.0.0.1:{args.port}")
    print(f"Analyzing: {repo}")
    print("Press Ctrl+C to stop.")
    start_server(repo, args.port, args.max)


def build_parser():
    parser = argparse.ArgumentParser(
        prog="chronicle",
        description="Chronicle — Git repository history analysis and visualization",
    )
    parser.add_argument("--version", action="version", version=f"chronicle {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Common arguments
    def add_repo_args(p, max_default=None):
        p.add_argument("--repo", help="Path to git repository (default: current directory)")
        p.add_argument("--max", type=int, default=max_default, help="Maximum commits to analyze")
        p.add_argument("--since", help="Only analyze commits after this date")
        p.add_argument("--until", help="Only analyze commits before this date")

    # analyze
    p = subparsers.add_parser("analyze", help="Full analysis with summary")
    add_repo_args(p)
    p.add_argument("--json", action="store_true", help="Output as JSON")
    p.add_argument("--output", "-o", help="Export to JSON file")
    p.add_argument("--no-network", action="store_true", help="Skip collaboration network analysis")
    p.set_defaults(func=cmd_analyze)

    # authors
    p = subparsers.add_parser("authors", help="List contributors")
    add_repo_args(p)
    p.add_argument("--sort-by", choices=["commits", "additions", "deletions", "net_lines", "files_touched", "active_days"], default="commits")
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_authors)

    # files
    p = subparsers.add_parser("files", help="List most modified files")
    add_repo_args(p)
    p.add_argument("--sort-by", choices=["commits", "additions", "deletions", "total_changes", "churn", "authors_count"], default="commits")
    p.add_argument("--limit", type=int, default=30)
    p.set_defaults(func=cmd_files)

    # timeline
    p = subparsers.add_parser("timeline", help="Commit timeline")
    add_repo_args(p)
    p.add_argument("--granularity", choices=["daily", "weekly", "monthly"], default="monthly")
    p.add_argument("--limit", type=int, default=30)
    p.set_defaults(func=cmd_timeline)

    # network
    p = subparsers.add_parser("network", help="Collaboration network")
    add_repo_args(p)
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=cmd_network)

    # trend
    p = subparsers.add_parser("trend", help="Code size evolution")
    add_repo_args(p)
    p.add_argument("--limit", type=int, default=30)
    p.set_defaults(func=cmd_trend)

    # milestones
    p = subparsers.add_parser("milestones", help="Largest commits by size")
    add_repo_args(p)
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=cmd_milestones)

    # export
    p = subparsers.add_parser("export", help="Export analysis results")
    add_repo_args(p)
    p.add_argument("--format", choices=["json", "csv", "markdown"], default="json")
    p.add_argument("--output", "-o", required=True, help="Output file or directory")
    p.set_defaults(func=cmd_export)

    # serve
    p = subparsers.add_parser("serve", help="Start web dashboard")
    add_repo_args(p)
    p.add_argument("--port", type=int, default=8765)
    p.set_defaults(func=cmd_serve)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()
