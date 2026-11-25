"""LEC-PART-1 (COORD 11-25): coi_partition cuts an AIG to the sequential cone of influence of a compare point subset.
The kept latch set must be closed under the next-state relation and every kept next state must be the same function
of (inputs, kept state) as in the whole AIG.
    python3 -m pytest -q tools/die_plan/test_lec_partition.py"""
import importlib.util
import random
from array import array
from pathlib import Path

spec = importlib.util.spec_from_file_location("lec_part_ut", Path(__file__).resolve().parent / "lec.py")
lec = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lec)


def _aig(I, nexts, ands):
    a = array("q")
    for x, y in ands:
        a.extend((x, y))
    return dict(I=I, L=len(nexts), O=0, A=len(ands), latches=list(nexts), outputs=[], ands=a)


def _map(I, names):
    return {"input": {i: [(f"in{i}", 0)] for i in range(I)}, "output": {},
            "latch": {i: [(n + ".lecq", 0)] for i, n in enumerate(names)}}


def _eval(aig, inputs, state, lit):
    I, L = aig["I"], aig["L"]
    memo = {}

    def go(l):
        v = l >> 1
        if v == 0:
            r = 0
        elif v <= I:
            r = inputs[v - 1]
        elif v <= I + L:
            r = state[v - I - 1]
        else:
            if v not in memo:
                k = 2 * (v - I - L - 1)
                memo[v] = go(aig["ands"][k]) & go(aig["ands"][k + 1])
            r = memo[v]
        return r ^ (l & 1)
    return go(lit)


def test_small_cone_keeps_only_dependencies():
    # inputs a=1 (lit 2), b=2 (lit 4); latches p0=3, p1=4, q=5, q1=6; and 7 = a & p1, and 8 = p1 & b
    aig = _aig(2, [14, 16, 12, 2], [(2, 8), (8, 4)])
    amap = _map(2, ["p0", "p1", "q", "q1"])
    cut, cmap, info = lec.coi_partition(aig, amap, r"^ff:p0$")
    assert info["points"] == ["ff:p0"]
    assert info["latches_kept"] == 2 and cut["L"] == 2               # p0 and the p1 it reads, not q / q1
    assert sorted(n for v in cmap["latch"].values() for n, _ in v) == ["p0.lecq", "p1.lecq"]
    pis, cps, _, _, _ = lec.key_points(cut, cmap)
    assert set(cps) == {"ff:p0", "ff:p1"}
    for a in (0, 1):
        for b in (0, 1):
            for s1 in (0, 1):
                assert _eval(cut, [a, b], [0, s1], cps["ff:p0"]) == (a & s1)
                assert _eval(cut, [a, b], [0, s1], cps["ff:p1"]) == (s1 & b)


def test_exclude_and_bb_points():
    aig = _aig(1, [2, 3, 2], [])
    amap = _map(1, ["u.x", "u.m.lec_bbi_a[0]", "v.y"])
    _, _, info = lec.coi_partition(aig, amap, r"^(ff|bb):u\.", r"^ff:")
    assert info["points"] == ["bb:u.m.lec_bbi_a[0]"] and info["latches_kept"] == 1


def test_random_aigs_cut_is_closed_and_exact():
    rng = random.Random(7)
    for trial in range(60):
        I, L = rng.randint(1, 4), rng.randint(2, 9)
        ands = []
        for k in range(rng.randint(0, 25)):
            top = I + L + k            # highest variable defined so far
            ands.append(tuple(sorted((2 * rng.randint(0, top) | rng.randint(0, 1),
                                      2 * rng.randint(0, top) | rng.randint(0, 1)), reverse=True)))
        top = I + L + len(ands)
        nexts = [2 * rng.randint(0, top) | rng.randint(0, 1) for _ in range(L)]
        aig = _aig(I, nexts, ands)
        names = [f"r{i}" for i in range(L)]
        pick = sorted(rng.sample(range(L), rng.randint(1, L)))
        cut, cmap, info = lec.coi_partition(aig, _map(I, names), "^ff:(" + "|".join(f"r{i}" for i in pick) + ")$")
        kept = [cmap["latch"][n][0][0][:-5] for n in range(cut["L"])]
        assert set(f"r{i}" for i in pick) <= set(kept)
        old_idx = [names.index(k) for k in kept]
        for _ in range(16):
            ins = [rng.randint(0, 1) for _ in range(I)]
            full = [rng.randint(0, 1) for _ in range(L)]
            sub = [full[i] for i in old_idx]
            for n, oi in enumerate(old_idx):     # same next state from the kept state alone: the cut is closed
                assert _eval(cut, ins, sub, cut["latches"][n]) == _eval(aig, ins, full, nexts[oi])


_dspec = importlib.util.spec_from_file_location("lec_part_drv_ut", Path(__file__).resolve().parent / "lec_part.py")
drv = importlib.util.module_from_spec(_dspec)
_dspec.loader.exec_module(drv)


def test_driver_partitions_cover_every_point_once():
    pts = [f"ff:u_dut.u_core.u_la.r{i}[0]" for i in range(30)] + [f"bb:u_dut.u_core.u_lb.m.lec_bbi_a[{i}]" for i in range(20)] \
        + [f"po:out[{i}]" for i in range(5)] + ["ff:u_dut.u_rrl_3.q", "ff:u_dut.g[1].x[0]"]
    for n in (1, 2, 3, 6):
        parts = drv.plan(drv.auto_parts(pts, n, 3))
        seen = [p for inc, exc in parts for p in drv.selected(pts, inc, exc)]
        assert sorted(seen) == sorted(pts)             # every point in exactly one partition (rest bin is last)
    assert drv.prefix("ff:u_dut.g[1].x[0]", 2) == ("ff", "u_dut.g[1]")


def test_driver_explicit_regex_plus_rest():
    pts = ["bb:u.a.lec_bbi_x[0]", "ff:u.a.r[0]", "ff:u.b.r[0]"]
    parts = drv.plan([r"^bb:"])
    assert [drv.selected(pts, i, e) for i, e in parts] == [["bb:u.a.lec_bbi_x[0]"], ["ff:u.a.r[0]", "ff:u.b.r[0]"]]
