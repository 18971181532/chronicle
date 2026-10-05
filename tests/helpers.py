"""Test helpers — create temporary git repos with sample history."""

import os
import subprocess
import tempfile
from datetime import datetime, timedelta


def make_commit(repo, filename, content, author_name="Test Author",
                author_email="test@example.com", message=None, date=None):
    """Create a file and commit it in the given repo."""
    path = os.path.join(repo, filename)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    subprocess.run(["git", "-C", repo, "add", filename], capture_output=True)
    env = os.environ.copy()
    env["GIT_AUTHOR_NAME"] = author_name
    env["GIT_AUTHOR_EMAIL"] = author_email
    env["GIT_COMMITTER_NAME"] = author_name
    env["GIT_COMMITTER_EMAIL"] = author_email
    if date:
        env["GIT_AUTHOR_DATE"] = date
        env["GIT_COMMITTER_DATE"] = date
    msg = message or f"Add {filename}"
    subprocess.run(["git", "-C", repo, "commit", "-m", msg],
                   capture_output=True, env=env)


def create_temp_repo():
    """Create a temporary git repo with sample commit history."""
    repo = tempfile.mkdtemp(prefix="chronicle_test_")
    subprocess.run(["git", "init", "-b", "main", repo], capture_output=True)
    subprocess.run(["git", "-C", repo, "config", "user.name", "Test Author"], capture_output=True)
    subprocess.run(["git", "-C", repo, "config", "user.email", "test@example.com"], capture_output=True)

    base_date = datetime(2024, 1, 15, 10, 0, 0)

    # Author 1: several commits
    make_commit(repo, "src/main.py", "print('hello')\n",
                author_name="Alice", author_email="alice@example.com",
                message="Initial main module",
                date=base_date.strftime("%Y-%m-%dT%H:%M:%S"))

    make_commit(repo, "src/utils.py", "def helper():\n    return 42\n",
                author_name="Alice", author_email="alice@example.com",
                message="Add utility functions",
                date=(base_date + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S"))

    make_commit(repo, "src/main.py", "print('hello world')\nfrom utils import helper\n",
                author_name="Alice", author_email="alice@example.com",
                message="Update main to use utils",
                date=(base_date + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%S"))

    # Author 2
    make_commit(repo, "tests/test_main.py", "def test_main():\n    assert True\n",
                author_name="Bob", author_email="bob@example.com",
                message="Add tests for main",
                date=(base_date + timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%S"))

    make_commit(repo, "src/utils.py", "def helper():\n    return 42\n\ndef helper2():\n    return 99\n",
                author_name="Bob", author_email="bob@example.com",
                message="Add helper2 to utils",
                date=(base_date + timedelta(days=4)).strftime("%Y-%m-%dT%H:%M:%S"))

    # Author 3 touches shared files
    make_commit(repo, "src/main.py", "print('hello world')\nfrom utils import helper, helper2\n\nif __name__ == '__main__':\n    print(helper())\n",
                author_name="Carol", author_email="carol@example.com",
                message="Add main entry point",
                date=(base_date + timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%S"))

    make_commit(repo, "docs/README.md", "# Project\n\nA test project.\n",
                author_name="Carol", author_email="carol@example.com",
                message="Add documentation",
                date=(base_date + timedelta(days=6)).strftime("%Y-%m-%dT%H:%M:%S"))

    return repo
