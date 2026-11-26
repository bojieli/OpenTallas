import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import xtap_hold_census as X  # noqa: E402

BEFORE = "OT_PREGRT_FF_HOLD class before port_in 7 ws -166.77 same_tap 301 ws -20.39 cross_tap 1554 ws -57.53 port_out 0 ws 0.00\n"
AFTER = "OT_PREGRT_FF_HOLD class after port_in 6 ws -166.77 same_tap 0 ws 0.00 cross_tap 3 ws -49.25 port_out 0 ws 0.00\n"


def _kit(tmp, name, after, aff):
    g = tmp / "qwen_compute" / name
    g.mkdir(parents=True)
    (g / "pregrt_ff_hold.log").write_text(BEFORE + (after or ""))
    (g / "config.mk").write_text(f"export OT_TAP_PAIR_AFFINITY = {aff}\nexport OT_TAP_PAIR_UM = 64\n")
    return g


def test_parse_and_summary(tmp_path):
    a = _kit(tmp_path, "a", AFTER, 1)
    b = _kit(tmp_path, "b", AFTER.replace("cross_tap 3", "cross_tap 0"), 0)
    rows = [X.kit_row(a), X.kit_row(b)]
    assert rows[0]["before"]["cross_tap"] == 1554 and rows[0]["affinity"] and not rows[1]["affinity"]
    s = X.summarize(rows)["QC"]
    assert s["kits"] == 2 and s["residual_kits"] == 1 and s["residual_ends"] == 3 and s["residual_worst_ps"] == -49.25
    assert s["median_cross_before_on"] == 1554 and s["median_cross_before_off"] == 1554


def test_missing_log_is_skipped(tmp_path):
    assert X.kit_row(tmp_path) is None
