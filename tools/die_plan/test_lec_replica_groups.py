"""replica_groups: exact per-bucket support grouping (LEC-TOOL-3, Q2n2 OOM fix)."""
import random
import tracemalloc

import lec


def _old_groups(d, points, compare):
    # Pre-LEC-TOOL-3 reference: one design-wide bitset per node.
    norm = lambda k: lec.GENCOPY.sub(lambda m: m[0].split("[")[0] + "[]", k)
    symbols = {}
    def sym(k):
        if k not in symbols:
            symbols[k] = 1 << len(symbols)
        return symbols[k]
    support = [0] * (d["I"] + d["L"] + d["A"] + 1)
    for v in range(1, d["I"] + d["L"] + 1):
        support[v] = sym(("anonymous", v))
    for k, lit in sorted(points.items()):
        support[lit >> 1] = 0 if k.startswith("ff:") else sym(("point", k))
    base = d["I"] + d["L"] + 1
    for i in range(d["A"]):
        support[base+i] = support[d["ands"][2*i] >> 1] | support[d["ands"][2*i+1] >> 1]
    out = {}
    for k, lit in compare.items():
        if k.startswith("ff:") and lec.GENCOPY.search(k):
            out.setdefault((norm(k), support[lit >> 1]), []).append(k)
    return out


def _canon(g):
    return sorted(sorted(v) for v in g.values())


def _random_design(rng, I, L, A):
    base = I + L + 1
    ands = []
    for i in range(A):
        hi = base + i
        ands += [2 * rng.randrange(0, hi) + rng.randrange(2), 2 * rng.randrange(0, hi) + rng.randrange(2)]
    d = {"I": I, "L": L, "A": A, "ands": ands}
    nv = base + A
    points = {}
    for j in range(I):
        points["in:x[%d]" % j] = 2 * (1 + j)
    for j in range(L):
        points["ff:g_c[%d].q[%d]" % (j % 4, j)] = 2 * (1 + I + j)
    if rng.random() < .5:
        points["in:k"] = 0                      # constant-node point edge case
    compare = {}
    for j in range(3 * L):
        name = rng.choice(["ff:g_a[%d].r" % j, "ff:g_b[%d].s[%d]" % (j % 5, j), "ff:plain%d" % j,
                           "ff:g_a[%d].u.g_z[%d].v" % (j % 3, j)])
        compare[name] = 2 * rng.randrange(0, nv) + rng.randrange(2)
    return d, points, compare


def test_replica_groups_identical_to_reference_on_random_aigs():
    rng = random.Random(7)
    for _ in range(300):
        d, p, c = _random_design(rng, rng.randrange(1, 12), rng.randrange(1, 10), rng.randrange(0, 60))
        assert _canon(lec.replica_groups(d, p, c)) == _canon(_old_groups(d, p, c))


def test_replica_groups_mutant_distinct_input_splits_cohort():
    # g_a[0].r = x0 & q0, g_a[1].r = x0 & q1 (state copies interchangeable) -> one cohort;
    # mutant: g_a[1].r = x1 & q1 (different primary input) -> must split.
    I, L = 2, 2
    base = I + L + 1
    d = {"I": I, "L": L, "A": 2, "ands": [2, 6, 2, 8]}
    p = {"in:x[0]": 2, "in:x[1]": 4, "ff:g_c[0].q[0]": 6, "ff:g_c[1].q[1]": 8}
    c = {"ff:g_a[0].r": 2 * base, "ff:g_a[1].r": 2 * (base + 1)}
    assert _canon(lec.replica_groups(d, p, c)) == [["ff:g_a[0].r", "ff:g_a[1].r"]]
    d["ands"] = [2, 6, 4, 8]
    assert _canon(lec.replica_groups(d, p, c)) == [["ff:g_a[0].r"], ["ff:g_a[1].r"]]


def test_replica_groups_memory_bounded_on_wide_design():
    # 200k inputs, 400k ANDs, small replicated cohorts: the reference holds a
    # 200k-bit int per node (~GBs); the bucketed form must stay tiny.
    rng = random.Random(3)
    I, L, A = 200000, 16, 400000
    base = I + L + 1
    ands = []
    for i in range(A):
        if i < I // 2:
            ands += [2 * (1 + 2 * i), 2 * (2 + 2 * i)]       # pairwise layer over all inputs
        else:
            hi = base + i
            ands += [2 * rng.randrange(base, hi), 2 * rng.randrange(base, hi)]
    d = {"I": I, "L": L, "A": A, "ands": ands}
    p = {"ff:g_c[%d].q" % j: 2 * (1 + I + j) for j in range(L)}
    c = {}
    for j in range(8):
        a = base + 4 * j
        c["ff:g_a[%d].r" % j] = 2 * a
    tracemalloc.start()
    g = lec.replica_groups(d, p, c)
    peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    assert len(sum(g.values(), [])) == 8
    assert peak < 50 * 2**20
