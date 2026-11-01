"""Paired sibling closure (FLOW-19 10-31, S81 xfin x4): gate flops paired by signature to DIFFERENT members of a gold
copy class (gate VD[172] -> gold leaf[177] while the gold issue logic reads leaf[173]; the five leaf valids of one
flit group hold one value) left the gold members free of each other -> 19 false 'differs' points (g_grp[10..11]),
co-simulation 0 mismatches.  The closure proposes gold partner == sibling partner of equal trace + next state; the
induction decides.
    python3 -m pytest -q tools/die_plan/test_lec_paired_siblings.py"""
import collections
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lec  # noqa: E402
from test_lec_memory_layout import _seq, _sim_prove  # noqa: E402


def _mux(m, s, a, b):                     # s ? a : b
    return m.AND(m.AND(s, a) ^ 1, m.AND(s ^ 1, b) ^ 1) ^ 1


def _design(tmp_path, b_mode="copy"):
    """gold a, b (b a copy of a, or a mutant 'en' = loads only on rn & s), gold o <= a.  gate ga, gb (both copies of
    a's function), gate o <= ga.  The gate pairs are seeded CROSSED (ga -> gold b, gb -> gold a), as the xfin
    signature pairing chose."""
    bf = {"copy": lambda m, l: _mux(m, l["rn"], l["x"], l["b"]),
          "en": lambda m, l: _mux(m, m.AND(l["rn"], l["s"]), l["x"], l["b"])}[b_mode]
    g, gm = _seq(tmp_path, "gold", ["rn", "x", "s"], ["a", "b", "o"],
                 lambda m, l: {"a": _mux(m, l["rn"], l["x"], l["a"]), "b": bf(m, l), "o": l["a"]})
    t, tm = _seq(tmp_path, "gate", ["rn", "x", "s"], ["ga", "gb", "o"],
                 lambda m, l: {"ga": _mux(m, l["rn"], l["x"], l["ga"]), "gb": bf(m, {**l, "b": l["gb"]}),
                               "o": l["ga"]})
    L = lec.Lec(g, gm, t, tm)
    L.hyp[("gate", "ff:u_dut.ga")] = ("eq", "gold", "ff:u_dut.b", 0)
    L.hyp[("gate", "ff:u_dut.gb")] = ("eq", "gold", "ff:u_dut.a", 0)
    return L


def _run(tmp_path, b_mode="copy", closure=True):
    L = _design(tmp_path, b_mode)
    log = []
    if closure:
        lec.paired_sibling_closure(L, log, lec.seq_traces(L, log), collections.Counter())
    m, _ = L.build(with_compare=True, with_hyp=True)
    return L, _sim_prove(m), log


def test_crossed_pairs_without_closure_differ(tmp_path):
    _, st, _ = _run(tmp_path, closure=False)
    assert st["ff:u_dut.o"] == "differs"           # the xfin false NOT EQUIVALENT


def test_closure_relates_sibling_partners_and_proves(tmp_path):
    L, st, log = _run(tmp_path)
    assert L.hyp[("gold", "ff:u_dut.b")] == ("eq", "gold", "ff:u_dut.a", 0)
    assert st["ff:u_dut.o"] == "proved"
    assert all(v == "proved" for n, v in st.items() if n.startswith("hyp:"))   # inductive with every relation
    assert any("paired sibling closure: 1 " in x for x in log)


def test_mutant_non_copy_is_not_related(tmp_path):
    L, st, _ = _run(tmp_path, b_mode="en")
    assert ("gold", "ff:u_dut.b") not in L.hyp
    assert st["ff:u_dut.o"] == "differs"           # a real difference is still reported


def test_full_correspondence_still_proves(tmp_path, monkeypatch):
    monkeypatch.setattr(lec, "prove", lambda m, *a, **k: _sim_prove(m))
    L = _design(tmp_path)
    lec.correspond(L, tmp_path, 100, [])
    m, _ = L.build(with_compare=True, with_hyp=True)
    assert _sim_prove(m)["ff:u_dut.o"] == "proved"


