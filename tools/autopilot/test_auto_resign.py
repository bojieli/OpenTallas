"""auto_resign: what may launch, what stays for a lane, and that the record path runs with no agent."""
import json
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import auto_resign as AR

DIE, TAG = "qwen_kvsys", "flow-20261104-g-kv"
BUILD = "ab" * 20
HOLDS = "qwen_kvsys\tqkd_hr_core_*\tRF-C ruling\n*\t*astk*\tDIE-KV ruling\n"


def rpy_local(host, code, args, timeout=600):
    r = subprocess.run([sys.executable, "-I", "-", json.dumps(args)], input=code, capture_output=True, text=True, timeout=60)
    for line in reversed(r.stdout.splitlines()):
        if line.startswith("AP_JSON "):
            return json.loads(line[8:])
    return {"error": r.stderr[-300:]}


def make_kit(root, name="dp_x", verdict="SIGNED", generated="2026-11-04T01:00:00-08:00", reasons=()):
    kit = root / "kit"
    base = kit / "run" / "results" / "asap7" / name / "base"
    base.mkdir(parents=True)
    (base / "6_final.odb").write_bytes(b"odb")
    (base / "6_final.v").write_text("module x; endmodule\n")
    (kit / "signoff").mkdir()
    (kit / "signoff" / "signoff.json").write_text(json.dumps(dict(
        name=name, verdict=verdict, local_verdict="SIGNED", generated=generated, reasons=list(reasons),
        face_guard={"top": "top_x"}, inputs=dict(odb=str(base / "6_final.odb"), kit=str(kit), orfs=str(kit / "run"), final_v=str(base / "6_final.v")))))
    (kit / "PROVENANCE.json").write_text(json.dumps({"provenance": {"commit": BUILD}}))
    return kit


@pytest.fixture
def ap(tmp_path):
    coord = tmp_path / "coord"
    (coord / "lanes").mkdir(parents=True)
    apd = tmp_path / "ap"
    apd.mkdir()
    (coord / AR.HOLD).write_text(HOLDS)
    cache = tmp_path / "cache.json"
    cache.write_text(json.dumps({"generated": time.time(), "plans": {"p": {"die": DIE, "signed_types": {}, "signed_cores": {}, "signed_designs": {}, "designs": {}}}, "retired_records": []}))
    launched, lines = [], []

    def read_coord(rel):
        try:
            return (coord / rel).read_text()
        except OSError:
            return ""
    a = SimpleNamespace(DRY=False, AP_DIR=apd, REPO=tmp_path, RELEASE_CACHE=cache, HUB_NAME="intel2", OT_RUN="ot-run",
                        read_coord=read_coord, rpy=rpy_local, log=lambda m: None, now_s=lambda: "now", ssh_host=lambda h: h,
                        flow_tags=lambda die=None: [TAG], load_state=lambda: {"jobs": {}}, unit_active=lambda u: False,
                        parse_client_log=lambda t: {"exit": 0}, tsv_append=lambda *x: None,
                        coord_append=lambda rel, line: lines.append(line),
                        launch_unit=lambda unit, log, argv: launched.append((unit, argv)) or True,
                        sh=lambda *a, **k: (0, "", ""), launched=launched, lines=lines, coord=coord, cache=cache, apd=apd)
    return a


@pytest.fixture(autouse=True)
def fake_hub(monkeypatch):
    shas = {f: "0" * 64 for f in AR.TAG_TOOL_FILES}
    monkeypatch.setattr(AR, "tag_shas", lambda AP, tag: dict(shas))
    monkeypatch.setattr(AR, "known_commit", lambda AP, sha, branch=None: sha if sha == BUILD or sha == "cd" * 20 else "")
    monkeypatch.setattr(AR, "stage_tools", lambda AP, host, root, tag, s: ("/tools/" + tag, ""))
    monkeypatch.setattr(AR, "ROOTS", ())


def register(ap, kit, name="x", bc="-", host="h1"):
    (ap.coord / AR.REGISTRY).write_text("# die name host dir build lane note\n%s\t%s\t%s\t%s\t%s\tDIE-KV\tpilot\n" % (DIE, name, host, kit, bc))


def only_item(ap):
    return next(iter(AR.load_state(ap.apd)["items"].values()))


def roots_ok(monkeypatch, tmp_path):
    (tmp_path / "claude").mkdir(exist_ok=True)
    monkeypatch.setattr(AR, "ROOTS", (str(tmp_path),))


def test_registered_dir_launches_with_die_priority_on_db_host(ap, tmp_path, monkeypatch):
    roots_ok(monkeypatch, tmp_path)
    kit = make_kit(tmp_path)
    register(ap, kit)
    AR.step(ap)
    assert only_item(ap)["status"] == "RUNNING"
    unit, argv = ap.launched[0]
    assert argv[:1] == ["ot-run"] and "--crit" in argv and argv[argv.index("--hosts") + 1] == "h1" and "--no-spill" in argv
    i = argv.index("--")
    assert argv[i + 2:i + 4] == ["-I", "/tools/%s/resign_driver.py" % TAG] and "--auto" in argv
    assert argv[argv.index("--build-commit") + 1] == BUILD and argv[argv.index("--tag") + 1] == TAG
    assert argv[argv.index("--routed-db") + 1].endswith("6_final.odb")
    assert argv[argv.index("--dir") + 1] == "/tools/" + TAG    # a spill-marked kit is no --dir ot-run would place on


def test_needs_parent_only_is_a_candidate(ap, tmp_path, monkeypatch):
    roots_ok(monkeypatch, tmp_path)
    register(ap, make_kit(tmp_path, verdict="LOCAL_PASS_NEEDS_PARENT", reasons=["io_hold_parent: NEEDS_PARENT"]))
    AR.step(ap)
    assert only_item(ap)["status"] == "RUNNING"


def test_other_open_reason_waits(ap, tmp_path, monkeypatch):
    roots_ok(monkeypatch, tmp_path)
    register(ap, make_kit(tmp_path, verdict="LOCAL_PASS_NEEDS_PARENT", reasons=["io_hold_parent: x", "pg: y"]))
    AR.step(ap)
    assert only_item(ap)["status"] == "WAIT" and not ap.launched


