"""Matched copy closure (LEC-TOOL-2 10-27): two MATCHED registers hold one value and each side reads a different
copy (HBM ot_hgi_coll_gq_land r4: ln_s[*][15:13] = g_dst[15:13] in all eight landing lanes, hold while rn low;
synthesis kept four copies per bit and the gold / gate record muxes read different ones -> 24 record bits 277..279
'differed' with every cone input matched).  The closure proposes ('both', copy) == first copy for matched registers
of equal sequential trace and equal next state with the pair bound; the induction proof decides.
    python3 -m pytest -q tools/die_plan/test_lec_matched_copies.py"""
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lec  # noqa: E402
from test_lec_memory_layout import _seq, _sim_prove  # noqa: E402


def _mux(m, s, a, b):                     # s ? a : b
    return m.AND(m.AND(s, a) ^ 1, m.AND(s ^ 1, b) ^ 1) ^ 1


def _design(tmp_path, c2_mode="copy", gate_reads="c2"):
    """gold and gate: c1 <= rn ? x : c1; c2 per c2_mode (both sides identical, so c2's own compare point is equal):
    'copy' = like c1 (a copy), 'en' = loads x only on rn & s (mutant: other load condition), 'late' = loads c1
    (mutant: one cycle later).  gold o <= c1; gate o <= `gate_reads`."""
    c2f = {"copy": lambda m, l: _mux(m, l["rn"], l["x"], l["c2"]),
           "en": lambda m, l: _mux(m, m.AND(l["rn"], l["s"]), l["x"], l["c2"]),
           "late": lambda m, l: _mux(m, l["rn"], l["c1"], l["c2"])}[c2_mode]
    regs = lambda m, l: {"c1": _mux(m, l["rn"], l["x"], l["c1"]), "c2": c2f(m, l)}
    g, gm = _seq(tmp_path, "gold", ["rn", "x", "s"], ["c1", "c2", "o"], lambda m, l: dict(regs(m, l), o=l["c1"]))
    t, tm = _seq(tmp_path, "gate", ["rn", "x", "s"], ["c1", "c2", "o"],
                 lambda m, l: dict(regs(m, l), o=l[gate_reads]))
    return lec.Lec(g, gm, t, tm)


def _verdict(tmp_path, monkeypatch, L):
    monkeypatch.setattr(lec, "prove", _sim_prove)
    log = []
    lec.correspond(L, tmp_path, 100, log)
    m, _ = L.build(with_compare=True, with_hyp=True)
    return _sim_prove(m)["ff:u_dut.o"], log


def test_copies_read_on_different_sides_prove(tmp_path, monkeypatch):
    L = _design(tmp_path)
    st, log = _verdict(tmp_path, monkeypatch, L)
    assert st == "proved"
    assert L.hyp[("both", "ff:u_dut.c2")] == ("eq", "gold", "ff:u_dut.c1", 0)
    assert any("matched copy closure: 1 " in x for x in log)


def test_without_closure_the_copies_stay_free(tmp_path, monkeypatch):
    monkeypatch.setenv("OT_LEC_COPY_CLOSURE", "0")
    st, _ = _verdict(tmp_path, monkeypatch, _design(tmp_path))
    assert st == "differs"                 # the 10-27 gq_land failure mode


@pytest.mark.parametrize("mode", ["en", "late"])
def test_mutant_non_copy_is_not_merged(tmp_path, monkeypatch, mode):
    L = _design(tmp_path, c2_mode=mode)
    st, _ = _verdict(tmp_path, monkeypatch, L)
    assert st == "differs" and ("both", "ff:u_dut.c2") not in L.hyp


def test_mutant_with_forged_equal_traces_is_refuted(tmp_path, monkeypatch):
    # trace screening is only a candidate filter: forge equal traces for a non-copy (other load condition); the
    # bound-state next-state check / induction must still refuse it
    real = lec.seq_traces

    def forged(L, log, **kw):
        T = real(L, log, **kw)
        for sd in ("gold", "gate"):
            T[(sd, "ff:u_dut.c2")] = T[(sd, "ff:u_dut.c1")]
        return T
    monkeypatch.setattr(lec, "seq_traces", forged)
    L = _design(tmp_path, c2_mode="en")
    st, _ = _verdict(tmp_path, monkeypatch, L)
    assert st == "differs" and ("both", "ff:u_dut.c2") not in L.hyp


def test_same_copy_on_both_sides_needs_no_closure(tmp_path, monkeypatch):
    L = _design(tmp_path, gate_reads="c1")
    st, _ = _verdict(tmp_path, monkeypatch, L)
    assert st == "proved"
