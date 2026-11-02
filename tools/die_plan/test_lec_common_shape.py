"""lec.py common-shape pairing of a re-laid array whose two sides dropped DIFFERENT constant bits
(HBM-CORES-KITS-39 11-01: h9b u_fcore.queue 32 x 64, gold lacks [*][62..63], gate lacks [*][34..35] -> neither bit
set is a subset of the other, the array was re-keyed queue#t and 1920 + 1920 flops stayed free: 71 UNPROVEN).
Mutant: the gate swaps two rows' write decode -> must stay a difference.
    python3 -m pytest -q tools/die_plan/test_lec_common_shape.py"""
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lec  # noqa: E402
from test_lec_memory_layout import _seq, _sim_prove  # noqa: E402

R, B = 4, 8


def _design(tmp_path, mutant, compact=False):
    """q[r][b] <= (we & a == r) ? d[b] & keep[b] : q[r][b], bits 1 and 3 always written 0 (constant 0 from the
    0 power-up).  gold drops bit 3, gate drops bit 1 (each frontend proved a different constant).  o[b] <= q[h][b]
    for the live bits (the one-side-only bits have no-reset X power-up, which LEC rightly does not assume away).
    mutant: the gate's rows 0 and 1 swap their write decode."""
    ins = ["we", "a0", "a1", "h0", "h1"] + [f"d{b}" for b in range(B)]

    def build(drop, swap, rename=lambda b: b):
        keys = [f"q[{r}][{rename(b)}]" for r in range(R) for b in range(B) if b != drop]
        outs = [f"o[{b}]" for b in range(B) if b not in (1, 3)]

        def nxt(m, l):
            def sel(a0, a1, r):
                x = l[a0] if r & 1 else l[a0] ^ 1
                y = l[a1] if r & 2 else l[a1] ^ 1
                return m.AND(x, y)

            def q(r, b):
                return 0 if b == drop else l[f"q[{r}][{rename(b)}]"]

            def mux(s, x, y):                 # s ? x : y
                return m.AND(m.AND(s, x) ^ 1, m.AND(s ^ 1, y) ^ 1) ^ 1
            n = {}
            for r in range(R):
                rr = ({0: 1, 1: 0}.get(r, r)) if swap else r
                w = m.AND(l["we"], sel("a0", "a1", rr))
                for b in range(B):
                    if b != drop:
                        n[f"q[{r}][{rename(b)}]"] = mux(w, l[f"d{b}"] if b not in (1, 3) else 0, q(r, b))
            for b in range(B):
                if b in (1, 3):
                    continue
                acc = 0
                for r in range(R):
                    acc = m.AND(acc ^ 1, m.AND(sel("h0", "h1", r), q(r, b)) ^ 1) ^ 1
                n[f"o[{b}]"] = acc
            return n
        return keys + outs, nxt
    # compact: the gold dropped the same constant bit 1 but numbered the rest 0..6 (a memory narrowed before it
    # was mapped, like the h9b gold queue); the gate keeps the RTL bit names and lacks [*][1]
    gk, gf = build(1, False, lambda b: b - (b > 1)) if compact else build(3, False)
    tk, tf = build(1, mutant)
    g, gm = _seq(tmp_path, "gold", ins, gk, gf)
    t, tm = _seq(tmp_path, "gate" + str(mutant), ins, tk, tf)
    return lec.Lec(g, gm, t, tm)


def test_common_shape_maps_identity_and_reversed():
    g = {f"ff:u.q[{r}][{b}]": (r, b) for r in range(R) for b in range(B) if b != 3}
    t = {f"ff:u.q#t[{r}][{b}]": (r, b) for r in range(R) for b in range(B) if b != 1}
    kind, maps = lec.common_shape_maps(g, t)
    assert kind == "common" and len(maps) == 2 and all(len(mp) == R * (B - 2) for mp in maps)
    assert maps[0]["ff:u.q#t[2][0]"] == "ff:u.q[2][0]"
    assert maps[1]["ff:u.q#t[2][0]"] == "ff:u.q[1][0]"
    assert "ff:u.q#t[0][3]" not in maps[0]             # one-side-only bits are never paired by name


@pytest.mark.parametrize("g,t", [
    ({"ff:u.q[0][0]": (0, 0)}, {"ff:u.q#t[0][0][0]": (0, 0, 0)}),                    # different index depth
    ({f"ff:u.q[{b}]": (b,) for b in range(8)}, {f"ff:u.q#t[{b}]": (b,) for b in range(4, 13)}),  # 50 % common, other count
])
def test_common_shape_maps_refuses(g, t):
    assert lec.common_shape_maps(g, t) == (None, [])


def test_compacted_side_pairs_by_rank():
    # h9b queue: gold names 0..61 (compacted), gate keeps RTL names and lacks the constant beat[3:2] = 34..35
    g = {f"ff:u.q[{r}][{b}]": (r, b) for r in range(R) for b in range(6)}
    t = {f"ff:u.q#t[{r}][{b}]": (r, b) for r in range(R) for b in range(8) if b not in (2, 3)}
    kind, maps = lec.common_shape_maps(g, t)
    assert kind == "rank" and len(maps) == 2
    assert maps[0]["ff:u.q#t[1][1]"] == "ff:u.q[1][1]" and maps[0]["ff:u.q#t[1][4]"] == "ff:u.q[1][2]"
    assert maps[0]["ff:u.q#t[2][7]"] == "ff:u.q[2][5]" and maps[1]["ff:u.q#t[0][7]"] == "ff:u.q[3][5]"


@pytest.mark.parametrize("compact", [False, True])
@pytest.mark.parametrize("mutant", [False, True])
def test_one_side_constant_bits_pair_end_to_end(tmp_path, monkeypatch, mutant, compact):
    monkeypatch.setattr(lec, "prove", _sim_prove)
    L = _design(tmp_path, mutant, compact)
    assert "ff:u_dut.q" in L.relaid and "ff:u_dut.q#t[0][0]" in L.tonly
    log = []
    lec.correspond(L, tmp_path, 100, log)
    m, _ = L.build(with_compare=True, with_hyp=True)
    verdicts = _sim_prove(m)
    if mutant:
        assert "differs" in verdicts.values()
    else:
        assert any(("rank shape" if compact else "common shape") in x for x in log), log
        assert set(verdicts.values()) == {"proved"}, {k: v for k, v in verdicts.items() if v != "proved"}


def test_opt_out_keeps_the_array_unpaired(tmp_path, monkeypatch):
    monkeypatch.setattr(lec, "prove", _sim_prove)
    monkeypatch.setenv("OT_LEC_COMMON_SHAPE", "0")
    L = _design(tmp_path, False)
    log = []
    lec.alias_arrays(L, log, work=tmp_path)
    assert not any(" shape " in x for x in log)
    assert "ff:u_dut.q#t[0][0]" in L.tonly
