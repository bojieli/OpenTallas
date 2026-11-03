"""No-reset pipeline constant that needs two edges (HBM n4ext / hnx_fused_lane 11-02, DIE-HBM-59/LEC C4): an x*x
multiplier's s1 copies of x (r1, r1b, no reset) feed s = r1 ^ r1b (the sign / odd product bits), which is 0 after two
edges from ANY state with any inputs; synthesis folds s to 0.  Ternary reset propagation calls s X, the one-edge raw
D base needs r1 == r1b (an equality hypothesis, which supplies no base), and KIT-WAVE-16 loaded proposals need a guard register, so the constant was dropped and every
reader 'differs'.  The universal raw prefix base now runs by default at the reset window (OT_LEC_RESET_CYCLES,
default 4); OT_LEC_RAW_BASE_STEPS=0 turns it off.  Control: s = x ^ r1b (x fresh at each edge) is never constant.
    python3 -m pytest -q tools/die_plan/test_lec_prefix_default.py"""
import collections
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lec  # noqa: E402
from test_lec_memory_layout import _seq  # noqa: E402
from test_lec_raw_bases import _exact  # noqa: E402


def _design(tmp_path, control=False):
    def gold(m, l):
        return {"r1": l["x"], "r1b": l["x"], "s": m.XOR(l["x"] if control else l["r1"], l["r1b"])}
    g, gm = _seq(tmp_path, "gold", ["x"], ["r1", "r1b", "s"], gold)
    return lec.Lec(g, gm, g, gm)


@pytest.mark.parametrize("env,control,kept", [
    ({}, False, True),                                   # default: reset window 4 -> proved at edge 4
    ({"OT_LEC_RESET_CYCLES": "2"}, False, True),
    ({"OT_LEC_RAW_BASE_STEPS": "0"}, False, False),      # explicit off = old behaviour
    ({}, True, False),                                   # control: a fresh input each edge is never constant
])
def test_two_edge_constant_kept_by_default(tmp_path, monkeypatch, env, control, kept):
    for k in ("OT_LEC_RAW_BASE_STEPS", "OT_LEC_RESET_CYCLES"):
        monkeypatch.delenv(k, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setattr(lec, "prove", _exact)
    L = _design(tmp_path, control)
    k = "ff:u_dut.s"
    # synthesis merged r1b into r1: the equality is a correspondence hypothesis, which cannot supply a base case
    L.hyp = {("gold", k): ("const", 0), ("gold", "ff:u_dut.r1b"): ("eq", "gold", "ff:u_dut.r1", 0)}
    lec.noreset_filter(L, [], collections.Counter(), work=tmp_path, conflicts=100)
    assert (("gold", k) in L.hyp) is kept
