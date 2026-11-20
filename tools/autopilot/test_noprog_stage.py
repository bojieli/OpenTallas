"""tests for noprog_stage.py (NOPROG-FIX-1115): one parser test per flow stage on real log snippets (noprog_fixtures/, cut from live
kits on epyc2 / intel1, 2026-11-15), the PROGRESSING / SLOW / NO-PROGRESS classes, the exclusion-free host scan helpers.
The tests start no process: docker / ssh / coord are never called."""
import os, sys, tempfile, json
from types import SimpleNamespace
sys.path.insert(0, os.path.dirname(__file__))
import noprog_stage as ns

FX = os.path.join(os.path.dirname(__file__), "noprog_fixtures")
H = 3600
NOW = 1_000_000_000.0


def fx(name):
    return open(os.path.join(FX, name), errors="replace").read()


def anchors_for(n, age_h, last_write_h=0.0):
    return [(NOW - age_h * H, 0), (NOW - last_write_h * H, n)]


def run(kind, text, age_h, last_write_h=0.0, cores=1.0, job_h=None, exact=True):
    res = ns.parse_stage(kind, text)
    an = anchors_for(res["n"], age_h, last_write_h)
    return ns.classify(kind, res, an, NOW, (job_h or age_h) * H, NOW - last_write_h * H, cores, exact)


# ---------------------------------------------------------------- stage kinds
def test_stage_kind_every_stage():
    k = ns.stage_kind
    assert k("run/logs/a/b/base/1_2_yosys.log") == "synth"
    assert k("run/logs/a/b/base/2_1_floorplan.log") == "floorplan"
    assert k("run/logs/a/b/base/3_3_place_gp.tmp.log") == "place_gp"
    assert k("run/logs/a/b/base/3_1_place_gp_skip_io.log") == "place_gp"
    assert k("run/logs/a/b/base/3_4_place_resized.tmp.log") == "place_rs"
    assert k("run/logs/a/b/base/3_5_place_dp.tmp.log") == "place_dp"
    assert k("run/logs/a/b/base/4_1_cts.tmp.log") == "cts"
    assert k("run/logs/a/b/base/5_1_grt.tmp.log") == "grt"
    assert k("run/logs/a/b/base/5_2_route.tmp.log") == "route"
    assert k("/x/unitruns/u004_b/drt.log") == "route"
    assert k("/x/die/drt_TT.log") == "route"
    assert k("run/logs/a/b/base/6_report.log") == "sta"
    assert k("/x/cert1/signoff.log") == "sta"
    assert k("/x/lec_run.log") == "lec"
    assert k("/x/sdc_lint.log") == "other"
    assert k("/x/prep.log") == "other"


# ---------------------------------------------------------------- parsers on real snippets
def test_synth_parser_counts_yosys_passes():
    res = ns.parse_stage("synth", fx("yosys.txt"))
    assert res["events"] and res["series"] == []


def test_floorplan_repair_timing_table_metric():
    res = ns.parse_stage("floorplan", fx("floorplan.txt"))
    assert res["table"] and res["name"] == "repair_Viol"
    vals = [v for _, v in res["series"]]
    assert vals[0] == 1081 and len(vals) >= 8


def test_gpl_overflow_series_from_timing_driven_table():
    res = ns.parse_stage("place_gp", fx("gpl_table.txt"))
    assert res["name"] == "gpl_overflow"
    vals = [v for _, v in res["series"]]
    assert vals[0] == 0.4446 and vals[-1] == 0.4404 and len(vals) == 12


def test_gpl_initial_place_has_events_not_series():
    res = ns.parse_stage("place_gp", fx("gpl_init.txt"))
    assert res["series"] == [] and len(res["events"]) >= 10


def test_resize_repair_design_remaining():
    res = ns.parse_stage("place_rs", fx("resize.txt"))
    assert res["name"] == "repair_Remaining"
    vals = [v for _, v in res["series"]]
    assert vals[0] == 231299 and vals == sorted(vals, reverse=True)


