"""LATENCY-R 11-18 (COORD 11-18 optimistic launch): publish_apply apply / bind-fail."""
import json
import pytest
import sys
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import publish_apply as PA  # noqa: E402


def coord(tmp_path, die_extra=None):
    c = tmp_path / "coord"
    (c / "autopilot").mkdir(parents=True)
    (c / "lanes/handoff").mkdir(parents=True)
    d = {"src": "/x/old", "event": "E0", "plan_sha256": "s1", "hold_event_items": {"s1": ["cbn_q00", "cbn_q00__cl1", "sle_fe_v1", "slw_st_a_v1"]},
         "owner_lane": "QC-PLAN-R3"}
    d.update(die_extra or {})
    (c / "autopilot/kit_wave.json").write_text(json.dumps({"dies": {"qc": d}}))
    return c


def test_types_from_log_matches_whole_plan_item_names():
    items = ["cbn_q00", "cbn_q00__cl1", "sle_fe_v1", "slw_st_a_v1"]
    log = "BIND ERROR cbn_q00__cl1: port mismatch\nLATCHECK FAIL lane 7 in slw_st_a_v1 (u_lane7)\nok sle_fe_v1x"
    assert PA.types_from_log(log, items) == ["cbn_q00__cl1", "slw_st_a_v1"]


def test_bind_fail_record_holds_only_named_types():
    r = PA.bind_fail_record({"plan_sha256": "s1"}, ["a", "b"], "QC-PLAN-R3", "n3-bind", "x")
    assert r["items"] == ["a", "b"] and r["release"] == ["result:QC-PLAN-R3:n3-bind"] and r["cancel_running"] and r["plan_sha"] == "s1"


def test_bind_fail_dry_prints_patch(tmp_path, capsys, monkeypatch):
    c = coord(tmp_path)
    monkeypatch.setattr(PA.HR, "add_record", lambda cfg, die, rec: rec)
    a = types.SimpleNamespace(coord=str(c), die="qc", lane="QC-PLAN-R3", id="n3", types="sle_fe_v1", log=None, reason="", dry=True)
    assert PA.cmd_bind_fail(a) == 0
    patch = json.loads(capsys.readouterr().out)
    assert patch[0]["path"] == "/dies/qc/hold_records" and patch[0]["value"][0]["items"] == ["sle_fe_v1"]


def test_bind_fail_with_no_named_type_holds_nothing(tmp_path):
    c = coord(tmp_path)
    log = tmp_path / "b.log"
    log.write_text("die-wide elab error")
    a = types.SimpleNamespace(coord=str(c), die="qc", lane="L", id="n3", types="", log=str(log), reason="", dry=False)
    assert PA.cmd_bind_fail(a) == 2


def test_apply_is_optimistic_commits_starts_the_advisory_gate_and_posts(tmp_path):
    c = coord(tmp_path)
    cand = tmp_path / "cand.json"
    cand.write_text(json.dumps({"die": "qc", "tree": "/x/new", "manifest_hash": "a" * 64, "plan": "/p", "plan_sha256": "s2", "hosts": ["epyc9"]}))
    seen = {}

    def apply_fn(C, obj, src, ev, pilot_item=None, optimistic=None):
        seen.update(optimistic=optimistic, obj=obj)
        rcpt = Path(C) / "lanes/handoff/qc_atomic_apply_1.json"
        rcpt.write_text("{}")
        return {"applied": "qc", "event": "N3", "source": "/x/new", "receipt": str(rcpt), "warnings": ["ADVISORY publish_gate: none"], "gen_hosts": ["epyc9"]}
    calls = []

    def run(argv, **k):
        calls.append(argv)
        return types.SimpleNamespace(returncode=0, stdout="", stderr="")
    a = types.SimpleNamespace(coord=str(c), candidate=str(cand), expect_source="/x/old", expect_event="E0", lane="QC-PLAN-R3", pilot_item=None, no_gate=False)
    assert PA.cmd_apply(a, run=run, apply_fn=apply_fn, commit_fn=lambda C, r: "ok") == 0
    assert seen["optimistic"] is True and seen["obj"]["optimistic"] is True
    gate = [x for x in calls if x[0] == "systemd-run"][0]
    assert "--expect-source" in gate and gate[gate.index("--expect-source") + 1] == "/x/new" and gate[gate.index("--expect-event") + 1] == "N3"
    gc = json.loads((c / "lanes/handoff/qc_atomic_apply_1.gate_candidate.json").read_text())
    assert gc["optimistic"] is True
    p = [x for x in calls if x[0] == "bash"][0]
    assert p[2] == "QC-PLAN-R3" and "APPLIED-OPTIMISTIC" in p[3] and "advisory warning" in p[3]


