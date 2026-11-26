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
    d = dict(plateau3=2000, plateau3_kind="flat", age_h=5.0, type="slw_fe_v1", unit="oth-u-9", host="epyc9", kit="/srv/x/kit-wave/qwen_compute/E/items/slw_fe_v1/gen/slw_fe_v1", lane="", smell=[], grt_odb="/k/5_1_grt.odb")
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


# ---------------------------------------------------------------- rule v2 (QC-DRT-ECO 11-25 19:50, COORD adopted)
def test_v2_window_classes_low_trending_dead_and_hang():
    flat1 = [500] + [1] * 30
    assert nw.plateau_v2(flat1, 480, 0.1, 4)[0] == "LOW"                      # 1 violation, 8 min/iter: needs 3 h = 23 iterations, has 30
    assert nw.plateau_v2([500] + [1] * 15, 480, 0.1, 4) is None               # 15 iterations < 22.5 needed: no verdict yet
    trend = [300, 251] + [251 - i * 3 for i in range(1, 14)]
    assert nw.plateau_v2(trend, 1000, 0.1, 4)[0] == "TRENDING"                 # cldb4efe33: 251 > 208 = 17 %
    assert nw.plateau_v2([9000] + [800] * 25, 600, 0.1, 4)[0] == "DEAD"       # flat over 50
    h = nw.plateau_v2([9000, 4, 4, 4], 300, 7.4, 4.0)                          # R9: <= 20 violations and silent = long stubborn iteration, LOW not DEAD
    assert h[0] == "LOW" and "R9" in h[2]
    h = nw.plateau_v2([9000, 800, 800, 800], 300, 7.4, 4.0)                    # above 20: silent while openroad burns CPU is still DEAD
    assert h[0] == "DEAD" and "no trend" in h[2]
    assert nw.plateau_v2([9000, 21, 21, 21], 300, 7.4, 4.0)[0] == "DEAD"        # boundary: 20 is LOW, 21 is not
    assert nw.plateau_v2([9000, 4, 4, 4], 300, 7.4, 0.01) is None             # silent and idle is the old hung rule, not this one


def test_v2_experiment_containers_are_exempt():
    assert nw.is_experiment("qcdrt-fw-A", "/x/stage.log")
    assert nw.is_experiment("oth-ubuntu-1", "/w/exp.log")
    assert not nw.is_experiment("oth-ubuntu-1", "/w/5_2_route.tmp.log")
    assert nw.plateau_exempt(dict(container="qcdrt-fw-B", log="/w/x.log")) == "experiment"


def test_v2_report_only_first_pass_then_twin_and_already_gone(tmp_path, monkeypatch):
    coord(tmp_path, monkeypatch)
    (tmp_path / "autopilot").mkdir(exist_ok=True)
    (tmp_path / "autopilot/PLATEAU-CLASS-OWNERS.tsv").write_text("QC\tslw_fe_v1\tQC-FEV1-CL08\n")
    sweep_file(tmp_path, [("QC", "slw_fe_v1", "no", at(NOW, 900), "QC-GONE")])
    assert nw.class_owner("QC", "slw_fe_v1__cl9", str(tmp_path)) == "QC-FEV1-CL08"
    dead = dict(plateau3=800, plateau3_kind="dead", plateau_v2=["DEAD", 800, "800 violations flat"], age_h=9.0, grt_odb="/k/5_1_grt.odb")
    a = prow(unit="oth-u-1", host="epyc8", **dead)
    b = prow(unit="oth-u-2", host="intel1", **dict(dead, plateau3=956, plateau_v2=["DEAD", 956, "956 flat"]))
    calls = []
    out = nw.plateau_act_pass([a, b], {}, NOW, post=False, cancel=lambda u: calls.append(u) or (0, "ok"), sweep=nw.owners_sweep(str(tmp_path)))
    assert calls == []                                                         # no PLATEAU-V2.live: report-only
    assert all("report-only first pass" in o["action"] for o in out)
    assert {o["owner"] for o in out} == {"QC-FEV1-CL08"}                       # R6 class owner
    (tmp_path / "lanes/PLATEAU-V2.live").write_text("")
    out = nw.plateau_act_pass([a, b], {}, NOW + 5, post=False, cancel=lambda u: calls.append(u) or (1, "ot-run --cancel: nothing found for 'x' on any fleet host"), sweep=nw.owners_sweep(str(tmp_path)))
    assert {o["class"] for o in out} == {"ALREADY-GONE"}                       # R8: a gone unit is not a cancel
    assert len(calls) == 2


