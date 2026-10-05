"""Tests for timeline module."""

import unittest
from datetime import datetime

from chronicle import timeline
from chronicle.git_reader import Commit, FileChange


def make_commits():
    return [
        Commit(sha="a1", author_name="A", author_email="a@b.com",
               date=datetime(2024, 1, 1, 10, 0), subject="t",
               files=[FileChange("a.py", 5, 1)]),
        Commit(sha="a2", author_name="B", author_email="b@b.com",
               date=datetime(2024, 1, 1, 14, 0), subject="t",
               files=[FileChange("b.py", 3, 0)]),
        Commit(sha="a3", author_name="A", author_email="a@b.com",
               date=datetime(2024, 1, 15, 9, 0), subject="t",
               files=[FileChange("a.py", 2, 1)]),
        Commit(sha="a4", author_name="A", author_email="a@b.com",
               date=datetime(2024, 2, 1, 11, 0), subject="t",
               files=[FileChange("c.py", 10, 2)]),
    ]


class TestAggregateTimeline(unittest.TestCase):
    def test_daily(self):
        tl = timeline.aggregate_timeline(make_commits(), "daily")
        self.assertIsInstance(tl, dict)
        self.assertIn("2024-01-01", tl)
        self.assertEqual(tl["2024-01-01"]["commits"], 2)

    def test_monthly(self):
        tl = timeline.aggregate_timeline(make_commits(), "monthly")
        self.assertIn("2024-01", tl)
        self.assertIn("2024-02", tl)
        self.assertEqual(tl["2024-01"]["commits"], 3)
        self.assertEqual(tl["2024-02"]["commits"], 1)

    def test_weekly(self):
        tl = timeline.aggregate_timeline(make_commits(), "weekly")
        self.assertIsInstance(tl, dict)
        self.assertGreater(len(tl), 0)

    def test_additions_deletions(self):
        tl = timeline.aggregate_timeline(make_commits(), "daily")
        self.assertEqual(tl["2024-01-01"]["additions"], 8)
        self.assertEqual(tl["2024-01-01"]["deletions"], 1)

    def test_net(self):
        tl = timeline.aggregate_timeline(make_commits(), "daily")
        self.assertEqual(tl["2024-01-01"]["net"], 7)

    def test_authors_count(self):
        tl = timeline.aggregate_timeline(make_commits(), "daily")
        self.assertEqual(tl["2024-01-01"]["authors"], 2)

    def test_empty(self):
        tl = timeline.aggregate_timeline([], "daily")
        self.assertEqual(len(tl), 0)


class TestBuildHeatmap(unittest.TestCase):
    def test_returns_dict(self):
        hm = timeline.build_heatmap(make_commits())
        self.assertIsInstance(hm, dict)
        self.assertIn("weeks", hm)
        self.assertIn("max_count", hm)
        self.assertIn("total", hm)

    def test_total_commits(self):
        hm = timeline.build_heatmap(make_commits())
        self.assertEqual(hm["total"], 4)

    def test_weeks_structure(self):
        hm = timeline.build_heatmap(make_commits())
        self.assertIsInstance(hm["weeks"], list)
        if hm["weeks"]:
            self.assertEqual(len(hm["weeks"][0]), 7)  # 7 days per week

    def test_cell_structure(self):
        hm = timeline.build_heatmap(make_commits())
        for week in hm["weeks"]:
            for cell in week:
                self.assertIn("date", cell)
                self.assertIn("count", cell)
                self.assertIn("level", cell)

    def test_level_range(self):
        hm = timeline.build_heatmap(make_commits())
        for week in hm["weeks"]:
            for cell in week:
                self.assertGreaterEqual(cell["level"], 0)
                self.assertLessEqual(cell["level"], 4)

    def test_empty(self):
        hm = timeline.build_heatmap([])
        self.assertEqual(hm["total"], 0)
        self.assertEqual(hm["max_count"], 0)


class TestBusiestPeriods(unittest.TestCase):
    def test_returns_list(self):
        periods = timeline.get_busiest_periods(make_commits())
        self.assertIsInstance(periods, list)

    def test_busiest_first(self):
        periods = timeline.get_busiest_periods(make_commits())
        self.assertEqual(periods[0]["date"], "2024-01-01")
        self.assertEqual(periods[0]["commits"], 2)

    def test_limit(self):
        periods = timeline.get_busiest_periods(make_commits(), top_n=2)
        self.assertEqual(len(periods), 2)


class TestHourlyDistribution(unittest.TestCase):
    def test_returns_24_hours(self):
        h = timeline.get_hourly_distribution(make_commits())
        self.assertEqual(len(h), 24)

    def test_counts(self):
        h = timeline.get_hourly_distribution(make_commits())
        self.assertEqual(h["10"], 1)
        self.assertEqual(h["14"], 1)
        self.assertEqual(h["9"], 1)
        self.assertEqual(h["11"], 1)


class TestWeekdayDistribution(unittest.TestCase):
    def test_returns_7_days(self):
        w = timeline.get_weekday_distribution(make_commits())
        self.assertEqual(len(w), 7)

    def test_keys(self):
        w = timeline.get_weekday_distribution(make_commits())
        for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]:
            self.assertIn(day, w)


if __name__ == "__main__":
    unittest.main()