def test_apply_starts_background_precheck_on_first_gen_host(tmp_path):
    """PRECHECK-1119: the estimator runs after the apply on the die's first gen host; --no-precheck turns it off"""
    obj = {"die": "qc", "tree": "/x/new", "plan": "physical/p.json", "hosts": ["epyc9"]}
    res = {"applied": "qc", "event": "N3", "gen_hosts": ["epyc8", "epyc9"]}
    pa = PA.precheck_argv(obj, res, "QC-PLAN-R3", now=5)
    assert pa[:7] == ["timeout", "60", "ssh", "-n", "-o", "ControlPath=none", "epyc8"] and "systemd-run" in pa
    assert pa[pa.index("--plan") + 1] == "/x/new/physical/p.json" and pa[pa.index("--tools") + 1] == "/x/new/tools/die_plan"
    assert pa[pa.index("--owner") + 1] == "QC-PLAN-R3" and pa[pa.index("--unit") + 1] == "precheck-qc-5"
    assert pa[pa.index("--kit-hosts") + 1] == ",".join(res.get("gen_hosts") or obj.get("config", {}).get("gen_hosts") or pa[6:7])
    assert PA.precheck_argv({"die": "qc"}, {}, "L") is None
    c = coord(tmp_path)
    cand = tmp_path / "cand.json"
    cand.write_text(json.dumps(dict(obj, manifest_hash="a" * 64, plan_sha256="s2")))

    def apply_fn(C, o, src, ev, pilot_item=None, optimistic=None):
        rcpt = Path(C) / "lanes/handoff/qc_atomic_apply_2.json"
        rcpt.write_text("{}")
        return dict(res, source="/x/new", receipt=str(rcpt), warnings=[])
    for off in (False, True):
        calls = []

        def run(argv, **k):
            calls.append(argv)
            return types.SimpleNamespace(returncode=0, stdout="", stderr="")
        a = types.SimpleNamespace(coord=str(c), candidate=str(cand), expect_source="/x/old", expect_event="E0", lane="QC-PLAN-R3",
                                  pilot_item=None, no_gate=True, no_precheck=off, skip_bind_check=True)
        assert PA.cmd_apply(a, run=run, apply_fn=apply_fn, commit_fn=lambda C, r: "ok") == 0
        assert bool([x for x in calls if x[0] == "timeout" and "precheck_hook.py" in " ".join(x)]) is (not off)
        post = [x for x in calls if x[0] == "bash"][0][3]
        assert ("precheck precheck-qc-" in post) is (not off) and ("precheck off" in post) is off


# S81-DIE-R3 11-18 (COORD): the post-apply strict bind + LATCHECK run in a hardlink copy publish_apply makes, never in the composed tree
import hashlib  # noqa: E402
import os  # noqa: E402
import subprocess  # noqa: E402
import src_manifest as SM  # noqa: E402


def published_tree(tmp_path):
    """a minimal published manifest tree: plan, asbuilt and bind out, read-only (src_manifest.publish's make_ro)"""
    t = tmp_path / "kw45" / "src_x_d8f_work"
    files = {"tools/die_plan/bind.py": "print('bind')\n", "physical/die_plan/s81/plan.json": "{}\n",
             "physical/die_plan/s81/pr/native_bind/asbuilt_run.json": "{}\n", "physical/die_plan/s81/pr/native_bind/out/a.sv": "module a; endmodule\n"}
    for rel, txt in files.items():
        (t / rel).parent.mkdir(parents=True, exist_ok=True)
        (t / rel).write_text(txt)
    m = {"main_sha": "0" * 40, "scope": ["tools", "physical"], "overlay": {},
         "files": {rel: hashlib.sha256(txt.encode()).hexdigest() for rel, txt in files.items()}}
    m["manifest_hash"] = SM.manifest_hash(m)
    (t / SM.MANIFEST).write_text(json.dumps(m))
    (t / SM.HASHFILE).write_text(m["manifest_hash"] + "\n")
    SM.make_ro(str(t))
    return t


