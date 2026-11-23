"""QC-COLL RST-COTAP 11-22: opt-in clock.tap_reset_split (tap_reset_split.tcl, per-tap copy of the last reset stage)."""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import schema  # noqa: E402


def test_schema_key_is_boolean_and_on_disk():
    p = schema.SCHEMA["properties"]["partition_types"]["additionalProperties"]["properties"]["clock"]["properties"]
    assert p["tap_reset_split"] == {"type": "boolean"}
    disk = json.loads((HERE / "die_plan.schema.json").read_text())
    q = disk["properties"]["partition_types"]["additionalProperties"]["properties"]["clock"]["properties"]
    assert q["tap_reset_split"] == {"type": "boolean"}


def test_gen_phys_exports_split_and_affinity_and_ships_the_tcl():
    g = (HERE / "gen_phys.py").read_text()
    assert '"tap_reset_split.tcl"' in g
    assert re.search(r'get\("tap_reset_split"\) is True', g) and "export OT_TAP_RESET_SPLIT = 1" in g
    # split implies the affinity pass (majority tap first, copies for the other taps)
    assert re.search(r'tap_reset_affinity"\) is True or t\.get\("clock", \{\}\)\.get\("tap_reset_split"\) is True', g)


def test_clock_taps_hook_is_opt_in_and_after_affinity():
    c = (HERE / "clock_taps.tcl").read_text()
    assert c.index("tap_reset_affinity.tcl]") < c.index("tap_reset_split.tcl]")
    assert 'OT_TAP_RESET_SPLIT) eq "1"' in c


def test_split_copies_keep_polarity_and_inputs():
    t = (HERE / "tap_reset_split.tcl").read_text()
    # copies take the same master, every non-clock input net of the source, and the chain cells are copied per tap
    assert "dbInst_create $blk [$inst getMaster]" in t and "dbInst_create $blk [$ci getMaster]" in t
    assert "CLK CLKN" in t and "$a disconnect; $a connect $drv" in t
    assert "deleteInst" not in t and "swapMaster" not in t
    assert "puts \"OT_TAP_RESET_SPLIT sources" in t


def test_launch_cotap_is_opt_in_schema_and_export():
    # QC-COLL RST-LAUNCH 11-23: the launching synchroniser stage follows the moved/copied last stage onto its tap
    p = schema.SCHEMA["properties"]["partition_types"]["additionalProperties"]["properties"]["clock"]["properties"]
    assert p["tap_reset_split_launch"] == {"type": "boolean"}
    disk = json.loads((HERE / "die_plan.schema.json").read_text())
    q = disk["properties"]["partition_types"]["additionalProperties"]["properties"]["clock"]["properties"]
    assert q["tap_reset_split_launch"] == {"type": "boolean"}
    g = (HERE / "gen_phys.py").read_text()
    assert re.search(r'get\("tap_reset_split_launch"\) is True', g) and "export OT_TAP_RESET_SPLIT_LAUNCH = 1" in g


def test_launch_cotap_walks_back_to_tie_and_never_deletes():
    t = (HERE / "tap_reset_split.tcl").read_text()
    assert 'OT_TAP_RESET_SPLIT_LAUNCH) eq "1"' in t and "OT_TAP_RESET_SPLIT_LAUNCH_DEPTH" in t
    assert "proc back" in t and "proc launch" in t and "string match TIE*" in t
    # copies keep master and every non-clock input; a solo launcher only gets its clock pin moved
    assert "dbInst_create $blk [$l getMaster]" in t and "$lck disconnect; $lck connect [$blk findNet $t]" in t
    assert "deleteInst" not in t and "swapMaster" not in t
    assert 'puts "OT_TAP_RESET_SPLIT_LAUNCH stages' in t
    # the launch pass is gated: the default (no env) leaves the split byte-for-byte in behaviour
    run = t[t.index("proc run {}"):]
    assert run.count("if {$ldo}") == 3