def test_dp_objective_per_pass():
    res = ns.parse_stage("place_dp", fx("dp.txt"))
    assert res["name"] == "dpl_objective"
    assert res["series"] and res["series"][0][1] > 4e9


def test_cts_events_skip_repeats_and_use_log_growth():
    res = ns.parse_stage("cts", fx("cts.txt"))
    assert res["series"] == [] and len(res["events"]) > 20


def test_grt_hold_repair_table_tns():
    res = ns.parse_stage("grt", fx("grt_hold.txt"))
    assert res["table"] and res["name"] == "repair_TNS"
    vals = [v for _, v in res["series"]]
    assert vals[0] == 543155.188 and vals[-1] == 534718.25      # |TNS|, 40 iterations, 1.6 %


def test_grt_extra_iteration_loop_counter_is_progress():
    """epyc9 col_h9_r0_p5 (11-15 23:xx): 10+ jobs were in the GRT-0102 loop (iteration 13/30, 19/30), log written minutes ago.  The loop
    counter is news; the congestion total after the loop is the metric."""
    text = fx("grt_loop.txt")
    res = ns.parse_stage("grt", text)
    lines = text.splitlines()
    assert any("GRT-0102" in lines[i] for i in res["events"])
    assert res["name"] == "grt_overflow" and res["series"][-1][1] == 40.0
    loop = "\n".join(l for l in lines if "GRT-0101" in l or "GRT-0102" in l)
    cls, ev = run("grt", loop, age_h=36, last_write_h=0.1)
    assert cls == "PROGRESSING" and "extra iteration" in ev
    cls, ev = run("grt", loop, age_h=36, last_write_h=17, cores=1.0)
    assert cls == "NO-PROGRESS" and "17." in ev


def test_drt_unit_log_is_events_only_inside_first_iteration():
    res = ns.parse_stage("route", fx("drt_unit.txt"))
    assert res["series"] == [] and res["events"]


def test_drt_iterations_series_from_finished_route():
    res = ns.parse_stage("route", fx("drt_done.txt"))
    vals = [v for _, v in res["series"]]
    assert vals == [1599, 115, 54, 0] or vals[-1] == 0 and vals[0] > vals[1]


def test_lec_has_no_metric():
    res = ns.parse_stage("lec", "anything\nline\n")
    assert res["series"] == [] and res["n"] == 2


# ---------------------------------------------------------------- classes
def gpl_rows(vals):
    return "Iteration | Overflow |     HPWL (um) |  HPWL(%) |   Penalty | Group\n" + "\n".join(
        f"{i * 10:8d} | {v:8.4f} |  1.1e+07 |   +0.0% |  4.09e-13 |" for i, v in enumerate(vals))


def test_progressing_when_metric_improves_2pct_in_window():
    vals = [0.9 - 0.01 * i for i in range(60)]
    cls, ev = run("place_gp", gpl_rows(vals), age_h=10, last_write_h=0.1)
    assert cls == "PROGRESSING", ev


def test_no_progress_flat_metric_for_window_with_evidence_line():
    cls, ev = run("place_gp", gpl_rows([0.44] * 60), age_h=9, last_write_h=0.2)
    assert cls == "NO-PROGRESS" and "gpl_overflow best 0.44" in ev and "stagnant" in ev


def test_flat_metric_but_young_is_not_no_progress():
    cls, ev = run("place_gp", gpl_rows([0.44] * 60), age_h=3, last_write_h=0.2)
    assert cls == "SLOW", ev


def test_slow_between_2_and_6_hours_flat():
    cls, _ = run("place_gp", gpl_rows([0.44] * 40), age_h=4, last_write_h=0.1)
    assert cls == "SLOW"


def test_log_alive_young_stage_is_progressing():
    cls, _ = run("cts", fx("cts.txt"), age_h=0.5, last_write_h=0.0)
    assert cls == "PROGRESSING"


