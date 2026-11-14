"""QC s29 (KIT-OPS-3 11-14): die-level clock.pregrt_ff_hold default + schema keys; a type's own value wins."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pregrt_ff_hold as P
import schema as S


def test_die_default_applies_and_type_wins():
    P.set_die_clock({"pregrt_ff_hold": True, "pregrt_hold_guard_ps": 30})
    try:
        assert P.config_lines({}) == ["export OT_PREGRT_FF_HOLD = 1", "export OT_PREGRT_HOLD_GUARD = 30"]
        assert P.config_lines({"clock": {"pregrt_ff_hold": False}}) == []
        assert P.config_lines({"clock": {"pregrt_hold_guard_ps": 45}})[1] == "export OT_PREGRT_HOLD_GUARD = 45"
    finally:
        P.set_die_clock({})
    assert P.config_lines({}) == []


def test_schema_accepts_die_level_keys():
    c = S.SCHEMA["properties"]["clock"]["properties"]
    assert {"pregrt_ff_hold", "pregrt_ff_hold_note", "pregrt_hold_guard_ps"} <= set(c)
    assert "hard_cores_deferred" in S.SCHEMA["properties"]["partition_types"]["additionalProperties"]["properties"]