def test_constant_trace_copies_are_still_related(tmp_path):
    # xfin x4 rerun: the leaf valids of flit group 45..49 were never set in the 48 random trace cycles (constant
    # trace -> no trace class), so 173/177 stayed unrelated (30 points differ); constant-trace partners are grouped
    # by their constant and separated by the next-state check / induction
    L = _design(tmp_path)
    L.trace_const = {("gold", "ff:u_dut.a"): 0, ("gold", "ff:u_dut.b"): 0}
    T = {("gold", "ff:u_dut.a"): None, ("gold", "ff:u_dut.b"): None}
    assert lec.paired_sibling_closure(L, [], T, collections.Counter()) == 1
    assert L.hyp[("gold", "ff:u_dut.b")] == ("eq", "gold", "ff:u_dut.a", 0)
    m, _ = L.build(with_compare=True, with_hyp=True)
    assert _sim_prove(m)["ff:u_dut.o"] == "proved"
    M = _design(tmp_path, "en")
    M.trace_const = dict(L.trace_const)
    assert lec.paired_sibling_closure(M, [], T, collections.Counter()) == 0


def _rare_design(tmp_path):
    """two copy groups {a, b} and {c, d} in ONE constant-trace class: each sets on its own rare decoded hit (ten
    inputs all one / x9 zero), toggles on it, as the xfin leaf valids of different flit groups; the gate pairs
    are crossed inside each group (ga -> b, gb -> a, gc -> d, gd -> c)."""
    xs = [f"x{i}" for i in range(10)]

    def hit(m, l, last):
        acc = l["rn"]
        for x in xs[:-1]:
            acc = m.AND(acc, l[x])
        return m.AND(acc, l[xs[-1]] ^ (0 if last else 1))

    def setr(m, l, h, q):                    # q' = rn & (h ^ q): toggles on its hit
        return m.AND(l["rn"], m.AND(m.AND(h, q) ^ 1, m.AND(h ^ 1, q ^ 1) ^ 1))

    def nxt(m, l, names):
        ha, hc = hit(m, l, True), hit(m, l, False)
        a, b, c, d, o, p = names
        return {a: setr(m, l, ha, l[a]), b: setr(m, l, ha, l[b]), c: setr(m, l, hc, l[c]), d: setr(m, l, hc, l[d]),
                o: l[a], p: l[c]}
    g, gm = _seq(tmp_path, "gold", ["rn"] + xs, ["a", "b", "c", "d", "o", "p"],
                 lambda m, l: nxt(m, l, ["a", "b", "c", "d", "o", "p"]))
    t, tm = _seq(tmp_path, "gate", ["rn"] + xs, ["ga", "gb", "gc", "gd", "o", "p"],
                 lambda m, l: nxt(m, l, ["ga", "gb", "gc", "gd", "o", "p"]))
    L = lec.Lec(g, gm, t, tm)
    for gk, ok in (("ga", "b"), ("gb", "a"), ("gc", "d"), ("gd", "c")):
        L.hyp[("gate", f"ff:u_dut.{gk}")] = ("eq", "gold", f"ff:u_dut.{ok}", 0)
    keys = [f"ff:u_dut.{k}" for k in "abcd"]
    L.trace_const = {("gold", k): 0 for k in keys}
    return L, {("gold", k): None for k in keys}


def test_constant_class_split_by_witness_into_copy_groups(tmp_path):
    # xfin x4c: ~12k constant-trace partners in one class bound to leaf[128]; a plain next-state check never separated
    # leaf[173..177] (rare set), sim_refine only dropped them -> still 30 points differ.  The witness lanes split the
    # class into its copy groups, each with its own representative.
    L, T = _rare_design(tmp_path)
    assert lec.paired_sibling_closure(L, [], T, collections.Counter()) == 2
    assert L.hyp[("gold", "ff:u_dut.b")] == ("eq", "gold", "ff:u_dut.a", 0)
    assert L.hyp[("gold", "ff:u_dut.d")] == ("eq", "gold", "ff:u_dut.c", 0)
    assert ("gold", "ff:u_dut.c") not in L.hyp
    m, _ = L.build(with_compare=True, with_hyp=True)
    st = _sim_prove(m)
    assert st["ff:u_dut.o"] == "proved" and st["ff:u_dut.p"] == "proved"
    assert all(v == "proved" for n, v in st.items() if n.startswith("hyp:"))
