"""Merged register whose surviving twin READS it (HBM kshare splitstrap 11-02, DIE-HBM-59/LEC C3): an async FIFO's
rd_bin[MSB] and rd_gray[MSB] load the same rd_next[MSB] = rd_bin[MSB] ^ carry; synthesis merges rd_bin[MSB] into
rd_gray[MSB].  merged_proposals fingerprinted each flop with only its OWN state as SELF, so rd_bin[MSB] (reads itself)
and rd_gray[MSB] (reads rd_bin[MSB], not itself) never matched -> gold rd_bin[MSB] left free -> rd_gray[MSB-1..MSB]
NOT EQUIVALENT in all 4 lanes.  A pair where one flop reads the other now matches with BOTH read as SELF; the
proposal is still proved inductively (a wrong one is dropped, never assumed).
    python3 -m pytest -q tools/die_plan/test_lec_merged_reads_twin.py"""
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lec  # noqa: E402
from test_lec_memory_layout import _seq, _sim_prove  # noqa: E402


def X(m, a, b):
    return m.AND(m.AND(a, b ^ 1) ^ 1, m.AND(a ^ 1, b) ^ 1) ^ 1


def _design(tmp_path, mutant=False):
    """2-bit gray read pointer.  gold: b0, b1 (bin), g1 (= next b1), g0 (= next b1 ^ next b0), o <= g0 ^ g1.
    gate: b1 merged into g1 (every read of b1 reads g1).  mutant: the gate's g1 holds on !f instead (not a twin)."""
    def gold(m, l):
        b0n = X(m, l["b0"], l["f"]); b1n = X(m, l["b1"], m.AND(l["b0"], l["f"]))
        return {"b0": b0n, "b1": b1n, "g1": b1n, "g0": X(m, b1n, b0n), "o": X(m, l["g0"], l["g1"])}

    def gate(m, l):
        b0n = X(m, l["b0"], l["f"])
        car = m.AND(l["b0"], l["f"] ^ 1) if mutant else m.AND(l["b0"], l["f"])
        g1n = X(m, l["g1"], car)
        return {"b0": b0n, "g1": g1n, "g0": X(m, g1n, b0n), "o": X(m, l["g0"], l["g1"])}
    g, gm = _seq(tmp_path, "gold", ["f"], ["b0", "b1", "g1", "g0", "o"], gold)
    t, tm = _seq(tmp_path, "gate", ["f"], ["b0", "g1", "g0", "o"], gate)
    return lec.Lec(g, gm, t, tm)


def test_twin_that_reads_the_merged_register_is_proposed(tmp_path):
    L = _design(tmp_path)
    log = []
    lec.merged_proposals(L, log)
    assert L.hyp.get(("gold", "ff:u_dut.b1")) == ("eq", "gold", "ff:u_dut.g1", 0)


@pytest.mark.parametrize("mutant,differs", [(False, False), (True, True)])
def test_end_to_end_and_mutant(tmp_path, monkeypatch, mutant, differs):
    monkeypatch.setattr(lec, "prove", _sim_prove)
    L = _design(tmp_path, mutant)
    lec.correspond(L, tmp_path, 100, [])
    m, _ = L.build(with_compare=True, with_hyp=True)
    st = _sim_prove(m)
    assert any(v == "differs" for k, v in st.items() if "u_dut.o" in k or "g0" in k or "g1" in k) == differs