def test_glob_row_takes_the_newest_record_that_counts(ap, tmp_path, monkeypatch):
    roots_ok(monkeypatch, tmp_path)
    make_kit(tmp_path / "i1" if (tmp_path / "i1").mkdir() is None else None)
    k2 = make_kit(tmp_path / "i2" if (tmp_path / "i2").mkdir() is None else None)
    (tmp_path / "i3" / "signoff").mkdir(parents=True)
    (tmp_path / "i3" / "signoff" / "signoff.json").write_text(json.dumps({"verdict": "NOT SIGNED"}))
    (ap.coord / AR.REGISTRY).write_text("%s\tx\th1\t%s/i*/kit\t-\tL\tn\n" % (DIE, tmp_path))
    import os
    os.utime(k2 / "signoff" / "signoff.json", (time.time() + 60, time.time() + 60))
    AR.step(ap)
    argv = ap.launched[0][1]
    assert str(k2) in argv[argv.index("--routed-db") + 1]


def test_no_provable_build_commit_stays_for_a_lane_and_says_so(ap, tmp_path, monkeypatch):
    roots_ok(monkeypatch, tmp_path)
    kit = make_kit(tmp_path)
    (kit / "PROVENANCE.json").unlink()
    (kit / "LEC_TOOL.json").write_text(json.dumps({"commit": BUILD}))     # the tool's commit, not the build
    register(ap, kit)
    AR.step(ap)
    assert only_item(ap)["status"] == "LANE" and "NO-BUILD-COMMIT" in only_item(ap)["why"] and not ap.launched
    assert any("NO-BUILD-COMMIT" in x for x in ap.lines)


def test_commit_the_hub_does_not_have_is_no_proof(ap, tmp_path, monkeypatch):
    roots_ok(monkeypatch, tmp_path)
    kit = make_kit(tmp_path)
    (kit / "PROVENANCE.json").write_text(json.dumps({"build_commit": "ee" * 20}))
    register(ap, kit)
    AR.step(ap)
    assert "NO-BUILD-COMMIT" in only_item(ap)["why"]


def test_row_commit_is_used(ap, tmp_path, monkeypatch):
    roots_ok(monkeypatch, tmp_path)
    kit = make_kit(tmp_path)
    (kit / "PROVENANCE.json").unlink()
    register(ap, kit, bc="cd" * 20)
    AR.step(ap)
    assert ap.launched[0][1][ap.launched[0][1].index("--build-commit") + 1] == "cd" * 20


@pytest.mark.parametrize("name,why", [("qkd_hr_core_peer", "HELD"), ("kv_astk_a", "HELD")])
def test_held_designs_never_launch(ap, tmp_path, monkeypatch, name, why):
    roots_ok(monkeypatch, tmp_path)
    register(ap, make_kit(tmp_path, name="dp_" + name), name=name)
    AR.step(ap)
    assert only_item(ap)["status"] == "SKIP" and why in only_item(ap)["why"] and not ap.launched


@pytest.mark.parametrize("text", ["", "# only a comment\n"])
def test_empty_hold_file_stops_every_launch(ap, tmp_path, monkeypatch, text):
    roots_ok(monkeypatch, tmp_path)
    register(ap, make_kit(tmp_path))
    (ap.coord / AR.HOLD).write_text(text)
    AR.step(ap)
    assert not ap.launched and "unreadable or empty" in AR.load_state(ap.apd)["blocked"]


def test_stale_cache_stops_launches(ap, tmp_path, monkeypatch):
    roots_ok(monkeypatch, tmp_path)
    register(ap, make_kit(tmp_path))
    c = json.loads(ap.cache.read_text())
    c["generated"] = time.time() - AR.CACHE_MAX_AGE_S - 60
    ap.cache.write_text(json.dumps(c))
    AR.step(ap)
    assert not ap.launched


@pytest.mark.parametrize("how", ["file", "config"])
def test_kill_switch(ap, tmp_path, monkeypatch, how):
    roots_ok(monkeypatch, tmp_path)
    register(ap, make_kit(tmp_path))
    if how == "file":
        (ap.apd / "auto_resign.stop").write_text("")
    else:
        (ap.apd / "kit_wave.json").write_text(json.dumps({"auto_resign": False}))
    AR.step(ap)
    assert not ap.launched


def test_already_credited_is_skipped(ap, tmp_path, monkeypatch):
    roots_ok(monkeypatch, tmp_path)
    register(ap, make_kit(tmp_path))
    c = json.loads(ap.cache.read_text())
    c["plans"]["p"]["signed_types"] = {"x": ["host:rec"]}
    ap.cache.write_text(json.dumps(c))
    AR.step(ap)
    assert only_item(ap)["status"] == "SKIP" and not ap.launched


def test_revoked_netlist_and_view(ap, tmp_path, monkeypatch):
    roots_ok(monkeypatch, tmp_path)
    kit = make_kit(tmp_path)
    register(ap, kit)
    import hashlib
    sha = hashlib.sha256(next(kit.rglob("6_final.v")).read_bytes()).hexdigest()
    (ap.coord / AR.REVOKED).write_text("kv\tx\tsha256:%s\tmeasured FAIL\t2026-11-03\n" % sha)
    AR.step(ap)
    assert "COUNT-REVOKED" in only_item(ap)["why"] and not ap.launched
    assert AR.revoked_hit("head\tx\th1:%s\tr\td\n" % tmp_path, "h1", str(kit), "") and not AR.revoked_hit("head\tx\th2:%s\tr\td\n" % tmp_path, "h1", str(kit), "")


def test_retired_by_name_is_judged_on_the_original_date(ap, tmp_path, monkeypatch):
    roots_ok(monkeypatch, tmp_path)
    register(ap, make_kit(tmp_path))
    (ap.coord / AR.RETIRED).write_text("name:%s:x\t2026-11-04 02:00\tL\tsuperseded\n" % DIE)
    AR.step(ap)
    assert "RETIRED" in only_item(ap)["why"] and not ap.launched


