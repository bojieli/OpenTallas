"""S81-STAGE-SEAT: ADV-PLACED-HOP-RATIO on placed_scan.json: clean + mutant + absent + plan_advisory registration."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_placed_hop_ratio as A  # noqa: E402


def _scan(tmp, mean):
    d = {"type": "t5", "groups": [
        {"src": "u_a", "end": "u_b", "bits": 100, "mean_um": mean, "row": "2/300um"},
        {"src": "u_c", "end": "u_d", "bits": 8, "mean_um": 900, "row": "none"}]}
    p = Path(tmp) / "placed_scan.json"
    p.write_text(json.dumps(d))
    return str(p)


def test_clean_and_mutant(tmp_path):
    ok = A.findings({}, None, placed_scan=_scan(tmp_path, 340))              # 340 <= 1.2 x 300 = 360
    assert len(ok) == 1 and "0 groups" in ok[0]
    bad = A.findings({}, None, placed_scan=_scan(tmp_path, 584))
    assert any("u_a->u_b placed 584 um plan 300 um x1.9" in x for x in bad) and "1 groups / 100 bits" in bad[-1]


def test_absent_is_info_not_warn(tmp_path):
    out = A.findings({}, None, placed_scan=str(tmp_path))
    assert len(out) == 1 and out[0].startswith("#")


def test_registered_in_plan_advisory():
    import plan_advisory as PA
    assert ("PLACED-HOP-RATIO", "adv_placed_hop_ratio") in PA.CHECKS
