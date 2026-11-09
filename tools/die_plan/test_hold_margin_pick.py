"""hold_margin_pick.py: HBM big-core GRT hold-repair target (HBM-CORES-B 11-09)."""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import hold_margin_pick as P  # noqa: E402

CFG = "export OT_HOLD_FF_MARGIN = 0\nexport OT_HOLD_FF_MARGIN_BIG = 35\nexport OT_HOLD_FF_MARGIN_BIG_CELLS = 100000\n"


def cells(n):
    return json.dumps({"schema": "opentallas.native_cell_count.v1", "stage": "pre_floorplan", "stdcells": n,
                       "macros": 0, "limit": 400000})


def test_big_core_gets_target_and_reg2reg():
    assert P.pick("0", CFG, cells(139000)) == (35.0, "reg2reg", P.pick("0", CFG, cells(139000))[2])
    assert "139000 stdcells > 100000" in P.pick("0", CFG, cells(139000))[2]


def test_small_core_keeps_margin():
    hm, scope, _ = P.pick("0", CFG, cells(60000))
    assert (hm, scope) == (0.0, None)


def test_threshold_is_strict():
    assert P.pick("0", CFG, cells(100000))[:2] == (0.0, None)
    assert P.pick("0", CFG, cells(100001))[:2] == (35.0, "reg2reg")


def test_explicit_larger_margin_wins():
    assert P.pick("40", CFG, cells(200000))[:2] == (40.0, None)


def test_kit_nonport_scope_kept():
    assert P.pick("0", CFG + "export OT_HOLD_REPAIR_SCOPE = nonport\n", cells(200000))[:2] == (35.0, "nonport")


def test_kit_override_export_last_wins():
    cfg = CFG + "override export OT_HOLD_FF_MARGIN_BIG = 0\n"
    assert P.pick("0", cfg, cells(200000))[:2] == (0.0, None)


def test_missing_keys_or_receipt_keep_margin():
    assert P.pick("10", "export OT_HOLD_FF_MARGIN = 10\n", cells(200000))[:2] == (10.0, None)
    assert P.pick("10", CFG, None)[:2] == (10.0, None)
    assert P.pick("10", CFG, "{not json")[:2] == (10.0, None)


def test_cli_line(tmp_path):
    (tmp_path / "config.mk").write_text(CFG)
    (tmp_path / "n.json").write_text(cells(150000))
    out = subprocess.run([sys.executable, "-I", str(HERE / "hold_margin_pick.py"), "0", str(tmp_path / "config.mk"),
                          str(tmp_path / "n.json")], capture_output=True, text=True, check=True).stdout
    assert out.startswith("OT_HOLD_PICK hm=35 scope=reg2reg reason=")
    out = subprocess.run([sys.executable, "-I", str(HERE / "hold_margin_pick.py"), "0", str(tmp_path / "config.mk"),
                          str(tmp_path / "missing.json")], capture_output=True, text=True, check=True).stdout
    assert out.startswith("OT_HOLD_PICK hm=0 scope=- ")


def test_runner_and_generator_wire_it():
    run = (HERE.parents[1] / "physical/die_plan/hbm_arch_cores/run_kit_hbm.sh").read_text()
    gen = (HERE.parents[1] / "physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py").read_text()
    assert "/work/hold_margin_pick.py" in run and "OT_HOLD_REPAIR_SCOPE=" in run
    assert '"hold_margin_pick.py"' in gen and "OT_HOLD_FF_MARGIN_BIG = " in gen
