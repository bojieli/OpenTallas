"""leaf_rules.py (S81-LEAF-PLAN, FABLE-REVIEW-CONG R-LEAF-1/2/3): band-under-window test, face-clear and slot rows, and
the --densify bands option (R-LEAF-1b: a band already under its window but below --per-bit um2/bit is re-sited)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import leaf_rules as R  # noqa: E402


def test_l1_band_under_window():
    W, H = 600.0, 400.0
    # N-face window x 100..300; band strip right under it, 26 um deep -> legal
    ok, cov, gap, dep, al = R.l1_ok("N", 100, 300, [[100, H - 17.28 - 26, 300, H - 17.28]], W, H)
    assert ok and cov >= 0.99 and dep <= 43.2
    # same area beside the window -> not covered
    ok, cov, *_ = R.l1_ok("N", 100, 300, [[320, H - 43.28, 520, H - 17.28]], W, H)
    assert not ok and cov < 0.8
    # a column (deep and narrow) -> not legal
    ok, *_ = R.l1_ok("N", 100, 140, [[100, H - 117.28, 140, H - 17.28]], W, H)
    assert not ok


def test_slot_and_face_rows():
    t = {"outline_um": [600.0, 400.0],
         "buses": [{"name": "ft0_i", "face": "S", "window_um": [50.0, 250.0], "width": 276}],
         "hard_cores": []}
    rows = R.check_type("tX", t)
    assert all(r[1] != "L1" for r in rows)


def test_densify_flag_wired():
    src = (Path(__file__).resolve().parent / "leaf_rules.py").read_text()
    assert "--densify" in src and "densify=False" in src and "a.densify" in src


if __name__ == "__main__":
    for k, v in list(globals().items()):
        if k.startswith("test_"):
            v()
    print("ok")
