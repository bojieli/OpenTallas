"""FLEET-WATCH-1015 / FLOW-OPS-0900: UNSIGNABLE rule of the no-progress watchdog (job > 3 h, measured unable to sign), NOTICE to the owning lane, cancel 30 min later by ot-run --cancel <exact unit> unless KEEP."""
import json, os, sys, types
sys.path.insert(0, os.path.dirname(__file__))
import noprog_watchdog as nw

NOW = 1_000_000_000.0


def cts(d, ws, mtime):
    p = d / "run/logs/asap7/dp_x/base/4_1_cts.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"cts__timing__setup__ws": ws, "cts__timing__hold__ws": -9999.0}))
    os.utime(p, (mtime, mtime))
    return p


def test_measured_setup_reads_only_the_file_this_job_wrote(tmp_path):
    cts(tmp_path, -1550.85, NOW - 100)
    assert nw.measured_setup([str(tmp_path)], NOW - 3600)[0] == -1550.85
    assert nw.measured_setup([str(tmp_path)], NOW + 5000) is None            # written before this container started: an earlier attempt
    assert nw.measured_setup([str(tmp_path / "nothing"), None, ""], 0) is None
    (tmp_path / "run/logs/asap7/dp_x/base/4_1_cts.json").write_text("{not json")
    assert nw.measured_setup([str(tmp_path)], 0) is None
    (tmp_path / "run/logs/asap7/dp_x/base/4_1_cts.json").write_text(json.dumps({"cts__timing__hold__ws": -500.0}))
    assert nw.measured_setup([str(tmp_path)], 0) is None                      # hold-only data is not a setup measurement


def ev(setup, age=12.0, ident="dpkit-col_h9_r2__t1-1", prio="", kind="other"):
    return nw.unsignable_evidence(ident, prio, kind, age, None if setup is None else (setup, "/k/4_1_cts.json"))


def test_the_rule_fires_only_below_minus_300_and_after_3_h():
    assert "-301.00 ps" in ev(-301.0) and "-1550.85" in ev(-1550.85)
    for s in (-300.0, -299.0, -150.0, -42.0, 10.0, None):                     # between -42 and -300, at the line, positive, unmeasured
        assert ev(s) is None, s
    assert ev(-500.0, age=3.0) is None and ev(-500.0, age=2.0) is None and ev(-500.0, age=3.1)


def test_never_proofs_ecos_plan_jobs_lec_or_hbm():
    assert ev(-900, prio="plan") is None and ev(-900, prio="proof") is None and ev(-900, kind="lec") is None
    assert ev(-900, ident="dpkit-x-eco_r2-5") is None and ev(-900, ident="/srv/a/eco/gen/t1") is None
    assert ev(-900, ident="/srv/a/coll_core_proof_pkw2b/gen/t1") is None
    assert ev(-900, ident="/srv/a/runs/hbm/kit-wave/hbm/p/items/t1") is None
    assert ev(-900, ident="dpkit-second_core-7") is not None                    # 'eco' inside a word is not an ECO


def row(unit="oth-ubuntu-1-2", host="epyc9", key="c1|/k1", verdict=nw.UNSIGNABLE, lane="", type_="t1", ident=""):
    return {"unit": unit, "host": host, "key": key, "verdict": verdict, "type": type_, "kit": "/s/runs/s81/kit-wave/s81/3fa87b/items/t1/gen/t1", "why": "4_1_cts.json cts__timing__setup__ws -700.00 ps",
            "gb": 48.0, "setup_ps": -700.0, "age_h": 12.0, "lane": lane, "container": "dpkit-" + type_ + "-1", "ident": ident or ("dpkit-" + type_ + "-1"), "prio": "", "kind": "grt"}


def coord(tmp_path, monkeypatch):
    (tmp_path / "bin").mkdir(); (tmp_path / "lanes").mkdir(); (tmp_path / "lanes/posts").mkdir()
    (tmp_path / "bin/post.sh").write_text("#!/bin/bash\necho \"$1|$2\" >> " + str(tmp_path / "posted") + "\n")
    monkeypatch.setattr(nw, "COORD", str(tmp_path)); monkeypatch.delenv("NOPROG_UNSIGNABLE_ACT", raising=False)
    monkeypatch.setenv("NOPROG_UNSIGNABLE_MODE", "report")       # the 11-20 drop-in: no longer read (FLOW-OPS-0900)


def posted(tmp_path):
    p = tmp_path / "posted"
    return p.read_text().splitlines() if p.exists() else []


