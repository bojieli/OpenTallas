"""swap_ahub_boundary pins the AP_OFS of the hardened qkd_ahub ck7_r27 view (and ties it to the strap view, KV-AHUB-RH1) (KV AP_OFS re-harden 11-14:
ffe0ffdfffdfffdf = the bound hub_C value, derived by kv_regen from the landed ES/EN ap depth; ffddffdc.. is stale)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_core_clocks as K  # noqa: E402

CORES = [dict(inst="ahub", module="qkd_ahub", native_boundary_adapter="qkd_ahub_ck7_r27")]


def _bound(ap):
    return ("module t(input ck, input [35:0] am0,am1,am2,am3);\n"
            f"    qkd_ahub_static_dw #(.AP_OFS({ap}), .FR_OFS(-7), .Z_IN_STRIDE(4)) u_ahub (\n"
            "        .ck(ck),\n        .am0(am0),\n        .am1(am1),\n        .am2(am2),\n        .am3(am3)\n    );\nendmodule\n")


def test_new_ap_ofs_accepted():
    out, receipt = K.swap_ahub_boundary(_bound("64'hffe0ffdfffdfffdf"), CORES)
    assert "qkd_ahub u_ahub (" in out
    assert receipt[0]["native_params"]["AP_OFS"] == "64'hffe0ffdfffdfffdf"


def test_old_ap_ofs_refused():
    with pytest.raises(ValueError, match="native parameter signature changed"):
        K.swap_ahub_boundary(_bound("64'hffddffdcffdfffdf"), CORES)


STRAP = [dict(inst="ahub", module="qkd_ahub", native_boundary_adapter="qkd_ahub_ck7_strap")]


def test_strap_view_ties_bound_table():
    out, receipt = K.swap_ahub_boundary(_bound("64'hffe3ffe2ffe1ffe1"), STRAP)
    assert "qkd_ahub u_ahub (" in out and "qkd_ahub_static_dw" not in out
    assert ".strap_ofs_ap(32'he3e2e1e1)" in out and ".strap_ofs_fr(8'hf9)" in out
    assert ".ck({7{ck}})" in out and ".am0({am0[35:2], am0[0]})" in out
    assert receipt[0]["adapter"] == "qkd_ahub_ck7_strap"
    assert [t["pin"] for t in receipt[0]["tieoffs"]] == ["strap_ofs_ap", "strap_ofs_fr"]
    assert receipt[0]["cycles_changed"] == 0


def test_strap_view_takes_any_8bit_table():
    out, _ = K.swap_ahub_boundary(_bound("64'hffddffdcffdfffdf"), STRAP)
    assert ".strap_ofs_ap(32'hdddcdfdf)" in out
    out, _ = K.swap_ahub_boundary(_bound("64'h0002000200020002"), STRAP)
    assert ".strap_ofs_ap(32'h02020202)" in out


def test_strap_view_refuses_wide_offset():
    with pytest.raises(ValueError, match="does not fit the 8-bit strap"):
        K.swap_ahub_boundary(_bound("64'hff00ffe2ffe1ffe1"), STRAP)


def test_strap_view_refuses_other_stride():
    b = _bound("64'hffe3ffe2ffe1ffe1").replace(".Z_IN_STRIDE(4)", ".Z_IN_STRIDE(16)")
    with pytest.raises(ValueError, match="Z_IN_STRIDE 4"):
        K.swap_ahub_boundary(b, STRAP)


def test_strap_values_match_core_encoding():
    assert K.ahub_strap_values("64'hffe3ffe2ffe1ffe1", "-7") == (0xE3E2E1E1, 0xF9)
