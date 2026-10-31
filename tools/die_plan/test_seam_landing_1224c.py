"""OWNER 12.24c (COORD 10-31): seam_landing planner setup estimate uses the nominal 0 ps setup uncertainty."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import seam_landing as SL  # noqa: E402
from die_sta import PERIOD_PS  # noqa: E402

M = json.loads((Path(__file__).resolve().parent / "die_ci_margins.json").read_text())


def test_budget_setup_nominal_hold_unchanged(monkeypatch):
    monkeypatch.delenv("OT_MARGIN_POLICY", raising=False)
    lib, xt = M["lib"], M["derived"]["xtalk_default"]
    b = SL.budgets(M)
    assert b["unc_setup_ps"] == 0.0 and b["unc_hold_ps"] == 25.0
    assert b["setup_tt_ps"] == round(PERIOD_PS - lib["TT"]["clk_q_max_ps"] - lib["TT"]["setup_ps"] - xt["setup_ps"], 2)
    assert b["hold_ff_ps"] == round(lib["FF"]["clk_q_min_ps"] - lib["FF"]["hold_ps"] - 25.0 - xt["hold_ps"], 2)
    legacy = SL.budgets(M, "legacy")
    assert round(b["setup_tt_ps"] - legacy["setup_tt_ps"], 2) == 60.0 and legacy["hold_ff_ps"] == b["hold_ff_ps"]
