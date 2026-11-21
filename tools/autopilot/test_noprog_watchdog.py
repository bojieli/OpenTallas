"""tests for noprog_watchdog.py: metric parsing per stage, the 6 h / 2 % verdict, policy (plan / HBM / keep), cancel decision."""
import os, sys, tempfile
sys.path.insert(0, os.path.dirname(__file__))
import noprog_watchdog as nw

H = 3600
NOW = 1_000_000_000.0


def anchors_for(n, age_h, last_write_h=0.0):
    """stage started age_h ago, last log write last_write_h ago, n lines"""
    return [(NOW - age_h * H, 0), (NOW - last_write_h * H, n)]


def gpl_text(overflows):
    return "\n".join(f"{i * 10:8d} |{o:9.4f} |  1.2e+08 |   -0.5% |  2.1e-06 |" for i, o in enumerate(overflows))


# ---------------------------------------------------------------- parsing
def test_gpl_series():
    res = nw.extract("gpl", "[NesterovSolve] Iter\n" + gpl_text([0.9, 0.5, 0.31]))
    assert res["name"] == "overflow" and [v for _, v in res["series"]] == [0.9, 0.5, 0.31]
    assert nw.stage_kind("run/logs/asap7/dp_x/base/3_3_place_gp.tmp.log") == "gpl"


def test_drt_series_uses_iteration_totals_not_percent_lines():
    t = ("[INFO DRT-0195] Start 1st optimization iteration.\n    Completing 10% with 500 violations.\n    elapsed time = 00:00:00\n"
         "[INFO DRT-0199]   Number of violations = 120.\n[INFO DRT-0195] Start 2nd optimization iteration.\n    Completing 10% with 120 violations.\n"
         "[INFO DRT-0199]   Number of violations = 90.\n[INFO DRT-0195] Start 3rd optimization iteration.\n    Completing 10% with 90 violations.\n")
    res = nw.extract("drt", t)
    assert [v for _, v in res["series"]] == [120, 90]
    assert res["growth_idx"] == len(t.splitlines()) - 1


GRT_REPAIR = """Iteration |   Area    | Resized | Buffers | Nets repaired | Remaining
---------------------------------------------------------------------
        0 |     +0.0% |       0 |       0 |             0 |     90000
     1000 |     +0.1% |       0 |    5000 |          3000 |     80000
[WARNING RSZ-0104] Net a only has one pin. Check if it is intended to be dangling.
     2000 |     +0.1% |       0 |    9000 |          6000 |     70000
"""


def test_repair_table_remaining_and_final_closes_it():
    res = nw.extract("grt", GRT_REPAIR)
    assert res["name"] == "repair_Remaining" and [v for _, v in res["series"]] == [90000, 80000, 70000]
    done = nw.extract("grt", GRT_REPAIR + "    final |     +0.7% |       0 |   9437 |          6898 |         0\n[INFO RSZ-0034] Found 3 slew violations.\n")
    assert done["series"] == []          # a finished table is not the metric any more


def test_repair_timing_table_uses_viol_column_and_hold_table_uses_abs_tns():
    t = ("   Iter   | Removed | Resized | Inserted | Cloned |  Pin  |   Area   |    WNS   |   StTNS    |   EnTNS    |  Viol  |  Worst  \n"
         "---\n        0 |       0 |       0 |        0 |      0 |     0 |    +0.0% |  -30.000 |     -100.0 |    -500.0 |   3600 | u/x\n"
         "      100 |      10 |      20 |        5 |      0 |     0 |    -0.0% |  -29.000 |     -90.0 |    -400.0 |   3000 | u/x\n")
    res = nw.extract("grt", t)
    assert res["name"] == "repair_Viol" and [v for _, v in res["series"]] == [3600, 3000]
    hold = ("Iteration | Resized | Buffers | Cloned Gates |   Area   |   WNS   |   TNS   | Endpoint\n---\n"
            "        0 |       0 |       0 |            0 |    +0.0% | -110.793 | -148030.188 | u/D\n")
    assert nw.extract("other", hold)["series"][0][1] == 148030.188


