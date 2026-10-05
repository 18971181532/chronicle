"""Tests for network module."""

import unittest
from datetime import datetime

from chronicle import network
from chronicle.git_reader import Commit, FileChange


def make_commits():
    return [
        Commit(sha="a1", author_name="Alice", author_email="alice@example.com",
               date=datetime(2024, 1, 1), subject="t",
               files=[FileChange("src/main.py", 10, 2), FileChange("src/utils.py", 5, 0)]),
        Commit(sha="a2", author_name="Bob", author_email="bob@example.com",
               date=datetime(2024, 1, 2), subject="t",
               files=[FileChange("src/main.py", 3, 1), FileChange("tests/test.py", 8, 0)]),
        Commit(sha="a3", author_name="Carol", author_email="carol@example.com",
               date=datetime(2024, 1, 3), subject="t",
               files=[FileChange("src/utils.py", 2, 1), FileChange("src/main.py", 1, 0)]),
        Commit(sha="a4", author_name="Dave", author_email="dave@example.com",
               date=datetime(2024, 1, 4), subject="t",
               files=[FileChange("docs/readme.md", 20, 0)]),
    ]


class TestBuildCollaborationNetwork(unittest.TestCase):
    def setUp(self):
        self.net = network.build_collaboration_network(make_commits())

    def test_returns_dict(self):
        self.assertIsInstance(self.net, dict)
        self.assertIn("nodes", self.net)
        self.assertIn("edges", self.net)

    def test_node_count(self):
        self.assertEqual(self.net["node_count"], 4)

    def test_nodes_have_stats(self):
        for node in self.net["nodes"]:
            self.assertIn("id", node)
            self.assertIn("name", node)
            self.assertIn("commits", node)
            self.assertIn("degree", node)

    def test_edges_connect_collaborators(self):
        # Alice and Bob both touched src/main.py -> connected
        edge_keys = {(e["source"], e["target"]) for e in self.net["edges"]}
        found = False
        for (s, t) in edge_keys:
            if ("Alice" in s and "Bob" in t) or ("Bob" in s and "Alice" in t):
                found = True
        self.assertTrue(found, "Alice and Bob should be connected")

    def test_dave_isolated(self):
        # Dave only touched docs/readme.md, no one else did
        dave = next(n for n in self.net["nodes"] if "Dave" in n["id"])
        self.assertEqual(dave["degree"], 0)

    def test_edge_weight(self):
        # Alice and Carol share src/main.py and src/utils.py = weight 2
        for edge in self.net["edges"]:
            if ("Alice" in edge["source"] and "Carol" in edge["target"]) or \
               ("Carol" in edge["source"] and "Alice" in edge["target"]):
                self.assertEqual(edge["weight"], 2)

    def test_empty(self):
        net = network.build_collaboration_network([])
        self.assertEqual(net["node_count"], 0)
        self.assertEqual(net["edge_count"], 0)


class TestComputeCentrality(unittest.TestCase):
    def setUp(self):
        self.net = network.build_collaboration_network(make_commits())
        self.cent = network.compute_centrality(self.net)

    def test_returns_dict(self):
        self.assertIsInstance(self.cent, dict)

    def test_all_nodes_present(self):
        for node in self.net["nodes"]:
            self.assertIn(node["id"], self.cent)

    def test_degree_centrality_range(self):
        for nid, c in self.cent.items():
            self.assertGreaterEqual(c["degree_centrality"], 0)
            self.assertLessEqual(c["degree_centrality"], 1)

    def test_influence_score(self):
        for nid, c in self.cent.items():
            self.assertIn("influence_score", c)
            self.assertGreaterEqual(c["influence_score"], 0)

    def test_single_node(self):
        net = {"nodes": [{"id": "A", "commits": 5, "name": "A"}], "edges": []}
        cent = network.compute_centrality(net)
        self.assertEqual(cent["A"]["degree_centrality"], 0)


class TestFindClusters(unittest.TestCase):
    def setUp(self):
        self.net = network.build_collaboration_network(make_commits())
        self.clusters = network.find_clusters(self.net)

    def test_returns_list(self):
        self.assertIsInstance(self.clusters, list)

    def test_all_nodes_in_clusters(self):
        total = sum(len(c) for c in self.clusters)
        self.assertEqual(total, self.net["node_count"])

    def test_dave_in_own_cluster(self):
        # Dave is isolated, should be in his own cluster
        dave_cluster = [c for c in self.clusters if any("Dave" in n for n in c)]
        self.assertEqual(len(dave_cluster), 1)
        self.assertEqual(len(dave_cluster[0]), 1)

    def test_sorted_by_size(self):
        sizes = [len(c) for c in self.clusters]
        self.assertEqual(sizes, sorted(sizes, reverse=True))


class TestGetFileCollaborationMatrix(unittest.TestCase):
    def test_returns_dict(self):
        m = network.get_file_collaboration_matrix(make_commits(), top_files=10)
        self.assertIsInstance(m, dict)
        self.assertIn("files", m)
        self.assertIn("authors", m)
        self.assertIn("matrix", m)

    def test_main_py_has_multiple_authors(self):
        m = network.get_file_collaboration_matrix(make_commits(), top_files=10)
        main_row = next(r for r in m["matrix"] if r["file"] == "src/main.py")
        author_count = sum(main_row["authors"].values())
        self.assertEqual(author_count, 3)  # Alice, Bob, Carol

    def test_limit(self):
        m = network.get_file_collaboration_matrix(make_commits(), top_files=2)
        self.assertEqual(len(m["files"]), 2)


if __name__ == "__main__":
    unittest.main()
