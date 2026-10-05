import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from qwen_o4_slot_budget import OUTPUT, derive  # noqa: E402


def test_record_is_current_and_bounds_m5():
    got = derive()
    assert got == json.loads(OUTPUT.read_text())
    assert got["best_fitting_linear_estimate"]["slots"] == 3
    sweep = got["slot_sweep"]
    assert [row["fits_linear_tile_estimate"] for row in sweep] == [True, True, True, False, False]
    assert sweep[2]["best_serial_model"]["tokens_s"] < got["m5_design_rate_tokens_s"]
