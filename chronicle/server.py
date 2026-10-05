"""HTTP server for the Chronicle web dashboard."""

import json
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from chronicle.analyzer import analyze_repo
from chronicle import git_reader


# Global cache for analysis results
_analysis_cache = {"result": None, "lock": threading.Lock()}


def get_analysis(repo_path: str, max_commits=None, force=False):
    """Get or compute analysis result with caching."""
    with _analysis_cache["lock"]:
        if _analysis_cache["result"] is not None and not force:
            return _analysis_cache["result"]
        result = analyze_repo(repo_path, max_commits=max_commits)
        _analysis_cache["result"] = result
        return result


class ChronicleHandler(BaseHTTPRequestHandler):
    """HTTP request handler for Chronicle API and static files."""

    repo_path = "."
    max_commits = None

    def log_message(self, format, *args):
        pass  # Suppress default logging

    def _send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, filepath, content_type):
        try:
            with open(filepath, "rb") as f:
                body = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except FileNotFoundError:
            self.send_error(404)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        # API routes
        if path == "/api/stats":
            result = get_analysis(self.repo_path, self.max_commits)
            self._send_json({
                "repo": result.repo_info,
                "summary": result.productivity,
                "commits_count": len(result.commits),
                "authors_count": len(result.author_stats),
                "files_count": len(result.file_stats),
                "branches": result.branches,
                "tags": result.tags[:20],
            })

        elif path == "/api/authors":
            result = get_analysis(self.repo_path, self.max_commits)
            sort_by = params.get("sort", ["commits"])[0]
            from chronicle.authors import rank_authors
            ranked = rank_authors(result.author_stats, sort_by)
            self._send_json([{"key": k, **v} for k, v in ranked])

        elif path == "/api/files":
            result = get_analysis(self.repo_path, self.max_commits)
            sort_by = params.get("sort", ["commits"])[0]
            limit = int(params.get("limit", [100])[0])
            from chronicle.files import rank_files
            ranked = rank_files(result.file_stats, sort_by, limit)
            self._send_json(ranked)

        elif path == "/api/timeline":
            result = get_analysis(self.repo_path, self.max_commits)
            granularity = params.get("granularity", ["monthly"])[0]
            data = getattr(result, f"timeline_{granularity}", result.timeline_monthly)
            self._send_json(data)

        elif path == "/api/heatmap":
            result = get_analysis(self.repo_path, self.max_commits)
            self._send_json(result.heatmap)

        elif path == "/api/network":
            result = get_analysis(self.repo_path, self.max_commits)
            self._send_json(result.collab_network)

        elif path == "/api/centrality":
            result = get_analysis(self.repo_path, self.max_commits)
            self._send_json(result.centrality)

        elif path == "/api/clusters":
            result = get_analysis(self.repo_path, self.max_commits)
            self._send_json(result.clusters)

        elif path == "/api/trend":
            result = get_analysis(self.repo_path, self.max_commits)
            self._send_json(result.loc_trend)

        elif path == "/api/milestones":
            result = get_analysis(self.repo_path, self.max_commits)
            self._send_json(result.milestones)

        elif path == "/api/extensions":
            result = get_analysis(self.repo_path, self.max_commits)
            from chronicle.files import get_file_extensions
            self._send_json(get_file_extensions(result.file_stats))

        elif path == "/api/directories":
            result = get_analysis(self.repo_path, self.max_commits)
            depth = int(params.get("depth", [1])[0])
            from chronicle.files import get_directory_stats
            self._send_json(get_directory_stats(result.file_stats, depth))

        elif path == "/api/hourly":
            result = get_analysis(self.repo_path, self.max_commits)
            from chronicle.timeline import get_hourly_distribution, get_weekday_distribution
            self._send_json({
                "hourly": get_hourly_distribution(result.commits),
                "weekday": get_weekday_distribution(result.commits),
            })

        elif path == "/api/refresh":
            result = get_analysis(self.repo_path, self.max_commits, force=True)
            self._send_json({"status": "refreshed", "commits": len(result.commits)})

        # Static files
        elif path == "/" or path == "/index.html":
            web_dir = os.path.join(os.path.dirname(__file__), "web")
            self._send_file(os.path.join(web_dir, "index.html"), "text/html; charset=utf-8")
        elif path == "/style.css":
            web_dir = os.path.join(os.path.dirname(__file__), "web")
            self._send_file(os.path.join(web_dir, "style.css"), "text/css; charset=utf-8")
        elif path == "/app.js":
            web_dir = os.path.join(os.path.dirname(__file__), "web")
            self._send_file(os.path.join(web_dir, "app.js"), "application/javascript; charset=utf-8")
        else:
            self.send_error(404)


def start_server(repo_path: str, port: int = 8765, max_commits=None):
    """Start the Chronicle web dashboard server."""
    handler = ChronicleHandler
    handler.repo_path = repo_path
    handler.max_commits = max_commits

    server = HTTPServer(("127.0.0.1", port), handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
