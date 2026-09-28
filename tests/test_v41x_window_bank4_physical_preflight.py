"""Physical partial-result record must stay honest and source-pinned."""

import json

from tools.v41x_window_bank4_physical_preflight import BASE, build_record


def test_preflight_is_current():
    saved = json.loads((BASE / "preflight.json").read_text())
    assert saved == build_record()
    assert saved["flow_completed"] is False
    assert saved["routed_timing_claim"] is False
    assert saved["run"]["macro_count"] == 4