def test_notice_to_owning_lane_then_cancel_after_30_min_by_exact_unit(tmp_path, monkeypatch):
    coord(tmp_path, monkeypatch)
    calls, seen = [], {}
    cancel = lambda u: (calls.append(u), (0, "containers stopped: dpkit-t1-1"))[1]
    mode, cand, done = nw.unsignable_pass([row(lane="FAM-S81-COL")], seen, NOW, cancel=cancel)
    assert mode == "act" and len(cand) == 1 and done == [] and calls == []
    p = posted(tmp_path)
    assert len(p) == 1 and p[0].startswith("FLEET-WATCH-1015|NOTICE [FLEET-WATCH-1015 -> FAM-S81-COL]") and "oth-ubuntu-1-2" in p[0] and "KEEP <unit>" in p[0]
    nw.unsignable_pass([row(lane="FAM-S81-COL")], seen, NOW + 1700, cancel=cancel)
    assert calls == [] and len(posted(tmp_path)) == 1                                           # inside the 30 min: nothing, no re-post
    _m, _c, done = nw.unsignable_pass([row(lane="FAM-S81-COL")], seen, NOW + 1801, cancel=cancel)
    assert calls == ["oth-ubuntu-1-2"] and done[0]["unit"] == "oth-ubuntu-1-2"
    tsv = (tmp_path / "lanes/CANCEL-UNSIGNABLE-1120.tsv").read_text().splitlines()
    assert len(tsv) == 1 and tsv[0].split("\t")[:3] == ["oth-ubuntu-1-2", "epyc9", "t1"] and "NOTICE to FAM-S81-COL" in tsv[0] and "ot-run --cancel oth-ubuntu-1-2 rc=0" in tsv[0]
    assert posted(tmp_path)[-1].startswith("FLEET-WATCH-1015|CANCELLED [FLEET-WATCH-1015 -> FAM-S81-COL]")
    nw.unsignable_pass([row(lane="FAM-S81-COL")], seen, NOW + 4000, cancel=cancel)
    assert calls == ["oth-ubuntu-1-2"]                                                          # once only


def test_keep_post_stops_the_cancel(tmp_path, monkeypatch):
    coord(tmp_path, monkeypatch)
    calls, seen = [], {}
    cancel = lambda u: (calls.append(u), (0, "ok"))[1]
    nw.unsignable_pass([row(lane="L1")], seen, NOW, cancel=cancel)
    (tmp_path / "lanes/posts/L1.md").write_text("- 2026-11-21 09:10 PST KEEP oth-ubuntu-1-2 setup recovering in my A/B\n")
    nw.unsignable_pass([row(lane="L1")], seen, NOW + 3600, cancel=cancel)
    assert calls == []


def test_first_listed_time_survives_a_changing_list(tmp_path, monkeypatch):
    coord(tmp_path, monkeypatch)
    calls, seen = [], {}
    cancel = lambda u: (calls.append(u), (0, "ok"))[1]
    nw.unsignable_pass([row()], seen, NOW, cancel=cancel)
    nw.unsignable_pass([row(unit="oth-ubuntu-7-7", key="c7|/k7")], seen, NOW + 900, cancel=cancel)    # list changed, the first unit missing this tick
    assert seen["unsig_units"]["epyc9|oth-ubuntu-1-2"]["first"] == NOW
    nw.unsignable_pass([row(), row(unit="oth-ubuntu-7-7", key="c7|/k7")], seen, NOW + 1900, cancel=cancel)
    assert calls == ["oth-ubuntu-1-2"]                                                          # 7-7 was noticed at +900: not yet


def test_decide_only_jobs_are_posted_for_a_decision_and_never_cancelled(tmp_path, monkeypatch):
    coord(tmp_path, monkeypatch)
    calls, seen = [], {}
    cancel = lambda u: (calls.append(u), (0, "ok"))[1]
    rows = [row(unit="oth-a-1-1", type_="ot_s81sl_leaf__t11", key="a|/a"), row(unit="oth-b-2-2", type_="slw_su_c__cl92142dac", key="b|/b"),
            row(unit="oth-c-3-3", type_="ot_s81sl_leaf__t110", key="c|/c")]
    for t in (NOW, NOW + 2000, NOW + 9000):
        nw.unsignable_pass(rows, seen, t, cancel=cancel)
    assert calls == ["oth-c-3-3"]                                                               # t110 is not t11
    p = "\n".join(posted(tmp_path))
    assert "DECISION [FLEET-WATCH-1015 -> FABLE-FIX-S81-LEAF-R5]" in p and "DECISION [FLEET-WATCH-1015 -> QC-PLAN-R10]" in p
    assert p.count("DECISION") == 2                                                             # once each


