"""pytest: ADV-ROW-APPLIED by op content (S81 KVLEAF-T2-HARD-1 style: ops accepted by reference but not in the plan)."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adv_row_applied as A  # noqa: E402

PLAN = {"partition_types": {"t1": {"outline_um": [10, 20], "clock": {"tap_mode": "grid"}}}}


def test_full_none_partial():
    full = [{"op": "replace", "path": "/partition_types/t1/outline_um", "value": [10, 20]}]
    none = [{"op": "replace", "path": "/partition_types/t1/outline_um", "value": [99, 99], "old": [10, 20]}]
    part = full + [{"op": "add", "path": "/partition_types/t1/clock/x", "value": 1}]
    assert A.status(*A.applied(full, PLAN)[:2]) == "FULL"
    assert A.status(*A.applied(none, PLAN)[:2]) == "NONE" and A.applied(none, PLAN)[2] == 1          # still at the old value
    assert A.status(*A.applied(part, PLAN)[:2]) == "PARTIAL"


def test_dotted_path_and_add_or_replace_and_remove():
    ops = [{"path": "partition_types.t1.clock.tap_mode", "value": "grid"}, {"op": "add_or_replace", "path": "/partition_types/t1/clock/tap_mode", "value": "grid"},
           {"op": "remove", "path": "/partition_types/t1/gone"}]
    assert A.applied(ops, PLAN)[:2] == (3, 3)


def test_findings_not_run_and_file(tmp_path):
    assert "NOT-RUN" in A.findings(PLAN, "p")[0]
    f = tmp_path / "row.json"
    f.write_text(json.dumps({"ops": [{"op": "replace", "path": "/partition_types/t1/outline_um", "value": [1, 1]}]}))
    out = A.findings(PLAN, "p", None, rows=[str(f)])
    assert "NONE 0/1" in out[0] and "NOT applied" in out[0] and "1 NONE" in out[-1]
    assert A.findings(None, "p", None, rows=["/nonexistent"])[0].startswith("WARN ADV-ROW-APPLIED not checked")
