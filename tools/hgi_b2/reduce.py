"""B2 cross-cluster reduction in the golden's exact summation order.

The golden sum (hgi_sim.lib.csum) is: chunks of 8 elements summed sequentially from +0 (the tail chunk padded with
zeros), then a pairwise tree over the chunk sums padded with zero chunks to a power of two.  That order is reproduced
exactly by a LEFT-TO-RIGHT binary counter: push each finished chunk sum at level 0, combine the two top entries while
they are the same level (add(left, right)), and at the end pad with zero subtrees until one root of 2^p chunks remains.
The counter's state after any prefix is (stack of (level, value), the open chunk's partial sum, its element count), so
a row split into contiguous per-cluster ranges is reduced by passing that state cluster q -> q + 1 over the slice ring
(cluster 3 finalises).  Any split point is exact, including one inside a chunk.  State size per row:
<= log2(chunks) + 1 stack words + 1 partial + 1 count.
"""
from __future__ import annotations

import numpy as np

from hgi_sim import lib as A

F = np.float32
CH = A.CHUNK


class ChainState:
    """Binary-counter csum state for R rows (vectorised over rows)."""

    def __init__(self, rows):
        self.rows = rows
        self.stack = []                  # [(level, value[rows])], levels strictly decreasing
        self.part = np.zeros(rows, F)
        self.pn = 0                      # elements in the open chunk
        self.chunks = 0                  # finished chunks

    def words(self):
        return self.rows * (len(self.stack) + 2)

    def _push(self, lvl, v):
        while self.stack and self.stack[-1][0] == lvl:
            _, left = self.stack.pop()
            v = A.add(left, v)
            lvl += 1
        self.stack.append((lvl, v))

    def feed(self, t):
        """t [rows, k]: the next k elements of every row, in order."""
        t = np.asarray(t, F).reshape(self.rows, -1)
        for i in range(t.shape[1]):
            self.part = A.add(self.part, t[:, i])
            self.pn += 1
            if self.pn == CH:
                self._push(0, self.part)
                self.chunks += 1
                self.part, self.pn = np.zeros(self.rows, F), 0
        return self

    def finish(self):
        if self.pn or self.chunks == 0:              # the tail chunk, zero padded as the golden pads elements
            z = np.zeros(self.rows, F)
            while self.pn < CH:
                self.part = A.add(self.part, z)
                self.pn += 1
            self._push(0, self.part)
            self.chunks += 1
        P = 1
        while P < self.chunks:
            P <<= 1
        while self.chunks < P:                       # zero chunks to the power of two (the golden's zero padding)
            self._push(0, np.zeros(self.rows, F))
            self.chunks += 1
        assert len(self.stack) == 1
        return self.stack[0][1]


def chain(parts):
    """parts: per-cluster [rows, k_q] column blocks of one reduction in order -> (sums, max state words on a hop)."""
    parts = [np.asarray(p, F).reshape(1, -1) if np.ndim(p) == 1 else np.asarray(p, F) for p in parts]
    st = ChainState(parts[0].shape[0])
    hop = 0
    for q, p in enumerate(parts):
        st.feed(p)
        if q < len(parts) - 1:
            hop = max(hop, st.words())
    return st.finish(), hop


def selftest(seed=1):
    rng = np.random.default_rng(seed)
    bad = 0
    for n in (1, 7, 8, 9, 64, 100, 1024, 1280, 4096, 5120, 12288, 20480, 2048 + 3):
        for rows in (1, 3):
            t = (rng.standard_normal((rows, n)) * rng.choice([1e-3, 1, 1e3], (rows, n))).astype(F)
            g = A.csum(t)
            for cuts in ([n // 4, n // 2, 3 * n // 4], sorted(rng.integers(0, n + 1, 3).tolist()), [0, 0, n]):
                b = [0] + list(cuts) + [n]
                s, _ = chain([t[:, b[i]:b[i + 1]] for i in range(4)])
                bad += int(not np.array_equal(np.asarray(s, F).view(np.uint32), np.asarray(g, F).reshape(-1).view(np.uint32)))
    return bad


if __name__ == "__main__":
    import sys
    b = selftest()
    print("csum chain vs golden csum: mismatches", b)
    sys.exit(1 if b else 0)
