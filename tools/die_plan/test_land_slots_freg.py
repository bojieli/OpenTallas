"""FREG-1 rings are not declared as hold_mux / ring_start in the kit land_slots (DIE-HEAD-59 11-03, hd_turn_a l48tb)."""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
import clock_landings as CL


def _self(freg):
    wreg = {"buses": ["t_i"], "dsrep": 2, "freg": freg}
    plan = {"partition_types": {"X": {"clock": {"landing_ring_wreg": wreg}}}}
    return SimpleNamespace(ca=True, ca_type={"X": {"rings": {"t_i": {"depth": 4}, "u_i": {"depth": 3}}, "role": ("none", "")}},
                           by_type={"X": {"inputs": ("t_i", "u_i"), "outputs": ()}}, dataflow=True, plan=plan,
                           types={"X": {}}, tstart=None)


def test_freg_ring_not_declared_other_ring_kept():
    b = CL.Landings.land_slots(_self(True), "X")["buses"]
    assert not [k for k in b if k.endswith("t_i")]
    assert b["u_i"]["form"] == "hold_mux" and b["cland_fstart_in_u_i"]["form"] == "ring_start"


def test_wreg_without_freg_still_declared():
    b = CL.Landings.land_slots(_self(False), "X")["buses"]
    assert b["t_i"] == {"D": 4, "form": "hold_mux"} and b["cland_fstart_in_t_i"]["ring"] == "t_i"
