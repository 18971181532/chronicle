"""Tests for analyzer module."""

import json
import shutil
import unittest

from chronicle import analyzer
from chronicle.analyzer import AnalysisResult, analyze_repo, quick_summary
from tests.helpers import create_temp_repo


class TestAnalysisResult(unittest.TestCase):
    def test_to_dict(self):
        r = AnalysisResult("/tmp/repo")
        r.repo_info = {"branch": "main"}
        r.productivity = {"total_commits": 0}
        d = r.to_dict()
        self.assertIsInstance(d, dict)
        self.assertIn("repo", d)
        self.assertIn("summary", d)

    def test_to_json(self):
        r = AnalysisResult("/tmp/repo")
        r.repo_info = {"branch": "main"}
        r.productivity = {"total_commits": 0}
        j = r.to_json()
        data = json.loads(j)
        self.assertEqual(data["repo"]["branch"], "main")


class TestAnalyzeRepo(unittest.TestCase):
    def setUp(self):
        self.repo = create_temp_repo()

    def tearDown(self):
        shutil.rmtree(self.repo, ignore_errors=True)

    def test_returns_analysis_result(self):
        result = analyze_repo(self.repo)
        self.assertIsInstance(result, AnalysisResult)

    def test_commits_parsed(self):
        result = analyze_repo(self.repo)
        self.assertEqual(len(result.commits), 7)

    def test_repo_info(self):
        result = analyze_repo(self.repo)
        self.assertEqual(result.repo_info["branch"], "main")

    def test_author_stats(self):
        result = analyze_repo(self.repo)
        self.assertEqual(len(result.author_stats), 3)

    def test_file_stats(self):
        result = analyze_repo(self.repo)
        self.assertGreater(len(result.file_stats), 0)

    def test_timeline(self):
        result = analyze_repo(self.repo)
        self.assertGreater(len(result.timeline_monthly), 0)

    def test_heatmap(self):
        result = analyze_repo(self.repo)
        self.assertIsNotNone(result.heatmap)
        self.assertIn("weeks", result.heatmap)

    def test_network(self):
        result = analyze_repo(self.repo)
        self.assertIn("nodes", result.collab_network)
        self.assertGreater(result.collab_network["node_count"], 0)

    def test_centrality(self):
        result = analyze_repo(self.repo)
        self.assertIsInstance(result.centrality, dict)

    def test_clusters(self):
        result = analyze_repo(self.repo)
        self.assertIsInstance(result.clusters, list)

    def test_loc_trend(self):
        result = analyze_repo(self.repo)
        self.assertGreater(len(result.loc_trend), 0)

    def test_milestones(self):
        result = analyze_repo(self.repo)
        self.assertGreater(len(result.milestones), 0)

    def test_productivity(self):
        result = analyze_repo(self.repo)
        self.assertEqual(result.productivity["total_commits"], 7)

    def test_branches(self):
        result = analyze_repo(self.repo)
        self.assertGreater(len(result.branches), 0)

    def test_max_commits(self):
        result = analyze_repo(self.repo, max_commits=3)
        self.assertEqual(len(result.commits), 3)

    def test_no_network(self):
        result = analyze_repo(self.repo, include_network=False)
        self.assertEqual(result.collab_network, {})


class TestQuickSummary(unittest.TestCase):
    def setUp(self):
        self.repo = create_temp_repo()
        self.result = analyze_repo(self.repo)

    def tearDown(self):
        shutil.rmtree(self.repo, ignore_errors=True)

    def test_returns_string(self):
        s = quick_summary(self.result)
        self.assertIsInstance(s, str)

    def test_contains_key_info(self):
        s = quick_summary(self.result)
        self.assertIn("Commits", s)
        self.assertIn("Authors", s)

    def test_contains_top_contributors(self):
        s = quick_summary(self.result)
        self.assertIn("Top contributors", s)

    def test_contains_most_modified(self):
        s = quick_summary(self.result)
        self.assertIn("Most modified files", s)


if __name__ == "__main__":
    unittest.main()
