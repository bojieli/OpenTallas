"""LEC-SPEED: the inlined node translation in Lec.build (FAST_BUILD) must build the bit-identical AIG as the
original per-node Aig.AND path, and must still expose a non-equivalence."""
import random
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lec

NI, NL = 6, 5


def design(seed, flip_and=None, xors=True):
    """random AIGER dict: NI inputs, NL latches, ANDs over earlier literals; with explicit AIG XOR patterns."""
    rnd = random.Random(seed)
    ands, n = [], NI + NL

    def lit_pool():
        return [2 * v + c for v in range(1, n + 1) for c in (0, 1)] + [0, 1]

    for k in range(60):
        pool = lit_pool()
        if xors and k % 7 == 3:
            x, y = rnd.choice(pool), rnd.choice(pool)
            a = [x, y ^ 1]
            b = [x ^ 1, y]
            ands += [max(a), min(a)]            # AND(x, ~y)
            n += 1
            ands += [max(b), min(b)]            # AND(~x, y)
            n += 1
            p, q = 2 * (n - 1), 2 * n
            ands += [max(p ^ 1, q ^ 1), min(p ^ 1, q ^ 1)]   # ~(~p & ~q) is XOR(x, y) after the final complement
            n += 1
        else:
            ands += sorted([rnd.choice(pool), rnd.choice(pool)], reverse=True)
            n += 1
    if flip_and is not None:
        ands[flip_and] ^= 1
    pool = [2 * v + c for v in range(1, n + 1) for c in (0, 1)]
    latches = [rnd.choice(pool[-40:]) for _ in range(NL)]
    d = {"I": NI, "L": NL, "A": len(ands) // 2, "latches": latches, "ands": ands, "outputs": []}
    amap = {"input": {}, "output": {}, "latch": {i: [(f"u.r{i}$_DFF_P_.lecq", 0)] for i in range(NL)}}
    return d, amap


def built(gold, gate, fast, monkeypatch):
    monkeypatch.setattr(lec, "FAST_BUILD", fast)
    L = lec.Lec(gold[0], gold[1], gate[0], gate[1])
    m, kind = L.build()
    return L, m, kind


def test_fast_build_is_bit_identical_to_the_original_path(monkeypatch):
    for seed in range(12):
        g, t = design(seed), design(seed + 100)
        _, a, ka = built(g, t, False, monkeypatch)
        _, b, kb = built(g, t, True, monkeypatch)
        assert list(a.ands) == list(b.ands) and a.outs == b.outs and a.onames == b.onames
        assert a.strash == b.strash and ka == kb and a.ni == b.ni


def test_equal_designs_stay_proved_and_a_mutant_is_still_caught(monkeypatch):
    g = design(7)
    for fast in (False, True):
        _, m, _ = built(g, design(7), fast, monkeypatch)
        val, mask = m.simulate(8, seed=5)
        assert m.outs and all(lec.lit_val(val, mask, o) == 0 for o in m.outs)
    found = 0
    for idx in range(0, 120, 3):
        mut = design(7, flip_and=idx)
        res = []
        for fast in (False, True):
            _, m, _ = built(g, mut, fast, monkeypatch)
            val, mask = m.simulate(8, seed=5)
            res.append([lec.lit_val(val, mask, o) for o in m.outs])
        assert res[0] == res[1]
        found += any(res[1])
    assert found > 0          # a flipped gate input is observable: the fast path reports the difference


def test_build_memo_reuses_only_an_unchanged_state(monkeypatch):
    g, t = design(3), design(4)
    L = lec.Lec(g[0], g[1], t[0], t[1])
    m1, k1 = L.build_memo()
    dl = dict(L.dlit)
    L.dlit = {}                      # something else clobbered the attributes build() sets
    m2, k2 = L.build_memo()
    assert m2 is m1 and k2 == k1 and L.dlit == dl          # hit: same AIG, attributes restored
    ref, kref = L.build(with_compare=False, with_hyp=False)
    assert list(ref.ands) == list(m1.ands) and kref == k1
    L.hyp[("both", "ff:u.r0")] = ("const", 1)              # a new hypothesis changes the AIG: no stale hit
    m3, _ = L.build_memo()
    assert m3 is not m1
    ref3, _ = L.build(with_compare=False, with_hyp=False)
    assert list(ref3.ands) == list(m3.ands)
    monkeypatch.setenv("OT_LEC_BUILD_MEMO_CHECK", "1")     # check mode rebuilds on a hit and compares
    L.build_memo()
    L.build_memo()


def test_build_memo_off_matches_on(monkeypatch):
    g, t = design(5), design(6)
    res = []
    for flag in (False, True):
        monkeypatch.setattr(lec, "BUILD_MEMO", flag)
        L = lec.Lec(g[0], g[1], t[0], t[1])
        L.build_memo()
        m, _ = L.build_memo()
        res.append((list(m.ands), dict(L.dlit)))
    assert res[0] == res[1]


# ---- automatic cone partitioning (autopart) ----
def _parts(verdicts, sel):
    return [dict(name=f"p{i}", include="x", exclude=None, selected=s, verdict=v, counts=dict(differs=int(v == "NOT EQUIVALENT"), undecided=0),
                 reason=f"r{i}", failing=[dict(point=s[0])] if v == "NOT EQUIVALENT" else [])
            for i, (v, s) in enumerate(zip(verdicts, sel))]


def test_autopart_plan_covers_every_point_once():
    pts = [f"ff:u{i % 7}.a.b.c{i}" for i in range(500)] + ["po:o[0]", "bb:x.y"]
    inc = lec.autopart_includes(pts, 4)
    plan = lec.autopart_plan(inc)
    cnt = {p: 0 for p in pts}
    for i, e in plan:
        for p in lec.autopart_select(pts, i, e):
            cnt[p] += 1
    assert set(cnt.values()) == {1}


def test_autopart_merge_equivalent_only_when_all_equivalent_and_covered():
    pts = ["ff:a", "ff:b", "ff:c"]
    ok = lec.autopart_merge(pts, _parts(["EQUIVALENT"] * 2, [["ff:a", "ff:b"], ["ff:c"]]), {})
    assert ok["verdict"] == "EQUIVALENT" and ok["counts"]["proved"] == 3
    neq = lec.autopart_merge(pts, _parts(["EQUIVALENT", "NOT EQUIVALENT"], [["ff:a", "ff:b"], ["ff:c"]]), {})
    assert neq["verdict"] == "NOT EQUIVALENT" and neq["failing"][0]["point"] == "ff:c"
    unp = lec.autopart_merge(pts, _parts(["EQUIVALENT", "UNPROVEN"], [["ff:a", "ff:b"], ["ff:c"]]), {})
    assert unp["verdict"] == "UNPROVEN"


def test_autopart_coverage_gap_is_refused():
    pts = ["ff:a", "ff:b", "ff:c"]
    gap = lec.autopart_merge(pts, _parts(["EQUIVALENT"] * 2, [["ff:a"], ["ff:c"]]), {})   # ff:b in no partition
    assert gap["verdict"] == "UNPROVEN" and "coverage gap" in gap["reason"] and "ff:b" in gap["reason"]
    assert gap["counts"]["proved"] == 0
