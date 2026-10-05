import json

from tools.w13_column_corner_gate import CHIP, POLICY, check, digest


def fixture(root):
    block = "ot_gpu_tc16"
    source = root / "rtl/top.sv"
    source.parent.mkdir()
    source.write_text("module top; endmodule\n")
    record = {"schema": "opentallas-chip-block-corners-v1", "block": block, "clock_period_ps": 833.0, "policy": POLICY,
              "closed_signoff": True, "sources": [{"path": "rtl/top.sv", "sha256": digest(source)}], "corners": {}}
    for corner, timing in (("SS", "setup"), ("FF", "hold")):
        model = CHIP / "abstracts" / block / f"{block}_{corner.lower()}.lib"
        (root / model).parent.mkdir(parents=True, exist_ok=True)
        (root / model).write_text(corner)
        record["corners"][corner] = {"rc": 0, "macros_at_tt": [], "timing_model": str(model),
                                    timing + "_wns_ps": 3.0, timing + "_tns_ps": 0.0}
    path = root / CHIP / "corners" / f"{block}.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(record))
    return block, path, record


def test_failed_verdict_with_existing_ss_lib_is_rejected(tmp_path):
    block, path, record = fixture(tmp_path)
    assert check(tmp_path, block, ["rtl/top.sv"])["passed"]
    record["closed_signoff"] = False
    record["corners"]["SS"]["setup_wns_ps"] = -1
    path.write_text(json.dumps(record))
    before = path.read_bytes()
    result = check(tmp_path, block, ["rtl/top.sv"])
    assert "failed_signoff_verdict" in result["issues"]
    assert "SS:invalid_setup_wns_ps" in result["issues"]
    assert path.read_bytes() == before


def test_source_drift_and_incomplete_source_list(tmp_path):
    block, _, _ = fixture(tmp_path)
    (tmp_path / "rtl/top.sv").write_text("changed")
    result = check(tmp_path, block, ["rtl/top.sv", "rtl/missing.sv"])
    assert "source_list_mismatch" in result["issues"]
    assert "source_pin_mismatch:rtl/top.sv" in result["issues"]


def test_unqualified_corner_and_missing_ff_model(tmp_path):
    block, path, record = fixture(tmp_path)
    record["corners"]["SS"]["macros_at_tt"] = ["memory"]
    record["corners"]["FF"]["hold_wns_ps"] = float("nan")
    path.write_text(json.dumps(record))
    (tmp_path / record["corners"]["FF"]["timing_model"]).unlink()
    result = check(tmp_path, block, ["rtl/top.sv"])
    assert "SS:unqualified_macro_corner" in result["issues"]
    assert "FF:invalid_hold_wns_ps" in result["issues"]
    assert "FF:missing_or_wrong_timing_model" in result["issues"]


def test_missing_record_and_wrong_constraints(tmp_path):
    assert check(tmp_path, "ot_gpu_tc16", ["rtl/top.sv"])["issues"] == ["missing_corner_record"]
    block, path, record = fixture(tmp_path)
    record.update(clock_period_ps=920.0, policy="TT pathfinding")
    path.write_text(json.dumps(record))
    result = check(tmp_path, block, ["rtl/top.sv"])
    assert "wrong_clock_period" in result["issues"]
    assert "wrong_uncertainty_policy" in result["issues"]