def test_v2_last_copy_without_5_1_grt_is_not_cancelled(tmp_path, monkeypatch):
    coord(tmp_path, monkeypatch)
    (tmp_path / "lanes/PLATEAU-V2.live").write_text("")
    sweep_file(tmp_path, [("QC", "slw_fe_v1", "no", at(NOW, 900), "QC-GONE")])
    r = prow(plateau3=800, plateau3_kind="dead", plateau_v2=["DEAD", 800, "800 flat"], age_h=9.0, grt_odb="")
    calls = []
    out = nw.plateau_act_pass([r], {}, NOW, post=False, cancel=lambda u: calls.append(u) or (0, "ok"), sweep=nw.owners_sweep(str(tmp_path)))
    assert calls == [] and "5_1_grt.odb" in out[0]["action"]


def test_r9_low_notice_carries_report_only_eco_handoff():
    r = prow(plateau3=9, plateau3_kind="low", plateau_v2=["LOW", 9, "9 violations flat"], age_h=48.6, type="slw_fe_v1", kit="/k/gen/slw_fe_v1__cl", host="epyc8")
    cls, txt = nw.plateau_act_class(r)
    assert cls == "REPAIR-NOTICE" and "ECO-HANDOFF (report-only" in txt and "/k/gen/slw_fe_v1__cl epyc8" in txt and "P-ECO-NO-GAIN" in txt
    r2 = prow(plateau3=40, plateau3_kind="low", plateau_v2=["LOW", 40, "40 violations flat"], age_h=9.0)
    assert "ECO-HANDOFF" not in nw.plateau_act_class(r2)[1]


class _R:
    def __init__(self, rc=0, out="ARMED\n"): self.returncode, self.stdout = rc, out


def test_eco_handoff_launch_gates(tmp_path, monkeypatch):
    coord(tmp_path, monkeypatch)
    r = prow(plateau3=9, plateau3_kind="low", plateau_v2=["LOW", 9, "9 flat"], host="epyc8", kit="/srv/x/gen/slw_fe_v1__cl")
    calls = []
    run = lambda h, c, inp=None, timeout=0: calls.append((h, c, inp)) or _R()
    st = {}
    assert nw.eco_handoff(r, st, 1.0, run)[0] is False and calls == []                 # no enable file: report-only
    (tmp_path / "lanes/ECO-HANDOFF.live").write_text("1\n")
    assert nw.eco_handoff(dict(r, host="intel2"), st, 1.0, run)[0] is False and calls == []   # not a kit host
    assert nw.eco_handoff(dict(r, host="epyc9"), st, 1.0, run)[0] is False and calls == []
    ok, why = nw.eco_handoff(r, st, 1.0, run)
    assert ok and len(calls) == 1 and calls[0][0] == "epyc8" and "mkdir" in open(nw.ECO_WAITER_SRC).read() and calls[0][2].startswith("#!/bin/bash")
    assert "grep -F -- /srv/x/gen/slw_fe_v1__cl" in calls[0][1]
    assert nw.eco_handoff(r, st, 2.0, run)[0] is False and len(calls) == 1             # one waiter per kit
    st2 = {}
    ok, why = nw.eco_handoff(r, st2, 3.0, lambda h, c, inp=None, timeout=0: _R(0, "EXISTS\n"))
    assert ok and "not duplicated" in why                                               # a waiter already on the kit host
    assert nw.eco_handoff(dict(r, kit="/srv/x; rm -rf /"), {}, 1.0, run)[0] is False   # path is shell-checked


def test_eco_handoff_pass_arms_once_and_stays_report_only_without_file(tmp_path, monkeypatch):
    coord(tmp_path, monkeypatch)
    sweep_file(tmp_path, [("QC", "slw_fe_v1", "yes", at(NOW, 5), "QC-DRT-TAIL")])
    r = prow(plateau3=9, plateau3_kind="low", plateau_v2=["LOW", 9, "9 flat"], host="epyc8", kit="/srv/x/gen/slw_fe_v1__cl")
    calls = []
    monkeypatch.setattr(nw, "run_host", lambda h, c, inp=None, timeout=0: calls.append(h) or _R())
    seen = {}
    nw.plateau_act_pass([r], seen, NOW)
    assert calls == []
    (tmp_path / "lanes/ECO-HANDOFF.live").write_text("1\n")
    out = nw.plateau_act_pass([r], {}, NOW)
    assert calls == ["epyc8"] and any("ECO-HANDOFF armed" in o["action"] for o in out)