def test_grt_extra_iteration_loop_has_no_metric_and_iteration_lines_are_noise():
    t = ("[INFO GRT-0053] Routing resources analysis:\nM2 Horizontal 1 2 3\n\n[INFO GRT-0101] Running extra iterations to remove congestion.\n"
         + "".join(f"[INFO GRT-0102] Start extra iteration {i}/30\n[WARNING GRT-0273] Disabled NDR for net: n{i}\n" for i in range(1, 16)))
    res = nw.extract("grt", t)
    assert res["series"] == []
    assert res["growth_idx"] == 3                  # the GRT-0101 line is the last non-noise line


def test_stage_kind():
    assert nw.stage_kind("x/5_2_route.tmp.log") == "drt"
    assert nw.stage_kind("x/5_1_grt.tmp.log") == "grt"
    assert nw.stage_kind("x/1_2_yosys.log") == "yosys"
    assert nw.stage_kind("x/lec_run.log") == "lec"
    assert nw.stage_kind("x/4_1_cts.tmp.log") == "other"


# ---------------------------------------------------------------- verdict
def series_res(vals, per_row_h):
    """rows evenly spaced per_row_h apart, the last one now"""
    n = len(vals)
    return {"name": "overflow", "series": [(i, v) for i, v in enumerate(vals)], "growth_idx": n - 1, "n": n}, \
           [(NOW - (n - 1) * per_row_h * H, 0), (NOW, n - 1)]


def test_improving_metric_is_progress_forever():
    vals = [1.0 * 0.97 ** i for i in range(400)]          # 3 % better each row, 100 h in total
    res, anc = series_res(vals, 0.25)
    assert nw.judge(res, anc, NOW)[0] == "PROGRESS"


def test_flat_metric_for_window_is_no_progress():
    vals = [1.0 * 0.9 ** i for i in range(20)] + [0.17] * 400      # best 0.15 reached long ago, then flat at 0.17
    res, anc = series_res(vals, 0.25)
    v, why, _ = nw.judge(res, anc, NOW)
    assert v == "NO-PROGRESS", why


def test_improvement_below_two_percent_is_no_progress_and_above_is_progress():
    base = [1.0] * 100
    r1, a1 = series_res(base + [1.0] * 20 + [0.985] * 20, 0.25)      # 1.5 % inside the last 5 h
    assert nw.judge(r1, a1, NOW)[0] == "NO-PROGRESS"
    r2, a2 = series_res(base + [1.0] * 20 + [0.97] * 20, 0.25)
    assert nw.judge(r2, a2, NOW)[0] == "PROGRESS"


def test_young_stage_is_never_judged():
    res, anc = series_res([0.5] * 50, 0.05)              # 2.5 h of evidence
    assert nw.judge(res, anc, NOW)[0] == "YOUNG"


def test_zero_is_done():
    res, anc = series_res([5, 3, 1, 0], 3)
    assert nw.judge(res, anc, NOW)[0] == "PROGRESS"


def test_drt_cycling_back_up_is_no_progress():
    # the 112 h HEAD late fix: best 41 long ago, then restarts at 1851 .. 1002, never below 41 again
    vals = [64618, 10324, 5000, 1000, 114, 41] + [1851, 1520, 1131, 1075, 1596, 886, 552, 1589, 1138] * 4
    res, anc = series_res(vals, 3)
    assert nw.judge(res, anc, NOW)[0] == "NO-PROGRESS"


def test_log_growth_rule_for_a_metricless_stage():
    # S81 leaf GRT extra-iteration loop: 200 meaningful lines early, 195 iteration lines after, 176 h old
    res = {"name": None, "series": [], "growth_idx": 199, "n": 395}
    v, why, _ = nw.judge(res, anchors_for(395, 176, 0.9), NOW)
    assert v == "NO-PROGRESS" and "non-iteration" in why
    res = {"name": None, "series": [], "growth_idx": 394, "n": 395}          # the last line is real news
    assert nw.judge(res, anchors_for(395, 176, 0.1), NOW)[0] == "PROGRESS"
    assert nw.judge(res, anchors_for(395, 2, 0.1), NOW)[0] == "YOUNG"