def test_events_only_stage_silent_6h_no_progress():
    cls, ev = run("cts", fx("cts.txt"), age_h=8, last_write_h=7, cores=1.5)
    assert cls == "NO-PROGRESS" and "no new meaningful log line" in ev


def test_events_only_stage_silent_3h_slow():
    cls, _ = run("cts", fx("cts.txt"), age_h=8, last_write_h=3, cores=1.5)
    assert cls == "SLOW"


def test_hung_silent_1h_idle_cpu():
    cls, ev = run("cts", fx("cts.txt"), age_h=2, last_write_h=1.5, cores=0.0)
    assert cls == "NO-PROGRESS" and "hung" in ev


def test_restarted_series_does_not_make_a_13h_job_young():
    """kv3_hgi_v2 (11-15): a repair table that restarted inside the last 6 h left the old watchdog on YOUNG for 13 h.  Evidence is the
    log's age, the best is taken across restarts: the same table with a 7 h silent log is NO-PROGRESS, never YOUNG."""
    text = fx("grt_hold.txt")
    cls, ev = run("grt", text, age_h=13, last_write_h=7.0)
    assert cls == "NO-PROGRESS" and "YOUNG" not in ev and "window-gain 0.0%" in ev
    cls, ev = run("grt", text, age_h=13, last_write_h=0.3)
    assert cls in ("PROGRESSING", "SLOW") and "repair_TNS best 534718" in ev


def test_repair_timing_rows_with_star_parse():
    """floorplan / grt repair_timing rows are printed "3154* |"; the old row regex dropped them"""
    res = ns.parse_stage("grt", "Iter | WNS | TNS | Viol\n----\n   10* | -1.0 | -500.0 | 7\n   20* | -1.0 | -400.0 | 6\n")
    assert [v for _, v in res["series"]] == [7, 6]


def test_restart_that_improves_inside_window_is_progress():
    first = [0.5 - 0.0001 * i for i in range(30)]          # long flat phase, then a restart high but falling fast
    second = [0.9 - 0.02 * i for i in range(30)]
    cls, ev = run("place_gp", gpl_rows(first + second), age_h=12, last_write_h=0.0)
    assert cls == "PROGRESSING", ev


def test_evidence_bounded_by_job_age():
    """a log born before the container (reused work dir) cannot give more evidence than the job's own age"""
    res = ns.parse_stage("place_gp", gpl_rows([0.44] * 60))
    an = anchors_for(res["n"], 20, 0.1)
    cls, _ = ns.classify("place_gp", res, an, NOW, 2 * H, NOW - 0.1 * H, 1.0)
    assert cls != "NO-PROGRESS"


def test_unexact_times_stretch_window():
    cls, _ = run("place_gp", gpl_rows([0.44] * 60), age_h=6.5, last_write_h=0.2, exact=False)
    assert cls != "NO-PROGRESS"


def test_lec_classes_use_file_activity():
    res = ns.parse_stage("lec", "x\n")
    an = anchors_for(res["n"], 30, 30)
    assert ns.classify("lec", res, an, NOW, 30 * H, NOW - 30 * H, 1.0, True, lec_mt=NOW - 0.2 * H)[0] == "PROGRESSING"
    assert ns.classify("lec", res, an, NOW, 30 * H, NOW - 30 * H, 1.0, True, lec_mt=NOW - 3 * H)[0] == "SLOW"
    assert ns.classify("lec", res, an, NOW, 30 * H, NOW - 30 * H, 1.0, True, lec_mt=NOW - 7 * H)[0] == "NO-PROGRESS"
    assert ns.classify("lec", res, an, NOW, 30 * H, NOW - 30 * H, 0.0, True, lec_mt=NOW - 1.5 * H)[0] == "NO-PROGRESS"


def test_nolog_job():
    assert ns.classify_nolog(0.5 * H, 4.0)[0] == "PROGRESSING"
    assert ns.classify_nolog(3 * H, 0.0)[0] == "NO-PROGRESS"
    assert ns.classify_nolog(8 * H, 3.0)[0] == "SLOW"