def test_off_switch_file_reports_only(tmp_path, monkeypatch):
    coord(tmp_path, monkeypatch)
    (tmp_path / "lanes/UNSIGNABLE-WATCHDOG.off").write_text("COORD: paused\n")
    calls, seen = [], {}
    cancel = lambda u: (calls.append(u), (0, "ok"))[1]
    for t in (NOW, NOW + 4000):
        mode, _c, _d = nw.unsignable_pass([row()], seen, t, cancel=cancel)
    assert mode == "report" and calls == [] and len(posted(tmp_path)) == 1 and "report mode" in posted(tmp_path)[0]


def test_siblings_and_unitless_rows_block_and_functional_bug_counts(tmp_path, monkeypatch):
    coord(tmp_path, monkeypatch)
    calls, seen = [], {}
    cancel = lambda u: (calls.append(u), (0, "ok"))[1]
    (tmp_path / "lanes/UNSIGNABLE-FUNCTIONAL.tsv").write_text("oth-ubuntu-4-4\tLATCHECK lane latency error 3 cycles\n")
    rows = [row(unit="oth-ubuntu-9-9", key="c2|/k2", verdict="PROGRESS"), row(unit="oth-ubuntu-9-9", key="c2b|/k2b"),
            row(unit=None, key="c3|/k3"), row(unit="oth-ubuntu-4-4", key="f|/f", verdict="PROGRESS")]
    for t in (NOW, NOW + 1801):
        nw.unsignable_pass(rows, seen, t, cancel=cancel)
    assert calls == ["oth-ubuntu-4-4"]


def test_flat_repair_below_gate_and_exemptions():
    assert "FLAT" in nw.unsignable_evidence("dpkit-t1-1", "", "grt", 4.0, (-120.0, "/k/5_1_grt.tmp.log", "flat"))
    assert nw.unsignable_evidence("dpkit-t1-1", "", "grt", 4.0, (-120.0, "/k/5_1_grt.log", "")) is None       # final, above -300: a lane may still fix it
    assert nw.unsignable_evidence("dpkit-t1-1", "", "grt", 4.0, (-30.0, "/k/5_1_grt.tmp.log", "flat")) is None  # inside the gate
    for ident in ("/srv/x/kit-wave/s81/E/private/LANE/t1_1/gen", "dpkit-t1_hold_eco-1", "/srv/a/qc-hold-0030-kits/t1", "/srv/a/holdfix/t1"):
        assert nw.unsignable_evidence(ident, "", "grt", 9.0, (-900.0, "/k/x")) is None, ident
    assert nw.unsignable_evidence("dpkit-threshold-1", "", "grt", 9.0, (-900.0, "/k/x"))                      # 'hold' inside a word


def test_grt_flat_two_rounds_on_lane_jobs():
    r = {"age_h": 5.0, "kind": "grt", "ident": "dpkit-t1-1", "prio": "", "verdict": nw.GRT_LABEL, "why": "NO-PROGRESS: overflow has not fallen across 2 consecutive rounds (9 9 9)"}
    assert "2 consecutive rounds" in nw.grt_unsignable_evidence(r)
    assert nw.grt_unsignable_evidence(dict(r, age_h=2.0)) is None and nw.grt_unsignable_evidence(dict(r, why="DESIGN-FAIL: overflow 2000 at round 10")) is None
    assert nw.grt_unsignable_evidence(dict(r, verdict="PROGRESS", grt_flat="overflow 9 at iteration 5 -> 9 at iteration 10")) .startswith("GRT overflow flat")


def test_cancel_goes_through_ot_run_cancel_with_the_exact_unit():
    seen = []
    def run(argv, **k):
        seen.append(argv); return types.SimpleNamespace(returncode=0, stdout="ot-run --cancel: epyc9: containers stopped: x\n", stderr="")
    assert nw.ot_run_cancel("oth-ubuntu-1-2", run=run) == (0, "ot-run --cancel: epyc9: containers stopped: x")
    assert seen[0][1:] == ["--cancel", "oth-ubuntu-1-2"] and seen[0][0].endswith("ot-run")


def test_unsignable_is_not_a_host_cancel_verdict():
    assert nw.UNSIGNABLE not in nw.BAD_VERDICTS            # a host scan never cancels it; only the hub, after NOTICE + 30 min


def tree(d, name, text, mtime):
    p = d / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    os.utime(p, (mtime, mtime))
    return p


