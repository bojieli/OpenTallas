"""early_core_map resolves a hard core named by its placed physical_inst (S81 SVC bound macros, e1cb82cd5ce)."""
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import die_sta_related as D  # noqa: E402


def _plan(monkeypatch, row_inst):
    t = {"clock": {"core_taps": "early"},
         "hard_cores": [{"inst": "u_rsv.u_c", "physical_inst": "u_bound.u_rsv_u_c", "module": "ot_core",
                         "pins_file": "p.json", "outline_um": [10, 10]}]}
    plan = {"partition_types": {"T": t}}

    class FakePlan:
        def __init__(self, raw, path=None):
            self.parts = {"p0": {"type": "T"}}
            self.types = raw["partition_types"]
    fs = types.SimpleNamespace(Plan=FakePlan)
    fg = types.SimpleNamespace(core_tap_rows=lambda P, tn, c, pending: [("clk_c0", row_inst, "clk", 1.0, 2.0)])
    monkeypatch.setitem(sys.modules, "schema", fs)
    monkeypatch.setitem(sys.modules, "gen_phys", fg)
    return D.early_core_map(plan, {"t_p0__clk_c0": {"part": "p0"}})


def test_physical_inst_name_maps_module(monkeypatch):
    m = _plan(monkeypatch, "u_bound.u_rsv_u_c")
    assert m["t_p0__clk_c0"][0]["module"] == "ot_core"


def test_logical_inst_name_still_maps(monkeypatch):
    m = _plan(monkeypatch, "u_rsv.u_c")
    assert m["t_p0__clk_c0"][0]["module"] == "ot_core"
