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
