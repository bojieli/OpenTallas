"""PLATEAU-ACT 11-25 (COORD FLOW-0930 F-10): the plateau measure (< 5 % fall over 3 DRT iterations, or rising) and the pass that acts on it: a hand-to-repair notice under 100 marks, CANCEL-ELIGIBLE rows
over 1000 marks and 3 h, an ot-run --cancel only when the owner is dead or silent > 1 h, never a TT-passing / KEEP kit.  Notices go to the OWNERS-SWEEP fresh_owner, else the die ALLFIX lane."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
import noprog_watchdog as nw
import noprog_stage as ns
from test_noprog_design_fail import coord, posted, NOW
from test_noprog_smell import srow

HDR = ("die\ttype\tkind\tstate\tage_h\towning_lane\tmatch\towner_alive\tlane_last_post\tagent_id\tkit_last_action\tkit_last_time\tlane_last_mention\tflags\t_probe\tfresh_owner\towner_lane_states\tsweep_flags")


def sweep_file(tmp_path, rows):
    lines = ["# OWNERS-SWEEP test", HDR]
    for die, typ, alive, last, fresh in rows:
        lines.append("\t".join([die, typ, "type", "x", "1", "L", "type", alive, last, "", "", "", "", "", "", fresh, "", ""]))
    (tmp_path / "lanes/OWNERS-SWEEP.tsv").write_text("\n".join(lines) + "\n")


def at(now, minutes_ago):
    """OWNERS-SWEEP lane_last_post text for `minutes_ago` before now (PST)"""
    from zoneinfo import ZoneInfo
    import datetime as dt
    return dt.datetime.fromtimestamp(now - minutes_ago * 60, ZoneInfo("America/Los_Angeles")).strftime("%m-%d %H:%M")


def test_plateau3_flat_rising_falling():
    assert nw.drt_plateau3([9000, 3000, 1500, 1480, 1470, 1460]) == (1460, "flat")        # 1500 -> 1460 = 2.7 % over 3 iterations
    assert nw.drt_plateau3([9000, 3000, 1500, 1600, 1700, 1800]) == (1800, "rising")
    assert nw.drt_plateau3([9000, 3000, 1500, 1200, 900, 700]) is None                     # falling 50 %
    assert nw.drt_plateau3([9000, 4900, 4850, 4800, 4750]) == (4750, "flat")
    assert nw.drt_plateau3([100, 100, 100]) is None                                         # fewer than 4 totals
    assert nw.drt_plateau3([100, 80, 60, 0]) is None                                        # reached 0


def test_owner_routing_fresh_owner_else_allfix(tmp_path, monkeypatch):
    coord(tmp_path, monkeypatch)
    sweep_file(tmp_path, [("QC", "slw_fe_v1", "yes", at(NOW, 5), "QC-DRT-TAIL+QC-ALLFIX"), ("QC", "slw_hc1", "no", at(NOW, 400), "QC-OLD-LANE"), ("KV", "kv3_hg", "yes", at(NOW, 3), "KV-ALLFIX")])
    sw = nw.owners_sweep(str(tmp_path))
    assert nw.route_owner("QC", "slw_fe_v1", sw) == ("QC-DRT-TAIL", "alive")
    assert nw.route_owner("QC", "slw_fe_v1__cl08d14f0d", sw) == ("QC-DRT-TAIL", "alive")        # family suffix
    assert nw.route_owner("QC", "slw_hc1", sw) == ("QC-ALLFIX", "dead")                          # owner not alive: the die ALLFIX lane
    assert nw.route_owner("S81", "unknown_type", sw, "COORD") == ("S81-ALLFIX-INT", "unknown")
    assert nw.route_owner("HEAD", "x", {}) == ("HEAD-ALLFIX", "unknown")
    assert abs(nw.owner_silent_s(sw, "QC", "slw_fe_v1", NOW) - 300) < 61


def prow(**k):
    d = dict(plateau3=2000, plateau3_kind="flat", age_h=5.0, type="slw_fe_v1", unit="oth-u-9", host="epyc9", kit="/srv/x/kit-wave/qwen_compute/E/items/slw_fe_v1/gen/slw_fe_v1", lane="", smell=[])
    d.update(k)
    return srow(**d)


def test_under_100_marks_sends_a_hand_to_repair_notice_to_the_owner_never_cancels(tmp_path, monkeypatch):
    coord(tmp_path, monkeypatch)
    sweep_file(tmp_path, [("QC", "slw_fe_v1", "yes", at(NOW, 5), "QC-DRT-TAIL")])
    calls = []
    out = nw.plateau_act_pass([prow(plateau3=60, plateau3_kind="rising")], {}, NOW, cancel=lambda u: calls.append(u) or (0, "x"))
    assert [o["class"] for o in out] == ["REPAIR-NOTICE"] and calls == []
    assert any("PLATEAU-ACT -> QC-DRT-TAIL" in x and "hand to DRC repair / ECO-route" in x for x in posted(tmp_path))
    tsv = (tmp_path / "lanes/PLATEAU-ACT.tsv").read_text().splitlines()
    assert tsv[0].split("\t")[:3] == ["t", "class", "die"] and "REPAIR-NOTICE" in tsv[1] and "QC-DRT-TAIL" in tsv[1]


def test_over_1000_marks_waits_for_a_silent_or_dead_owner_then_cancels_by_exact_unit(tmp_path, monkeypatch):
    coord(tmp_path, monkeypatch)
    sweep_file(tmp_path, [("QC", "slw_fe_v1", "yes", at(NOW, 10), "QC-DRT-TAIL")])
    calls, seen = [], {}
    cancel = lambda u: calls.append(u) or (0, "containers stopped")
    out = nw.plateau_act_pass([prow()], seen, NOW, cancel=cancel)
    assert [o["class"] for o in out] == ["CANCEL-ELIGIBLE"] and calls == [] and "notice only" in out[0]["action"]
    assert nw.plateau_act_pass([prow()], seen, NOW + 900, cancel=cancel) == []                       # one row per kit and class
    sweep_file(tmp_path, [("QC", "slw_fe_v1", "yes", at(NOW + 7200, 90), "QC-DRT-TAIL")])           # the owner has been silent 90 min
    out = nw.plateau_act_pass([prow()], seen, NOW + 7200, cancel=cancel)
    assert calls == ["oth-u-9"] and out[0]["class"] == "CANCELLED" and "ot-run --cancel oth-u-9" in out[0]["action"]
    assert "CANCEL-PLATEAU" in (tmp_path / "autopilot/cancel_marks.tsv").read_text()
    assert nw.plateau_act_pass([prow()], seen, NOW + 7300, cancel=cancel) == [] and calls == ["oth-u-9"]   # never twice


def test_dead_owner_cancels_at_once_and_the_notice_goes_to_the_allfix_lane(tmp_path, monkeypatch):
    coord(tmp_path, monkeypatch)
    sweep_file(tmp_path, [("QC", "slw_fe_v1", "no", at(NOW, 1), "QC-GONE")])
    calls = []
    out = nw.plateau_act_pass([prow()], {}, NOW, cancel=lambda u: calls.append(u) or (0, "ok"))
    assert calls == ["oth-u-9"] and out[0]["owner"] == "QC-ALLFIX"
    assert any("PLATEAU-ACT -> QC-ALLFIX" in x for x in posted(tmp_path))


def test_never_cancels_tt_passing_keep_young_or_switched_off(tmp_path, monkeypatch):
    coord(tmp_path, monkeypatch)
    sweep_file(tmp_path, [("QC", "slw_fe_v1", "no", at(NOW, 1), "QC-GONE")])
    calls = []
    cancel = lambda u: calls.append(u) or (0, "ok")
    out = nw.plateau_act_pass([prow(setup_ps=-12.0)], {}, NOW, cancel=cancel)                       # TT setup passes the -42 ps gate: converged
    assert [o["class"] for o in out] == ["SPARED-TNS0"] and calls == []
    assert nw.plateau_act_pass([prow(age_h=2.0, unit="u2")], {}, NOW, cancel=cancel) == []         # under 3 h
    assert nw.plateau_act_pass([prow(verdict="KEEP", unit="u3")], {}, NOW, cancel=cancel) == []
    assert nw.plateau_act_pass([prow(plateau3=500, unit="u4")], {}, NOW, cancel=cancel) == []      # 100..1000: no action
    monkeypatch.setenv("NOPROG_PLATEAU_ACT", "report")
    out = nw.plateau_act_pass([prow(unit="u5")], {}, NOW, cancel=cancel)
    assert out[0]["class"] == "CANCEL-ELIGIBLE" and calls == []


def test_stage_class_plateau_for_a_flat_drt_kit_and_progressing_when_the_iteration_in_flight_beats_it():
    flat = "\n".join(f"[INFO DRT-0199] Number of violations = {v}" for v in [9000, 3000, 1500, 1480, 1470, 1460])
    cls, ev = _route(flat)
    assert cls == "PLATEAU" and "1460" in ev
    falling = "\n".join(f"[INFO DRT-0199] Number of violations = {v}" for v in [9000, 3000, 1500, 1200, 900, 700])
    assert _route(falling)[0] != "PLATEAU"
    beating = flat + "\n[INFO DRT-0199] Start iteration 6\nCompleting 10% with 900 violations\nCompleting 30% with 800 violations"
    assert _route(beating)[0] != "PLATEAU"


def _route(text):
    from test_noprog_stage import run
    return run("route", text, 10.0)


def test_one_routing_path_owner_of_uses_fresh_owner_then_own_lane_then_allfix(tmp_path, monkeypatch):
    coord(tmp_path, monkeypatch)
    sweep_file(tmp_path, [("QC", "slw_fe_v1", "yes", at(NOW, 5), "QC-DRT-TAIL"), ("QC", "slw_hc1", "no", at(NOW, 900), "QC-OLD")])
    (tmp_path / "lanes/LANE-STATUS.tsv").write_text("QC-GONE\tstood-down\tnone\t11-21\tx\n")
    kit = "/srv/x/kit-wave/qwen_compute/E/items/slw_fe_v1/gen/slw_fe_v1"
    assert nw.owner_of([prow()]) == "QC-DRT-TAIL"                                              # live fresh_owner wins over the job's own lane
    assert nw.owner_of([prow(type="slw_hc1", lane="QC-LIVE")]) == "QC-LIVE"                    # owner dead: the job's own lane when it is not stood down
    assert nw.owner_of([prow(type="slw_hc1", lane="QC-GONE")]) == "QC-ALLFIX"                  # ... stood down: the die ALLFIX lane
    assert nw.owner_of([prow(type="slw_hc1", lane="")]) == "QC-ALLFIX"
    assert nw.smell_recipients("QC", "QC-ALLFIX") == "FP-CONVERGE-QC, QC-ALLFIX"
