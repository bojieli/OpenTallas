"""COORD 10-29 11:09 (hd_ctl KEEP FAIL ruling): lec.py treats a register as a constant only when its D input is
structurally constant (or its reset / a reset-rooted reload chain gives the constant), and lists EVERY such register
(KIT/lec/noreset_constants.tsv, uncapped; lec.json keeps the first 500).  Mutants that must NOT be folded: a register
with a non-constant D, a no-reset register on an enable / hold path (D = en ? c : Q, the hd_ctl u_ht.u_tx hold
class), and a register with a reset path to a different value (loaded with two values).
    python3 -m pytest -q tools/die_plan/test_lec_const_fold_listing.py"""
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lec  # noqa: E402
from test_lec_memory_layout import _seq, _sim_prove  # noqa: E402


def _mux(m, s, a, b):                     # s ? a : b
    return m.AND(m.AND(s, a) ^ 1, m.AND(s ^ 1, b) ^ 1) ^ 1


IN = ["rn", "en", "a", "b"]


def _run(tmp_path, monkeypatch, kind, n=1):
    """gold: p0..p{n-1} no reset unless stated, o_i <= a & p_i (observed every cycle).  gate: synthesis folded every
    p_i to 1 (o_i <= a)."""
    ps = [f"p{i}" for i in range(n)]

    def gold(m, l):
        nx = {}
        for p in ps:
            d = {"lit": 1,                                         # D structurally the constant 1
                 "data": l["b"],                                   # MUTANT: non-constant D
                 "hold": _mux(m, l["en"], 1, l[p]),                # MUTANT: enable path, hold-or-constant
                 "rst0": _mux(m, l["rn"], 1, 0)}[kind]             # MUTANT: resets to 0, loads 1 (two values)
            nx[p] = d
            nx["o" + p] = m.AND(l["a"], l[p])
        return nx
    g, gm = _seq(tmp_path, "gold", IN, ps + ["o" + p for p in ps], gold)
    t, tm = _seq(tmp_path, "gate", IN, ["o" + p for p in ps], lambda m, l: {"o" + p: l["a"] for p in ps})
    L = lec.Lec(g, gm, t, tm)
    monkeypatch.setattr(lec, "prove", _sim_prove)
    log = []
    lec.correspond(L, tmp_path, 100, log)
    lec.noreset_filter(L, log, __import__("collections").Counter())
    m, _ = L.build(with_compare=True, with_hyp=True)
    res = _sim_prove(m)
    rep = lec.noreset_report(L)
    lst = lec.noreset_listing(L, tmp_path / "noreset_constants.tsv")
    rows = [r.split("\t") for r in (tmp_path / "noreset_constants.tsv").read_text().splitlines()[1:]]
    return L, res, rep, lst, rows


def test_structurally_constant_d_is_folded_and_listed(tmp_path, monkeypatch):
    L, res, rep, lst, rows = _run(tmp_path, monkeypatch, "lit")
    assert res["ff:u_dut.op0"] == "proved"
    assert L.hyp[("gold", "ff:u_dut.p0")] == ("const", 1)
    assert ["kept", "gold", "ff:u_dut.p0", "1", "1", "reset"] in rows
    assert lst["n_kept"] == rep["n_kept"] == 1 and len(lst["sha256"]) == 64


def test_listing_is_uncapped(tmp_path, monkeypatch):
    L, res, rep, lst, rows = _run(tmp_path, monkeypatch, "lit", n=520)
    assert all(v == "proved" for v in res.values())
    kept = {r[2] for r in rows if r[0] == "kept"}
    assert len(kept) == lst["n_kept"] == 520 and "ff:u_dut.p519" in kept


@pytest.mark.parametrize("kind", ["data", "hold", "rst0"])
def test_mutants_are_not_folded(tmp_path, monkeypatch, kind):
    L, res, rep, lst, rows = _run(tmp_path, monkeypatch, kind)
    assert res["ff:u_dut.op0"] == "differs"                  # the difference is reported, never assumed away
    assert L.hyp.get(("gold", "ff:u_dut.p0"), ("none",))[0] != "const"
    assert not [r for r in rows if r[0] == "kept" and r[2] == "ff:u_dut.p0"]
