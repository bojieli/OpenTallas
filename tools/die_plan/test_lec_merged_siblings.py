"""Merged register paired with one of several kept copies, gate loads on another copy (QC slw_hc0 10-26, QC-LEC-3:
NOT EQUIVALENT 9/100346 = POOLc[0..8]; e_pool[1] paired with e_poolc1[0], gate POOLc reads e_poolc1[3], and the
self-holding never-reset copies were left free of each other).  merged_proposals now also proposes the chosen copy's
same-support siblings equal to it (bound-state simulation first, induction decides).
    python3 -m pytest -q tools/die_plan/test_lec_merged_siblings.py"""
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lec  # noqa: E402
from test_lec_memory_layout import _seq, _sim_prove  # noqa: E402


def _design(tmp_path, gate_o_from, c1b_en="p"):
    """gold: c0 loads d on v & !p, c1a and c1b (two kept copies) on v & p, e1 (= e_pool[1], merged by synthesis)
    on v & p; o <= e1.  gate: c0, c1a, c1b and o <= `gate_o_from`.  c1b_en='np' makes c1b NOT a copy (mutant)."""
    hold = lambda m, e, d, q: m.AND(m.AND(e, d) ^ 1, m.AND(e ^ 1, q) ^ 1) ^ 1
    en = {"p": lambda m, l: m.AND(l["v"], l["p"]), "np": lambda m, l: m.AND(l["v"], l["p"] ^ 1)}
    regs = lambda m, l: {"c0": hold(m, en["np"](m, l), l["d"], l["c0"]),
                         "c1a": hold(m, en["p"](m, l), l["d"], l["c1a"]),
                         "c1b": hold(m, en[c1b_en](m, l), l["d"], l["c1b"])}
    g, gm = _seq(tmp_path, "gold", ["v", "p", "d"], ["c0", "c1a", "c1b", "e1", "o"],
                 lambda m, l: dict(regs(m, l), e1=hold(m, en["p"](m, l), l["d"], l["e1"]), o=l["e1"]))
    t, tm = _seq(tmp_path, "gate", ["v", "p", "d"], ["c0", "c1a", "c1b", "o"],
                 lambda m, l: dict(regs(m, l), o=l[gate_o_from]))
    return lec.Lec(g, gm, t, tm)


def test_siblings_proposed_only_for_real_copies(tmp_path):
    L = _design(tmp_path, "c1b")
    log = []
    lec.merged_proposals(L, log)
    rep = L.hyp[("gold", "ff:u_dut.e1")]
    assert rep[0] == "eq" and rep[2] in ("ff:u_dut.c1a", "ff:u_dut.c1b")
    other = "ff:u_dut.c1b" if rep[2] == "ff:u_dut.c1a" else "ff:u_dut.c1a"
    assert L.hyp[("both", other)] == ("eq", "gold", rep[2], 0)
    assert ("both", "ff:u_dut.c0") not in L.hyp            # other epoch: same support, different load condition
    assert "sibling copies proposed" in log[-1]


@pytest.mark.parametrize("gate_o_from,c1b_en,differs", [
    ("c1b", "p", False),     # gate loads on the sibling copy: EQ (failed before this fix)
    ("c1a", "p", False),
    ("c0", "p", True),       # mutant: wrong epoch copy
    ("c1b", "np", True),     # mutant: c1b is not a copy of e1
])
def test_end_to_end_and_mutants(tmp_path, monkeypatch, gate_o_from, c1b_en, differs):
    monkeypatch.setattr(lec, "prove", _sim_prove)
    L = _design(tmp_path, gate_o_from, c1b_en)
    lec.correspond(L, tmp_path, 100, [])
    m, _ = L.build(with_compare=True, with_hyp=True)
    assert (_sim_prove(m)["ff:u_dut.o"] == "differs") == differs
