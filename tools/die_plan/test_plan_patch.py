import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import plan_patch as PP  # noqa: E402

PLAN = {"partition_types": {"T": {"a": 3, "b": True, "l": [1, 2]}}}


def row(*ops):
    return {"row": "R", "ops": list(ops)}


def test_test_only_row_is_a_pure_precondition():
    r = row({"op": "test", "path": "/partition_types/T/a", "value": 3})
    assert PP.apply_row(PLAN, r) == PLAN
    with pytest.raises(PP.PatchError, match="have 3"):
        PP.apply_row(PLAN, row({"op": "test", "path": "/partition_types/T/a", "value": 4}))


def test_replace_needs_old_value_check_and_input_is_untouched():
    t = {"op": "test", "path": "/partition_types/T/a", "value": 3}
    out = PP.apply_row(PLAN, row(t, {"op": "replace", "path": "/partition_types/T/a", "value": 5}))
    assert out["partition_types"]["T"]["a"] == 5 and PLAN["partition_types"]["T"]["a"] == 3
    out = PP.apply_row(PLAN, row({"op": "replace", "path": "/partition_types/T/b", "old": True, "value": False}))
    assert out["partition_types"]["T"]["b"] is False
    with pytest.raises(PP.PatchError, match="no old-value check"):
        PP.apply_row(PLAN, row({"op": "replace", "path": "/partition_types/T/a", "value": 5}))
    with pytest.raises(PP.PatchError, match="old value differs"):
        PP.apply_row(PLAN, row({"op": "replace", "path": "/partition_types/T/a", "old": 9, "value": 5}))


def test_add_remove_missing_and_unknown_fail_closed():
    out = PP.apply_row(PLAN, row({"op": "add", "path": "/partition_types/T/n", "value": 1}))
    assert out["partition_types"]["T"]["n"] == 1
    for bad in (row({"op": "add", "path": "/partition_types/T/a", "value": 1}),
                row({"op": "remove", "path": "/partition_types/T/a"}),
                row({"op": "test", "path": "/partition_types/X/a", "value": 1}),
                row({"op": "move", "path": "/partition_types/T/a", "value": 1}),
                row({"op": "replace", "path": "/partition_types/T/zz", "old": 1, "value": 2})):
        with pytest.raises(PP.PatchError):
            PP.apply_row(PLAN, bad)
    out = PP.apply_row(PLAN, row({"op": "remove", "path": "/partition_types/T/l/0", "old": 1}))
    assert out["partition_types"]["T"]["l"] == [2]
