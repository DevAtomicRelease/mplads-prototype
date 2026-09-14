"""NumPy-only Isolation Forest (Liu, Ting & Zhou 2008). Vendored into six_source so
the canonical build has no cross-directory runtime dependency. Seeded and versioned;
output is descriptive full-snapshot atypicality, not a fraud probability or forecast."""
from __future__ import annotations

import math

import numpy as np

from common import SEED


def isolation_scores(matrix: np.ndarray, seed: int = SEED, tree_count: int = 100, sample_size: int = 256) -> np.ndarray:
    """Isolation Forest following Liu et al. (2008), implemented with NumPy only."""
    rng = np.random.default_rng(seed)
    matrix = np.asarray(matrix, dtype=float)
    medians = np.nanmedian(matrix, axis=0)
    matrix = np.where(np.isnan(matrix), medians, matrix)
    n = min(sample_size, len(matrix))
    if n < 2:
        return np.full(len(matrix), .5)
    max_depth = math.ceil(math.log2(n))

    def c(size):
        if size <= 1:
            return 0.0
        if size == 2:
            return 1.0
        return 2 * (math.log(size - 1) + np.euler_gamma) - 2 * (size - 1) / size

    def tree(train, depth):
        if depth >= max_depth or len(train) <= 1:
            return c(len(train))
        low, high = train.min(axis=0), train.max(axis=0)
        usable = np.flatnonzero(high > low)
        if not len(usable):
            return c(len(train))
        feature = int(rng.choice(usable))
        split = float(rng.uniform(low[feature], high[feature]))
        left = train[:, feature] < split
        return feature, split, tree(train[left], depth + 1), tree(train[~left], depth + 1)

    def walk(node, indexes, depth, total):
        if not isinstance(node, tuple):
            total[indexes] += depth + node
            return
        feature, split, left, right = node
        selected = matrix[indexes, feature] < split
        if selected.any():
            walk(left, indexes[selected], depth + 1, total)
        if (~selected).any():
            walk(right, indexes[~selected], depth + 1, total)

    lengths = np.zeros(len(matrix))
    for _ in range(tree_count):
        root = tree(matrix[rng.choice(len(matrix), n, replace=False)], 0)
        walk(root, np.arange(len(matrix)), 0, lengths)
    return np.power(2, -lengths / tree_count / c(n))
