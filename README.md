# Chronicle ⏱

**Git repository history analysis and visualization** — zero dependencies, local-first, interactive dashboard.

Chronicle parses your git history and produces deep insights: contributor statistics, file change hotspots, contribution heatmaps, collaboration networks, code size evolution trends, and major commit milestones — all rendered in an interactive Canvas-based web dashboard.

## Features

- **📊 Overview** — key metrics at a glance: commits, contributors, files, additions/deletions, activity patterns
- **🔥 Heatmap** — GitHub-style contribution heatmap with configurable time ranges
- **👥 Authors** — detailed contributor rankings with commit stats, line changes, active days, first/last commit
- **🕸 Network** — force-directed collaboration graph showing which developers work together on shared files, with cluster detection and centrality metrics
- **📁 Files** — file change bubble chart, directory activity bars, most-modified files table with churn metrics
- **📈 Trend** — code size evolution (estimated LOC over time), major commits by size
- **📅 Timeline** — daily/weekly/monthly commit activity with line changes per period

## Installation

```bash
pip install chronicle-git
```

Or run directly from source:

```bash
git clone https://github.com/18971181532/chronicle.git
cd chronicle
pip install -e .
```

**Zero third-party dependencies** — only Python 3.9+ standard library.

## Quick Start

```bash
# Analyze any git repo and see a summary
chronicle analyze /path/to/repo

# Start the interactive web dashboard
chronicle serve /path/to/repo --port 8765
# Open http://127.0.0.1:8765 in your browser
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `chronicle analyze` | Full analysis with human-readable summary |
| `chronicle authors` | List contributors ranked by commits/additions/etc |
| `chronicle files` | List most modified files with churn metrics |
| `chronicle timeline` | Commit timeline (daily/weekly/monthly) |
| `chronicle network` | Collaboration network overview |
| `chronicle trend` | Code size evolution (estimated LOC) |
| `chronicle milestones` | Largest commits by total lines changed |
| `chronicle export` | Export results to JSON, CSV, or Markdown |
| `chronicle serve` | Start interactive web dashboard |

### Examples

```bash
# Top 10 contributors by additions
chronicle authors --sort-by additions --limit 10

# Monthly timeline
chronicle timeline --granularity monthly

# Export full report as Markdown
chronicle export --format markdown -o report.md

# Analyze last 500 commits only
chronicle analyze --max 500

# Analyze commits since 2024-01-01
chronicle analyze --since 2024-01-01
```

## Web Dashboard

The dashboard features multiple interactive views:

- **Overview** — stat cards, monthly commit bar chart, hourly activity area chart, top contributors list, language mix donut
- **Heatmap** — 6-month/1-year/2-year contribution heatmap with intensity levels
- **Authors** — sortable, scrollable contributors table with all metrics
- **Network** — force-directed collaboration graph with draggable nodes, edge weights by shared files, cluster detection
- **Files** — packed bubble chart of file change frequency, directory activity bars, detailed files table
- **Trend** — estimated LOC area chart over time, major commits table
- **Timeline** — granularity-switchable commit activity table

## Architecture

```
chronicle/
├── __init__.py          # Package init
├── __main__.py          # python -m chronicle
├── git_reader.py        # Git command execution & log parsing
├── analyzer.py          # Main analysis orchestrator
├── authors.py           # Contributor statistics
├── files.py             # File change & hotspot analysis
├── timeline.py          # Time aggregation & heatmap
├── network.py           # Collaboration network & centrality
├── trend.py             # Code size evolution & milestones
├── export.py            # JSON/CSV/Markdown export
├── cli.py               # Command-line interface
├── server.py            # HTTP server + REST API
└── web/
    ├── index.html       # Dashboard UI
    ├── style.css        # Dark theme
    └── app.js           # Canvas visualizations (zero deps)
```

## How It Works

1. **Git log parsing** — Uses `git log --numstat` with custom separators to safely parse commits, authors, dates, and file-level line changes
2. **Analysis engines** — Each module (authors, files, timeline, network, trend) computes specific metrics from the parsed commit list
3. **REST API** — The HTTP server exposes all analysis results as JSON endpoints
4. **Canvas dashboard** — Pure JavaScript Canvas 2D rendering for all charts (bar, line, area, donut, heatmap, force-directed graph, packed bubbles) — no chart libraries

## Testing

```bash
python -m unittest discover -s tests -v
```

100+ unit tests covering all modules, with temporary git repos created on the fly.

## CI

Tests run on GitHub Actions across:
- Ubuntu + Windows
- Python 3.9, 3.10, 3.11, 3.12

## License

MIT License — see [LICENSE](LICENSE) for details.
