"""KIT-OPS-5 11-15 (OWNER via COORD): an attempt of an older plan event is never resumed / kill-pinned; the item is generated fresh."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW  # noqa: E402


def test_same_event_or_no_event_is_current():
    d = {"event": "s29q103S4C"}
    assert KW.prev_on_current_plan({"event": "s29q103S4C"}, d)
    assert KW.prev_on_current_plan({}, d)
    assert KW.prev_on_current_plan({"event": "x"}, {})


def test_older_event_is_not_current():
    assert not KW.prev_on_current_plan({"event": "s29q103S3R"}, {"event": "s29q103S4C"})
    assert not KW.prev_on_current_plan({"event": "kvgeom5"}, {"event": "kvgeom6"})
