"""QC-CB-GEN-1115 (FABLE-PD-QC-1115 L3 / L4 / L6): clock entry access lookup by logical or physical inst, the by-design M7
N/S-face fclk entry layer, the macro-crossing placement advisory.   python3 -m pytest -q tools/die_plan/test_qccb_gen_1115.py"""
import json
import re
from pathlib import Path

import gen_phys
import kit_contract as KC
import test_kit_contract as TK
from test_kit_contract import kit  # noqa: F401  (fixture)

HERE = Path(__file__).resolve().parent


def test_core_is_matches_logical_and_physical_inst():
    c = {"inst": "u_t22", "physical_inst": "u_bound.u_t22"}
    assert gen_phys._core_is(c, "u_t22") and gen_phys._core_is(c, "u_bound.u_t22")
    assert not gen_phys._core_is(c, "u_t32") and not gen_phys._core_is(c, None)
    assert gen_phys._core_is({"inst": "u_t22"}, "u_t22") and not gen_phys._core_is({"inst": "u_t22"}, "u_bound.u_t22")


def test_entry_access_lookups_use_the_helper():
    g = (HERE / "gen_phys.py").read_text()
    assert 'c["inst"] == row["inst"]' not in g                       # the budget lookup that dropped clock_entry_access
    assert g.count("_core_is(c, ") >= 3                              # core_tap_pins, entry_block_boxes, budget core_taps


def test_macro_cross_check_is_generic_and_wired():
    tcl = (HERE / "macro_cross_check.tcl").read_text()
    assert "OT_MACRO_CROSS nets" in tcl and "ot_mcross_min_um" in tcl
    assert not re.search(r"u_(t|d|bound)", tcl.split("mc_main")[1])        # no instance / type name in the logic
    g = (HERE / "gen_phys.py").read_text()
    assert gen_phys.MACRO_CROSS_HOOK == "source /work/macro_cross_check.tcl"
    assert g.index("DLY_SPREAD_HOOK + ") < g.index("MACRO_CROSS_HOOK + ")  # after the spread, in the same release hook


def test_landing_clock_one_layer_below_top_is_by_design_not_other_layers(kit):
    contract = TK._landing_clock(kit)
    b = json.loads((kit / "budget.json").read_text())
    b["signal_max"] = "M8"
    (kit / "budget.json").write_text(json.dumps(b))
    errors = KC.clock_pin_geometry(kit)[0]
    assert not [e for e in errors if e.startswith("landing_contract.json: clock")], errors   # M7 under an M8 top: by design
    contract["pins"][0]["layer"] = "M6"
    (kit / "landing_contract.json").write_text(json.dumps(contract))
    assert [e for e in KC.clock_pin_geometry(kit)[0] if e.startswith("landing_contract.json: clock")]