def bind_candidate(t, hosts=("epyc8",)):
    nb = f"{t}/physical/die_plan/s81/pr/native_bind"
    return {"die": "s81", "marker": {"tree": str(t), "plan": f"{t}/physical/die_plan/s81/plan.json", "die_gen_env": {"OT_NATIVE_RESET_SCOPE": "die"},
                                     "config": {"gen_hosts": list(hosts), "kit_rtl": {"mode": "bind", "bind_out": f"{nb}/out", "asbuilt": f"{nb}/asbuilt_run.json"}}}}


def _chmod_back(tmp_path):
    for dp, dn, fn in os.walk(tmp_path):
        os.chmod(dp, 0o755)


def test_postbind_spec_is_a_sibling_copy_with_tree_relative_inputs(tmp_path):
    t = tmp_path / "T"
    s = PA.postbind_spec(bind_candidate(t), "1118")
    assert s["copy"] == f"{t}_postbind_1118" and os.path.dirname(s["copy"]) == str(tmp_path)        # a sibling: src_manifest.linked_children sees it
    assert s["plan"] == "physical/die_plan/s81/plan.json" and s["asbuilt"] == "physical/die_plan/s81/pr/native_bind/asbuilt_run.json"
    assert s["host"] == "epyc8" and s["env"] == {"OT_NATIVE_RESET_SCOPE": "die"}
    assert PA.postbind_spec({"tree": "/x", "plan": "/p"}, "1") is None                                    # no bind candidate: nothing to run


def test_postbind_job_writes_only_under_postbind_never_the_candidate_bind_out(tmp_path):
    s = PA.postbind_spec(bind_candidate(tmp_path / "T"), "1118")
    sh = PA.postbind_run_sh(s)
    assert f"cd {s['copy']}" in sh and "--strict" in sh and "lane_asbuilt_latency.py" in sh
    assert s["bind_out"] not in sh and "native_bind/out" not in sh                                        # the published bind is never rewritten
    assert sh.count(f"--out {s['copy']}/_postbind/out") == 2 and "export OT_NATIVE_RESET_SCOPE=die" in sh


def test_postbind_copy_keeps_the_published_tree_verified_and_unwritten(tmp_path):
    """the D8f failure class: the copy is made by the tool; the published tree still verifies --ro (shared inodes accounted by .link-base) and a
    write in the copy cannot reach it"""
    SM.CACHE_DIR = str(tmp_path / "cache")
    t = published_tree(tmp_path)
    try:
        assert SM.verify(str(t), ro=True, full=True)[0] == []
        s = PA.postbind_spec(bind_candidate(t), "1118")
        p = subprocess.run(["bash", "-c", PA.postbind_prep_sh(s)], capture_output=True, text=True)
        assert p.returncode == 0, p.stderr
        cp = Path(s["copy"])
        assert (cp / "_postbind/run.sh").read_text() == PA.postbind_run_sh(s)
        assert (cp / SM.LINKBASE).read_text().strip() == os.path.realpath(t)
        assert os.lstat(cp / "physical/die_plan/s81/plan.json").st_ino == os.lstat(t / "physical/die_plan/s81/plan.json").st_ino
        errs = SM.verify(str(t), ro=True, full=True)[0]
        assert errs == [], errs                                                                             # still a valid published tree
        with pytest.raises(PermissionError):                                                                # shared files stay read-only
            open(cp / "physical/die_plan/s81/pr/native_bind/out/a.sv", "w")
        (cp / "_postbind/out").mkdir()
        (cp / "_postbind/out/a.sv").write_text("x")                                                         # the job's own outputs are fresh files
        assert (t / "physical/die_plan/s81/pr/native_bind/out/a.sv").read_text() == "module a; endmodule\n"
        again = subprocess.run(["bash", "-c", PA.postbind_prep_sh(s)], capture_output=True, text=True)
        assert again.returncode != 0                                                                        # never over an existing copy
    finally:
        _chmod_back(tmp_path)


def test_postbind_prep_refuses_a_tree_without_manifest(tmp_path):
    t = tmp_path / "W"
    (t / "physical").mkdir(parents=True)
    s = PA.postbind_spec(bind_candidate(t), "1")
    assert subprocess.run(["bash", "-c", PA.postbind_prep_sh(s)], capture_output=True).returncode != 0
    assert not os.path.exists(s["copy"]) and not os.path.exists(s["copy"] + ".part")


