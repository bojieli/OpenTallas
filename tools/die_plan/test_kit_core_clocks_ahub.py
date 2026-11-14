"""swap_ahub_boundary pins the AP_OFS of the hardened qkd_ahub ck7_r27 view (KV AP_OFS re-harden 11-14:
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
