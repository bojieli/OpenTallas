"""KW-FIX-44 11-10 (COORD rulings (3)): grt183_make.sh stops the 5_1_grt stage (a) when the full global route ended
congested at or above OT_GRT_CONGESTED_FAIL_MIN (GRT-INCR-CONGESTED), (b) when the post-route part of the stage runs past
OT_GRT_POST_MAX_S.  Local, no Docker/OpenROAD.
    python3 -m pytest -q tools/die_plan/test_grt_incr_congested_kit.py"""
import os
import time

from test_grt183_kit import calls, fake, kit, run

FAST = {"OT_GRT_STALL_POLL": "1", "OT_GRT_STALL_KILL_WAIT": "1"}


def grt_log(overflow=None, congested=True, extra=""):
    """a 5_1_grt.tmp.log as the full route leaves it (GRT-0096 table, GRT-0303 runtime)"""
    s = "global_route -congestion_report_file x -allow_congestion\n"
    if overflow is not None:
        s += ("[INFO GRT-0096] Final congestion report:\nLayer         Resource        Demand        Usage (%)    Max H / Max V / Total Congestion\n"
              f"M2            34279928       4033630           11.77%             8 /  0 / 7340\n"
              f"Total        189407777       22983179           12.13%            31 / 26 / {overflow}\n")
    if congested:
        s += "[WARNING GRT-0115] Global routing finished with congestion. Check the congestion regions in the DRC Viewer.\n"
    s += "[INFO GRT-0303] Global routing runtime = 13:46:45\n" + extra
    return s


def body(log, then="sleep 60; exit 0"):
    return "cat > $L/5_1_grt.tmp.log <<'EOF'\n" + log + "EOF\n" + then + "\n"


def test_congested_full_route_stops_at_once(tmp_path):
    k, r, l, s = kit(tmp_path)
    t = time.time()
    p = run(k, s, fake(tmp_path, body(grt_log(83032))), "grt", env=FAST)
    assert p.returncode == 21, p.stdout + p.stderr
    assert time.time() - t < 30
    assert "OT_GRT_CONGESTED_FAIL stage=grt full global route ended with congestion: total overflow 83032 >= 1000" in p.stdout
    assert "OT_GRT_STOP congested" in p.stdout and len(calls(k)) == 1          # no fresh-process re-run


def test_small_overflow_keeps_kw_fix_8(tmp_path):
    k, r, l, s = kit(tmp_path)
    p = run(k, s, fake(tmp_path, body(grt_log(31), then="sleep 4; exit 0")), "grt", env=FAST)
    assert p.returncode == 0 and "OT_GRT_CONGESTED_FAIL" not in p.stdout and "OT_GRT_STOP" not in p.stdout


def test_floor_and_opt_out_from_config(tmp_path):
    k, r, l, s = kit(tmp_path / "floor", "export OT_GRT_CONGESTED_FAIL_MIN = 50\n")
    p = run(k, s, fake(tmp_path / "floor", body(grt_log(60))), "grt", env=FAST)
    assert p.returncode == 21 and "total overflow 60 >= 50" in p.stdout
    k, r, l, s = kit(tmp_path / "off", "export OT_GRT_CONGESTED_FAIL = 0\nexport OT_GRT_POST_MAX_S = 0\n")
    p = run(k, s, fake(tmp_path / "off", body(grt_log(83032), then="sleep 4; exit 0")), "grt", env=FAST)
    assert p.returncode == 0 and "OT_GRT_" not in p.stdout.replace("OT_GRT183", "")


def test_uncongested_route_is_not_stopped(tmp_path):
    k, r, l, s = kit(tmp_path)
    p = run(k, s, fake(tmp_path, body(grt_log(0, congested=False), then="sleep 4; exit 0")), "grt", env=FAST)
    assert p.returncode == 0 and "OT_GRT_STOP" not in p.stdout


def test_time_cap_after_full_route_reports_slack(tmp_path):
    k, r, l, s = kit(tmp_path)
    log = grt_log(0, congested=False, extra=("OT_HOLD_GUARD_GRT start: hold ws -40.10 tns -900.0 viol 50, margin 5, 100 instances, budget 20 %\n"
                                              "OT_HOLD_GUARD_GRT chunk 3: hold ws -12.50 (+3.00) tns -100.0 viol 9, +10 buffers (cap 200), 900 s\n"
                                              "repair_design -verbose\n"))
    t = time.time()
    p = run(k, s, fake(tmp_path, body(log)), "grt", env=dict(FAST, OT_GRT_POST_MAX_S="3"))
    assert p.returncode == 21, p.stdout + p.stderr
    assert time.time() - t < 30
    line = next(x for x in p.stdout.splitlines() if x.startswith("OT_GRT_TIMECAP"))
    assert "stage=grt post-route repair over" in line and "(cap 3 s)" in line
    assert "hold_ws_ps=-12.50" in line and "setup_wns=unmeasured" in line and "last='repair_design -verbose'" in line
    assert len(calls(k)) == 1


def test_time_cap_never_cuts_the_full_route(tmp_path):
    k, r, l, s = kit(tmp_path)
    p = run(k, s, fake(tmp_path, 'printf "global_route -verbose\\n[INFO GRT-0101] Running extra iterations\\n" > $L/5_1_grt.tmp.log; sleep 5; exit 0\n'),
            "grt", env=dict(FAST, OT_GRT_POST_MAX_S="1"))
    assert p.returncode == 0 and "OT_GRT_TIMECAP" not in p.stdout


def test_log_of_an_earlier_run_is_ignored(tmp_path):
    k, r, l, s = kit(tmp_path)
    (l / "5_1_grt.tmp.log").write_text(grt_log(83032))
    os.utime(l / "5_1_grt.tmp.log", (1000, 1000))          # left by a killed run before this wrapper started
    p = run(k, s, fake(tmp_path, "sleep 4; exit 0\n"), "grt", env=dict(FAST, OT_GRT_POST_MAX_S="1"))
    assert p.returncode == 0 and "OT_GRT_STOP" not in p.stdout


def test_stall_rule_still_works_beside_the_new_stops(tmp_path):
    from test_grt_stall_kit import OK2, STALL1
    k, r, l, s = kit(tmp_path)
    p = run(k, s, fake(tmp_path, STALL1 + OK2), "grt", env=dict(FAST, OT_GRT_STALL_S="2"))
    assert p.returncode == 0 and "OT_GRT_STALL_RESUME attempt 2 rc 0" in p.stdout and "OT_GRT_STOP" not in p.stdout
