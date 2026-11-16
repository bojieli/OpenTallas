"""S81-SEAM-RST-1115: opt-in clock.tap_reset_affinity (tap_reset_affinity.tcl, last reset stage on its sinks' clock tap)."""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import schema  # noqa: E402


def test_schema_key_is_boolean_and_on_disk():
    p = schema.SCHEMA["properties"]["partition_types"]["additionalProperties"]["properties"]["clock"]["properties"]
    assert p["tap_reset_affinity"] == {"type": "boolean"}
    disk = json.loads((HERE / "die_plan.schema.json").read_text())
    q = disk["properties"]["partition_types"]["additionalProperties"]["properties"]["clock"]["properties"]
    assert q["tap_reset_affinity"] == {"type": "boolean"}


def test_gen_phys_exports_and_ships_the_tcl():
    g = (HERE / "gen_phys.py").read_text()
    assert '"tap_reset_affinity.tcl"' in g
    assert re.search(r'get\("tap_reset_affinity"\) is True', g) and "export OT_TAP_RESET_AFFINITY = 1" in g


def test_clock_taps_hook_is_opt_in_and_clock_pin_only():
    c = (HERE / "clock_taps.tcl").read_text()
    assert 'OT_TAP_RESET_AFFINITY) eq "1"' in c.replace("$::env(", "").replace("[info exists ::env(", "") or "OT_TAP_RESET_AFFINITY" in c
    t = (HERE / "tap_reset_affinity.tcl").read_text()
    # only the CLK / CLKN iterm is reconnected: no data, reset or cell edit
    assert t.count("$clk disconnect") == 1 and t.count("$clk connect") == 1
    assert "dbInst_create" not in t and "deleteInst" not in t and "swapMaster" not in t
