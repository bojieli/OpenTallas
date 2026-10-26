"""lec.py alias-array layout from the source memory geometry, refusal of mismatch-raising guessed layouts, the
single-candidate shortcut, and same-support merged-duplicate choice (QC slw_hc0 LEC 10-26: NOT EQUIVALENT
1363/99672 = a_pr / b_emin mis-strided re-keys + e_pool[1] proposed against the wrong per-epoch copy).
    python3 -m pytest -q tools/die_plan/test_lec_memory_layout.py"""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lec  # noqa: E402


def _sim_prove(m, *a, **k):
    val, mask = m.simulate(16, seed=12345)
    return {n: ("proved" if lec.lit_val(val, mask, o) == 0 else "differs") for n, o in zip(m.onames, m.outs)}


def _seq(tmp_path, name, inputs, latches, nxt_fn):
    m = lec.Aig()
    lits = {n: m.add_input(n) for n in list(inputs) + list(latches)}
    nxt = nxt_fn(m, lits)
    f = tmp_path / (name + ".aig")
    m.write(f)
    _, body = f.read_bytes().split(b"\n", 1)
    A = len(m.ands) // 2
    hdr = f"aig {m.ni + A} {len(inputs)} {len(latches)} 0 {A}\n" + "".join(f"{nxt[l]}\n" for l in latches)
    f.write_bytes(hdr.encode() + body)
    mp = {"input": {i: [(n, 0)] for i, n in enumerate(inputs)},
          "latch": {i: [(f"u_dut.{n}$_DFF_P_.lecq", 0)] for i, n in enumerate(latches)}, "output": {}}
    return lec.read_aig(f), mp


# ------------------------------------------------------------------------------------------ memory_layout
def test_widened_gold_narrowed_gate_uses_source_stride():
    # slw_hc0 a_pr: reg [23:0] a_pr [0:15]; gold opt_mem_widen x8 -> a_pr[0..1][0..191]; gate kept bits 3..16
    g = {f"ff:u.a_pr[{w}][{j}]": (w, j) for w in range(2) for j in range(192)}
    t = {f"ff:u.a_pr#t[{r}][{b}]": (r, b) for r in range(16) for b in range(3, 17)}
    mp = lec.memory_layout(g, t, (24, 16, 0))
    assert len(mp) == 224 and len(set(mp.values())) == 224
    assert mp["ff:u.a_pr#t[0][3]"] == "ff:u.a_pr[0][3]"
    assert mp["ff:u.a_pr#t[9][16]"] == "ff:u.a_pr[1][40]"            # element 9 = word 1, sub-word 1: 24 + 16
    assert mp["ff:u.a_pr#t[7][10]"] == "ff:u.a_pr[0][178]"           # 7 * 24 + 10
    # the radix read off the narrowed gate (17) would have put element 9 bit 16 at flat 169 instead of 232
    assert mp["ff:u.a_pr#t[9][16]"] != "ff:u.a_pr[0][169]"


def test_slang_packed_inner_dimension_is_msb_first():
    # slw_hc0 e_W: reg [17:0] e_W [0:1][0:15]; slang memory 2 x 288 (inner elements folded, element 0 at the MSB)
    g = {f"ff:u.e_W[{e}][{j}]": (e, j) for e in range(2) for j in range(288)}
    t = {f"ff:u.e_W#t[{a}][{b}]": (a, b) for a in range(32) for b in range(18)}
    mp = lec.memory_layout(g, t, (288, 2, 0))
    assert len(mp) == 576
    assert mp["ff:u.e_W#t[0][0]"] == "ff:u.e_W[0][270]"              # e 0, r 0 -> sub-element 15
    assert mp["ff:u.e_W#t[17][5]"] == "ff:u.e_W[1][257]"             # e 1, r 1 -> (15 - 1) * 18 + 5


@pytest.mark.parametrize("t,geom", [
    ({"ff:u.x#t[0][30]": (0, 30)}, (24, 16, 0)),                      # bit beyond the element width
    ({"ff:u.x#t[16][0]": (16, 0)}, (24, 16, 0)),                      # address beyond the memory
    ({"ff:u.x#t[0][0][1]": (0, 0, 1)}, (24, 16, 0)),                  # unsupported index shape: no guess
])
def test_memory_layout_refuses_anything_it_cannot_place(t, geom):
    g = {f"ff:u.x[{w}][{j}]": (w, j) for w in range(2) for j in range(192)}
    assert lec.memory_layout(g, t, geom) is None


