"""Tests for authors module."""

import unittest
from datetime import datetime

from chronicle import authors
from chronicle.git_reader import Commit, FileChange


def make_commits():
    return [
        Commit(sha="a1", author_name="Alice", author_email="alice@example.com",
               date=datetime(2024, 1, 1, 10, 0), subject="First",
               files=[FileChange("a.py", 10, 2)]),
        Commit(sha="a2", author_name="Alice", author_email="alice@example.com",
               date=datetime(2024, 1, 2, 14, 0), subject="Second",
               files=[FileChange("b.py", 5, 0), FileChange("a.py", 3, 1)]),
        Commit(sha="b1", author_name="Bob", author_email="bob@example.com",
               date=datetime(2024, 1, 3, 9, 0), subject="Bob's commit",
               files=[FileChange("c.py", 20, 5)]),
    ]


class TestAnalyzeAuthors(unittest.TestCase):
    def setUp(self):
        self.commits = make_commits()
        self.stats = authors.analyze_authors(self.commits)

    def test_returns_dict(self):
        self.assertIsInstance(self.stats, dict)

    def test_author_count(self):
        self.assertEqual(len(self.stats), 2)

    def test_alice_stats(self):
        key = "Alice <alice@example.com>"
        self.assertIn(key, self.stats)
        a = self.stats[key]
        self.assertEqual(a["commits"], 2)
        self.assertEqual(a["additions"], 18)
        self.assertEqual(a["deletions"], 3)
        self.assertEqual(a["net_lines"], 15)
        self.assertEqual(a["files_touched"], 2)

    def test_bob_stats(self):
        key = "Bob <bob@example.com>"
        b = self.stats[key]
        self.assertEqual(b["commits"], 1)
        self.assertEqual(b["additions"], 20)
        self.assertEqual(b["deletions"], 5)

    def test_active_days(self):
        key = "Alice <alice@example.com>"
        self.assertEqual(self.stats[key]["active_days"], 2)

    def test_first_last_commit(self):
        key = "Alice <alice@example.com>"
        a = self.stats[key]
        self.assertIsNotNone(a["first_commit"])
        self.assertIsNotNone(a["last_commit"])

    def test_hourly_distribution(self):
        key = "Alice <alice@example.com>"
        a = self.stats[key]
        self.assertIn(10, a["hourly"])
        self.assertIn(14, a["hourly"])

    def test_empty_commits(self):
        stats = authors.analyze_authors([])
        self.assertEqual(len(stats), 0)


class TestRankAuthors(unittest.TestCase):
    def setUp(self):
        self.stats = authors.analyze_authors(make_commits())

    def test_rank_by_commits(self):
        ranked = authors.rank_authors(self.stats, "commits")
        self.assertEqual(ranked[0][0], "Alice <alice@example.com>")

    def test_rank_by_additions(self):
        ranked = authors.rank_authors(self.stats, "additions")
        self.assertEqual(ranked[0][0], "Bob <bob@example.com>")

    def test_invalid_sort_falls_back(self):
        ranked = authors.rank_authors(self.stats, "invalid")
        self.assertEqual(len(ranked), 2)

    def test_returns_list(self):
        ranked = authors.rank_authors(self.stats)
        self.assertIsInstance(ranked, list)


class TestGetAuthorTimeline(unittest.TestCase):
    def test_daily(self):
        tl = authors.get_author_timeline(make_commits(), "Alice <alice@example.com>", "daily")
        self.assertEqual(tl["granularity"], "daily")
        self.assertIn("commits", tl)
        self.assertEqual(sum(tl["commits"].values()), 2)

    def test_monthly(self):
        tl = authors.get_author_timeline(make_commits(), "Alice <alice@example.com>", "monthly")
        self.assertEqual(tl["granularity"], "monthly")

    def test_unknown_author(self):
        tl = authors.get_author_timeline(make_commits(), "Nobody <no@example.com>", "daily")
        self.assertEqual(sum(tl["commits"].values()), 0)


if __name__ == "__main__":
    unittest.main()
