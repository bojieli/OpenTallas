"""Calibration claims must follow measured parameters, including SU width."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from qwen_rom_rt_token_w12 import runtime_claim


def test_tp2_su64_calibration_claim():
    import json
    p = ROOT / "results/rtl/qwen_rom_w12_runtime/terminal_20261001/rt64_token.json"
    claim = runtime_claim(json.loads(p.read_text())["design_point"])
    for text in ("TP-2", "G=6,144", "1,536 tile", "SU width 64", "tree cut 6",
                 "SMIN=6", "SMAX=11", "collective link latency 11 cycles"):
        assert text in claim
    assert "5,120" not in claim and "1,280" not in claim
    assert "product-rate ratios" in claim and "SS/FF" in claim
    assert "isolated W12 companion" in claim


def test_tp4_product_and_alternate_group_claims_follow_parameters():
    d = dict(tp=4, groups_per_die=6144, tiles_per_die=1536, su_width=1024,
             tree_cut=7, smin=7, smax=11, su_reducer_time_levels=7, collective_lat_cycles=339)
    claim = runtime_claim(d)
    for text in ("TP-4", "SU width 1024", "tree cut 7", "SMIN=7", "collective link latency 339 cycles"):
        assert text in claim
    d.update(tp=2, groups_per_die=5120, tiles_per_die=1280, su_width=64)
    claim = runtime_claim(d)
    assert "G=5,120" in claim and "1,280 tile" in claim and "SU width 64" in claim