def test_quiet_table_with_fresh_other_lines_is_progress():
    res = {"name": "repair_Remaining", "series": [(i, 50000.0) for i in range(10)], "growth_idx": 99, "n": 100}
    anc = [(NOW - 20 * H, 0), (NOW - 8 * H, 10), (NOW, 100)]       # rows 8-20 h ago, 90 more lines since then
    assert nw.judge(res, anc, NOW)[0] == "PROGRESS"
    res2 = dict(res, growth_idx=9)
    assert nw.judge(res2, anc, NOW)[0] == "NO-PROGRESS"


def test_judge_activity_for_lec():
    assert nw.judge_activity(NOW - 2 * H, NOW - 30 * H, NOW, "LEC")[0] == "PROGRESS"
    assert nw.judge_activity(NOW - 7 * H, NOW - 30 * H, NOW, "LEC")[0] == "NO-PROGRESS"
    assert nw.judge_activity(NOW - 1 * H, NOW - 3 * H, NOW, "LEC")[0] == "YOUNG"


def test_interp_time_is_piecewise_linear():
    anc = [(0, 0), (100, 10), (200, 110)]
    assert nw.interp_time(5, anc) == 50 and nw.interp_time(60, anc) == 150 and nw.interp_time(500, anc) == 200


# ---------------------------------------------------------------- policy
def test_plan_priority_and_bind_jobs_are_excluded_die_priority_is_not():
    assert nw.is_plan("plan", "x")
    assert not nw.is_plan("die", "dpkit-dsdv_slice_iq_C__t1 run_kit.sh place")
    # WAVE-PREPNR-1115: only a DECLARED priority=plan excludes; a command-line text match no longer does
    assert not nw.is_plan("", "bash bindB4L4_leafplan.sh strict_bind")
    assert not nw.is_plan("", "python3 latcheck.py")
    assert not nw.is_plan("", "--spec-b64 " + "Zg0/" * 40 + " run_kit.sh route")     # a base64 blob containing '/g0/' is not a G0 job


def test_hbm_detection_and_type_names():
    assert nw.is_hbm("hbmcore-ot_hbm_accel_smh_pt_w_ptwc31112_-402259")
    assert nw.is_hbm("/srv/x/hbm-collect-1/ptwc3/kit")
    assert nw.is_hbm("trialhbm-fabric-3957235")
    assert not nw.is_hbm("dpkit-ot_s81sl_leaf__t1-4093762")
    # KIT-OPS-6 11-14: a HEAD core built by the HBM core-kit generator is not HBM (die metadata decides, not the generator name)
    head = ("hbmcore-kit_elemA_1-4093762 /srv/opentallas-scratch2/claude/type-hdcore-elemab/elemA/kit_elemA "
            "/srv/opentallas-scratch2/claude/type-hdcore-elemab/elemA/kit_elemA/run bash run_kit_hbm.sh")
    assert not nw.is_hbm(head)
    # an HBM-die kit is still HBM, with or without the generator name
    assert nw.is_hbm("hbmcore-kit_x-1 /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/hbm/kit-wave/hbm/ev/items/PHY_NE/gen/k run_kit_hbm.sh")
    assert nw.is_hbm("dpkit-PHY_NE-1 /srv/x/claude/kit-ops-1/hbm_pEv11c/kit")
    assert nw.base_type("dpkit-col_h9_r0_p5__t1__pvb22875c0-1143335") == "col_h9_r0_p5__t1"
    assert nw.base_type("dpkit-serdes__t2-3945605-lec") == "serdes__t2"
    assert nw.base_type("dpkit-sle_sc_v1__cl64543eaf__cl5e017c6f-3460358") == "sle_sc_v1"


def test_keep_list():
    keep = ["/srv/x/kitS4/gen/seqhost__t1\tLEC proof, lane TL-SERDES", "other"]
    assert nw.keep_match(keep, "a /srv/x/kitS4/gen/seqhost__t1 b")
    assert not nw.keep_match(keep, "a /srv/y")


