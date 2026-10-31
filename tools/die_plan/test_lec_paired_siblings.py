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
