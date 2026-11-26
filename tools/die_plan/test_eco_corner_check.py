import json
import eco_corner_check as E


def mk(tmp, corner, ws, ff, tt):
    b = tmp / "run/logs/asap7/x/base"; b.mkdir(parents=True)
    (b / "6_report.log").write_text("read_liberty -corner %s /x.lib\n" % corner)
    (b / "6_report.json").write_text(json.dumps({"finish__timing__setup__ws": ws}))
    (tmp / "signoff").mkdir()
    (tmp / "signoff/signoff.json").write_text(json.dumps({"corners": {"tt": {"sdc_wns_max": tt}, "ff": {"sdc_wns_max": ff}}}))
    return tmp


def test_bc_report_matches_ff_not_tt(tmp_path):                      # slw_hc1 cl3449ea95 eco i1: +11.67 (bc) vs TT -239.72 vs FF +11.67
    r = E.check(mk(tmp_path, "bc", 11.6706, 11.67, -239.72))
    assert r["verdict"] == "MATCH" and r["corner"] == "ff" and r["signoff_other"] == {"tt": -239.72}


def test_real_same_corner_gap_is_flagged(tmp_path):
    assert E.check(mk(tmp_path, "tc", -100.9, 11.67, -239.72))["verdict"] == "MISMATCH"


def test_tt_gain_uses_signoff_tt(tmp_path):
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    a.write_text(json.dumps({"corners": {"tt": {"sdc_wns_max": -239.72}}})); b.write_text(json.dumps({"corners": {"tt": {"sdc_wns_max": -210.19}}}))
    assert E.tt_gain(a, b) == 12.3
    assert E.report_corner("read_liberty -corner tc a") == "tt"
