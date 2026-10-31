"""COORD 10-30 15:27 (HBM-CORES-KITS-28 ASK rst_col, default A): gen_core_kit_hbm writes the typed boundary
declaration (core.json boundary_role + boundary_guard_context.json v1) so sign-off face_guard and lec read the
kit's reset/clock ports from the kit, not from name patterns; data pins are never exempted."""
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "tools" / "die_plan"))
import signoff  # noqa: E402
import lec  # noqa: E402

spec = importlib.util.spec_from_file_location("coregen_bgctx", HERE / "gen_core_kit_hbm.py")
coregen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(coregen)


def test_hcol_form_bus_clock_and_reset(tmp_path):
    r = coregen.write_boundary_context(tmp_path, ["clk_pair[0]", "clk_pair[1]"], ["rst_col"])
    assert r == dict(clock_ports=["clk_pair"], reset_ports=["rst_col"])
    controls, ctx = signoff.boundary_controls(dict(kit=str(tmp_path)))
    assert controls == ["clk_pair", "rst_col"] and ctx["controls"] == controls
    assert lec.kit_reset_ports(tmp_path) == ["rst_col"]
    bg = json.loads((tmp_path / "boundary_guard_context.json").read_text())
    assert bg["data_pin_exemptions"] == [] and bg["unused_clock_ports"] == []
    # no hard-core latency contract: HBM cores keep the plan insertion target
    assert signoff.hard_core_latency_contract(dict(kit=str(tmp_path))) is None


def test_no_reset_and_retrofit_from_freeze(tmp_path):
    (tmp_path / "freeze.json").write_text(json.dumps(dict(schema="opentallas.hbm_arch.core_freeze.v1",
                                                          clocks=["clk"], resets=[])))
    r = coregen.retrofit_boundary_context(tmp_path)
    assert r == dict(clock_ports=["clk"], reset_ports=[])
    assert signoff.boundary_controls(dict(kit=str(tmp_path)))[0] == ["clk"]
    assert lec.kit_reset_ports(tmp_path) is None


def test_retrofit_refuses_other_schema(tmp_path):
    (tmp_path / "freeze.json").write_text(json.dumps(dict(schema="other", clocks=["clk"], resets=[])))
    try:
        coregen.retrofit_boundary_context(tmp_path)
    except SystemExit:
        return
    raise AssertionError("non-HBM freeze accepted")