def test_built_after_the_retire_date_passes(ap, tmp_path, monkeypatch):
    roots_ok(monkeypatch, tmp_path)
    register(ap, make_kit(tmp_path))
    (ap.coord / AR.RETIRED).write_text("name:%s:x\t2026-11-03 02:00\tL\tsuperseded\n" % DIE)
    AR.step(ap)
    assert only_item(ap)["status"] == "RUNNING"


def test_copy_of_a_retired_record(ap, tmp_path, monkeypatch):
    roots_ok(monkeypatch, tmp_path)
    register(ap, make_kit(tmp_path))
    c = json.loads(ap.cache.read_text())
    c["retired_records"] = [{"path": "h:/old", "name": "dp_x", "top": "top_x", "generated": "2026-11-04T01:00:00-08:00"}]
    ap.cache.write_text(json.dumps(c))
    AR.step(ap)
    assert "copy of" in only_item(ap)["why"]


def test_record_of_another_design_is_not_run(ap, tmp_path, monkeypatch):
    roots_ok(monkeypatch, tmp_path)
    register(ap, make_kit(tmp_path), name="y")
    AR.step(ap)
    assert only_item(ap)["status"] == "LANE" and not ap.launched


def _collect(ap, res, client=None):
    ap.parse_client_log = lambda t: client or {"exit": 0}
    orig = ap.rpy

    def rpy(host, code, args, timeout=600):
        return res if code == AR.PROBE_RESULT else orig(host, code, args, timeout)
    ap.rpy = rpy


def test_recorded_then_quiet(ap, tmp_path, monkeypatch):
    roots_ok(monkeypatch, tmp_path)
    register(ap, make_kit(tmp_path))
    AR.step(ap)
    _collect(ap, dict(prov=dict(kind="resign", flow_tag=TAG, lec_verdict="EQUIVALENT"), signoff=dict(verdict="SIGNED", tt=1, ff=2), lec=dict(verdict="EQUIVALENT")))
    n = len(ap.launched)
    AR.step(ap)
    assert only_item(ap)["status"] == "RECORDED" and any("RECORDED" in x for x in ap.lines)
    AR.step(ap)
    assert len(ap.launched) == n


def test_failed_is_not_retried_on_a_tag_with_the_same_tools(ap, tmp_path, monkeypatch):
    roots_ok(monkeypatch, tmp_path)
    register(ap, make_kit(tmp_path))
    AR.step(ap)
    _collect(ap, dict(signoff=dict(verdict="NOT SIGNED", local="NOT SIGNED", tt=-3, ff=1, reasons=["setup_tt"])))
    AR.step(ap)
    assert only_item(ap)["status"] == "LANE" or only_item(ap)["status"] == "FAILED"
    ap.flow_tags = lambda die=None: ["flow-20261104-h-kv"]    # same signoff.py + lec.py bytes (fake_hub)
    n = len(ap.launched)
    AR.step(ap)
    AR.step(ap)
    assert len(ap.launched) == n and "not retried" in only_item(ap)["why"]


def test_failed_reruns_when_the_checker_changed(ap, tmp_path, monkeypatch):
    roots_ok(monkeypatch, tmp_path)
    kit = make_kit(tmp_path)
    register(ap, kit)
    AR.step(ap)
    _collect(ap, dict(signoff=dict(verdict="SIGNED", tt=1, ff=1), lec=dict(verdict="NON-EQUIVALENT", reason="x")))
    AR.step(ap)
    assert "LEC" in only_item(ap)["why"]
    monkeypatch.setattr(AR, "tag_shas", lambda A, tag: {f: "1" * 64 for f in AR.TAG_TOOL_FILES})
    ap.flow_tags = lambda die=None: ["flow-20261104-h-kv"]
    n = len(ap.launched)
    AR.step(ap)
    assert len(ap.launched) == n + 1
    out = ap.launched[-1][1][ap.launched[-1][1].index("--out") + 1]
    assert "flow-20261104-h-kv" in out                       # the failed dir stays as evidence


def test_infra_relaunches_once_with_more_memory_after_oom(ap, tmp_path, monkeypatch):
    roots_ok(monkeypatch, tmp_path)
    register(ap, make_kit(tmp_path))
    AR.step(ap)
    _collect(ap, {"oom": "lec.log"})
    AR.step(ap)                                   # collected: relaunch in the same pass
    assert len(ap.launched) == 2
    argv = ap.launched[1][1]
    assert argv[argv.index("--mem") + 1] == "48"
    assert argv[argv.index("--out") + 1].endswith("_a2")     # first dir stays
    AR.step(ap)                                   # second OOM: no further automatic relaunch
    assert len(ap.launched) == 2 and only_item(ap)["status"] in ("FAILED", "LANE")


def test_retracted_tag_is_a_candidate_again(ap, tmp_path, monkeypatch):
    roots_ok(monkeypatch, tmp_path)
    register(ap, make_kit(tmp_path))
    AR.step(ap)
    _collect(ap, dict(prov=dict(kind="resign", flow_tag=TAG, lec_verdict="EQUIVALENT")))
    AR.step(ap)
    ap.flow_tags = lambda die=None: ["flow-20261104-f-kv"]
    AR.step(ap)
    assert len(ap.launched) == 2 and "flow-20261104-f-kv" in ap.launched[1][1]


def test_wave_candidate_needs_a_current_plan_row(tmp_path):
    so = {"path": "/k/signoff/signoff.json"}
    jobs = {"a": dict(id="a", status="WAIT-PARENT", die=DIE, type="x", path="/k", probe="h", src="main@" + BUILD, signoff=so),
            "b": dict(id="b", status="WAIT-PARENT", die=DIE, type="y", path="/old", probe="h", src="main@" + BUILD, signoff=so),
            "c": dict(id="c", status="SIGNED", die=DIE, type="z", path="/k", probe="h", signoff=so),
            "d": dict(id="d", status="WAIT-PARENT", die=DIE, type="w", path="/lane", probe="h", signoff=so)}
    tsv = "die\titem\tkit\tplan_current\n%s\tx\th:/k\tyes\n%s\ty\th:/old\tno\n" % (DIE, DIE)
    got = AR.wave_candidates(jobs, AR.wave_kits(tsv))
    assert [c["name"] for c in got] == ["x"] and got[0]["path"] == "/k"


