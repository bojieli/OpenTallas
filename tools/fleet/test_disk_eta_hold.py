"""FABLE-FLOW-1900 (C): disk-ETA admission hold in ot-run + disk_rate.py pushes the fall rate and stops the top writer's lane."""
import json, os, sys, types
sys.path.insert(0, os.path.dirname(__file__))
import test_ot_run_scratch_disk as T
import disk_rate as D

m = T.m
NOW = 1_000_000.0


def row(free, rate, age=60):
    return dict(disk_gb=free, disk_rate_gb_h=rate, disk_rate_t=NOW - age)


def test_hold_when_the_fall_plus_the_job_crosses_the_floor():
    why = m.eta_refusal(row(100, 40), 20, NOW)          # 100 - 40 - 20 = 40 < 50
    assert why.startswith("disk-ETA") and "40 GB" in why
    assert m.eta_refusal(row(200, 40), 20, NOW) == ""   # 140 left
    assert m.eta_refusal(row(100, 0), 20, NOW) == ""    # not falling: the plain floors decide
    assert m.eta_refusal(row(60, 80, age=7200), 20, NOW) == ""   # stale sample ignored
    assert m.eta_refusal({"disk_gb": 60}, 20, NOW) == ""         # no sample


def test_drop_eta_keeps_the_other_hosts_and_reports_the_held_one():
    ok = {"a": row(100, 40), "b": row(400, 40)}
    out, held = m.drop_eta(ok, 20, now=NOW)
    assert list(out) == ["b"] and list(held) == ["a"]


def test_probe_line_is_parsed_into_the_row():
    probe = f"OT_SCRATCH_FREE {T.S2 if hasattr(T, 'S2') else '/srv/opentallas-scratch2'} 400 0\nOT_ROOTFS 9 500\nOT_DISK_ETA 37.5 {int(NOW)}\n"
    r = m.scratch_disk({"disk_gb": 400}, None, probe, host="epyc2")
    assert r["disk_rate_gb_h"] == 37.5 and r["disk_rate_t"] == NOW


def test_disk_rate_pushes_the_rate_and_stops_the_top_lane_only_inside_the_stop_horizon(tmp_path):
    D.HIST = str(tmp_path / "h.json")
    pushed, stopped = [], []
    GB = 1e9
    seq = iter([{"/srv/opentallas-scratch2": 400 * GB}, {"/srv/opentallas-scratch2": 340 * GB}])
    D.sample = lambda host: next(seq) if host == "epyc9" else {}
    D.HOSTS = ["epyc9"]
    D.main(post=False, now=NOW - 3600, pusher=lambda *a: pushed.append(a), stopper=lambda h: stopped.append(h) or " STOP")
    D.main(post=False, now=NOW, pusher=lambda *a: pushed.append(a), stopper=lambda h: stopped.append(h) or " STOP")
    assert pushed[-1][0] == "epyc9" and abs(pushed[-1][1] - 60.0) < 1.0           # 60 GB/h
    assert stopped == []                                                          # (340 - 50) / 60 = 4.8 h: alert horizon, not the stop horizon
    D.sample = lambda host: {"/srv/opentallas-scratch2": 100 * GB} if host == "epyc9" else {}
    D.main(post=False, now=NOW + 3600, pusher=lambda *a: pushed.append(a), stopper=lambda h: stopped.append(h) or " STOP")
    assert stopped == ["epyc9"]                                                   # 340 -> 100 GB in an hour: floor in < 1 h


def test_top_writer_skips_infrastructure_and_the_hold_never_cancels(tmp_path):
    out = json.dumps({"rt": 90, "autopilot": 80, "qc-types-r": 41.2, "kv-102": 12})
    calls = []

    def run(argv, **k):
        calls.append(argv)
        return types.SimpleNamespace(returncode=0, stdout=out if "lane_quota" in str(argv) else "", stderr="")
    assert D.top_writer_lane("epyc9", run=run) == ("qc-types-r", 41.2)
    txt = D.hold_top_lane("epyc9", run=run, switch_off=str(tmp_path / "none"))
    assert "ALERT top writer lane qc-types-r" in txt and "/claude/qc-types-r" in txt and "running units untouched" in txt
    flat = " ".join(" ".join(map(str, c)) for c in calls)
    assert "--cancel" not in flat and "ot-heavy-stop" not in flat and "kill" not in flat       # no cancel of any running unit
    assert "disk_eta_lanes" in flat
    (tmp_path / "OFF").write_text("")
    assert "disabled" in D.hold_top_lane("epyc9", run=run, switch_off=str(tmp_path / "OFF"))


def test_lane_hold_refuses_new_admission_under_the_lane_dir_only():
    r = dict(disk_gb=500, lane_holds=[(NOW - 60, "/srv/opentallas-scratch2/claude/qc-types-r")])
    assert m.lane_hold_refusal(r, "/srv/opentallas-scratch2/claude/qc-types-r/x/y", NOW).startswith("disk-ETA lane hold")
    assert m.lane_hold_refusal(r, "/srv/opentallas-scratch2/claude/kv-102/x", NOW) == ""
    assert m.lane_hold_refusal(r, "/srv/opentallas-scratch2/claude/qc-types-r2/x", NOW) == ""     # prefix of the name is not under it
    assert m.lane_hold_refusal(dict(r, lane_holds=[(NOW - 9000, r["lane_holds"][0][1])]), "/srv/opentallas-scratch2/claude/qc-types-r/x", NOW) == ""   # stale hold ends
    ok = {"a": r, "b": dict(disk_gb=500)}
    out, held = m.drop_eta(ok, 20, now=NOW, d="/srv/opentallas-scratch2/claude/qc-types-r/x")
    assert list(out) == ["b"] and list(held) == ["a"]
    out, held = m.drop_eta(ok, 20, now=NOW, d="/srv/opentallas-scratch2/claude/qc-types-r/x", plan=True)
    assert sorted(out) == ["a", "b"] and not held                                           # --priority plan jobs are never held


def test_lane_hold_probe_lines_and_recovery_clears_the_file(tmp_path):
    probe = f"OT_SCRATCH_FREE /srv/opentallas-scratch2 400 0\nOT_ROOTFS 9 500\nOT_LANE_HOLD {int(NOW)} /srv/opentallas-scratch2/claude/a\n"
    assert m.scratch_disk({"disk_gb": 400}, None, probe, host="epyc2")["lane_holds"] == [(NOW, "/srv/opentallas-scratch2/claude/a")]
    D.HIST = str(tmp_path / "h.json")
    cleared = []
    D.sample = lambda host: {"/srv/opentallas-scratch2": 400e9}
    D.HOSTS = ["epyc9"]
    D.main(post=False, now=NOW, pusher=lambda *a: None, stopper=lambda h: " X", clearer=lambda h: cleared.append(h))
    assert cleared == ["epyc9"]


def test_small_job_skips_the_fall_rate_hold_but_not_the_hard_floor():
    """P-RAIL-BYPASS: a --disk 2 gate is not held by a 40 GB/h fall; it is still held when it would cross the floor itself"""
    assert m.eta_refusal(row(100, 40), 20, NOW) != ""                 # a 20 GB job is held (100 - 40 - 20 < floor)
    assert m.eta_refusal(row(100, 40), 2, NOW) == ""                  # a 2 GB job passes
    assert m.eta_refusal(row(100, 400), 5, NOW) == ""                 # even in a steep fall
    assert m.eta_refusal(row(52, 40), 5, NOW).startswith("disk-ETA")  # 52 - 5 = 47 < floor 50: hard floor still holds it
