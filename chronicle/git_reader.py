"""Run git commands and parse raw output into structured data."""

import os
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class FileChange:
    """A single file changed in a commit."""
    path: str
    additions: int = 0
    deletions: int = 0
    status: str = "modified"  # modified, added, deleted, renamed

    @property
    def total(self) -> int:
        return self.additions + self.deletions

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "additions": self.additions,
            "deletions": self.deletions,
            "status": self.status,
        }


@dataclass
class Commit:
    """A single git commit."""
    sha: str
    author_name: str
    author_email: str
    date: datetime
    subject: str
    body: str = ""
    files: list = field(default_factory=list)  # List[FileChange]
    parents: list = field(default_factory=list)  # List[str]

    @property
    def short_sha(self) -> str:
        return self.sha[:7]

    @property
    def total_additions(self) -> int:
        return sum(f.additions for f in self.files)

    @property
    def total_deletions(self) -> int:
        return sum(f.deletions for f in self.files)

    @property
    def author_key(self) -> str:
        """Normalize author identity (name <email>)."""
        return f"{self.author_name} <{self.author_email}>"

    def to_dict(self) -> dict:
        return {
            "sha": self.sha,
            "author_name": self.author_name,
            "author_email": self.author_email,
            "date": self.date.isoformat(),
            "subject": self.subject,
            "body": self.body,
            "files": [f.to_dict() for f in self.files],
            "parents": self.parents,
        }


def run_git(repo_path: str, args: list, timeout: int = 30) -> str:
    """Run a git command in the given repo and return stdout."""
    cmd = ["git", "-C", repo_path] + args
    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=timeout,
        encoding="utf-8", errors="replace",
    )
    return result.stdout


def is_git_repo(repo_path: str) -> bool:
    """Check if a path is a valid git repository."""
    try:
        out = run_git(repo_path, ["rev-parse", "--is-inside-work-tree"], timeout=5)
        return out.strip() == "true"
    except Exception:
        return False


def get_repo_info(repo_path: str) -> dict:
    """Get basic repository information."""
    info = {}
    try:
        info["branch"] = run_git(repo_path, ["rev-parse", "--abbrev-ref", "HEAD"]).strip()
    except Exception:
        info["branch"] = "unknown"
    try:
        info["head_sha"] = run_git(repo_path, ["rev-parse", "HEAD"]).strip()
    except Exception:
        info["head_sha"] = ""
    try:
        remote = run_git(repo_path, ["remote", "get-url", "origin"]).strip()
        info["remote"] = remote if remote else None
    except Exception:
        info["remote"] = None
    try:
        info["root"] = run_git(repo_path, ["rev-parse", "--show-toplevel"]).strip()
    except Exception:
        info["root"] = os.path.abspath(repo_path)
    return info


# Separator for git log format fields — unlikely to appear in commit messages
_SEP = "\x1f"  # Unit separator
_RECORD_SEP = "\x1e"  # Record separator


def parse_commits(repo_path: str, max_count: Optional[int] = None,
                  since: Optional[str] = None, until: Optional[str] = None) -> list:
    """
    Parse all commits from a git repository.

    Uses a custom format with rare separators to safely handle
    commit messages containing newlines and special characters.
    """
    fmt = _SEP.join([
        "%H",   # full hash
        "%an",  # author name
        "%ae",  # author email
        "%aI",  # author date ISO 8601
        "%s",   # subject
        "%P",   # parent hashes
    ]) + _RECORD_SEP

    args = ["log", f"--format={fmt}", "--numstat", "--no-merges"]
    if max_count:
        args.append(f"-{max_count}")
    if since:
        args.extend(["--since", since])
    if until:
        args.extend(["--until", until])

    raw = run_git(repo_path, args, timeout=120)
    return _parse_log_output(raw)


def _parse_log_output(raw: str) -> list:
    """
    Parse git log output with numstat into Commit objects.

    The output format is:
        <header with \\x1f separators>\\x1e
        <numstat lines>
        <next header>\\x1e
        <numstat lines>

    So numstat for a commit appears AFTER that commit's record separator,
    before the next commit's header. We parse line-by-line: a line
    containing \\x1f is a header; lines between headers are numstat.
    """
    commits = []
    current_commit = None
    pending_numstat = []

    for line in raw.split("\n"):
        if _SEP in line:
            # This is a commit header — finalize previous commit
            if current_commit is not None:
                current_commit.files = _parse_numstat_lines(pending_numstat)
                commits.append(current_commit)
            pending_numstat = []
            current_commit = _parse_header_line(line)
        elif line.strip():
            # Numstat line (or part of multi-line body, but body is in header)
            pending_numstat.append(line.strip())

    # Finalize last commit
    if current_commit is not None:
        current_commit.files = _parse_numstat_lines(pending_numstat)
        commits.append(current_commit)

    return commits


def _parse_header_line(line: str) -> Optional[Commit]:
    """Parse a single header line containing \\x1f separators."""
    parts = line.split(_SEP)
    if len(parts) < 5:
        return None

    sha = parts[0].strip()
    author_name = parts[1]
    author_email = parts[2]
    date_str = parts[3]
    subject = parts[4]
    parents_str = parts[5] if len(parts) > 5 else ""

    try:
        date = datetime.fromisoformat(date_str)
    except (ValueError, TypeError):
        try:
            date = datetime.strptime(date_str[:19], "%Y-%m-%dT%H:%M:%S")
        except (ValueError, TypeError):
            date = datetime.now()

    parents = parents_str.split() if parents_str else []

    return Commit(
        sha=sha, author_name=author_name, author_email=author_email,
        date=date, subject=subject, body="", files=[],
        parents=parents,
    )


def _parse_numstat_lines(lines: list) -> list:
    """Parse numstat lines into FileChange objects."""
    files = []
    for line in lines:
        if not line:
            continue
        num_parts = line.split("\t")
        if len(num_parts) >= 3:
            add_str, del_str, path = num_parts[0], num_parts[1], num_parts[2]
            additions = int(add_str) if add_str.isdigit() else 0
            deletions = int(del_str) if del_str.isdigit() else 0
            files.append(FileChange(
                path=path, additions=additions,
                deletions=deletions, status="modified",
            ))
    return files


def get_branches(repo_path: str) -> list:
    """Get list of branches with their latest commit info."""
    raw = run_git(repo_path, ["branch", "-v", "--no-abbrev"])
    branches = []
    for line in raw.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        current = line.startswith("*")
        line = line.lstrip("* ").strip()
        parts = line.split(None, 2)
        if len(parts) >= 2:
            branches.append({
                "name": parts[0],
                "sha": parts[1],
                "current": current,
                "subject": parts[2] if len(parts) > 2 else "",
            })
    return branches


def get_tags(repo_path: str) -> list:
    """Get list of tags with their dates."""
    raw = run_git(repo_path, [
        "tag", "--sort=-creatordate",
        "--format=%(refname:short)%09%(creatordate:iso8601)%09%(objectname:short)",
    ])
    tags = []
    for line in raw.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) >= 2:
            tags.append({
                "name": parts[0],
                "date": parts[1],
                "sha": parts[2] if len(parts) > 2 else "",
            })
    return tags


def get_file_at_commit(repo_path: str, sha: str, path: str) -> Optional[str]:
    """Get file content at a specific commit."""
    try:
        return run_git(repo_path, ["show", f"{sha}:{path}"], timeout=10)
    except Exception:
        return None