def _fake_L(gold, gate, build):
    return SimpleNamespace(gp=dict.fromkeys(gold, 0), tp=dict(zip(gate, range(10, 10 + len(gate)))),
                           gc={}, tc={}, matched=[], gonly=list(gold), tonly=list(gate), hyp={},
                           galias={k: [gate[0]] for k in gold}, build=build)


def test_alias_array_takes_source_geometry_without_simulation(monkeypatch, tmp_path):
    gold = [f"ff:u.m[0][{j}]" for j in range(6)]                     # W = 3, S = 2, widened x2
    gate = [f"ff:u.m#t[{r}][{b}]" for r in range(2) for b in range(2)]
    def no_build(**kw):
        raise AssertionError("source geometry layout must not be scored by simulation")
    L = _fake_L(gold, gate, no_build)
    monkeypatch.setattr(lec, "slang_elements", lambda p: {})
    monkeypatch.setattr(lec, "memory_geometry", lambda p: {"ff:u.m": (3, 2, 0)})
    log = []
    lec.alias_arrays(L, log, work=tmp_path)
    assert sorted(L.matched) == ["ff:u.m[0][0]", "ff:u.m[0][1]", "ff:u.m[0][3]", "ff:u.m[0][4]"]
    assert L.tp["ff:u.m[0][3]"] == 12                                 # gate m#t[1][0]
    assert "source memory layout" in log[-1] and L.hyp == {}


class _AllDiffer:
    """a simulation in which every matched compare point disagrees (gold literal 0 vs gate literal 1)."""
    def __init__(self, L):
        self.L = L
    def __call__(self, **kw):
        self.L.dlit = {(s, k): (0 if s == "gold" else 1) for s in ("gold", "gate") for k in self.L.gp}
        return SimpleNamespace(simulate=lambda words, seed=0: ([0], -1)), None


def test_alias_array_refuses_layout_that_raises_mismatches(monkeypatch, tmp_path):
    gold = [f"ff:u.q[{i}][{j}]" for i in range(2) for j in range(2)]
    gate = [f"ff:u.SX#t[{i}][{j}]" for i in range(2) for j in range(2)]
    L = _fake_L(gold, gate, None)
    L.build = _AllDiffer(L)
    monkeypatch.setattr(lec, "slang_elements", lambda p: {})
    monkeypatch.setattr(lec, "memory_geometry", lambda p: {})
    tp0 = dict(L.tp)
    log = []
    lec.alias_arrays(L, log, work=tmp_path)
    assert L.tp == tp0 and L.matched == [] and "REFUSED" in log[-1]


def test_alias_array_single_candidate_is_not_scored(monkeypatch, tmp_path):
    gold = [f"ff:u.q[{i}]" for i in range(4)]
    gate = [f"ff:u.SX[{i}]" for i in range(4)]
    def no_build(**kw):
        raise AssertionError("one candidate: scoring cannot change the choice")
    L = _fake_L(gold, gate, no_build)
    monkeypatch.setattr(lec, "slang_elements", lambda p: {})
    monkeypatch.setattr(lec, "memory_geometry", lambda p: {})
    log = []
    lec.alias_arrays(L, log, work=tmp_path)
    assert L.matched == sorted(gold) and "single layout" in log[-1]


def test_memory_geometry_reads_pre_techmap_memories(tmp_path):
    f = tmp_path / "gold.aliases.json"
    f.write_text(json.dumps({"modules": {"lec_top": {"memories": {
        "u_dut.genblk1.m": {"width": 24, "size": 16, "start_offset": 0}}, "cells": {}, "netnames": {}}}}))
    assert lec.memory_geometry(f) == {"ff:u_dut.m": (24, 16, 0)}
    assert lec.memory_geometry(tmp_path / "absent.json") == {}


