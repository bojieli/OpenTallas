"""RST-COTAP clones (clock.tap_reset_split, main 6135636053bb; COORD -> FLOW-OPS-R2 11-22): tap_reset_split.tcl copies a last reset stage
once per other clock tap as <src>_rtap_<tap>, same D / RESETN / SETN, CLK on that tap.  The gate netlist then has registers the RTL lacks;
LEC must take each clone as a gate-side duplicate of its source (proved by induction, never assumed), and reject a clone that is not one.
    python3 -m pytest -q tools/die_plan/test_lec_tap_clone.py"""
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lec  # noqa: E402
from test_lec import _sim_prove  # noqa: E402


def _pair(tmp_path, clone_next, clone_name, read=6):
    # gold: rs <= d; o(q) <= rs           gate: rs <= d; rs_rtap <= clone_next; o(q) <= rs_rtap  (the sink reads the clone)
    g = tmp_path / "gold.aig"
    g.write_bytes(b"aig 3 1 2 0 0\n2\n4\n")
    t = tmp_path / "gate.aig"
    t.write_bytes(f"aig 4 1 3 0 0\n2\n{clone_next}\n{read}\n".encode())     # read 7: Q = !IQN state
    gm = {"input": {0: [("d", 0)]}, "latch": {0: [("u_rst.rs$_DFF_PN0_.lecq", 0)], 1: [("u_dut.o$_DFF_P_.lecq", 0)]}, "output": {}}
    tm = {"input": {0: [("d", 0)]}, "latch": {0: [("u_rst.rs$_DFF_PN0_.lecq", 0)], 1: [(clone_name, 0)], 2: [("u_dut.o$_DFF_P_.lecq", 0)]},
          "output": {}}
    return lec.Lec(lec.read_aig(g), gm, lec.read_aig(t), tm)


@pytest.mark.parametrize("name", ["u_rst.rs$_DFF_PN0__rtap_clk_t77.lecq", "u_rst.rs$_DFF_PN0__rtap_clk_t77_1.lecq",
                                  "u_rst/rs$_DFF_PN0__rtap_clk_t3.IQN$_DFF_PN0_.lecq"])
def test_tap_clone_is_proved_duplicate_of_its_source(tmp_path, monkeypatch, name):
    monkeypatch.setattr(lec, "prove", _sim_prove)
    clone, inv = lec.flop_key(name)
    L = _pair(tmp_path, 3 if inv else 2, name, 7 if inv else 6)         # an ASAP7 IQN flop stores !D: its true copy has next state !d
    clone = "ff:" + clone
    assert clone in L.tonly
    lec.correspond(L, tmp_path, 100, [])
    assert L.hyp.get(("gate", clone), (None,))[0] == "eq" and L.hyp[("gate", clone)][2] == "ff:u_rst.rs"
    m, _ = L.build(with_compare=True, with_hyp=True)
    assert set(_sim_prove(m).values()) == {"proved"}


def test_wrong_clone_is_not_accepted(tmp_path, monkeypatch):
    monkeypatch.setattr(lec, "prove", _sim_prove)
    L = _pair(tmp_path, 3, "u_rst.rs$_DFF_PN0__rtap_clk_t77.lecq")         # clone next state !d: not a copy
    lec.correspond(L, tmp_path, 100, [])
    m, _ = L.build(with_compare=True, with_hyp=True)
    assert "differs" in set(_sim_prove(m).values())


def test_tap_clone_proposals_unit():
    from types import SimpleNamespace
    L = SimpleNamespace(matched=["ff:a.x"], tonly=["ff:a.rs_rtap_clk_t2", "ff:a.x$_DFF_P__rtap_clk_t9_2", "ff:a.y_rtap_clk_t1", "ff:b.z"],
                        tp={"ff:a.rs": 2, "ff:a.x": 4, "ff:b.z": 6, "ff:a.rs_rtap_clk_t2": 8, "ff:a.x$_DFF_P__rtap_clk_t9_2": 10,
                            "ff:a.y_rtap_clk_t1": 12}, hyp={})
    log = []
    assert lec.tap_clone_proposals(L, log) == 2
    assert L.hyp == {("gate", "ff:a.rs_rtap_clk_t2"): ("eq", "gate", "ff:a.rs", 0),
                     ("gate", "ff:a.x$_DFF_P__rtap_clk_t9_2"): ("eq", "gold", "ff:a.x", 0)}
    assert "tap clone" in log[0]
