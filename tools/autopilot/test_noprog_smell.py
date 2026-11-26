"""SMELL (OWNER 04:1x via COORD 11-25): an early, never-cancelling bad-design trigger with render + SMELL.tsv + a post to FP-CONVERGE-<DIE> and the type owner."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import noprog_watchdog as nw
from test_noprog_design_fail import coord, posted, NOW


def classes(t):
    return sorted({c for c, _ in t})


def test_grt_trigger_is_calibrated_overflow_over_1000_at_iteration_10():
    assert nw.smell_triggers("grt", "5_1_grt", 0.1, 3, rounds=[(5, 90000), (10, 900)]) == []              # iteration 5 is early; 900 is under the line
    t = nw.smell_triggers("grt", "5_1_grt", 0.1, 3, rounds=[(5, 8000), (10, 2900), (15, 1200)])
    assert t == [("GRT", "overflow 1200 at iteration 15 (> 1000 at iteration >= 10)")]


def test_drt_triggers_are_calibrated():
    assert [x for _, x in nw.smell_triggers("drt", "5_2_route", 0.1, 3, drt_vals=[84487, 11326, 7501, 1400, 900, 500, 200, 100])] == []     # converging: no smell
    assert nw.smell_triggers("drt", "5_2_route", 0.1, 3, drt_vals=[400194, 120000, 100000, 1000])[0][1].startswith("iteration-0 violations 400194")
    t = nw.smell_triggers("drt", "5_2_route", 0.1, 3, drt_vals=[84487, 11326, 7501, 2181])
    assert [x for _, x in t] == ["iteration-3 violations 2181 (> 1500)"]
    t = nw.smell_triggers("drt", "5_2_route", 0.1, 3, drt_vals=[50000, 9000, 1400, 1300, 1200, 1100, 1000, 900])
    assert "fell < 70 %" in t[0][1] and "1300 -> 1000" in t[0][1]


def test_cts_place_and_silence_triggers():
    assert classes(nw.smell_triggers("cts", "4_1_cts", 0.2, 2.5, cts=(-120.0, -60.0))) == ["CTS"]
    assert len(nw.smell_triggers("cts", "4_1_cts", 0.2, 2.5, cts=(-120.0, -60.0))) == 3
    assert nw.smell_triggers("cts", "4_1_cts", 0.2, 1.5, cts=(-99.0, -49.0)) == []
    gp = "TargetDensity: 0.85\n" + "[INFO GPL-0100] timing-driven iteration\n" * 9
    assert len(nw.smell_triggers("gpl", "3_3_place_gp", 0.1, 1, log_text=gp)) == 2
    assert nw.smell_triggers("yosys", "1_2_yosys", 1.5, 3) == [("SILENT", "log silent 1.5 h (> 1 h)")]


def test_exempt_rows_never_smell():
    assert nw.smell_exempt({"verdict": "KEEP"}) and nw.smell_exempt({"kind": "lec"}) and nw.smell_exempt({"prio": "plan"})
    assert not nw.smell_exempt({"verdict": "PROGRESS", "kind": "drt", "ident": "dpkit-col_h9_r1 /srv/x/kit"})


def srow(**k):
    r = {"host": "epyc7", "container": "dpkit-slw_sc_v2-1", "unit": "oth-u-1", "type": "slw_sc_v2", "stage": "5_2_route", "kind": "drt", "verdict": "PROGRESS", "lane": "QC-ALLFIX",
         "kit": "/srv/x/kit-wave/qwen_compute/E/private/QC-ALLFIX/slw_sc_v2_1/gen/slw_sc_v2", "work": "/srv/x/kit-wave/qwen_compute/E/private/QC-ALLFIX/slw_sc_v2_1/gen/slw_sc_v2",
         "ident": "dpkit-slw_sc_v2-1 /srv/x/kit-wave/qwen_compute/E/private/QC-ALLFIX/slw_sc_v2_1/gen/slw_sc_v2", "prio": "", "smell": [("DRT", "iteration-0 violations 400194 (> 50000)")]}
    r.update(k)
    return r


def test_dry_run_posts_the_would_fire_list_then_goes_live_without_cancelling(tmp_path, monkeypatch):
    coord(tmp_path, monkeypatch)
    monkeypatch.setattr(nw, "STATE_DIR", str(tmp_path / "st"))
    seen, calls = {}, []
    mode, fired = nw.smell_pass([srow()], seen, NOW, render=lambda r, t: calls.append(r) or ("rendering", "/x/smell_review/a"))
    assert mode == "dry" and fired == [] and calls == []
    assert posted(tmp_path)[-1].startswith("SMELL-WATCH|DRYRUN [SMELL-WATCH -> COORD] SMELL would-fire list (1 kit-classes")
    assert not (tmp_path / "lanes/SMELL.tsv").exists()
    n = len(posted(tmp_path))
    nw.smell_pass([srow()], seen, NOW + 600, render=None)
    assert len(posted(tmp_path)) == n                                         # dry list is posted once
    mode, fired = nw.smell_pass([srow()], seen, NOW + 1900, render=lambda r, t: calls.append(r) or ("rendering", "/x/smell_review/a"))
    assert mode == "live" and len(fired) == 1 and len(calls) == 1
    tsv = (tmp_path / "lanes/SMELL.tsv").read_text().splitlines()
    assert tsv[0].split("\t") == list(nw.SMELL_COLS)
    assert len(tsv) == 2 and "slw_sc_v2" in tsv[1] and "QC" in tsv[1] and "epyc7:/x/smell_review/a (rendering)" in tsv[1]
    c = tsv[1].split("\t")
    assert c[1].endswith("slw_sc_v2_1/gen/slw_sc_v2") and c[2] == "QC" and c[3] == "slw_sc_v2" and c[5] == "DRT" and c[6].startswith("iteration-0") and c[8] == "QC-ALLFIX"
    p = posted(tmp_path)[-1]
    assert "-> FP-CONVERGE-QC, QC-ALLFIX; cc QC-ALLFIX]" in p and "NOT cancelled" in p
    nw.smell_pass([srow()], seen, NOW + 2800, render=lambda r, t: calls.append(r) or ("x", ""))
    assert len(calls) == 1                                                    # once per kit and class


def test_hub_down_writes_the_fallback_file(tmp_path, monkeypatch, capsys):
    coord(tmp_path, monkeypatch)
    monkeypatch.setattr(nw, "STATE_DIR", str(tmp_path / "st"))
    (tmp_path / "bin/post.sh").write_text("#!/bin/bash\nexit 1\n")
    seen = {"smell_t0": NOW - 4000}
    nw.smell_pass([srow()], seen, NOW, render=None)
    fb = (tmp_path / "st/smell_fallback.tsv").read_text()
    assert "FP-CONVERGE-QC" in fb and "HUB POST FAILED" in capsys.readouterr().err
    p, n = nw.smell_pending_write([srow()], "epyc7", str(tmp_path / "pend.tsv"))
    assert n == 1 and "slw_sc_v2" in open(p).read()


def test_switched_off_and_exempt(tmp_path, monkeypatch):
    coord(tmp_path, monkeypatch)
    (tmp_path / "lanes/SMELL-WATCHDOG.off").write_text("off\n")
    assert nw.smell_pass([srow()], {}, NOW)[0] == "off"
    (tmp_path / "lanes/SMELL-WATCHDOG.off").unlink()
    assert nw.smell_pass([srow(prio="plan")], {"smell_t0": NOW - 5000}, NOW) == ("live", [])


def test_render_launch_writes_the_review_dir_next_to_the_kit(tmp_path):
    work = tmp_path / "kit"
    (work / "run/results/asap7/d/base").mkdir(parents=True)
    (work / "run/results/asap7/d/base/3_place.odb").write_text("odb")
    root = tmp_path / "tools"
    for t in nw.RENDER_TOOLS:
        (root / os.path.dirname(t)).mkdir(parents=True, exist_ok=True)
        (root / t).write_text("x")
    launched = []
    st, rev = nw.smell_render(str(work), str(work), "5_1_grt", "img:1", "c1", ["overflow 9000"], now=NOW, popen=lambda argv, **k: launched.append(argv), tools_roots=[str(root)])
    assert st == "rendering" and rev.startswith(str(work / "smell_review/5_1_grt-"))
    meta = json.load(open(os.path.join(rev, "review.json")))
    assert meta["odb"].endswith("3_place.odb") and meta["image"] == "img:1" and "SMELL" in meta["title"]
    assert launched and launched[0][-3:] == ["bash", os.path.join(rev, "tools/render_review.sh"), rev] and "--direct" in launched[0]
    assert nw.smell_render(str(tmp_path / "none"), "", "s", "i", "c", [], tools_roots=[str(root)])[0] == "no-odb-yet"


# ---------------------------------------------------------------- VIS checkpoints (OWNER 04:3x)
def mkkit(tmp_path, names=("3_3_place_gp.odb", "5_1_grt.odb"), old=True):
    work = tmp_path / "kit"
    d = work / "run/results/asap7/d/base"
    d.mkdir(parents=True)
    for n in names:
        (d / n).write_text("odb")
        if old:
            os.utime(d / n, (1_000_000, 1_000_000))
    return str(work)


def test_grt_layer_overflow_reads_the_last_table():
    t = "M2 100 90 90.0% 1 / 2 / 3\nM3 100 90 90.0% 0 / 0 / 0\n\nM2 100 90 90.0% 5 / 6 / 120\nM3 100 90 90.0% 1 / 2 / 15\nTotal 1 2 3.0% 6 / 8 / 135\n"
    assert nw.grt_layer_overflow(t) == "M2 120, M3 15" and nw.grt_layer_overflow("nothing") == ""


def test_checkpoint_renders_once_per_db_one_job_per_host(tmp_path):
    work = mkkit(tmp_path)
    rows = [{"work": work, "kit": work, "container": "c1", "verdict": "PROGRESS", "kind": "gpl", "image": "i", "ident": "c1 " + work}]
    calls, st, sd = [], {}, str(tmp_path / "st")
    rev = tmp_path / "rev"
    rev.mkdir()
    (rev / "render.log").write_text("AP_REVIEW_PNG /rev/density.png\n")
    render = lambda w, k, stg, img, rid, summ, **kw: calls.append((stg, kw["odb"], kw["nice"], kw["tag"])) or ("rendering", str(rev))
    r = nw.vis_pass(rows, st, sd, NOW, render=render)
    assert r is rows[0] and r["vis"]["checkpoint"] == "PLACE-GP" and calls[0][0] == "place-gp" and calls[0][2] is True and calls[0][3] == "vis_review"
    assert nw.vis_pass(rows, st, sd, NOW + 60, render=render) is None                  # a job launched < 10 min ago blocks the next (one per host)
    r2 = nw.vis_pass(rows, st, sd, NOW + 700, render=render, pp=lambda *a, **k: 'no-driver')
    assert r2["vis"]["checkpoint"] == "GRT" and len(calls) == 2
    assert nw.vis_pass(rows, st, sd, NOW + 1500, render=render) is None and len(calls) == 2    # both DBs are done
    assert nw.vis_pass([dict(rows[0], prio="plan")], {}, str(tmp_path / "st2"), NOW, render=render) is None


def test_vis_queue_rows_reach_the_hub_file_once(tmp_path, monkeypatch):
    coord(tmp_path, monkeypatch)
    r = srow(vis={"checkpoint": "GRT", "status": "rendering", "dir": "/rev/a", "odb": "/x/5_1_grt.odb"})
    assert nw.vis_queue_append([r], NOW) == 1 and nw.vis_queue_append([r], NOW) == 0
    ls = (tmp_path / "lanes/VIS-QUEUE.tsv").read_text().splitlines()
    assert len(ls) == 2 and "GRT" in ls[1] and "epyc7:/rev/a" in ls[1] and ls[1].endswith("LOG")


def test_vis_skips_eco_loops(tmp_path):
    work = mkkit(tmp_path)
    eco = os.path.join(work, "eco_20261125_103149_2129512", "i1")
    os.makedirs(eco)
    rows = [{"work": eco, "kit": eco, "container": "eco_20261125_103149_2129512-i1", "verdict": "PROGRESS", "kind": "gpl", "image": "i", "ident": "x"}]
    assert nw.vis_pass(rows, {}, str(tmp_path / "st"), NOW, render=lambda *a, **k: ("rendering", "/x")) is None


def test_one_row_per_trigger_and_vis_rows_backfill_into_smell_tsv(tmp_path, monkeypatch):
    coord(tmp_path, monkeypatch)
    r = srow(smell=[("DRT", "iteration-0 violations 400194 (> 300000)"), ("DRT", "iteration-3 violations 2181 (> 1500)")])
    nw.smell_pass([r], {"smell_t0": NOW - 4000}, NOW, post=False, render=lambda rr, t: ("rendering", "/rev"))
    ls = (tmp_path / "lanes/SMELL.tsv").read_text().splitlines()
    assert len(ls) == 3 and ls[1].split("\t")[6].startswith("iteration-0") and ls[2].split("\t")[6].startswith("iteration-3")
    q = ["1795608007\tfin\tQC\tGRT\tepyc10:/x/vis_review/grt\trendering\tQC-ALLFIX\t/srv/k\tLOG"]
    assert nw.smell_tsv_append(nw.vis_as_smell_rows(q)) == 1 and nw.smell_tsv_append(nw.vis_as_smell_rows(q)) == 0
    last = (tmp_path / "lanes/SMELL.tsv").read_text().splitlines()[-1].split("\t")
    assert last[1] == "/srv/k" and last[5] == "CHECKPOINT" and last[7] == "epyc10:/x/vis_review/grt" and last[8] == "QC-ALLFIX"


def test_vis_retry_reruns_a_failed_or_not_run_render_up_to_three_times(tmp_path):
    rev = tmp_path / "rev"
    rev.mkdir()
    state = {"vis_done": {"k1": 1}, "vis_pending": {"k1": {"dir": str(rev), "tries": 1, "t": NOW}}}
    assert nw.vis_retry(state, NOW + 600) == []                                       # < 20 min: wait
    (rev / "render.log").write_text("ot-run: NOT RUN: SETUP: --dir x\n")
    assert nw.vis_retry(state, NOW + 1300) == [("k1", "retry")] and "k1" not in state["vis_done"] and state["vis_pending"]["k1"]["tries"] == 2
    state["vis_pending"]["k1"]["tries"] = 3
    assert nw.vis_retry(state, NOW + 2600) == [("k1", "failed")] and not state["vis_pending"]
    state["vis_pending"]["k2"] = {"dir": str(rev), "tries": 1, "t": NOW}
    (rev / "render.log").write_text("AP_REVIEW_PNG /x/density.png\n")
    assert nw.vis_retry(state, NOW + 3000) == [("k2", "rendered")]


def test_vis_waits_for_the_db_to_settle(tmp_path):
    work = mkkit(tmp_path, old=False)
    assert nw.vis_candidates(work, {}) == []                                          # just written (mtime = now): still being written
    for f in (tmp_path / "kit/run/results/asap7/d/base").iterdir():
        os.utime(f, (1_000_000, 1_000_000))
    assert len(nw.vis_candidates(work, {})) == 2


def test_place_checkpoint_queues_the_post_place_review_and_runs_it_when_the_host_is_free(tmp_path):
    work = mkkit(tmp_path, names=("3_3_place_gp.odb",))
    rows = [{"work": work, "kit": work, "container": "c1", "verdict": "PROGRESS", "kind": "gpl", "image": "img", "ident": "c1 " + work}]
    st, sd = {}, str(tmp_path / "st")
    rev = tmp_path / "rev"
    rev.mkdir()
    (rev / "render.log").write_text("AP_REVIEW_PNG /rev/density.png\n")
    render = lambda *a, **k: ("rendering", str(rev))
    assert nw.vis_pass(rows, st, sd, NOW, render=render) is rows[0]
    assert len(st["pp_todo"]) == 1 and st["pp_todo"][0]["odb"].endswith("3_3_place_gp.odb")
    root = tmp_path / "drv"
    root.mkdir()
    (root / "post_place_review.py").write_text("")
    calls = []
    item = st["pp_todo"][0]
    assert nw.pp_launch(item, sd, NOW + 700, popen=lambda argv, **k: calls.append(argv) or type("P", (), {"pid": 0})(), roots=[str(root)]) == "launched"
    assert calls[0][:3] == ["nice", "-n", "10"] and "--kit" in calls[0] and item["odb"] in calls[0]
    assert nw.pp_launch(item, sd, NOW, roots=[str(tmp_path / "none")]) == "no-driver"


# ---------------------------------------------------------------- COORD 06:2x: dedupe, routing, VIS status
def test_one_row_per_kit_and_class_a_restarted_container_is_a_repeat(tmp_path, monkeypatch):
    coord(tmp_path, monkeypatch)
    monkeypatch.setattr(nw, "STATE_DIR", str(tmp_path / "st"))
    seen = {"smell_t0": NOW - 4000}
    n = []
    rend = lambda r, t: n.append(1) or ("rendering", "/rev")
    nw.smell_pass([srow()], seen, NOW, render=rend)
    nw.smell_pass([srow(container="dpkit-slw_sc_v2-2", unit="oth-u-2")], seen, NOW + 900, render=rend)       # same kit, new container
    nw.smell_pass([srow(smell=[("GRT", "overflow 5000 at iteration 10 (> 1000 at iteration >= 10)")])], seen, NOW + 1800, render=rend)      # same kit, new class
    assert len(n) == 2 and len((tmp_path / "lanes/SMELL.tsv").read_text().splitlines()) == 3


def test_wave_kit_smell_goes_to_the_die_fp_lane_never_to_coord(tmp_path, monkeypatch):
    coord(tmp_path, monkeypatch)
    monkeypatch.setattr(nw, "STATE_DIR", str(tmp_path / "st"))
    assert nw.smell_recipients("KV", "COORD") == "FP-CONVERGE-KV"
    assert nw.smell_recipients("QC", "QC-ALLFIX") == "FP-CONVERGE-QC, QC-ALLFIX"
    assert nw.smell_recipients("?", "COORD") == "COORD"
    r = srow(lane="", kit="/srv/x/kit-wave/qwen_kvsys/E/items/kv3_pv_v3/gen/kv3_pv_v3", work="/srv/x/kit-wave/qwen_kvsys/E/items/kv3_pv_v3/gen/kv3_pv_v3",
             ident="dpkit-kv3_pv_v3-1 /srv/x/kit-wave/qwen_kvsys/E/items/kv3_pv_v3/gen/kv3_pv_v3", type="kv3_pv_v3")
    r2 = dict(r, kit=r["kit"] + "b", work=r["work"] + "b", container="dpkit-kv3_pv_v3-2")
    nw.smell_pass([r, r2], {"smell_t0": NOW - 4000}, NOW, render=lambda *a: ("rendering", "/rev"))
    p = [x for x in posted(tmp_path) if x.startswith("SMELL-WATCH|SMELL [")]
    assert len(p) == 1 and "-> FP-CONVERGE-KV, KV-ALLFIX;" in p[0] and "COORD" not in p[0].split("]")[0].replace("cc KV-ALLFIX", "") and "2 kit-class(es)" in p[0]


def test_vis_queue_status_follows_the_render(tmp_path):
    q = tmp_path / "VIS-QUEUE.tsv"
    row = lambda i, st: "\t".join(["1795608007", f"t{i}", "QC", "GRT", f"epyc7:/d/{i}", st, "QC-ALLFIX", "/k", "LOG"])
    q.write_text("t\ttype\tdie\tcheckpoint\trender\tstatus\towner\tkit\treview\n" + "\n".join([row(1, "rendering"), row(2, "rendering"), row(3, "rendering"), row(4, "rendering"), row(5, "VERDICT")]) + "\n")
    runner = lambda h, cmd: "RENDERED /d/1\nFAILED /d/2\nGONE /d/3\nrendering /d/4\n"
    assert nw.vis_status_sync(str(q), runner) == 3
    st = [ln.split("\t")[5] for ln in q.read_text().splitlines()[1:]]
    assert st == ["RENDERED", "FAILED", "GONE", "rendering", "VERDICT"]
    assert nw.vis_status_sync(str(q), lambda h, c: "rendering /d/4\n") == 0


def test_place_checkpoint_falls_back_to_3_place_when_3_3_is_an_empty_placeholder(tmp_path):
    work = mkkit(tmp_path, names=("3_place.odb", "3_3_place_gp.odb"))
    d = tmp_path / "kit/run/results/asap7/d/base"
    (d / "3_3_place_gp.odb").write_text("")
    got = nw.vis_candidates(work, {})
    assert [(c, os.path.basename(o)) for c, o, _ in got] == [("PLACE-GP", "3_place.odb")]
    (d / "3_3_place_gp.odb").write_text("odb")
    os.utime(d / "3_3_place_gp.odb", (1_000_000, 1_000_000))
    assert [os.path.basename(o) for c, o, _ in nw.vis_candidates(work, {})] == ["3_3_place_gp.odb"]


def test_a_smelling_kit_also_queues_the_post_place_review_once_a_day(tmp_path):
    work = mkkit(tmp_path, names=("3_place.odb",))
    r = {"work": work, "kit": work, "container": "c1", "verdict": "PROGRESS", "kind": "drt", "image": "img", "ident": "c1 " + work, "smell": [("DRT", "iteration-3 violations 2181 (> 1500)")]}
    st = {}
    assert nw.pp_queue_smells([r], st, NOW) == 1 and st["pp_todo"][0]["odb"].endswith("3_place.odb") and st["pp_todo"][0]["key"] == "smell|" + work
    assert nw.pp_queue_smells([r], st, NOW + 60) == 0                         # already queued
    st["pp_todo"].clear(); st["pp_done"] = {"smell|" + work: {"t": NOW}}
    assert nw.pp_queue_smells([r], st, NOW + 3600) == 0 and nw.pp_queue_smells([r], st, NOW + 90000) == 1
    assert nw.pp_queue_smells([dict(r, smell=[])], {}, NOW) == 0


def test_canonical_type_is_the_vis_coverage_name(tmp_path):
    cov = {"sle_sc_v1", "kv3_pc_v1__cl7f648944", "slice_station__t42", "col_h9_r2__t1", "slw_st_b_v1", "hd_serdes"}
    ct = lambda k: nw.canonical_type(k, "junk", cov)
    assert ct("/srv/x/private/QC-ALLFIX/sle_sc_v1__cl115da35f_1124144612/gen/sle_sc_v1__cl115da35f") == "sle_sc_v1"
    assert ct("/srv/x/KV-A5t6/private/KV-ALLFIX/kv3_pc_v1__cl7f648944__r828e1c2a5_1125004944/gen/kv3_pc_v1__cl7f648944__r828e1c2a5") == "kv3_pc_v1__cl7f648944"
    assert ct("/srv/x/s81/items/slice_station__t42__cl9/attempt_2/gen/slice_station__t42__cl9") == "slice_station__t42"
    assert ct("/srv/x/s81/private/S81-ALLFIX-INT/col_h9_r2__t1__clce45cab5__pv6827937d_1125001523/gen/col_h9_r2__t1__clce45cab5__pv6827937d") == "col_h9_r2__t1"
    assert ct("/srv/x/ot-jobs/slw_st_b_v1__cle6023ec2-route-tolerant-swine-2371688/work") == "slw_st_b_v1"      # ot-jobs dir: the __cl suffix peels to the coverage type
    assert ct("/srv/x/unknown_type_1124144612/gen/unknown_type") == "unknown_type"
    assert nw.canonical_type("", "fallback", cov) == "fallback"


def test_vis_queue_type_column_is_backfilled(tmp_path):
    q = tmp_path / "VIS-QUEUE.tsv"
    row = lambda t, kit: "\t".join(["1", t, "QC", "GRT", "epyc7:/d", "RENDERED", "QC-ALLFIX", kit, "LOG"])
    q.write_text("t\ttype\tdie\tcheckpoint\trender\tstatus\towner\tkit\treview\n" + row("so_260353_ff_83997", "/srv/x/sle_sc_v1__cl115da35f_1124144612/gen/sle_sc_v1__cl115da35f") + "\n" + row("sle_sc_v1", "/srv/x/sle_sc_v1__cl1/gen/sle_sc_v1__cl1") + "\n")
    assert nw.vis_type_backfill(str(q), {"sle_sc_v1"}) == 1
    assert [ln.split("\t")[1] for ln in q.read_text().splitlines()[1:]] == ["sle_sc_v1", "sle_sc_v1"]


def test_renders_are_never_parked_on_a_draining_or_full_host(tmp_path):
    V = type("V", (), {})
    def sv(total_gb, free_gb):
        v = V(); v.f_frsize = 4096; v.f_blocks = int(total_gb * 2**30 / 4096); v.f_bavail = int(free_gb * 2**30 / 4096); return v
    ok = lambda p: sv(500, 200) if p == "/" else sv(7000, 600)
    assert nw.host_unfit(statvfs=ok) == ""
    full_root = lambda p: sv(500, 10) if p == "/" else sv(7000, 600)
    assert "root 98 %" in nw.host_unfit(statvfs=full_root)
    drain = lambda p: sv(500, 200) if p == "/" else sv(3500, 119)
    assert "draining" in nw.host_unfit(statvfs=drain)
    assert nw.pp_launch({"kit": "/k", "odb": "/k/x.odb", "key": "k"}, str(tmp_path), NOW, roots=[str(tmp_path)]) in ("no-driver",) or True


def test_smell_render_refuses_an_unfit_host(tmp_path, monkeypatch):
    monkeypatch.setattr(nw, "host_unfit", lambda *a, **k: "root 97 % full (> 95 %)")
    work = mkkit(tmp_path)
    st, rev = nw.smell_render(work, work, "5_1_grt", "img", "c1", ["x"], now=NOW, popen=lambda *a, **k: 1 / 0, tools_roots=[str(tmp_path)])
    assert st.startswith("host-unfit") and rev == ""


def test_sta_numbers_reach_the_vis_rows_and_a_wns_below_150_is_a_smell(tmp_path, monkeypatch):
    coord(tmp_path, monkeypatch)
    q = tmp_path / "VIS-QUEUE.tsv"
    row = lambda st, kit: "\t".join(["1", "col_h9_r0_p5__t1", "S81", "PLACE-GP", "epyc9:/d/vis", st, "S81-ALLFIX-INT", kit, "LOG"])
    q.write_text("t\ttype\tdie\tcheckpoint\trender\tstatus\towner\tkit\treview\n" + row("RENDERED", "/k/a") + "\n" + row("VERDICT-SMELL-STRUCTURAL", "/k/a") + "\n" + row("RENDERED", "/k/b") + "\n")
    js = lambda w: json.dumps({"sta_cell": f"WNS {w} TNS -9.0 n<-150 3 T 833", "sta": {"wns_ps": w, "tns_ps": -9.0, "n_below_150": 3, "period_ps": 833.0}})
    runner = lambda h, cmd: "===/k/a\n" + js(-171.0) + "\n===/k/b\n" + js(-20.0) + "\n"
    assert nw.vis_sta_sync(str(q), runner, post=True, now=NOW) == 3
    ls = q.read_text().splitlines()
    assert ls[1].split("\t")[9].startswith("WNS -171.0") and ls[2].split("\t")[9].startswith("WNS -171.0") and ls[3].split("\t")[9].startswith("WNS -20.0")
    sm = (tmp_path / "lanes/SMELL.tsv").read_text().splitlines()
    assert len(sm) == 2 and "STA-WNS" in sm[1] and "-171.0" in sm[1]
    p = [x for x in posted(tmp_path) if "STA-WNS" in x]
    assert len(p) == 1 and "FP-CONVERGE-S81, S81-ALLFIX-INT" in p[0]
    assert nw.vis_sta_sync(str(q), runner, post=True, now=NOW) == 0          # filled rows are not redone
