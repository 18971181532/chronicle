"""Tests for git_reader module."""

import os
import shutil
import unittest
from datetime import datetime

from chronicle import git_reader
from chronicle.git_reader import Commit, FileChange
from tests.helpers import create_temp_repo


class TestFileChange(unittest.TestCase):
    def test_total(self):
        fc = FileChange(path="a.py", additions=10, deletions=5)
        self.assertEqual(fc.total, 15)

    def test_to_dict(self):
        fc = FileChange(path="a.py", additions=1, deletions=2, status="modified")
        d = fc.to_dict()
        self.assertEqual(d["path"], "a.py")
        self.assertEqual(d["additions"], 1)
        self.assertEqual(d["status"], "modified")


class TestCommit(unittest.TestCase):
    def test_short_sha(self):
        c = Commit(sha="abcdef1234567890", author_name="A", author_email="a@b.com",
                   date=datetime.now(), subject="test")
        self.assertEqual(c.short_sha, "abcdef1")

    def test_total_additions_deletions(self):
        c = Commit(sha="a", author_name="A", author_email="a@b.com",
                   date=datetime.now(), subject="t",
                   files=[FileChange("a.py", 5, 2), FileChange("b.py", 3, 1)])
        self.assertEqual(c.total_additions, 8)
        self.assertEqual(c.total_deletions, 3)

    def test_author_key(self):
        c = Commit(sha="a", author_name="Alice", author_email="alice@example.com",
                   date=datetime.now(), subject="t")
        self.assertEqual(c.author_key, "Alice <alice@example.com>")


class TestIsGitRepo(unittest.TestCase):
    def test_valid_repo(self):
        repo = create_temp_repo()
        try:
            self.assertTrue(git_reader.is_git_repo(repo))
        finally:
            shutil.rmtree(repo, ignore_errors=True)

    def test_invalid_repo(self):
        import tempfile
        d = tempfile.mkdtemp()
        try:
            self.assertFalse(git_reader.is_git_repo(d))
        finally:
            shutil.rmtree(d, ignore_errors=True)


class TestParseCommits(unittest.TestCase):
    def setUp(self):
        self.repo = create_temp_repo()

    def tearDown(self):
        shutil.rmtree(self.repo, ignore_errors=True)

    def test_returns_list(self):
        commits = git_reader.parse_commits(self.repo)
        self.assertIsInstance(commits, list)
        self.assertGreater(len(commits), 0)

    def test_commit_count(self):
        commits = git_reader.parse_commits(self.repo)
        self.assertEqual(len(commits), 7)

    def test_commit_fields(self):
        commits = git_reader.parse_commits(self.repo)
        c = commits[0]
        self.assertIsInstance(c, Commit)
        self.assertTrue(len(c.sha) >= 7)
        self.assertIsInstance(c.date, datetime)
        self.assertTrue(c.subject)

    def test_authors_present(self):
        commits = git_reader.parse_commits(self.repo)
        names = {c.author_name for c in commits}
        self.assertIn("Alice", names)
        self.assertIn("Bob", names)
        self.assertIn("Carol", names)

    def test_files_parsed(self):
        commits = git_reader.parse_commits(self.repo)
        all_files = set()
        for c in commits:
            for f in c.files:
                all_files.add(f.path)
        self.assertIn("src/main.py", all_files)
        self.assertIn("src/utils.py", all_files)

    def test_max_count(self):
        commits = git_reader.parse_commits(self.repo, max_count=3)
        self.assertEqual(len(commits), 3)

    def test_no_merges(self):
        commits = git_reader.parse_commits(self.repo)
        # Our test repo has no merge commits
        for c in commits:
            self.assertLessEqual(len(c.parents), 1)


class TestGetRepoInfo(unittest.TestCase):
    def setUp(self):
        self.repo = create_temp_repo()

    def tearDown(self):
        shutil.rmtree(self.repo, ignore_errors=True)

    def test_returns_dict(self):
        info = git_reader.get_repo_info(self.repo)
        self.assertIsInstance(info, dict)
        self.assertIn("branch", info)
        self.assertIn("head_sha", info)

    def test_branch_name(self):
        info = git_reader.get_repo_info(self.repo)
        self.assertEqual(info["branch"], "main")


class TestGetBranches(unittest.TestCase):
    def setUp(self):
        self.repo = create_temp_repo()

    def tearDown(self):
        shutil.rmtree(self.repo, ignore_errors=True)

    def test_returns_list(self):
        branches = git_reader.get_branches(self.repo)
        self.assertIsInstance(branches, list)
        self.assertGreater(len(branches), 0)

    def test_main_branch(self):
        branches = git_reader.get_branches(self.repo)
        names = [b["name"] for b in branches]
        self.assertIn("main", names)


if __name__ == "__main__":
    unittest.main()
