"""FLOW-OPS-0900 11-21 (FABLE-FLOW-0745 e): fail keys carry the first-error cause text, not a causeless header."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import flow_guard as FG  # noqa: E402
import kit_wave as KW  # noqa: E402

PF = """ot-run: RAN on intel1 (unit kw-x): exit 1
KIT_PREFLIGHT FAIL issues 1
  - macro_channels: macro column 4 x[959.052,1264.48]: E vertical channel 9.924 um < 10.8
make: *** [place] Error 1
"""
PF2 = PF.replace("9.924", "8.5").replace("x[959.052,1264.48]", "x[100.0,200.0]").replace("column 4", "column 7")
PF_OTHER = PF.replace("macro_channels: macro column 4 x[959.052,1264.48]: E vertical channel 9.924 um < 10.8",
                      "clock_entry_clear: io.tcl: clock entry clk_c0 (497.312, 125.28) over macro kv3_head_eighth_e1#1")


def test_preflight_reason_names_issue():
    cls, why = KW.classify("place", PF)
    assert "KIT_PREFLIGHT FAIL issues 1: macro_channels: macro column 4" in why, why


def test_preflight_key_groups_by_cause():
    k = lambda t: KW.fail_key({"a": 1}, *KW.classify("place", t))[0]
    assert k(PF) == k(PF2)               # numbers masked: same cause, same key
    assert k(PF) != k(PF_OTHER)          # another cause, another key
    assert FG.norm_text(KW.classify("place", PF)[1]) != FG.norm_text(KW.classify("place", PF_OTHER)[1])


def test_make_exit_header_gets_tool_error():
    line = KW.with_cause("FAIL_route make exit 2 (see run_route.log)",
                         "foo\nError: cts.tcl, 89 can't read \"tb_cdirect\": no such variable\nmake: *** Error 2\n")
    assert line.endswith("Error: cts.tcl, 89 can't read \"tb_cdirect\": no such variable"), line


def test_line_with_cause_unchanged():
    assert KW.with_cause("ValueError: bad pin", "anything") == "ValueError: bad pin"
    assert KW.with_cause("KIT_PREFLIGHT FAIL issues 1", "KIT_PREFLIGHT FAIL issues 1\nno bullets here\n") == "KIT_PREFLIGHT FAIL issues 1"


def test_route_make_fail_without_first_error_uses_tail():
    import autopilot as AP
    c = {"FAIL_route": "make exit 2 (see run_route.log)",
         "runlog_tail": "[INFO] x\n[ERROR GRT-0116] Global routing finished with congestion.\nmake: *** Error 2"}
    cls, kind, why = AP.classify(c, {})[:3]
    assert kind == "route-make-fail" and "GRT-0116" in why and "see run_route" not in why, why
    c = {"FAIL_route": "make exit 2 (see run_route.log)", "runlog_tail": "nothing useful"}
    assert "see run_route.log" in AP.classify(c, {})[2]       # nothing to name: the text stays as it was
