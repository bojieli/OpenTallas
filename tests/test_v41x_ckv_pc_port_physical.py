"""The wide selected-CKV fetch port element (ot_chip_v41x_ckv_pc_port, P=4 / S=16, one 256x256 1R1W SRAM macro)
closes place-and-route at 0.833 ns (1.2 GHz) ORFS WC with WC/BC hold, full metal (HBM_SERVICE band, W18b), on the
current RTL: results/physical_abi3/asap7/chip/v41_ckv/pc_port_p4s16_0p833_wc/physical.json."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REC = ROOT / "results/physical_abi3/asap7/chip/v41_ckv/pc_port_p4s16_0p833_wc/physical.json"


def test_port_closed_at_0p833_wc_on_current_rtl():
    r = json.loads(REC.read_text())
    d = r["design"]
    assert d["closed"] is True and d["top"] == "ot_chip_v41x_ckv_pc_port"
    assert abs(r["target_clock_period_ns"] - 0.833) < 1e-9
    m = r["place_and_route"]["metrics"]
    assert m["setup_violations"] == 0 and m["hold_violations"] == 0 and m["drc_errors"] == 0
    assert m["setup_wns_ns"] >= 0 and m["hold_wns_ns"] >= 0
    assert m["max_slew_violations"] == 0 and m["max_cap_violations"] == 0 and m["max_fanout_violations"] == 0
    for s in d["sources"]:
        assert hashlib.sha256((ROOT / s["path"]).read_bytes()).hexdigest() == s["sha256"], s["path"]
