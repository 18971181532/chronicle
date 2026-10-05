# Chronicle Examples

Try Chronicle on any git repository:

```bash
# Quick summary
chronicle analyze .

# Start the dashboard
chronicle serve . --port 8765
# Open http://127.0.0.1:8765

# Top contributors
chronicle authors --sort-by commits --limit 10

# Most modified files
chronicle files --sort-by total_changes --limit 20

# Monthly timeline
chronicle timeline --granularity monthly

# Collaboration network
chronicle network

# Code size trend
chronicle trend

# Export report
chronicle export --format markdown -o report.md
chronicle export --format json -o report.json
chronicle export --format csv -o ./exports/
```
