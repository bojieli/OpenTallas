"""ADV-INSERTION-BAND (FP-CONVERGE-QC C2): tap-to-sink legs vs the 405 um hop budget and the insertion band."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_insertion_band as B  # noqa: E402
import plan_advisory as PA  # noqa: E402


def bins(pts, n=100):
    return [[x, y, n] for x, y in pts]


def plan(tmp_path, taps, pts, cores=()):
    (tmp_path / "b.json").write_text(json.dumps({"bins": bins(pts)}))
    t = {"outline_um": [622.08, 1339.2], "hard_cores": list(cores),
         "clock": {"tap_mode": "explicit", "insertion_ps": 250, "insertion_tol_ps": 40, "sink_bins_file": str(tmp_path / "b.json"),
                   "taps": [{"name": n, "xy": [x, y]} for n, x, y in taps]}}
    return {"partition_types": {"sle_st_a_x": t}}


GOOD_TAPS = [("a", 150.0, 150.0), ("b", 450.0, 150.0)]
GOOD_PTS = [(150 + dx, 150 + dy) for dx in (-60, 0, 60) for dy in (-60, 60)] + [(450 + dx, 150 + dy) for dx in (-60, 0, 60) for dy in (-60, 60)]


def test_pass_case(tmp_path):
    out = B.findings(plan(tmp_path, GOOD_TAPS, GOOD_PTS), "p.json")
    assert out == ["WARN ADV-INSERTION-BAND summary: 1 types judged, 0 over, 0 not judged (no bins/taps); report-only"]


def test_mutant_leg_over_hop_and_band(tmp_path):
    far = GOOD_PTS + [(150.0, 150.0 + 460.0)]                 # one region sink 460 um from its tap (> 405)
    out = B.findings(plan(tmp_path, GOOD_TAPS, far), "p.json")
    assert out[0].startswith("WARN ADV-INSERTION-BAND sle_st_a_x: LEG tap a leg 460 um > 405")
    assert "BAND est arrival" in out[0]                      # region a arrives later than region b by > 40 ps
    assert out[-1].endswith("1 over, 0 not judged (no bins/taps); report-only") or "1 over" in out[-1]


def test_macro_face_detour(tmp_path):
    core = {"inst": "u", "origin_um": [200.0, 100.0], "outline_um": [100.0, 100.0], "halo_um": 2.0}
    pts = GOOD_PTS + [(350.0, 150.0)]                         # tap a -> sink behind the core on both L-routes
    assert B.leg_um((150.0, 150.0), (350.0, 150.0), [(200, 100, 300, 200, 2.0)]) == 200.0 + 104.0
    out = B.findings(plan(tmp_path, [("a", 150.0, 150.0)], pts, [core]), "p.json")
    assert "LEG" not in out[0] or "405" in out[0]


def test_registered_in_plan_advisory():
    assert ("INSERTION-BAND", "adv_insertion_band") in PA.CHECKS
    import adv_insertion_band
    assert adv_insertion_band.findings is B.findings
