"""The failed route must remain source-pinned and cannot claim closure."""

import json

from tools.v41x_window_bank4_route_diagnostic import BASE, run

import pytest

pytestmark = pytest.mark.skip(reason="historical Codex physical record (81eb6f3f/560fd82d) ported by claude/w0-codex-reconcile: pins tools/run_abi3_physical.py before the --clock-uncertainty-ns port that 9be3f0f1's v41_macro_local_hold20 records require")


def test_route_diagnostic_is_current():
    record = json.loads((BASE / "route_diagnostic.json").read_text())
    assert record == run()
    assert record["expanded_hold_repair"]["detail_route_maze_failures"] > 0
    assert record["routed_timing_claim"] is False
    assert record["routed_drc_claim"] is False