def test_counter_suggestions_are_written_never_run(ap, tmp_path, monkeypatch):
    roots_ok(monkeypatch, tmp_path)
    c = json.loads(ap.cache.read_text())
    c["plans"]["p"]["unversioned_types"] = {"z": ["h:/x/signoff.json no flow tag"]}
    ap.cache.write_text(json.dumps(c))
    AR.step(ap)
    assert not ap.launched and "\tz\t" in (ap.apd / AR.SUGGEST).read_text()


def test_launch_cap_per_tick(ap, tmp_path, monkeypatch):
    roots_ok(monkeypatch, tmp_path)
    rows = ""
    for i in range(AR.MAX_LAUNCH_PER_TICK + 3):
        (tmp_path / str(i)).mkdir()
        make_kit(tmp_path / str(i), name="dp_x%d" % i)
        rows += "%s\tx%d\th\t%s/%d/kit\t-\tL\tn\n" % (DIE, i, tmp_path, i)
    (ap.coord / AR.REGISTRY).write_text(rows)
    AR.step(ap)
    assert len(ap.launched) == AR.MAX_LAUNCH_PER_TICK


def test_dry_launches_nothing(ap, tmp_path, monkeypatch):
    roots_ok(monkeypatch, tmp_path)
    register(ap, make_kit(tmp_path))
    ap.DRY = True
    AR.step(ap)
    assert not ap.launched


# ---------------------------------------------------------------- near-miss late-ECO (item 2)
def eco_kit(root, tt=5.0, ff=-1.5, drc=0, fails=("hold_ff",), name="dp_x"):
    kit = make_kit(root, name=name, verdict="NOT SIGNED")
    p = kit / "signoff" / "signoff.json"
    d = json.loads(p.read_text())
    d["local_verdict"] = "NOT SIGNED"
    d["checks"] = {"setup_tt": {"wns_ps": tt, "verdict": "FAIL" if "setup_tt" in fails else "PASS"},
                   "hold_ff": {"wns_ps": ff, "verdict": "FAIL" if "hold_ff" in fails else "PASS"},
                   "drc": {"count": drc, "verdict": "FAIL" if "drc" in fails else "PASS"}}
    for f in fails:
        d["checks"].setdefault(f, {"verdict": "FAIL"})
    p.write_text(json.dumps(d))
    return kit


def test_near_miss_enters_the_loop_once(ap, tmp_path, monkeypatch):
    roots_ok(monkeypatch, tmp_path)
    monkeypatch.setattr(AR, "ECO_DISK_GB", 0)
    register(ap, eco_kit(tmp_path))
    ap.unit_active = lambda u: True
    AR.step(ap)
    it = only_item(ap)
    assert it["status"] == "ECO"
    argv = ap.launched[0][1]
    i = argv.index("--")
    assert argv[i + 3].endswith("/tools/die_plan/eco_loop.py") and argv[i + 4] == "run" and "--crit" in argv
    assert "--hold-margin" not in argv and "--max-iter" not in argv     # the tool's own limits
    AR.step(ap)
    assert len(ap.launched) == 1


@pytest.mark.parametrize("kw,word", [(dict(tt=-40.0, fails=("setup_tt",)), "bound"), (dict(ff=-31.0), "bound"), (dict(drc=51, fails=("drc",)), "bound"),
                                     (dict(fails=("hold_ff", "clock")), "ECO class"), (dict(fails=("antenna",)), "ECO class")])
def test_outside_the_approved_class_is_not_touched(ap, tmp_path, monkeypatch, kw, word):
    roots_ok(monkeypatch, tmp_path)
    monkeypatch.setattr(AR, "ECO_DISK_GB", 0)
    register(ap, eco_kit(tmp_path, **kw))
    AR.step(ap)
    assert only_item(ap)["status"] == "SKIP" and word in only_item(ap)["why"] and not ap.launched


def test_held_design_gets_no_eco(ap, tmp_path, monkeypatch):
    roots_ok(monkeypatch, tmp_path)
    monkeypatch.setattr(AR, "ECO_DISK_GB", 0)
    register(ap, eco_kit(tmp_path, name="dp_kv_astk_a"), name="kv_astk_a")
    AR.step(ap)
    assert "HELD" in only_item(ap)["why"] and not ap.launched


def _hand_loop(kit, base, best=None, loop_kit=None):
    """kit is the best iteration of a finished hand loop ROOT/iN"""
    rec = kit / "signoff" / "signoff.json"
    best = best or json.loads(rec.read_text())
    (kit.parent / "eco_loop.json").write_text(json.dumps(dict(verdict="EXHAUSTED", kit=str(loop_kit or "/none/k"),
                                                              base_metrics=base, best=dict(signoff=str(rec), metrics=best))))


NEAR = dict(tt=5.0, ff=-1.5, drv=0, drc=0, fails=["hold_ff"])


@pytest.mark.parametrize("base,best", [
    (dict(tt=5.0, ff=-9.0, drv=0, drc=0), NEAR),                                                        # ended near, improved
    (dict(tt=5.0, ff=0.0, drv=9, drc=0), dict(tt=5.0, ff=0.0, drv=3, drc=0, fails=["drv"])),            # DRV-only
    (dict(tt=5.0, ff=-1.5, drv=0, drc=0), NEAR),                                                        # no gain
])
def test_no_second_loop_on_a_hand_loop(ap, tmp_path, monkeypatch, base, best):
    """OWNER 11-07 05:3x: one late-stage iteration per routed form"""
    roots_ok(monkeypatch, tmp_path)
    monkeypatch.setattr(AR, "ECO_DISK_GB", 0)
    kit = eco_kit(tmp_path)
    _hand_loop(kit, base, best)
    register(ap, kit)
    AR.step(ap)
    it = only_item(ap)
    assert it["status"] == "LANE" and "no second loop" in it["why"] and "REDESIGN" in it["why"] and not ap.launched
    assert any("no second loop" in x for x in ap.lines)