def test_apply_starts_the_post_apply_bind_in_a_copy_and_names_it(tmp_path):
    c = coord(tmp_path)
    t = tmp_path / "T"
    cand = tmp_path / "cand.json"
    cand.write_text(json.dumps(bind_candidate(t)))
    calls = []

    def run(argv, **k):
        calls.append(argv)
        return types.SimpleNamespace(returncode=0, stdout="", stderr="")

    def apply_fn(C, obj, src, ev, pilot_item=None, optimistic=None):
        rcpt = Path(C) / "lanes/handoff/s81_atomic_apply_1.json"
        rcpt.write_text("{}")
        return {"applied": "s81", "event": "D8f", "source": str(t), "receipt": str(rcpt), "warnings": [], "gen_hosts": ["epyc8"]}
    a = types.SimpleNamespace(coord=str(c), candidate=str(cand), expect_source="/x/old", expect_event="E0", lane="S81-DIE-R3", pilot_item=None,
                              no_gate=True, skip_bind_check=True)
    orig = PA.start_postbind
    PA.start_postbind = lambda C, obj, lane, die, run=None: orig(C, obj, lane, die, run=run, stamp="1118", log_dir=str(tmp_path / "pb"))
    try:
        assert PA.cmd_apply(a, run=run, apply_fn=apply_fn, commit_fn=lambda C, r: "ok") == 0
    finally:
        PA.start_postbind = orig
    unit = [x for x in calls if x[0] == "systemd-run"][0]
    assert unit[unit.index("--unit") + 1] == "postbind-s81-1118"
    body = unit[-1]
    assert f"--plan-job bind --dir {t}_postbind_1118" in body and f"{t}_postbind_1118/_postbind/run.sh" in body and "POST-APPLY-BIND" in body
    assert (tmp_path / "pb/postbind-s81-1118.prep.sh").read_text() == PA.postbind_prep_sh(PA.postbind_spec(bind_candidate(t), "1118"))
    p = [x for x in calls if x[0] == "bash"][0]
    assert "postbind-s81-1118" in p[3] and f"{t}_postbind_1118" in p[3]
    calls.clear()
    a.no_post_bind = True
    assert PA.cmd_apply(a, run=run, apply_fn=apply_fn, commit_fn=lambda C, r: "ok") == 0
    assert not [x for x in calls if x[0] == "systemd-run"]


def test_postbind_unit_prep_line_really_makes_the_copy(tmp_path):
    """D8f 11-19: the unit's own prep line (not the script alone) must deliver the script over ssh stdin and make the copy; a fake ssh that
    honours -n (stdin = /dev/null) runs the host side locally"""
    SM.CACHE_DIR = str(tmp_path / "cache")
    t = published_tree(tmp_path)
    fake = tmp_path / "bin"
    fake.mkdir()
    (fake / "ssh").write_text('#!/bin/bash\nn=0; for x in "$@"; do [ "$x" = -n ] && n=1; done\n'
                              '[ $n = 1 ] && exec bash -s < /dev/null\nexec bash -s\n')
    (fake / "ssh").chmod(0o755)
    calls = []

    def run(argv, **k):
        calls.append(argv)
        return types.SimpleNamespace(returncode=0, stdout="", stderr="")
    try:
        unit, txt = PA.start_postbind(str(tmp_path / "coord"), bind_candidate(t), "S81-DIE-R3", "s81", run=run, stamp="1119", log_dir=str(tmp_path / "pb"))
        assert unit == "postbind-s81-1119"
        body = calls[0][-1]
        prep_line = body.split("\n")[0].replace(" || ", " && echo PREP_OK || echo PREP_FAIL #", 1)
        p = subprocess.run(["bash", "-c", prep_line], capture_output=True, text=True, env=dict(os.environ, PATH=f"{fake}:{os.environ['PATH']}"))
        assert "PREP_OK" in p.stdout, (p.stdout, p.stderr, (tmp_path / "pb/postbind-s81-1119.log").read_text())
        assert (Path(f"{t}_postbind_1119") / "_postbind/run.sh").is_file()
        assert SM.verify(str(t), ro=True, full=True)[0] == []
    finally:
        _chmod_back(tmp_path)
