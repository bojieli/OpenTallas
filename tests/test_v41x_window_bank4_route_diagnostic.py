"""The failed route must remain source-pinned and cannot claim closure."""

import json

from tools.v41x_window_bank4_route_diagnostic import BASE, run


def test_route_diagnostic_is_current():
    record = json.loads((BASE / "route_diagnostic.json").read_text())
    assert record == run()
    assert record["expanded_hold_repair"]["detail_route_maze_failures"] > 0
    assert record["routed_timing_claim"] is False
    assert record["routed_drc_claim"] is False
