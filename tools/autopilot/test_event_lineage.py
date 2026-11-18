"""WAVE-FLOW-R2 11-17 (COORD r631): event_adopt:X is met whenever X is in the die's current event lineage (QC N1B: S4q6d, L2, M, then N1B), fixed at the term."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import hold_records as HR
import kit_wave as KW

N1B = {"event": "s29q103S4Q9N1B", "plan_event": "s29q103S4Q9M5",
       "event_lineage": ["S4q6d", "s29q103S4Q9L2", "s29q103S4Q9M"],
       "planned_events": ["S4q6d", "S4q6e", "S4q9l2", "S4q9l2d", "s29q103S4Q9L2", "s29q103S4Q9M", "s29q103S4Q9N", "s29q103S4Q9N1B"]}
CFG = {"dies": {"qc": N1B}}


def met(term, d=N1B):
    return HR.term_met(term, {}, "qc", "item", {"dies": {"qc": d}}, HR.Ctx())


def test_lineage_ancestors_release_event_adopt_terms():
    for t in ("event_adopt:S4q6d", "event_adopt:s29q103S4Q9L2", "event_adopt:s29q103S4Q9M", "event_adopt:s29q103S4Q9N1B", "event_adopt:S4q6d*"):
        assert met(t), t                                    # the 21 QC holds QC-PLAN-R3 re-pointed by hand were of this kind
        assert KW._hold_term_met(t, N1B, lambda r: False), t     # the legacy auto-release path (hold_release_on) agrees
    for t in ("event_adopt:s29q103S4Q9N", "event_adopt:S4q6e", "event_adopt:S4q9l2d", "event_adopt:s29q103S4Q9N2"):
        assert not met(t), t                                # a descendant, a sibling and a variant that is not in the lineage stay held
    assert not met("event_adopt:S4q6d", {k: v for k, v in N1B.items() if k != "event_lineage"})   # no recorded lineage: only the current identities release


def test_lineage_is_known_to_the_term_validator():
    d = {k: v for k, v in N1B.items() if k != "planned_events"}
    assert HR.term_error("event_adopt:S4q6d", "qc", {"dies": {"qc": d}}) is None
    assert "no event" in (HR.term_error("event_adopt:S4q6e", "qc", {"dies": {"qc": d}}) or "")