def test_loop_that_started_from_this_db_stays_for_a_lane(ap, tmp_path, monkeypatch):
    roots_ok(monkeypatch, tmp_path)
    monkeypatch.setattr(AR, "ECO_DISK_GB", 0)
    kit = eco_kit(tmp_path)
    odb = next(kit.rglob("6_final.odb"))
    (tmp_path / "it2").mkdir()
    best = eco_kit(tmp_path / "it2", ff=-0.5)
    rec = best / "signoff" / "signoff.json"
    (kit / "eco_1").mkdir()
    (kit / "eco_1" / "eco_loop.json").write_text(json.dumps(dict(kit=str(kit), base_routed_db=str(odb), base_metrics=dict(tt=5.0, ff=-1.5, drv=0, drc=0),
                                                                 best=dict(signoff=str(rec), metrics=dict(tt=5.0, ff=-0.5, drv=0, drc=0, fails=["hold_ff"])))))
    register(ap, kit)
    AR.step(ap)
    assert only_item(ap)["status"] == "LANE" and "no second loop" in only_item(ap)["why"] and not ap.launched


@pytest.mark.parametrize("how", ["empty", "garbled"])
def test_unreadable_loop_stays_for_a_lane(ap, tmp_path, monkeypatch, how):
    roots_ok(monkeypatch, tmp_path)
    monkeypatch.setattr(AR, "ECO_DISK_GB", 0)
    kit = eco_kit(tmp_path)
    (kit.parent / "eco_loop.json").write_text("{}" if how == "empty" else "{not json")
    register(ap, kit)
    AR.step(ap)
    assert only_item(ap)["status"] == "LANE" and "not readable" in only_item(ap)["why"] and not ap.launched


def test_held_design_gets_no_second_loop(ap, tmp_path, monkeypatch):
    roots_ok(monkeypatch, tmp_path)
    monkeypatch.setattr(AR, "ECO_DISK_GB", 0)
    kit = eco_kit(tmp_path, name="dp_kv_astk_a")
    _hand_loop(kit, dict(tt=5.0, ff=-9.0, drv=0, drc=0), NEAR)
    register(ap, kit, name="kv_astk_a")
    AR.step(ap)
    assert "HELD" in only_item(ap)["why"] and not ap.launched


def test_own_loop_runs_once_then_goes_to_a_lane(ap, tmp_path, monkeypatch):
    roots_ok(monkeypatch, tmp_path)
    monkeypatch.setattr(AR, "ECO_DISK_GB", 0)
    register(ap, eco_kit(tmp_path, ff=-9.0))
    AR.step(ap)
    assert len(ap.launched) == 1
    out1 = tmp_path / "loop1"
    (out1).mkdir()
    i1 = eco_kit(out1, ff=-1.5)
    next(i1.rglob("6_final.odb")).write_bytes(b"odb after loop 1")
    (i1.parent / "eco_loop.json").write_text(json.dumps(dict(kit="/none/k", base_metrics=dict(tt=5.0, ff=-9.0, drv=0, drc=0),
                                                             best=dict(signoff=str(i1 / "signoff" / "signoff.json"), metrics=NEAR))))
    _eco_result(ap, dict(verdict="EXHAUSTED", reason="no gain", best_signoff=str(i1 / "signoff" / "signoff.json"), best_dir=str(i1), metrics=dict(tt=5.0, ff=-1.5, drv=0, drc=0)))
    AR.step(ap)
    assert len(ap.launched) == 1 and only_item(ap)["status"] == "LANE" and "no second loop" in only_item(ap)["why"]


@pytest.mark.parametrize("kw,launch", [(dict(ff=-9.0, ff_n=101.0), False), (dict(ff=-9.0, ff_n=100.0), True), (dict(drc=50, fails=("drc",)), False)])
def test_near_miss_counts_endpoints_and_drc_under_50(ap, tmp_path, monkeypatch, kw, launch):
    roots_ok(monkeypatch, tmp_path)
    monkeypatch.setattr(AR, "ECO_DISK_GB", 0)
    n = kw.pop("ff_n", None)
    kit = eco_kit(tmp_path, **kw)
    if n is not None:
        rec = kit / "signoff" / "signoff.json"
        d = json.loads(rec.read_text())
        d["checks"]["hold_ff"]["violators"] = n
        rec.write_text(json.dumps(d))
    register(ap, kit)
    ap.unit_active = lambda u: True
    AR.step(ap)
    assert bool(ap.launched) == launch and only_item(ap)["status"] == ("ECO" if launch else "SKIP")


@pytest.mark.parametrize("core,launch", [(dict(core_n=10.0, core_wns=-8.0), True), (dict(core_n=200.0, core_wns=-8.0), False), (dict(core_n=10.0, core_wns=-34.0), False)])
def test_near_miss_scores_core_split_of_a_mixed_record(ap, tmp_path, monkeypatch, core, launch):
    """COORD R4: the probe reads the FF census split, so a mixed record is judged on the endpoints sign-off leaves to the core"""
    roots_ok(monkeypatch, tmp_path)
    monkeypatch.setattr(AR, "ECO_DISK_GB", 0)
    kit = eco_kit(tmp_path, ff=-34.0)
    rec = kit / "signoff" / "signoff.json"
    d = json.loads(rec.read_text())
    d["checks"]["hold_ff"]["violators"] = 2100.0
    rec.write_text(json.dumps(d))
    (kit / "signoff" / "ff").mkdir(exist_ok=True)
    (kit / "signoff" / "ff" / "corner.json").write_text(json.dumps(dict(std_min_start=dict(core, err=0, trunc=0, oport=2000.0, nonport_n=2090.0, nonport_wns=-34.0))))
    register(ap, kit)
    ap.unit_active = lambda u: True
    AR.step(ap)
    assert bool(ap.launched) == launch and only_item(ap)["status"] == ("ECO" if launch else "SKIP")


