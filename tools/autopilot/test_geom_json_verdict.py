"""P-FALSE-GREEN (S81-GATE-LINT 11-26): a FAIL auto_geom.json shown as PASS-COND.  python3 -m pytest -q tools/autopilot/test_geom_json_verdict.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW  # noqa: E402

FAIL_LINE = "AP_AUTO_GEOM AUTO-GEOM FAIL grt=FAIL(0.4) outline=ok(1)"


def test_advisory_fail_is_mapped_but_displayed_fail():
    v, _f, _t = KW.geom_gate(FAIL_LINE)
    assert v == "PASS-COND"                                   # the wave still goes on to sign-off (OWNER 11-03)
    raw = KW.geom_json_verdict(FAIL_LINE)
    assert raw == "FAIL" and KW.geom_display(v, raw) == "FAIL (waived: PASS-COND)"
    assert KW.geom_gate(FAIL_LINE, advisory=False)[0] == "FAIL"
    assert KW.geom_display("FAIL", "FAIL") == "FAIL"


def test_pass_stays_pass_and_missing_line_is_none():
    ok = "AP_AUTO_GEOM AUTO-GEOM PASS outline=ok(1)"
    assert KW.geom_display(KW.geom_gate(ok)[0], KW.geom_json_verdict(ok)) == "PASS"
    assert KW.geom_json_verdict("") is None
