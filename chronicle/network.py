"""Collaboration network analysis."""

from collections import defaultdict
import math


def build_collaboration_network(commits: list, min_shared_files: int = 1) -> dict:
    """
    Build a collaboration network between authors based on shared file edits.

    Two authors are connected if they have both modified the same file.
    Edge weight = number of shared files.

    Returns nodes (authors with stats) and edges (pairs with weight).
    """
    # Map file -> set of authors who touched it
    file_authors = defaultdict(set)
    author_files = defaultdict(set)
    author_commits = defaultdict(int)
    author_additions = defaultdict(int)

    for commit in commits:
        key = commit.author_key
        author_commits[key] += 1
        author_additions[key] += commit.total_additions
        for f in commit.files:
            file_authors[f.path].add(key)
            author_files[key].add(f.path)

    # Build edges
    edges = []
    seen_pairs = set()
    for path, authors in file_authors.items():
        author_list = sorted(authors)
        for i in range(len(author_list)):
            for j in range(i + 1, len(author_list)):
                pair = (author_list[i], author_list[j])
                if pair not in seen_pairs:
                    seen_pairs.add(pair)
                    # Count shared files
                    shared = author_files[pair[0]] & author_files[pair[1]]
                    if len(shared) >= min_shared_files:
                        edges.append({
                            "source": pair[0],
                            "target": pair[1],
                            "weight": len(shared),
                            "shared_files": sorted(list(shared))[:20],
                        })

    # Build nodes
    nodes = []
    for key in author_commits:
        files = author_files[key]
        # Degree = number of unique collaborators
        collaborators = set()
        for edge in edges:
            if edge["source"] == key:
                collaborators.add(edge["target"])
            elif edge["target"] == key:
                collaborators.add(edge["source"])
        nodes.append({
            "id": key,
            "name": key.split(" <")[0] if " <" in key else key,
            "email": key.split("<")[1].rstrip(">") if "<" in key else "",
            "commits": author_commits[key],
            "additions": author_additions[key],
            "files_touched": len(files),
            "degree": len(collaborators),
            "collaborators": sorted(list(collaborators)),
        })

    # Sort nodes by commit count
    nodes.sort(key=lambda x: x["commits"], reverse=True)
    edges.sort(key=lambda x: x["weight"], reverse=True)

    return {
        "nodes": nodes,
        "edges": edges,
        "node_count": len(nodes),
        "edge_count": len(edges),
    }


def compute_centrality(network: dict) -> dict:
    """
    Compute simple centrality metrics for each node.

    - degree_centrality: fraction of possible connections
    - betweenness (approximate): not full BFS, but weighted by edge weights
    - influence_score: commits * degree * avg_edge_weight
    """
    nodes = network["nodes"]
    edges = network["edges"]
    n = len(nodes)

    if n <= 1:
        return {node["id"]: {"degree_centrality": 0, "influence": 0} for node in nodes}

    # Degree centrality
    degree = defaultdict(int)
    weighted_degree = defaultdict(float)
    for edge in edges:
        degree[edge["source"]] += 1
        degree[edge["target"]] += 1
        weighted_degree[edge["source"]] += edge["weight"]
        weighted_degree[edge["target"]] += edge["weight"]

    centrality = {}
    for node in nodes:
        nid = node["id"]
        deg = degree.get(nid, 0)
        centrality[nid] = {
            "degree_centrality": round(deg / (n - 1), 4),
            "weighted_degree": weighted_degree.get(nid, 0),
            "influence_score": round(
                node["commits"] * math.sqrt(max(deg, 1)) * math.sqrt(max(weighted_degree.get(nid, 1), 1)),
                2,
            ),
        }

    return centrality


def find_clusters(network: dict, resolution: float = 1.0) -> list:
    """
    Simple community detection using connected components + greedy merging.

    Returns list of clusters, each containing node ids.
    """
    nodes = {n["id"] for n in network["nodes"]}
    edges = network["edges"]

    # Build adjacency
    adj = defaultdict(set)
    for edge in edges:
        if edge["weight"] >= resolution:
            adj[edge["source"]].add(edge["target"])
            adj[edge["target"]].add(edge["source"])

    # Find connected components (BFS)
    visited = set()
    clusters = []

    for node in nodes:
        if node in visited:
            continue
        cluster = []
        queue = [node]
        visited.add(node)
        while queue:
            current = queue.pop(0)
            cluster.append(current)
            for neighbor in adj.get(current, set()):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        clusters.append(sorted(cluster))

    clusters.sort(key=len, reverse=True)
    return clusters


def get_file_collaboration_matrix(commits: list, top_files: int = 30) -> dict:
    """
    Build a matrix of which authors collaborate on which files.

    Useful for identifying key files that require cross-team coordination.
    """
    file_authors = defaultdict(set)
    file_commits = defaultdict(int)

    for commit in commits:
        for f in commit.files:
            file_authors[f.path].add(commit.author_key)
            file_commits[f.path] += 1

    # Top files by commit count
    top = sorted(file_commits.items(), key=lambda x: x[1], reverse=True)[:top_files]

    all_authors = set()
    for _, _ in top:
        pass
    for path, _ in top:
        all_authors.update(file_authors[path])

    author_list = sorted(all_authors)

    matrix = []
    for path, count in top:
        row = {"file": path, "commits": count, "authors": {}}
        for author in author_list:
            row["authors"][author] = 1 if author in file_authors[path] else 0
        matrix.append(row)

    return {
        "files": [p for p, _ in top],
        "authors": author_list,
        "matrix": matrix,
    }