def _eco_result(ap, r):
    orig = ap.rpy

    def rpy(host, code, args, timeout=600):
        return r if code == AR.PROBE_ECO_RESULT else orig(host, code, args, timeout)
    ap.rpy = rpy


def test_pass_goes_to_the_re_sign_on_the_best_dir(ap, tmp_path, monkeypatch):
    roots_ok(monkeypatch, tmp_path)
    monkeypatch.setattr(AR, "ECO_DISK_GB", 0)
    register(ap, eco_kit(tmp_path))
    AR.step(ap)
    (tmp_path / "root").mkdir()
    best = make_kit(tmp_path / "root")
    _eco_result(ap, dict(verdict="PASS", best_dir=str(best), best_signoff=str(best / "signoff" / "signoff.json"), metrics=dict(tt=5, ff=0.1, drv=0, drc=0)))
    AR.step(ap)
    assert only_item(ap)["status"] == "RUNNING"
    argv = ap.launched[-1][1]
    assert "--auto" in argv and argv[argv.index("--routed-db") + 1].startswith(str(best))


def test_loop_with_no_best_record_stays_for_a_lane(ap, tmp_path, monkeypatch):
    roots_ok(monkeypatch, tmp_path)
    monkeypatch.setattr(AR, "ECO_DISK_GB", 0)
    register(ap, eco_kit(tmp_path))
    AR.step(ap)
    _eco_result(ap, dict(verdict="EXHAUSTED", reason="no gain", metrics=dict(tt=5, ff=-0.1, drv=0, drc=0)))
    AR.step(ap)
    n = len(ap.launched)
    AR.step(ap)
    assert only_item(ap)["status"] == "LANE" and "no best record" in only_item(ap)["why"] and len(ap.launched) == n == 1
    assert any("EXHAUSTED" in x for x in ap.lines)


def test_eco_oom_relaunches_once_at_more_memory(ap, tmp_path, monkeypatch):
    roots_ok(monkeypatch, tmp_path)
    monkeypatch.setattr(AR, "ECO_DISK_GB", 0)
    register(ap, eco_kit(tmp_path))
    AR.step(ap)
    _eco_result(ap, dict(verdict="ECO_OOM", metrics={}))
    AR.step(ap)
    assert len(ap.launched) == 2
    assert ap.launched[1][1][ap.launched[1][1].index("--mem") + 1] == "96" and ap.launched[1][1][ap.launched[1][1].index("--out") + 1].endswith("_a2")
    AR.step(ap)
    assert len(ap.launched) == 2 and only_item(ap)["status"] == "LANE"



def test_eco_aborted_relaunches_once_at_same_memory(ap, tmp_path, monkeypatch):
    """KW-FIX-24 11-06: a loop stopped from outside (docker stop, no OOM line) is infra: one relaunch, --mem kept"""
    roots_ok(monkeypatch, tmp_path)
    monkeypatch.setattr(AR, "ECO_DISK_GB", 0)
    register(ap, eco_kit(tmp_path))
    AR.step(ap)
    mem0 = ap.launched[0][1][ap.launched[0][1].index("--mem") + 1]
    _eco_result(ap, dict(verdict="ABORTED", reason="ECO m0 session stopped from outside (rc 137)", metrics={}))
    AR.step(ap)
    assert len(ap.launched) == 2                                   # relaunched (was: LANE, no relaunch)
    assert ap.launched[1][1][ap.launched[1][1].index("--mem") + 1] == mem0
    AR.step(ap)
    assert len(ap.launched) == 2 and only_item(ap)["status"] == "LANE"


def test_eco_cap(ap, tmp_path, monkeypatch):
    roots_ok(monkeypatch, tmp_path)
    monkeypatch.setattr(AR, "ECO_DISK_GB", 0)
    monkeypatch.setattr(AR, "MAX_LAUNCH_PER_TICK", 99)
    rows = ""
    for i in range(AR.MAX_ECO_INFLIGHT + 2):
        (tmp_path / str(i)).mkdir()
        eco_kit(tmp_path / str(i), name="dp_x%d" % i)
        rows += "%s\tx%d\th\t%s/%d/kit\t-\tL\tn\n" % (DIE, i, tmp_path, i)
    (ap.coord / AR.REGISTRY).write_text(rows)
    ap.unit_active = lambda u: True
    AR.step(ap)
    assert len(ap.launched) == AR.MAX_ECO_INFLIGHT


def test_hub_kit_uses_the_name_ot_run_knows(ap, tmp_path, monkeypatch):
    roots_ok(monkeypatch, tmp_path)
    ap.ssh_host = lambda h: "localhost" if h == "intel2" else h
    register(ap, make_kit(tmp_path), host="intel2")
    AR.step(ap)
    argv = ap.launched[0][1]
    assert argv[argv.index("--hosts") + 1] == "localhost"


def test_stage_tools_leaves_a_ready_export_alone(ap, monkeypatch):
    monkeypatch.undo()
    calls = []

    def sh(cmd, timeout=300, input=None):
        calls.append(cmd)
        return (0, "", "")
    ap.sh = sh
    d, err = AR.stage_tools(ap, "h1", "/r", "flow-20261104-h-kv", {})
    assert d == "/r/claude/auto-resign/tools/flow-20261104-h-kv" and not err
    assert len(calls) == 1 and "test -f" in calls[0][-1]


# ---------------------------------------------------------------- one row's error never ends the pass (ROOT-MERGE-30 07:05)
def rows(ap, tmp_path, *names, kit=make_kit):
    text = "# die name host dir build lane note\n"
    for n in names:
        (tmp_path / n).mkdir()
        text += "%s\t%s\th1\t%s\t-\tDIE-KV\tpilot\n" % (DIE, n, kit(tmp_path / n, name="dp_" + n))
    (ap.coord / AR.REGISTRY).write_text(text)


def items_by_name(ap):
    return {it["name"]: it for it in AR.load_state(ap.apd)["items"].values()}


