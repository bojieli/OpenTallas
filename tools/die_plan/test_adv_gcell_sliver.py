"""ADV-GCELL-SLIVER: reference case (obs_gcell_cap.tcl header), pass and mutant."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_gcell_sliver as S  # noqa: E402
import plan_advisory as PA  # noqa: E402

REF_CENTRE = ((337.338 + 339.498) / 2, (345.06 + 346.41) / 2)      # the HEAD hd_host_e reserved rect


def plan(*xy):
    return {"partition_types": {"ty": {"clock": {"taps": [{"name": f"clk_t{i}", "xy": list(p)} for i, p in enumerate(xy)]}}}}


def test_reference_rect_is_a_sliver_on_the_top_edge():
    sl = dict(S.slivers(REF_CENTRE))
    assert sl == {"y+": 0.15}


def test_fixed_tap_is_silent_and_sliver_fix_finds_it():
    fx = S.sliver_fix(REF_CENTRE)
    assert fx is not None
    assert S.slivers((REF_CENTRE[0] + fx[0], REF_CENTRE[1] + fx[1])) == []
    assert S.findings(plan((REF_CENTRE[0] + fx[0], REF_CENTRE[1] + fx[1]))) == []


def test_mutant_reported_and_registered():
    out = S.findings(plan(REF_CENTRE))
    assert len(out) == 1 and out[0].startswith("WARN ADV-GCELL-SLIVER summary: 1 of 1 tap site rects (1 types)")
    assert ("GCELL-SLIVER", "adv_gcell_sliver") in PA.CHECKS