def test_an_old_plan_is_never_a_cancel_reason():
    """FLOW-FIX-2045 (OWNER: never cancel old-plan kits for a newer plan; a type counts once signed on any plan): the plan-sha reason is gone from the watchdog"""
    src = open(nw.__file__).read()
    assert "derive_superseded" not in src and "superseded.txt" not in src and "not a live adopted plan" not in src
    assert not hasattr(nw, "derive_superseded")
    assert "NEVER a reason" in src
    # the verdicts that remain are the documented ones: HBM parked, LEC > 24 h, and the judged window (NO-PROGRESS / DESIGN-FAIL)
    assert set(nw.BAD_VERDICTS) == {"NO-PROGRESS", "CANCEL-NOW", "DESIGN-FAIL"}
    import re
    reasons = re.findall(r'verdict="CANCEL-NOW", why="([^"]+)"', src)
    assert reasons == ["HBM is parked"], reasons


def test_route_done(tmp_path):
    w = tmp_path / "run/results/asap7/dp_x/base"
    w.mkdir(parents=True)
    assert not nw.route_done(str(tmp_path))
    (w / "5_route.odb").write_text("x")
    assert nw.route_done(str(tmp_path))


# ---------------------------------------------------------------- cancel decision
def row(c, unit, verdict, key=None):
    return {"container": c, "unit": unit, "verdict": verdict, "key": key or c, "gb": 1, "threads": 8}


def test_first_pass_reports_second_pass_cancels():
    rows = [row("a", "u1", "NO-PROGRESS")]
    assert nw.decide(rows, {}, NOW, True) == [] and rows[0]["action"].startswith("REPORTED")
    rows = [row("a", "u1", "NO-PROGRESS")]
    assert nw.decide(rows, {"a": NOW - 100}, NOW, True) == []                    # reported only 100 s ago: the hub has not posted yet
    rows = [row("a", "u1", "NO-PROGRESS")]
    assert nw.decide(rows, {"a": NOW - 2000}, NOW, True) == ["u1"] and rows[0]["action"] == "CANCELLED"
    rows = [row("a", "u1", "CANCEL-NOW")]
    assert nw.decide(rows, {"a": NOW - 2000}, NOW, False) == [] and rows[0]["action"].startswith("WOULD-CANCEL")


def test_scope_with_a_healthy_sibling_or_without_scope_is_report_only():
    rows = [row("a-lec", "u1", "NO-PROGRESS"), row("a", "u1", "PROGRESS")]
    assert nw.decide(rows, {"a-lec": 0}, NOW, True) == [] and rows[0]["action"].startswith("REPORT-ONLY")
    rows = [row("b", None, "NO-PROGRESS")]
    assert nw.decide(rows, {"b": 0}, NOW, True) == [] and "no ot-heavy scope" in rows[0]["action"]


def test_all_containers_of_a_scope_must_be_bad():
    rows = [row("a", "u1", "NO-PROGRESS"), row("a-lec", "u1", "NO-PROGRESS")]
    assert nw.decide(rows, {"a": 0, "a-lec": 0}, NOW, True) == ["u1"]


def test_estimated_line_times_get_a_longer_window():
    # last news 6.5 h ago, times interpolated: not yet NO-PROGRESS (window x1.25 = 7.5 h); with real samples over a window it is
    res = {"name": None, "series": [], "growth_idx": 199, "n": 225}
    anc = [(NOW - 8.4 * H, 0), (NOW - 6.5 * H, 200), (NOW, 225)]
    assert nw.judge(res, anc, NOW)[0] != "NO-PROGRESS"
    assert nw.judge(res, anc, NOW, exact=True)[0] == "NO-PROGRESS"


def test_standalone_lec_without_scope_is_cancellable_only_when_lec_only():
    r = row("happy_hodgkin", None, "CANCEL-NOW")
    r["lec_only"] = True
    assert nw.decide([r], {"happy_hodgkin": 0}, NOW, True) == [None]
    r2 = row("flow", None, "CANCEL-NOW")
    assert nw.decide([r2], {"flow": 0}, NOW, True) == []


LEGALIZER = """[INFO GRT-0101] Running extra iterations to remove congestion.
Iteration | Violations | Moved
---------------------------------
        0 |       4000 |  10
      100 |       3000 |  80
[INFO RSZ-0034] detailed placement legalizer pass
"""


