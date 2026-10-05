"""Tests for trend module."""

import unittest
from datetime import datetime

from chronicle import trend
from chronicle.git_reader import Commit, FileChange


def make_commits():
    return [
        Commit(sha="a1", author_name="A", author_email="a@b.com",
               date=datetime(2024, 1, 1), subject="Initial",
               files=[FileChange("main.py", 50, 0)]),
        Commit(sha="a2", author_name="A", author_email="a@b.com",
               date=datetime(2024, 1, 15), subject="Add feature",
               files=[FileChange("main.py", 30, 10), FileChange("utils.py", 20, 0)]),
        Commit(sha="a3", author_name="B", author_email="b@b.com",
               date=datetime(2024, 2, 1), subject="Refactor",
               files=[FileChange("main.py", 10, 20)]),
        Commit(sha="a4", author_name="B", author_email="b@b.com",
               date=datetime(2024, 2, 15), subject="Docs",
               files=[FileChange("README.md", 100, 0)]),
    ]


class TestComputeLOCTrend(unittest.TestCase):
    def test_returns_dict(self):
        loc = trend.compute_loc_trend(make_commits(), "monthly")
        self.assertIsInstance(loc, dict)

    def test_months_present(self):
        loc = trend.compute_loc_trend(make_commits(), "monthly")
        self.assertIn("2024-01", loc)
        self.assertIn("2024-02", loc)

    def test_cumulative_additions(self):
        loc = trend.compute_loc_trend(make_commits(), "monthly")
        self.assertEqual(loc["2024-01"]["cumulative_additions"], 100)
        self.assertEqual(loc["2024-02"]["cumulative_additions"], 210)

    def test_estimated_loc(self):
        loc = trend.compute_loc_trend(make_commits(), "monthly")
        # Jan: 50+30+20 - 10 = 90
        self.assertEqual(loc["2024-01"]["estimated_loc"], 90)
        # Feb: 90 + 10+100 - 20 = 180
        self.assertEqual(loc["2024-02"]["estimated_loc"], 180)

    def test_commits_per_period(self):
        loc = trend.compute_loc_trend(make_commits(), "monthly")
        self.assertEqual(loc["2024-01"]["commits"], 2)
        self.assertEqual(loc["2024-02"]["commits"], 2)

    def test_daily(self):
        loc = trend.compute_loc_trend(make_commits(), "daily")
        self.assertIn("2024-01-01", loc)

    def test_empty(self):
        loc = trend.compute_loc_trend([], "monthly")
        self.assertEqual(len(loc), 0)


class TestComputeGrowthRate(unittest.TestCase):
    def test_returns_dict(self):
        loc = trend.compute_loc_trend(make_commits(), "monthly")
        rates = trend.compute_growth_rate(loc)
        self.assertIsInstance(rates, dict)

    def test_feb_growth(self):
        loc = trend.compute_loc_trend(make_commits(), "monthly")
        rates = trend.compute_growth_rate(loc)
        self.assertIn("2024-02", rates)
        # Jan LOC=90, Feb LOC=180 -> growth = 100%
        self.assertEqual(rates["2024-02"]["growth_rate_pct"], 100.0)

    def test_absolute_change(self):
        loc = trend.compute_loc_trend(make_commits(), "monthly")
        rates = trend.compute_growth_rate(loc)
        self.assertEqual(rates["2024-02"]["absolute_change"], 90)

    def test_single_period(self):
        loc = {"2024-01": {"estimated_loc": 100}}
        rates = trend.compute_growth_rate(loc)
        self.assertEqual(len(rates), 0)


class TestGetMajorMilestones(unittest.TestCase):
    def test_returns_list(self):
        milestones = trend.get_major_milestones(make_commits())
        self.assertIsInstance(milestones, list)

    def test_sorted_by_size(self):
        milestones = trend.get_major_milestones(make_commits())
        sizes = [m["total"] for m in milestones]
        self.assertEqual(sizes, sorted(sizes, reverse=True))

    def test_docs_commit_largest(self):
        milestones = trend.get_major_milestones(make_commits())
        # README commit has 100 additions, largest
        self.assertEqual(milestones[0]["subject"], "Docs")

    def test_fields(self):
        milestones = trend.get_major_milestones(make_commits())
        m = milestones[0]
        self.assertIn("sha", m)
        self.assertIn("author", m)
        self.assertIn("date", m)
        self.assertIn("additions", m)
        self.assertIn("deletions", m)
        self.assertIn("files_changed", m)

    def test_limit(self):
        milestones = trend.get_major_milestones(make_commits(), top_n=2)
        self.assertEqual(len(milestones), 2)


class TestGetCommitSizeDistribution(unittest.TestCase):
    def test_returns_dict(self):
        dist = trend.get_commit_size_distribution(make_commits())
        self.assertIsInstance(dist, dict)

    def test_all_bins_present(self):
        dist = trend.get_commit_size_distribution(make_commits())
        for bin_name in ["tiny (1-10)", "small (11-50)", "medium (51-200)", "large (201-1000)", "huge (1000+)"]:
            self.assertIn(bin_name, dist)

    def test_total(self):
        dist = trend.get_commit_size_distribution(make_commits())
        self.assertEqual(sum(dist.values()), 4)

    def test_docs_in_medium(self):
        dist = trend.get_commit_size_distribution(make_commits())
        # Docs commit: 100 additions -> medium (51-200)
        self.assertGreaterEqual(dist["medium (51-200)"], 1)


class TestGetProductivityMetrics(unittest.TestCase):
    def test_returns_dict(self):
        p = trend.get_productivity_metrics(make_commits())
        self.assertIsInstance(p, dict)

    def test_total_commits(self):
        p = trend.get_productivity_metrics(make_commits())
        self.assertEqual(p["total_commits"], 4)

    def test_authors(self):
        p = trend.get_productivity_metrics(make_commits())
        self.assertEqual(p["authors"], 2)

    def test_total_additions(self):
        p = trend.get_productivity_metrics(make_commits())
        self.assertEqual(p["total_additions"], 210)

    def test_total_deletions(self):
        p = trend.get_productivity_metrics(make_commits())
        self.assertEqual(p["total_deletions"], 30)

    def test_net_lines(self):
        p = trend.get_productivity_metrics(make_commits())
        self.assertEqual(p["net_lines"], 180)

    def test_files_touched(self):
        p = trend.get_productivity_metrics(make_commits())
        self.assertEqual(p["files_touched"], 3)

    def test_active_days(self):
        p = trend.get_productivity_metrics(make_commits())
        self.assertEqual(p["active_days"], 4)

    def test_empty(self):
        p = trend.get_productivity_metrics([])
        self.assertEqual(p["total_commits"], 0)


if __name__ == "__main__":
    unittest.main()
