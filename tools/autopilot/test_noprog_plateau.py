"""STAGE-PLATEAU 11-25 (COORD, FABLE flow review 02:4x): DRT-PLATEAU and HOLD-STALL.  Cases are the real dry-run series of 11-25 (24 h of kit logs on all hosts)."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import noprog_watchdog as nw
from test_noprog_design_fail import coord, posted, NOW


def test_drt_flat_hd_serdes_fires_but_a_slow_converger_does_not():
    hd = [84487, 11326, 7501, 2181, 1984, 1917, 1864, 1846, 1817, 1803]
    assert nw.drt_plateau_evidence(hd[:8]) == ""                                    # it 7: 1984 -> 1846 = 7 %
    assert nw.drt_plateau_evidence(hd).startswith("DRT-PLATEAU flat: 1803")         # it 9: 1917 -> 1803 = 5.9 %?  see below
    sc3 = [233440, 40033, 28081, 2682, 1789, 1718, 1664, 1597, 1463, 1247, 894]      # sle_sc_v3 11-25: fell 4 %/iter, then reached 0 (route done)
    assert all(nw.drt_plateau_evidence(sc3[:n]) == "" for n in range(1, len(sc3) + 1))


def test_drt_rules_only_after_iteration_6_and_over_1k():
    assert nw.drt_plateau_evidence([9000, 8900, 8800, 8750, 8700, 8650, 8600]) == ""        # iteration 6: not yet
    assert nw.drt_plateau_evidence([9000, 8900, 8800, 8750, 8700, 8650, 8600, 8590]).startswith("DRT-PLATEAU flat")
    assert nw.drt_plateau_evidence([900, 890, 880, 870, 860, 850, 840, 835, 834]) == ""    # under 1k: left to run
    assert nw.drt_plateau_evidence([99999, 50000, 20000, 15000, 12000, 11000, 10500]) == ""


def test_drt_high_count_needs_a_stall_not_a_steady_fall():
    stuck = [400194, 123176, 102681, 59441, 55677, 54030, 53466, 53197]               # slw_sc_v2: stuck at 53k
    assert nw.drt_plateau_evidence(stuck).startswith("DRT-PLATEAU high: 53197")
    falling = [522000, 123388, 88579, 27606, 21818, 19783, 18538, 17467, 16679, 15606, 11997]   # sle_sc_v1 on epyc2: > 10k but falling 64 % later
    assert all(nw.drt_plateau_evidence(falling[:n]) == "" for n in range(1, len(falling) + 1))


def test_drt_rise_is_3x_the_best_on_two_totals_and_a_spike_that_recovers_is_spared():
    spike = [9091, 7726, 31531, 11676, 8463, 6858, 5806, 5300]                         # col_h9_r1: 31531 then recovered below the best
    assert all(nw.drt_plateau_evidence(spike[:n]) == "" for n in range(1, len(spike) + 1))
    held = [5099, 4070, 3524, 3168, 2937, 2818, 2761, 13398, 13300]                    # sle_sc_v1: still 4.8x the best on the next total
    assert nw.drt_plateau_evidence(held[:8]) == "" and nw.drt_plateau_evidence(held).startswith("DRT-PLATEAU rise")
    assert nw.drt_plateau_evidence([100, 0]) == "" and nw.drt_plateau_evidence([]) == ""


def test_hold_stall_never_stops_a_converged_or_single_row_tns():
    res = lambda ser: {"name": "repair_TNS", "series": ser}
    big = res([(1, 169360.0)])                                                         # kv3_pv_v3: one row, a 10,099 s pass in flight (then 3,862 and 0)
    assert nw.hold_stall_evidence("pregrt_ff_hold.log", big, "NO-PROGRESS", "flat") == ""
    assert nw.hold_stall_evidence("pregrt_ff_hold.log", res([(1, 5.0), (2, 3.0), (3, 0.0)]), "NO-PROGRESS", "x") == ""   # TNS 0: converged (11-23 incident)
    assert nw.hold_stall_evidence("pregrt_ff_hold.log", res([(1, 515.0), (2, 511.0), (3, 515.0)]), "PROGRESS", "x") == ""
    assert nw.hold_stall_evidence("5_1_grt.log", res([(1, 515.0), (2, 511.0), (3, 515.0)]), "NO-PROGRESS", "x") == ""
    ev = nw.hold_stall_evidence("pregrt_ff_hold.log", res([(1, 515.0), (2, 511.0), (3, 515.0)]), "NO-PROGRESS", "repair_TNS best 511 vs 515", "d")
    assert ev.startswith("HOLD-STALL pregrt_ff_hold")


def test_hold_stall_needs_a_row_older_than_the_window():
    res = {"name": "repair_TNS", "series": [(1, 515.0), (2, 511.0), (3, 515.0)]}
    anchors = [(0.0, 0), (10000.0, 10)]
    assert nw.hold_stall_evidence("pregrt_ff_hold.log", res, "NO-PROGRESS", "x", "", anchors, 10000.0, 7200.0)           # rows at 1k..3k s, window start 2.8k
    assert nw.hold_stall_evidence("pregrt_ff_hold.log", res, "NO-PROGRESS", "x", "", anchors, 4000.0, 7200.0) == ""      # all rows inside the window


def test_hold_judge_end_to_end_flat_table():
    rows = "\n".join(f"{i * 10:9d} | 0 | 5 | 0 | +0.0% | -10.0 | -{515 + (i % 2)}.0 | x" for i in range(1, 8))
    text = "Iteration | Resized | Buffers | Cloned Gates | Area | WNS | TNS | Endpoint\n-----\n" + rows + "\n"
    res = nw.extract("other", text)
    assert res["name"] == "repair_TNS" and len(res["series"]) == 7
    anchors = [(0.0, 0), (4 * 3600.0, res["n"])]
    v, why, det = nw.judge(res, anchors, 4 * 3600.0, window=2 * 3600, exact=True, zero_needs_growth=True)
    assert v == "NO-PROGRESS"
    assert nw.hold_stall_evidence("pregrt_ff_hold.log", res, v, why, det, anchors, 4 * 3600.0, 2 * 3600.0).startswith("HOLD-STALL")


def test_drc_region_summary():
    rpt = ("violation type: Short\n\tsrcs: a b\n\tbbox = (1229.5, 18.4) - (1229.6, 18.5) on Layer M2\n"
           "violation type: Short\n\tsrcs: a b\n\tbbox = (1230.3, 18.5) - (1230.4, 18.6) on Layer M2\n"
           "violation type: Lef58EolKeepOut\n\tsrcs: c\n\tbbox = (10.0, 10.0) - (10.1, 10.1) on Layer M3\n")
    s = nw.drc_region_summary(rpt)
    assert "DRC 3 marks" in s and "Short 2" in s and "M2 2" in s and "(1200..1250,0..50) um 2" in s
    assert nw.drc_region_summary("nothing") == ""


def prow(**k):
    r = {"unit": "oth-ubuntu-9-1", "host": "renewed-glider", "container": "dpkit-hd_serdes-1", "key": "c|k", "verdict": "PROGRESS", "why": "x", "type": "hd_serdes",
         "kit": "/srv/x/private/HEAD-WEST/hd_serdes_1124070219/gen/hd_serdes", "work": "/srv/x/private/HEAD-WEST/hd_serdes_1124070219/gen/hd_serdes", "gb": 30.0, "age_h": 9.0,
         "lane": "HEAD-WEST", "ident": "dpkit-hd_serdes-1 /srv/x/private/HEAD-WEST/hd_serdes_1124070219/gen/hd_serdes /x/pregrt_ff_hold.log", "prio": "", "kind": "drt",
         "stage": "5_2_route", "plateau": "DRT-PLATEAU flat: 1803 violations at iteration 9", "plateau_class": nw.DRT_PLATEAU, "drc_summary": "5_route_drc.rpt-30.rpt: DRC 1538 marks; types: Short 952"}
    r.update(k)
    return r


def test_plateau_cancel_goes_through_design_fail_pass_with_class_and_drc_summary(tmp_path, monkeypatch):
    coord(tmp_path, monkeypatch)
    monkeypatch.delenv("NOPROG_PLATEAU_MODE", raising=False)
    calls, seen = [], {}
    done = nw.design_fail_pass([prow()], seen, NOW, cancel=lambda u: (calls.append(u), (0, "containers stopped"))[1])
    assert calls == ["oth-ubuntu-9-1"] and done[0]["class"] == "DRT-PLATEAU" and "--reason design" in done[0]["cancel_method"]
    tsv = (tmp_path / "lanes/CANCEL-DESIGN-FAIL.tsv").read_text().splitlines()
    assert len(tsv) == 2 and "DRT-PLATEAU" in tsv[1] and "DRC 1538 marks" in tsv[1]
    assert "[DRT-PLATEAU]" in posted(tmp_path)[-1] and "-> HEAD-WEST" in posted(tmp_path)[-1]
    assert "CANCEL-DESIGN: DRT-PLATEAU" in (tmp_path / "autopilot/cancel_marks.tsv").read_text()
    nw.design_fail_pass([prow()], seen, NOW + 900, cancel=lambda u: (calls.append(u), (0, "ok"))[1])
    assert calls == ["oth-ubuntu-9-1"]


def test_hold_stall_class_and_its_log_name_is_not_a_hold_only_exemption(tmp_path, monkeypatch):
    coord(tmp_path, monkeypatch)
    calls = []
    r = prow(kind="other", stage="pregrt_ff_hold", plateau="HOLD-STALL pregrt_ff_hold: x", plateau_class=nw.HOLD_STALL, drc_summary="")
    assert "hold-only" in nw.design_fail_exempt(r)            # the log path in `ident` matches HOLD_ONLY_RE ...
    assert nw.plateau_exempt(r) == ""                          # ... which the plateau rules do not read
    done = nw.design_fail_pass([r], {}, NOW, cancel=lambda u: (calls.append(u), (0, "ok"))[1])
    assert calls == ["oth-ubuntu-9-1"] and done[0]["class"] == "HOLD-STALL"


def test_plateau_never_touches_young_exempt_keep_or_switched_off(tmp_path, monkeypatch):
    coord(tmp_path, monkeypatch)
    calls = []
    c = lambda u: (calls.append(u), (0, "ok"))[1]
    rows = [prow(unit="u1", age_h=2.5), prow(unit="u2", kit="/srv/a/x/eco/i1", work="/srv/a/x/eco/i1"), prow(unit="u3", prio="proof"), prow(unit="u4", verdict="KEEP"),
            prow(unit="u5", kit="/srv/a/holdfix/t1", work="/srv/a/holdfix/t1"), prow(unit="u6", plateau="")]
    assert nw.design_fail_pass(rows, {}, NOW, cancel=c) == [] and calls == []
    (tmp_path / "lanes/PLATEAU-WATCHDOG.off").write_text("off\n")
    assert nw.design_fail_pass([prow()], {}, NOW, cancel=c) == [] and calls == []
    (tmp_path / "lanes/PLATEAU-WATCHDOG.off").unlink()
    (tmp_path / "lanes/posts/L.md").write_text("- 2026-11-25 01:00 PST KEEP oth-ubuntu-9-1 probe\n")
    assert nw.design_fail_pass([prow()], {}, NOW, cancel=c) == [] and calls == []


def test_drt_plateau_is_sticky_the_sle_fw_v2_jump_does_not_clear_it():
    fw = [186583, 63684, 52270, 29786, 27162, 25898, 25079, 24397, 23959, 22940, 21399, 19250, 18158, 16673, 15812, 15279, 14980, 63558]
    assert nw.drt_plateau_evidence(fw).startswith("DRT-PLATEAU high: 23959")           # first match at iteration 8, kept after the jump
    assert nw.drt_plateau_at(fw) == ""                                                  # the per-prefix rule alone is guarded off by the spike
    assert nw.drt_plateau_evidence([9091, 7726, 31531, 11676, 8463]) == ""


def test_lec_is_never_no_progress():
    assert nw.lec_exempt("lec", "NO-PROGRESS", "no new LEC file/log write for 7.0 h")[0] == "PROGRESS"
    assert nw.lec_exempt("lec", "PROGRESS", "x") == ("PROGRESS", "x")
    assert nw.lec_exempt("yosys", "NO-PROGRESS", "x") == ("NO-PROGRESS", "x")


# ---------------------------------------------------------------- FLOW-0730 F6: PLATEAU label + routing (report-only)
def test_plateau5_needs_five_flat_iterations():
    flat = [9000, 5000, 3000, 1500, 1490, 1480, 1475, 1470, 1466]
    assert nw.drt_plateau5(flat) == 1466
    assert nw.drt_plateau5([9000, 5000, 3000, 1500, 1490, 1480, 1475, 1470, 1300]) is None        # last step -11 %
    assert nw.drt_plateau5([100, 100, 100, 100, 100]) is None                                      # fewer than 6 totals
    assert nw.drt_plateau5([100, 100, 100, 101, 100, 99]) == 99


def test_plateau_routes_by_violation_count():
    assert nw.plateau_route({"plateau5": 60})[0] == "REPAIR"
    assert nw.plateau_route({"plateau5": 500})[0] == "MID"
    assert nw.plateau_route({"plateau5": 1466, "age_h": 2.0})[0] == "SMELL"
    assert nw.plateau_route({"plateau5": 1466, "age_h": 5.0})[0] == "RECOMMEND-CANCEL"
    assert nw.plateau_route({}) is None


def test_plateau_pass_posts_once_report_only(tmp_path, monkeypatch):
    coord(tmp_path, monkeypatch)
    from test_noprog_smell import srow
    rows = [srow(plateau5=60, unit="u1", kit="/srv/x/private/QC-ALLFIX/a/gen/a", work="/srv/x/private/QC-ALLFIX/a/gen/a"), srow(plateau5=2000, age_h=9.0, unit="u2")]
    seen = {}
    out = nw.plateau_route_pass(rows, seen, NOW)
    assert sorted(c for _, c, _ in out) == ["RECOMMEND-CANCEL", "REPAIR"]
    p = posted(tmp_path)
    assert any("PLATEAU-REPAIR [SMELL-WATCH -> QC-ALLFIX, QC-DRT-TAIL;" in x for x in p) and any("PLATEAU-RECOMMEND-CANCEL" in x and "FP-CONVERGE-QC" in x and "cancel recommended" in x for x in p)
    assert nw.plateau_route_pass(rows, seen, NOW + 900) == []
    assert not (tmp_path / "autopilot/cancel_marks.tsv").exists()
