"""W11 FP32 add/mul latency sweep at SS (record consistency)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REC = ROOT / "results/physical_abi3/asap7/hdc/w11_fp/w11_fp_latency_sweep.json"


def test_selected_depths_close_at_their_domain_clock():
    rec = json.loads(REC.read_text())
    rows = {(r["unit"], r["lat"], r["target_period_ns"]): r for r in rec["rows"]}
    assert rows[("add", 7, 0.833)]["closed"] and rows[("add", 7, 0.833)]["ss_fmax_mhz"] >= 1200
    assert rows[("mul", 6, 0.833)]["closed"] and rows[("mul", 6, 0.833)]["ss_fmax_mhz"] >= 1200
    assert rows[("add", 3, 1.111)]["closed"] and rows[("add", 3, 1.111)]["ss_fmax_mhz"] >= 900
    assert not rows[("mul", 3, 1.111)]["closed"]          # the serial domain needs mul LAT 4
    assert rows[("mul", 4, 0.833)]["ss_fmax_mhz"] >= 900


def test_every_row_is_a_routed_ss_record():
    rec = json.loads(REC.read_text())
    for r in rec["rows"]:
        d = json.loads((REC.parent / r["run"] / "physical.json").read_text())
        assert d["design"]["clock_uncertainty_ns"] == 0.06
        assert "WC" in " ".join(d["runner"]["argv"]) and "ADDER_MAP_FILE=" in " ".join(d["runner"]["argv"])
