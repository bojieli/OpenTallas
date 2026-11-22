"""HARD-RING-BAND-1: a landing band whose ring is a signed hard child (hard_cores[] param_wrap, no band hard_core flag)
emits no soft ring group; the same band without the hard core still does."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import landing_place as LP  # noqa: E402

R = {"rect_um": [1, 2, 3, 4], "ring_place": "ff", "instance": "u_cland_fx_i"}
HC = {"inst": "cl_fx_i", "module": "kv_cland_w9", "physical_inst": "u_bound.u_cland_fx_i", "origin_um": [10, 10],
      "outline_um": [5, 5], "param_wrap": {"base": "ot_dp_clk_landing_cas", "params": {"W": 9, "WREG": 1}}}


class _P:
    def __init__(self, hard):
        t = {"buses": [], "ft_slots": [{"name": "fx"}], "outline_um": [100, 100],
             "clock": {"landing_contract": {"bands": {"fx_i": dict(R)}, "pins": []}}}
        if hard:
            t["hard_cores"] = [dict(HC)]
        self.types = {"t": t}


def test_soft_band_emits_ring_group():
    assert "ring:fx_i" in LP.tcl(_P(False), "t")


def test_hard_child_band_emits_no_ring_group():
    tcl = LP.tcl(_P(True), "t")
    assert "ring:fx_i" not in tcl and "{u_cland_fx_i {" not in tcl
