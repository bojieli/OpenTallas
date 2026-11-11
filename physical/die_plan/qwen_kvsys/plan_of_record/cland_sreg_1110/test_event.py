"""cland_sreg_1110 event: only landing_status_reg on the named types changes, every other byte stays."""
import importlib.util
import json
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("cland_sreg_event", HERE / "event.py")
ev = importlib.util.module_from_spec(spec); spec.loader.exec_module(ev)
PLAN = HERE.parent / "plan_c.json"


def test_only_status_reg_changes_on_main_plan():
    text = PLAN.read_text()
    out, changed = ev.apply(text, ev.DEFAULT_TYPES)
    a, b = json.loads(text), json.loads(out)
    assert changed and set(changed) <= set(ev.DEFAULT_TYPES)
    for tn in changed:
        assert b["partition_types"][tn].pop("landing_status_reg") is True
    assert a == b
    # re-applying is a no-op
    out2, changed2 = ev.apply(out, ev.DEFAULT_TYPES)
    assert out2 == out and changed2 == []
    # outside the changed type objects the text is byte-same
    assert len(out.splitlines()) - len(text.splitlines()) == len(changed)


def test_rejects_type_without_status_copy_ring():
    p = json.loads(PLAN.read_text())
    plain = next(k for k, v in p["partition_types"].items() if not v.get("landing_control_status_copy"))
    with pytest.raises(SystemExit, match="landing_control_status_copy"):
        ev.apply(PLAN.read_text(), (plain,))
