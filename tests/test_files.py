"""Tests for files module."""

import unittest
from datetime import datetime

from chronicle import files
from chronicle.git_reader import Commit, FileChange


def make_commits():
    return [
        Commit(sha="a1", author_name="Alice", author_email="alice@example.com",
               date=datetime(2024, 1, 1), subject="t",
               files=[FileChange("src/main.py", 10, 2), FileChange("src/utils.py", 5, 0)]),
        Commit(sha="a2", author_name="Bob", author_email="bob@example.com",
               date=datetime(2024, 1, 2), subject="t",
               files=[FileChange("src/main.py", 3, 1), FileChange("tests/test.py", 8, 0)]),
        Commit(sha="a3", author_name="Alice", author_email="alice@example.com",
               date=datetime(2024, 1, 3), subject="t",
               files=[FileChange("src/utils.py", 2, 1), FileChange("README.md", 20, 0)]),
    ]


class TestAnalyzeFiles(unittest.TestCase):
    def setUp(self):
        self.stats = files.analyze_files(make_commits())

    def test_returns_dict(self):
        self.assertIsInstance(self.stats, dict)

    def test_file_count(self):
        self.assertEqual(len(self.stats), 4)

    def test_main_py_stats(self):
        m = self.stats["src/main.py"]
        self.assertEqual(m["commits"], 2)
        self.assertEqual(m["additions"], 13)
        self.assertEqual(m["deletions"], 3)
        self.assertEqual(m["total_changes"], 16)

    def test_churn(self):
        m = self.stats["src/main.py"]
        self.assertEqual(m["churn"], 8.0)  # 16 total / 2 commits

    def test_authors_count(self):
        m = self.stats["src/main.py"]
        self.assertEqual(m["authors_count"], 2)

    def test_last_changed(self):
        m = self.stats["src/main.py"]
        self.assertIsNotNone(m["last_changed"])

    def test_empty(self):
        stats = files.analyze_files([])
        self.assertEqual(len(stats), 0)


class TestRankFiles(unittest.TestCase):
    def setUp(self):
        self.stats = files.analyze_files(make_commits())

    def test_rank_by_commits(self):
        ranked = files.rank_files(self.stats, "commits")
        self.assertEqual(ranked[0]["path"], "src/main.py")

    def test_rank_by_total_changes(self):
        ranked = files.rank_files(self.stats, "total_changes")
        # README has 20 changes, highest
        self.assertEqual(ranked[0]["path"], "README.md")

    def test_limit(self):
        ranked = files.rank_files(self.stats, "commits", 2)
        self.assertEqual(len(ranked), 2)

    def test_invalid_sort(self):
        ranked = files.rank_files(self.stats, "invalid")
        self.assertEqual(len(ranked), 4)


class TestGetFileExtensions(unittest.TestCase):
    def test_returns_dict(self):
        exts = files.get_file_extensions(files.analyze_files(make_commits()))
        self.assertIsInstance(exts, dict)
        self.assertIn(".py", exts)
        self.assertIn(".md", exts)

    def test_py_count(self):
        exts = files.get_file_extensions(files.analyze_files(make_commits()))
        self.assertEqual(exts[".py"]["files"], 3)

    def test_no_extension(self):
        stats = {"Makefile": {"path": "Makefile", "commits": 1, "additions": 0,
                               "deletions": 0, "total_changes": 0, "churn": 0,
                               "last_changed": None, "authors_count": 1, "authors": []}}
        exts = files.get_file_extensions(stats)
        self.assertIn("(no extension)", exts)


class TestGetDirectoryStats(unittest.TestCase):
    def test_depth_1(self):
        dirs = files.get_directory_stats(files.analyze_files(make_commits()), 1)
        self.assertIn("src", dirs)
        self.assertIn("tests", dirs)
        self.assertIn("(root)", dirs)

    def test_src_commits(self):
        dirs = files.get_directory_stats(files.analyze_files(make_commits()), 1)
        # src has main.py (2 commits) + utils.py (2 commits) = 4 commit-file pairs
        self.assertEqual(dirs["src"]["commits"], 4)


class TestGetHotspots(unittest.TestCase):
    def test_threshold(self):
        stats = files.analyze_files(make_commits())
        hotspots = files.get_hotspots(stats, threshold=2)
        self.assertEqual(len(hotspots), 2)  # main.py and utils.py

    def test_high_threshold(self):
        stats = files.analyze_files(make_commits())
        hotspots = files.get_hotspots(stats, threshold=100)
        self.assertEqual(len(hotspots), 0)


if __name__ == "__main__":
    unittest.main()
