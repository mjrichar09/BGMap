import numpy as np
import pandas as pd

from evaluate import dominant_publisher_clusters, find_games, neighbor_correlation, overlap, random_neighbors, shared_tag_rate, tag_matrix


def test_shared_tag_rate_and_random_baseline():
    tags = pd.Series([["a"], ["a"], ["b"], ["b"], []])
    m = tag_matrix(tags)
    nbrs = np.array([[1], [0], [3], [2], [0]])
    assert shared_tag_rate(m, nbrs) == 1.0  # untagged game 4 is excluded
    swapped = np.array([[2], [3], [0], [1], [0]])
    assert shared_tag_rate(m, swapped) == 0.0
    assert shared_tag_rate(m, nbrs, rows=np.array([True, False, False, False, False])) == 1.0


def test_tag_matrix_drops_generic_values():
    m = tag_matrix(pd.Series([["(Self-Published)"], ["(Self-Published)"]]), {"(Self-Published)"})
    assert m.sum() == 0


def test_random_neighbors_never_self():
    r = random_neighbors(50, 10)
    assert r.shape == (50, 10) and (r != np.arange(50)[:, None]).all() and r.max() < 50


def test_neighbor_correlation():
    v = np.array([1.0, 1.1, 5.0, 5.1])
    assert neighbor_correlation(v, np.array([[1], [0], [3], [2]])) > 0.99
    assert neighbor_correlation(v, np.array([[2], [3], [0], [1]])) < -0.99


def test_overlap_allows_wider_window():
    assert overlap(np.array([[1, 2]]), np.array([[2, 9, 1]])) == 1.0
    assert overlap(np.array([[1, 2]]), np.array([[2, 9]])) == 0.5


def test_dominant_publisher_and_find_games():
    df = pd.DataFrame({
        "name": ["Alpha", "Alpha", "Beta Deluxe"] + [f"g{i}" for i in range(17)],
        "rank": [5, 2, 3] + list(range(10, 27)),
        "cluster": [0] * 20,
        "cluster_label": ["Cards"] * 20,
        "publishers": [["Big Co"]] * 12 + [["(Unknown)"]] * 8,
    })
    flagged = dominant_publisher_clusters(df)
    assert flagged[0]["publisher"] == "Big Co" and flagged[0]["share"] == 0.6
    found = dict(find_games(df, ["alpha", "Beta", "Missing"]))
    assert found == {"alpha": 1, "Beta": 2, "Missing": None}  # best-ranked exact match; prefix fallback