def raising_for(ap, name, code=None):
    """the host probe raises for one row until the returned switch is cleared"""
    orig, on = ap.rpy, {"on": True}

    def rpy(host, c, args, timeout=600):
        if on["on"] and "/%s/" % name in json.dumps(args) + "/" and (code is None or c == code):
            raise ValueError("injected on " + name)
        return orig(host, c, args, timeout)
    ap.rpy = rpy
    return on


def logged(ap):
    got = []
    ap.log = got.append
    return got


def test_raise_after_a_launch_loses_nothing_and_the_pass_goes_on(ap, tmp_path, monkeypatch):
    roots_ok(monkeypatch, tmp_path)
    rows(ap, tmp_path, "a", "b", "c")
    on, log = raising_for(ap, "b"), logged(ap)
    ap.unit_active = lambda u: True
    AR.step(ap)
    it = items_by_name(ap)
    assert it["a"]["status"] == "RUNNING" and it["c"]["status"] == "RUNNING" and it["b"]["status"] == "NEW" and "attempt" not in it["b"]
    assert len(ap.launched) == 2 and any("ROW-SKIP" in x and "/b:" in x and "ValueError" in x for x in log)
    on["on"] = False                                 # next pass takes b, and only b
    AR.step(ap)
    assert [u for u, _ in ap.launched].count(it["a"]["unit"]) == 1 and len(ap.launched) == 3
    assert items_by_name(ap)["b"]["status"] == "RUNNING"


def test_launched_row_is_on_disk_before_the_next_row(ap, tmp_path, monkeypatch):
    roots_ok(monkeypatch, tmp_path)
    rows(ap, tmp_path, "a", "b")
    seen = []
    launched = ap.launch_unit

    def launch_unit(unit, log, argv):
        seen.append({k["name"]: k["status"] for k in AR.load_state(ap.apd)["items"].values()})
        return launched(unit, log, argv)
    ap.launch_unit = launch_unit
    ap.unit_active = lambda u: True
    AR.step(ap)
    assert len(seen) == 2 and seen[1]["a"] == "RUNNING"


def test_kill_mid_pass_keeps_the_launched_row(ap, tmp_path, monkeypatch):
    roots_ok(monkeypatch, tmp_path)
    rows(ap, tmp_path, "a", "b")
    orig = ap.rpy

    def rpy(host, c, args, timeout=600):
        if "/b/" in json.dumps(args):
            raise KeyboardInterrupt()                # not an Exception: the row guard lets it through
        return orig(host, c, args, timeout)
    ap.rpy = rpy
    ap.unit_active = lambda u: True
    with pytest.raises(KeyboardInterrupt):
        AR.step(ap)
    assert items_by_name(ap)["a"]["status"] == "RUNNING"


def test_raise_after_the_unit_started_keeps_the_row_on_record(ap, tmp_path, monkeypatch):
    roots_ok(monkeypatch, tmp_path)
    rows(ap, tmp_path, "a", "b")
    orig = ap.log

    def log(m):
        if "LAUNCH" in m and "/a " in m:
            raise OSError("log disk full")
        orig(m)
    ap.log = log
    ap.unit_active = lambda u: True
    AR.step(ap)
    it = items_by_name(ap)
    assert it["a"]["status"] == "RUNNING" and it["a"]["attempt"] == 1 and it["b"]["status"] == "RUNNING"
    AR.step(ap)
    assert len(ap.launched) == 2


def test_raise_after_an_eco_launch_loses_nothing(ap, tmp_path, monkeypatch):
    roots_ok(monkeypatch, tmp_path)
    monkeypatch.setattr(AR, "ECO_DISK_GB", 0)
    rows(ap, tmp_path, "a", "b", kit=eco_kit)
    raising_for(ap, "b")
    ap.unit_active = lambda u: True
    AR.step(ap)
    it = items_by_name(ap)
    assert it["a"]["status"] == "ECO" and it["a"]["eco_unit"] and it["b"]["status"] == "NEW" and len(ap.launched) == 1


def test_poll_row_raise_leaves_it_running_and_keeps_the_others(ap, tmp_path, monkeypatch):
    roots_ok(monkeypatch, tmp_path)
    rows(ap, tmp_path, "a", "b")
    ap.unit_active = lambda u: True
    AR.step(ap)
    st = AR.load_state(ap.apd)
    names = {it["name"]: it for it in st["items"].values()}
    orig, log = ap.rpy, logged(ap)
    on = {"on": True}

    def rpy(host, c, args, timeout=600):
        if c == AR.PROBE_RESULT:
            if on["on"] and args["out"] == names["b"]["out"]:
                raise ValueError("injected")
            return dict(signoff=dict(verdict="SIGNED", tt=1, ff=1), lec=dict(verdict="EQUIVALENT"), provenance=True)
        return orig(host, c, args, timeout)
    ap.rpy = rpy
    monkeypatch.setattr(AR, "classify", lambda client, res, tag: ("RECORDED", ""))
    ap.unit_active = lambda u: False
    AR.step(ap)
    it = items_by_name(ap)
    assert it["a"]["status"] == "RECORDED" and it["b"]["status"] == "RUNNING"
    assert any("/a RECORDED" in x for x in ap.lines) and not any("/b RECORDED" in x for x in ap.lines)
    assert any("ROW-SKIP" in x and "/b:" in x for x in log)
    on["on"] = False
    AR.step(ap)
    assert items_by_name(ap)["b"]["status"] == "RECORDED"


def test_poll_row_raise_after_changes_restores_the_row(ap, tmp_path, monkeypatch):
    roots_ok(monkeypatch, tmp_path)
    rows(ap, tmp_path, "a")
    ap.unit_active = lambda u: True
    AR.step(ap)
    orig = ap.rpy
    ap.rpy = lambda host, c, args, timeout=600: dict(signoff={}, lec={}) if c == AR.PROBE_RESULT else orig(host, c, args, timeout)
    monkeypatch.setattr(AR, "classify", lambda client, res, tag: ("RECORDED", ""))
    ap.unit_active = lambda u: False

    def boom(*a):
        raise OSError("tsv")
    ap.tsv_append = boom
    n = len(ap.launched)
    AR.step(ap)
    assert items_by_name(ap)["a"]["status"] == "RUNNING" and "finished" not in items_by_name(ap)["a"]
    assert not any("RECORDED" in x for x in ap.lines) and len(ap.launched) == n


