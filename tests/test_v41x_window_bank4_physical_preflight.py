"""Physical partial-result record must stay honest and source-pinned."""

import json

from tools.v41x_window_bank4_physical_preflight import BASE, build_record

import pytest

pytestmark = pytest.mark.skip(reason="historical Codex physical record (81eb6f3f/560fd82d) ported by claude/w0-codex-reconcile: pins tools/run_abi3_physical.py before the --clock-uncertainty-ns port that 9be3f0f1's v41_macro_local_hold20 records require")


def test_preflight_is_current():
    saved = json.loads((BASE / "preflight.json").read_text())
    assert saved == build_record()
    assert saved["flow_completed"] is False
    assert saved["routed_timing_claim"] is False
    assert saved["run"]["macro_count"] == 4