def test_grt_stage_ignores_the_legalizer_violations_table():
    """FABLE-PD-KV-1450 fix 7: the detailed-placement legalizer table is not global-route progress in 5_1_grt"""
    res = nw.extract("grt", LEGALIZER)
    assert res["series"] == [] and res["name"] is None
    assert res["growth_idx"] == 0                              # only the GRT-0101 line is global-route news
    assert nw.extract("other", LEGALIZER)["name"] == "repair_Violations"      # other stages keep the generic reading


def test_grt_incremental_activity_counts_as_growth():
    t = LEGALIZER + "[INFO GRT-0128] incremental global routing: 12 nets\n"
    assert nw.extract("grt", t)["growth_idx"] == len(t.splitlines()) - 1


# ---------------------------------------------------------------- DOCKERGRP-1400
def test_sh_retries_refused_docker_through_sg(monkeypatch):
    """a user manager started before ubuntu joined group docker gets 'permission denied': the call is retried through sg docker -c"""
    import subprocess as sp
    calls = []

    def fake(cmd, **kw):
        calls.append(cmd)
        if cmd[0] == "docker":
            return sp.CompletedProcess(cmd, 1, "", "permission denied while trying to connect to the docker API")
        return sp.CompletedProcess(cmd, 0, "abc123\n", "")
    monkeypatch.setattr(nw.subprocess, "run", fake)
    del nw.DOCKER_ERR[:]
    assert nw.sh("docker", "ps", "-q") == "abc123\n"
    assert calls[1] == ["sg", "docker", "-c", "docker ps -q"] and not nw.DOCKER_ERR


def test_sh_keeps_a_docker_failure_for_the_loud_line(monkeypatch):
    import subprocess as sp
    monkeypatch.setattr(nw.subprocess, "run", lambda cmd, **kw: sp.CompletedProcess(cmd, 1, "", "Cannot connect to the Docker daemon"))
    del nw.DOCKER_ERR[:]
    assert nw.sh("docker", "ps", "-q") == "" and "Cannot connect" in nw.DOCKER_ERR[0]
    del nw.DOCKER_ERR[:]
    assert nw.sh("echo", "x") == "" and not nw.DOCKER_ERR       # a non-docker failure is not a docker error


def test_stage_cap_and_heartbeat_lines_are_not_progress(tmp_path):
    # MEM-RECLAIM-2200 (FABLE-FLOW-2200 class 10): the STAGE-CAP keep line every few minutes made 148 jobs PROGRESSING with 0.0 h since the last event
    cap = "2026-11-21 05:51:50 STAGE-CAP keep /srv/x/5_1_grt.odb: busy\n"
    text = "[INFO GRT-0096] start\nsome real news\n" + cap * 50 + "WATCHER replaced pid 12 -> 13 x.sh\nheartbeat ok\n"
    res = nw.extract("other", text)
    assert res["n"] == 54 and res["growth_idx"] == 1                      # the last meaningful line is the real news
    v, why, _ = nw.judge(res, anchors_for(res["n"], 30, 0.0), NOW)
    assert v == "NO-PROGRESS", (v, why)
    # the log file that only carries those lines is never the job's log
    work = tmp_path / "w"
    (work / "run/logs/asap7/d/base").mkdir(parents=True)
    stage = work / "run/logs/asap7/d/base/5_2_route.tmp.log"
    stage.write_text("x\n")
    cap_log = work / "stage_odb_cap.log"
    cap_log.write_text(cap)
    hb = work / "kit_heartbeat.log"
    hb.write_text("beat\n")
    os.utime(stage, (NOW, NOW))
    os.utime(cap_log, (NOW + 500, NOW + 500))
    os.utime(hb, (NOW + 600, NOW + 600))
    log, mt = nw.candidate_logs(str(work), [], "dpkit-x", NOW - 100)
    assert log == str(stage) and mt == NOW
    cap_log.unlink(); hb.unlink(); stage.unlink()
    cap_log.write_text(cap)
    assert nw.candidate_logs(str(work), [], "dpkit-x", NOW - 100) == (None, 0)       # only the harness log: no flow log (NO-DATA), never PROGRESSING