SETUP_FINAL = ("   Iter   | Removed | Resized | Inserted | Cloned |  Pin  |   Area   |    WNS   |   StTNS    |   EnTNS    |  Viol  |  Worst  \n"
               "          | Buffers |  Gates  | Buffers  |  Gates | Swaps |          |          |            |            | Endpts | St/EnPt \n"
               "---------------------------------------------------------------------\n"
               "       0* |       0 |       0 |        0 |      0 |     0 |    +0.0% |  -52.600 |      -37.5 |      -37.5 |      3 | a/d\n"
               "      40* |       0 |       2 |        0 |      0 |     0 |    +0.0% |   -0.494 |       -4.0 |       -4.0 |      3 | a/d\n"
               "   final  |       0 |       2 |        0 |      0 |     0 |    +0.0% |   -0.494 |       -4.0 |       -4.0 |      3 | a/d\n")
HOLD = ("Iteration | Resized | Buffers | Cloned Gates |   Area   |   WNS   |   TNS   | Endpoint\n---------\n"
        "        0 |       0 |       0 |            0 |    +0.0% | -465.900 | -1019987.938 | x\n")


def test_the_newest_stage_number_wins_over_post_cts(tmp_path):
    """FABLE-FLOW-1200: slw_st_b was cancelled on post-CTS -405 while its GRT repair had reached -0.494 ps"""
    cts(tmp_path, -404.82, NOW - 5000)
    tree(tmp_path, "run/logs/asap7/dp_x/base/5_1_grt.log", HOLD + SETUP_FINAL, NOW - 100)
    assert nw.latest_setup([str(tmp_path)], NOW - 20000) == (-0.494, str(tmp_path / "run/logs/asap7/dp_x/base/5_1_grt.log"))
    assert ev(nw.latest_setup([str(tmp_path)], NOW - 20000)[0]) is None                       # -0.494 is inside the -42 gate: never cancelled


def test_the_tt_repair_log_and_stage_jsons_count_and_the_last_wns_is_the_result(tmp_path):
    cts(tmp_path, -648.0, NOW - 9000)
    tree(tmp_path, "tt_setup_keep.log", "OT_TT_SETUP_KEEP KEEP repaired: reloaded DB improved (wns -238.37 -> -196.78, tns -1 -> -2)\n", NOW - 50)
    assert nw.latest_setup([str(tmp_path)], NOW - 20000)[0] == -196.78
    tree(tmp_path, "run/logs/asap7/dp_x/base/5_1_grt.json", json.dumps({"globalroute__timing__setup__ws": -216.6}), NOW - 10)
    assert nw.latest_setup([str(tmp_path)], NOW - 20000)[0] == -216.6


def test_a_repair_still_improving_or_a_newer_hold_pass_is_unmeasured_not_the_stale_number(tmp_path):
    cts(tmp_path, -651.0, NOW - 9000)
    rows = "".join(f"{i * 10:8d}* |       0 |       2 |        0 |      0 |     0 |    +0.0% | {-600 + i * 8:8.3f} |      -4.0 |      -4.0 |      3 | a/d\n" for i in range(25))
    head = SETUP_FINAL.splitlines(True)[:3]
    tree(tmp_path, "run/logs/asap7/dp_x/base/5_1_grt.tmp.log", "".join(head) + rows, NOW - 5)
    assert nw.latest_setup([str(tmp_path)], NOW - 20000) is None                               # improving 8 ps per row: not final, not flat
    flat = "".join(f"{i * 10:8d}* |       0 |       2 |        0 |      0 |     0 |    +0.0% |  -311.700 |      -4.0 |      -4.0 |      3 | a/d\n" for i in range(25))
    tree(tmp_path, "run/logs/asap7/dp_x/base/5_1_grt.tmp.log", "".join(head) + flat, NOW - 5)
    assert nw.latest_setup([str(tmp_path)], NOW - 20000)[0] == -311.7                          # flat over 10 rows: the genuinely stuck case still counts
    tree(tmp_path, "run/logs/asap7/dp_x/base/5_1_grt.tmp.log", HOLD, NOW - 1)                    # newest file is a hold pass with no setup number
    assert nw.latest_setup([str(tmp_path)], NOW - 20000) is None


def test_a_resumed_job_is_unmeasured_until_it_reports(tmp_path):
    cts(tmp_path, -900.0, NOW - 40000)
    assert nw.latest_setup([str(tmp_path)], NOW - 3600) is None                                # the container started after the files were written


def test_owner_from_the_tree_path_when_the_unit_has_no_lane(tmp_path, monkeypatch):
    coord(tmp_path, monkeypatch)
    (tmp_path / "lanes/posts/FABLE-FIX-S81-SVC-1121.md").write_text("")
    r = row()
    r["kit"] = "/srv/opentallas-scratch2/claude/fable-fix-s81-svc-1121/kits/t1/gen"
    assert nw.owner_of([r]) == "FABLE-FIX-S81-SVC-1121" and nw.owner_of([row()]) == "COORD" and nw.owner_of([row(lane="L9")]) == "L9"