def test_poll_eco_row_raise_leaves_it_on_eco_and_keeps_the_others(ap, tmp_path, monkeypatch):
    roots_ok(monkeypatch, tmp_path)
    monkeypatch.setattr(AR, "ECO_DISK_GB", 0)
    rows(ap, tmp_path, "a", "b", kit=eco_kit)
    ap.unit_active = lambda u: True
    AR.step(ap)
    names = items_by_name(ap)
    assert names["a"]["status"] == names["b"]["status"] == "ECO"
    orig, log = ap.rpy, logged(ap)

    def rpy(host, c, args, timeout=600):
        if c == AR.PROBE_ECO_RESULT:
            if args["out"] == names["b"]["eco_out"]:
                raise ValueError("injected")
            return dict(verdict="NOT_ELIGIBLE", reason="r", metrics={})
        return orig(host, c, args, timeout)
    ap.rpy = rpy
    ap.unit_active = lambda u: False
    AR.step(ap)
    it = items_by_name(ap)
    assert it["a"]["status"] == "LANE" and it["b"]["status"] == "ECO" and any("ROW-SKIP" in x for x in log)
    assert any("/a late-ECO" in x for x in ap.lines)


def test_raise_outside_the_rows_saves_state_and_notices(ap, tmp_path, monkeypatch):
    roots_ok(monkeypatch, tmp_path)
    rows(ap, tmp_path, "a")
    ap.unit_active = lambda u: True
    AR.step(ap)
    orig = ap.rpy
    ap.rpy = lambda host, c, args, timeout=600: dict(signoff={}, lec={}) if c == AR.PROBE_RESULT else orig(host, c, args, timeout)
    monkeypatch.setattr(AR, "classify", lambda client, res, tag: ("RECORDED", ""))
    ap.unit_active = lambda u: False

    def boom(*a):
        raise ValueError("candidates")
    monkeypatch.setattr(AR, "candidates", boom)
    with pytest.raises(ValueError):                  # the tick hook logs this one
        AR.step(ap)
    assert only_item(ap)["status"] == "RECORDED" and any("RECORDED" in x for x in ap.lines)


# ---------------------------------------------------------------- KW-FIX-32 11-07: every die's newest tag staged on landing
def test_prestage_exports_newest_tag_on_every_host_once(ap, tmp_path, monkeypatch):
    root = tmp_path / "scr"
    (root / "claude").mkdir(parents=True)
    monkeypatch.setattr(AR, "ROOTS", (str(tmp_path / "missing"), str(root)))
    staged = []
    monkeypatch.setattr(AR, "stage_tools", lambda AP, host, r, tag, s: staged.append((host, r, tag)) or ("%s/t/%s" % (r, tag), ""))
    status = "ot-run status: epyc2 REFUSED (ROOT FS 96%) | intel1 admits 257 GB load 76/112 | localhost admits 657 GB | next job -> intel1"
    ap.sh = lambda cmd, timeout=300, input=None: (0, status, "") if "--status" in cmd else (0, "", "")
    tags = {"qwen_kvsys": "flow-20261107-dh-kv", "s81": "flow-20261107-ds-s81"}
    shas = {t: {"tools/die_plan/signoff.py": "0" * 64} for t in tags.values()}
    ctx = dict(tag=lambda die: tags.get(die), tool_key=lambda t: "k", shas=shas)
    st = {}
    out = AR.prestage(ap, st, ctx)
    assert sorted(staged) == sorted((h, str(root), t) for h in ("epyc2", "intel1", "localhost") for t in tags.values())
    assert all(w.startswith(str(root)) for _, _, w in out) and len(st["prestaged"]) == 6
    staged.clear()
    assert AR.prestage(ap, st, ctx) == [] and staged == []                      # once per host and tag
    tags["qwen_kvsys"] = "flow-20261107-dj-kv"                                  # a new tag lands
    shas["flow-20261107-dj-kv"] = {"tools/die_plan/signoff.py": "1" * 64}
    AR.prestage(ap, st, ctx)
    assert sorted(staged) == sorted((h, str(root), "flow-20261107-dj-kv") for h in ("epyc2", "intel1", "localhost"))


def test_prestage_budget_dry_off_and_no_root(ap, tmp_path, monkeypatch):
    staged = []
    monkeypatch.setattr(AR, "stage_tools", lambda AP, host, r, tag, s: staged.append(host) or ("/d", ""))
    ctx = dict(tag=lambda die: "flow-20261107-dh-kv" if die == "qwen_kvsys" else None, tool_key=lambda t: "k",
               shas={"flow-20261107-dh-kv": {"x": "0"}})
    monkeypatch.setattr(AR, "ROOTS", ())
    out = AR.prestage(ap, {}, ctx, hosts=["h1"])
    assert staged == [] and "no scratch root" in out[0][2]                       # nothing with room: not staged
    root = tmp_path / "scr"
    (root / "claude").mkdir(parents=True)
    monkeypatch.setattr(AR, "ROOTS", (str(root),))
    monkeypatch.setattr(AR, "PRESTAGE_MAX_PER_TICK", 2)
    st = {}
    AR.prestage(ap, st, ctx, hosts=["h1", "h2", "h3"])
    assert staged == ["h1", "h2"]                                                # budget: h3 next pass
    AR.prestage(ap, st, ctx, hosts=["h1", "h2", "h3"])
    assert staged == ["h1", "h2", "h3"]
    ap.DRY = True
    assert AR.prestage(ap, {}, ctx, hosts=["h9"]) == []
    ap.DRY = False
    monkeypatch.setenv("OT_AR_PRESTAGE", "0")
    assert AR.prestage(ap, {}, ctx, hosts=["h9"]) == [] and "h9" not in staged
