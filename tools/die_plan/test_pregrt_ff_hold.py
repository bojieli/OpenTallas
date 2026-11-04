"""HEAD-TILE-PREGRT-HOLD + clock.tap_core_etap plan forms (DH59-TILE 11-03): opt-in, off writes nothing."""
from pathlib import Path
import pytest
import gen_phys
import pregrt_ff_hold as PG
import schema

HERE = Path(__file__).resolve().parent


def test_off_writes_nothing(tmp_path):
    (tmp_path / "hold_gate.tcl").write_text("x\n" + PG.MARK + "y\n")
    assert PG.install({"clock": {}}, tmp_path) is False
    assert not (tmp_path / "pregrt_ff_hold.tcl").exists()


def test_on_keeps_the_gate_context_and_drops_the_verdict(tmp_path):
    (tmp_path / "hold_gate.tcl").write_text((HERE / "hold_gate.tcl").read_text())
    assert PG.install({"clock": {"pregrt_ff_hold": True}}, tmp_path) is True
    t = (tmp_path / "pregrt_ff_hold.tcl").read_text()
    assert "ot_io_hold_apply" in t and "OT_FWD_RING_INPUTS" in t       # same boundary contract as the gate
    assert "OT_HOLD_GATE FAIL" not in t and "OT_HOLD_STOP_PS" not in t  # no verdict: only sign-off blocks
    assert "repair_timing -hold" in t and "detailed_placement" in t and "check_placement" in t
    assert t.rstrip().endswith("write_db $::env(ODB)")


def test_marker_missing_fails_closed(tmp_path):
    (tmp_path / "hold_gate.tcl").write_text("no marker\n")
    with pytest.raises(ValueError):
        PG.install({"clock": {"pregrt_ff_hold": True}}, tmp_path)


def test_run_kit_step_is_guarded_and_before_grt():
    rk = gen_phys.RUN_KIT
    assert rk.count("grep -q '^export OT_PREGRT_FF_HOLD = 1' /work/config.mk") == 1
    assert rk.index("/work/hold_gate.log") < rk.index("/work/pregrt_ff_hold.tcl") < rk.index("OT_VCLK_CORNER=ff")


def test_schema_keys():
    ck = schema.SCHEMA["properties"]["partition_types"]["additionalProperties"]["properties"]["clock"]["properties"]
    assert ck["tap_core_etap"] == {"type": "boolean"} and ck["pregrt_ff_hold"] == {"type": "boolean"}
