from types import SimpleNamespace

import pytest

from scalar_hold_pads import install


def test_scalar_hold_pads_absent_has_no_kit_side_effects(tmp_path):
    plan = SimpleNamespace(types={"T": {"clock": {}}})
    assert install(plan, "T", tmp_path) == []
    assert not list(tmp_path.iterdir())


def test_scalar_hold_pads_preserve_pre_detail_hook_and_reject_vector(tmp_path):
    rows = [{"port": "status_i", "capture": "u_capture/q$_DFF_P_", "count": 3}]
    plan = SimpleNamespace(types={"T": {"module": "tile", "clock": {"scalar_hold_pads": rows}}})
    (tmp_path / "rtl").mkdir()
    wrapper = tmp_path / "rtl/tile.sv"
    wrapper.write_text("module tile(\n    input wire [1:0] status_i,\n    input wire clk);\nendmodule\n")
    pre = tmp_path / "face_flops_release.tcl"
    pre.write_text("puts stock_release\n")
    with pytest.raises(ValueError, match="invalid or duplicate scalar hold pad"):
        install(plan, "T", tmp_path)
    assert pre.read_text() == "puts stock_release\n"

    wrapper.write_text("module tile(\n    input wire status_i,\n    input wire clk);\nendmodule\n")
    assert install(plan, "T", tmp_path) == ["export POST_DETAIL_PLACE_TCL = /work/scalar_hold_pads_check.tcl"]
    assert pre.read_text().startswith("puts stock_release\n")
    assert pre.read_text().endswith("ot_scalar_hold_insert\n")
    assert (tmp_path / "scalar_hold_pads_check.tcl").read_text().endswith("ot_scalar_hold_check\n")
    assert "status_i {u_capture/q$_DFF_P_} 3 buffer" in (tmp_path / "scalar_hold_pads_plan.tcl").read_text()