def test_empty_log():
    cls, _ = run("cts", "", age_h=0.2)
    assert cls == "PROGRESSING"


# ---------------------------------------------------------------- scan helpers, hub output
def test_redirect_logs_maps_container_path_to_host_path():
    cmd = "bash -lc source env.sh; /usr/bin/time -v openroad -exit /w/drt.tcl > /w/drt.log 2>&1; echo EXIT $? >> /w/drt.log"
    mounts = [{"Source": "/srv/x/u004_b", "Destination": "/w"}, {"Source": "/srv/x/u004_b", "Destination": "/out"}]
    assert ns.redirect_logs(cmd, mounts)[0] == "/srv/x/u004_b/drt.log"


def row(cls, host="epyc2", stage="5_1_grt", stage_h=13.0, ev="e"):
    return {"cls": cls, "host": host, "kit": "/srv/x/kits/kv3_hgi_v2", "type": "t", "stage": stage, "stage_h": stage_h, "job_h": 13.2,
            "cores_now": 1.0, "gb": 5.0, "container": f"c-{cls}-{host}", "evidence": ev}


def test_tsv_sorts_no_progress_first_and_summary_lists_evidence():
    rows = [row("PROGRESSING"), row("NO-PROGRESS", stage_h=20, ev="repair_TNS best 534718 stagnant 8.0 h"), row("SLOW", host="epyc7")]
    t = ns.tsv(rows, "2026-11-15 17:00 PST", [])
    lines = t.splitlines()
    assert lines[0].startswith("# NOPROG") and lines[1].split("\t")[0] == "class"
    assert lines[2].split("\t")[0] == "NO-PROGRESS" and lines[-1].split("\t")[0] == "PROGRESSING"
    s = ns.summary(rows, "2026-11-15 17:00 PST", ["epyc9"])
    assert s.startswith("STATE [NOPROG-FIX-1115 -> COORD]") and "NO-PROGRESS 1" in s and "kv3_hgi_v2 5_1_grt stage 20" in s
    assert "repair_TNS best 534718" in s and "epyc9" in s and "no cancel" in s


def test_hub_writes_tsv_and_posts_through_post_sh_only(monkeypatch):
    """hub() with the host scan, coord-commit and post.sh replaced: file refreshed, one post per hour, no other process"""
    calls = []
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, "lanes"))
    os.makedirs(os.path.join(d, "state"))
    monkeypatch.setattr(ns, "COORD", d)
    monkeypatch.setattr(ns, "STATE_DIR", os.path.join(d, "state"))
    monkeypatch.setattr(ns, "push_and_scan", lambda host: (
        host, [row("NO-PROGRESS" if host == "epyc2" else "PROGRESSING", host=host)],
    ))
    monkeypatch.setattr(ns, "coord_commit", lambda msg, files: calls.append(("commit", files)))

    def post(cmd, **kwargs):
        calls.append(("run", os.path.basename(cmd[1]), cmd[2], cmd[3]))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(ns, "subprocess", SimpleNamespace(run=post))
    rows = ns.hub(now=NOW)
    assert len(rows) == len(ns.HOSTS)
    t = open(os.path.join(d, "lanes/NOPROG.tsv")).read()
    assert "NO-PROGRESS" in t.splitlines()[2]
    posts = [c for c in calls if c[0] == "run"]
    assert len(posts) == 1 and posts[0][1] == "post.sh" and posts[0][2] == "NOPROG-FIX-1115" and "NO-PROGRESS 1" in posts[0][3]
    before = open(os.path.join(d, "lanes/NOPROG.tsv")).read()
    ns.hub(now=NOW + 900)                              # 15 min later: nothing to commit -> the tracked file is NOT rewritten (no dirty checkout), no second post
    assert open(os.path.join(d, "lanes/NOPROG.tsv")).read() == before
    assert len([c for c in calls if c[0] == "run"]) == 1
    ns.hub(now=NOW + 3700)
    assert len([c for c in calls if c[0] == "run"]) == 2


