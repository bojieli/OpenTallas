"""Published closure verdicts name the setup slack by its corner (SIGNOFF 10-24); acceptance is unchanged."""
import os
import tempfile
os.environ.setdefault("CL_STATE", tempfile.mkdtemp(prefix="vmnames_"))
import closure_loop as cl


def test_tt_route_publishes_tt_setup_and_ss_info():
    m = dict(ss_ps=17.77, ss_tns_ps=0.0, ff_ps=6.59, drc=0, setup_corner="tt", ss_sensitivity_ps=-295.16,
             ss_sensitivity_tns_ps=-664737.1)
    v = cl.verdict_metrics(m)
    assert v["tt_setup_ps"] == 17.77 and v["ss_info_ps"] == -295.16 and v["ss_info_tns_ps"] == -664737.1
    assert v["ss_ps"] == 17.77 and "ss_ps" in v["deprecated_keys"]         # alias kept for existing readers
    assert v["ff_ps"] == 6.59 and v["drc"] == 0


def test_ss_corner_route_has_no_tt_value():
    v = cl.verdict_metrics(dict(ss_ps=4.0, ff_ps=1.0, drc=0, setup_corner="ss"))
    assert v["tt_setup_ps"] is None and v["ss_info_ps"] == 4.0


def test_acceptance_line_unchanged():
    assert (cl.SS_MIN, cl.FF_MIN) == (0.0, 0.0)
    assert cl.setup_corner_label(dict(setup_corner="tt")) == "TT"