# ------------------------------------------------------------------------- end to end on a small memory
def _mem_design(tmp_path, mutant):
    """gold: memory m [0:1] x 3 b widened to one 6-b word m[0][0..5] (bit 2 of each element constant 0);
    gate: m[r][0..1] (constant bits dropped).  Next state of element r bit b = x[3r + b].  The gate's own
    radix (2) puts element 1 at gold bits 2..3; the source geometry (3) at 3..4.  mutant: gate element 1 loads
    the other bit order (a real difference that must stay a difference)."""
    xs = [f"x{i}" for i in range(6)]
    g, gm = _seq(tmp_path, "gold", xs, [f"m[0][{j}]" for j in range(6)] + ["o"],
                 lambda m, l: {**{f"m[0][{j}]": (0 if j % 3 == 2 else l[f"x{j}"]) for j in range(6)},
                               "o": m.AND(l["m[0][3]"], l["m[0][4]"] ^ 1)})
    sel = (lambda r, b: f"x{3 * r + (1 - b)}") if mutant else (lambda r, b: f"x{3 * r + b}")
    t, tm = _seq(tmp_path, "gate", xs, [f"m[{r}][{b}]" for r in range(2) for b in range(2)] + ["o"],
                 lambda m, l: {**{f"m[{r}][{b}]": l[sel(r, b) if r == 1 else f"x{b}"] for r in range(2)
                                  for b in range(2)}, "o": m.AND(l["m[1][0]"], l["m[1][1]"] ^ 1)})
    (tmp_path / "gold.aliases.json").write_text(json.dumps({"modules": {"lec_top": {
        "memories": {"u_dut.m": {"width": 3, "size": 2, "start_offset": 0}}, "cells": {}, "netnames": {}}}}))
    return lec.Lec(g, gm, t, tm)


@pytest.mark.parametrize("mutant", [False, True])
def test_memory_layout_end_to_end_and_mutant(tmp_path, monkeypatch, mutant):
    monkeypatch.setattr(lec, "prove", _sim_prove)
    L = _mem_design(tmp_path, mutant)
    assert "ff:u_dut.m#t[1][0]" in L.tonly                             # relaid: gate names not trusted
    log = []
    lec.correspond(L, tmp_path, 100, log)
    assert any("source memory layout" in x for x in log)
    m, _ = L.build(with_compare=True, with_hyp=True)
    verdicts = _sim_prove(m)
    assert ("differs" in set(verdicts.values())) == mutant
    if mutant:
        assert verdicts["ff:u_dut.o"] == "differs"


def _epoch_design(tmp_path, gate_o_from):
    """slw_hc0 e_pool / e_poolc0 / e_poolc1: gold e1 (= e_pool[1]) loads d when v & p, c0 when v & !p, c1 when
    v & p; o <= e1.  Gate (synthesis merged e1 into c1): c0, c1, o <= `gate_o_from`.  e1's next-state support
    {v, p, d, SELF} equals c0's AND c1's."""
    hold = lambda m, e, d, q: m.AND(m.AND(e, d) ^ 1, m.AND(e ^ 1, q) ^ 1) ^ 1
    en0 = lambda m, l: m.AND(l["v"], l["p"] ^ 1)
    en1 = lambda m, l: m.AND(l["v"], l["p"])
    g, gm = _seq(tmp_path, "gold", ["v", "p", "d"], ["c0", "c1", "e1", "o"],
                 lambda m, l: {"c0": hold(m, en0(m, l), l["d"], l["c0"]), "c1": hold(m, en1(m, l), l["d"], l["c1"]),
                               "e1": hold(m, en1(m, l), l["d"], l["e1"]), "o": l["e1"]})
    t, tm = _seq(tmp_path, "gate", ["v", "p", "d"], ["c0", "c1", "o"],
                 lambda m, l: {"c0": hold(m, en0(m, l), l["d"], l["c0"]), "c1": hold(m, en1(m, l), l["d"], l["c1"]),
                               "o": l[gate_o_from]})
    return lec.Lec(g, gm, t, tm)


def test_merged_duplicate_pairs_with_the_copy_of_its_own_epoch(tmp_path):
    L = _epoch_design(tmp_path, "c1")
    log = []
    lec.merged_proposals(L, log)
    assert L.hyp[("gold", "ff:u_dut.e1")] == ("eq", "gold", "ff:u_dut.c1", 0)
    assert "re-chosen" in log[-1]


@pytest.mark.parametrize("gate_o_from,differs", [("c1", False), ("c0", True)])
def test_merged_duplicate_end_to_end_and_mutant(tmp_path, monkeypatch, gate_o_from, differs):
    monkeypatch.setattr(lec, "prove", _sim_prove)
    L = _epoch_design(tmp_path, gate_o_from)
    lec.correspond(L, tmp_path, 100, [])
    m, _ = L.build(with_compare=True, with_hyp=True)
    verdicts = _sim_prove(m)
    assert (verdicts["ff:u_dut.o"] == "differs") == differs