def test_failed_commit_restores_the_tracked_table():
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, "lanes")); os.makedirs(os.path.join(d, "state"))
    open(os.path.join(d, "lanes/NOPROG.tsv"), "w").write("# committed text\n")
    ns.COORD, ns.STATE_DIR = d, os.path.join(d, "state")
    ns.push_and_scan = lambda h: (h, [])

    class F:
        returncode = 1
    ns.coord_commit = lambda msg, files: F()
    ns.hub(now=NOW, post=False)
    assert open(os.path.join(d, "lanes/NOPROG.tsv")).read() == "# committed text\n"


def test_old_action_log_is_kept_under_new_name():
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, "lanes"))
    os.makedirs(os.path.join(d, "state"))
    old = "time\thost\ttype\tstage\nx\ty\tz\tw\n"
    open(os.path.join(d, "lanes/NOPROG.tsv"), "w").write(old)
    ns.COORD, ns.STATE_DIR = d, os.path.join(d, "state")
    got = []
    ns.push_and_scan = lambda h: (h, [])
    ns.coord_commit = lambda msg, files: got.append(files)
    ns.hub(now=NOW, post=False)
    assert open(os.path.join(d, "lanes/NOPROG-ACTIONS.tsv")).read() == old and "lanes/NOPROG-ACTIONS.tsv" in got[0]


def drt_partial_case(counts, stale=False, extra=""):
    # HEAD p16g: the old completed totals changed <2%; iteration 3 is long
    # and its real Completing counts improve before another completed total.
    text = ("[INFO DRT-0195] Start 1st optimization iteration.\n"
            "[INFO DRT-0199] Number of violations = 14622\n"
            "[INFO DRT-0195] Start 2nd optimization iteration.\n"
            "[INFO DRT-0199] Number of violations = 14445\n"
            "[INFO DRT-0195] Start 3rd optimization iteration.\n")
    text += "\n".join(f"Completing {10 * (i + 1)}% with {n} violations" for i, n in enumerate(counts)) + "\n" + extra
    res = ns.parse_stage("route", text)
    end_age = 7 if stale else 0
    anc = [(NOW - 32 * H, 0), (NOW - 14 * H, 3), (NOW - (end_age + 4) * H, 5), (NOW - end_age * H, res["n"] - 1)]
    return res, ns.classify("route", res, anc, NOW, 32 * H, NOW - end_age * H, 11.02)


def test_drt_active_iteration_improvement_is_separate_from_completed_totals():
    res, (cls, ev) = drt_partial_case([13437, 12438, 11462])
    assert [v for _, v in res["series"]] == [14622, 14445]
    assert [v for _, v in res["partial_series"]] == [13437, 12438, 11462]
    assert cls == "PROGRESSING", ev
    assert "drt_active_iteration_violations" in ev and "14.7%" in ev


def test_drt_percent_advances_with_flat_or_worse_quality_is_no_progress():
    for counts in ([14445, 14445, 14445], [14445, 15000, 15500]):
        _, (cls, ev) = drt_partial_case(counts)
        assert cls == "NO-PROGRESS", ev


def test_drt_old_partial_improvement_does_not_keep_job_alive():
    _, (cls, ev) = drt_partial_case([13437, 12438, 11462], stale=True)
    assert cls == "NO-PROGRESS", ev


def test_drt_partial_restart_never_combines_different_iteration_states():
    for restart in ("[INFO DRT-0195] Start 4th optimization iteration.\nCompleting 10% with 20000 violations\n",
                    "Completing 10% with 20000 violations\n"):
        res, (cls, ev) = drt_partial_case([13437, 12438, 11462], extra=restart)
        assert [v for _, v in res["partial_series"]] == [20000]
        assert cls == "NO-PROGRESS", ev


def test_drt_completed_iteration_discards_its_partial_witness():
    res, (cls, ev) = drt_partial_case([13437, 12438, 11462], extra="[INFO DRT-0199] Number of violations = 14445\n")
    assert res["partial_series"] == []
    assert cls == "NO-PROGRESS", ev
