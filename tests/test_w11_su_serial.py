"""W11 stream-unit elements in the serial clock domain (1.111 ns SS/FF, 60/25 ps): record consistency."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "results/physical_abi3/asap7/hdc/v41x/w11_serial"
sys.path.insert(0, str(ROOT / "tools"))


def _rows():
    return {r["run"]: r for r in json.loads((DIR / "summary.json").read_text())["runs"]}


def test_light_lane_closes_in_the_serial_domain():
    r = _rows()["sc_l5"]
    assert r["closed"] and r["status"] == "pass" and r["clock_period_ns"] == 1.111
    assert r["setup_wns_ps"] >= 0 and r["hold_wns_ps"] >= 0 and r["drc"] == 0 and r["signal_integrity_clean"]
    assert r["uncertainty_setup_hold_ps"] == [60, 25] and r["parameters"] == {"MLAT": 5, "ALAT": 4}
    assert r["ss_fmax_mhz"] >= 900


def test_failed_verdicts_are_kept():
    rows = _rows()
    assert rows["sc_l5m5"]["status"] == "error"          # M2-M5 congested at 25 % utilisation
    for n in ("sc_l1", "sc_l2", "sc_l3"):
        assert not rows[n]["closed"]


def test_summary_depths_match_the_campaign_model():
    import rtl_hdc_v41x_vec_campaign as C
    d = json.loads((DIR / "summary.json").read_text())["depths"]
    C.set_mlat(3, 3)
    assert d["before"]["linear_emit_to_write"] == 21 and d["before"]["exp_in_S"] == 49
    assert d["before"]["reducer_retire_to_result_tap0"] == 26
    C.set_mlat(5, 4)
    s = d["serial_build"]
    assert s["exp_in_S"] == C.SFU_DEPTH[C.I.SFU_EXP] == 71
    assert s["linear_emit_to_write"] == 30 and s["sigmoid_silu_in_S"] == 94 and s["reducer_retire_to_result_tap0"] == 35
    C.set_mlat(3, 3)


def test_every_record_is_pinned_to_a_clean_commit():
    for r in _rows().values():
        assert r["commit"] and r["worktree_dirty"] is False
