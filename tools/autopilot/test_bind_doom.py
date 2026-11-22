"""BIND-DOOM-1122 (FABLE-FLOW-0350 B1): live binds are re-checked with rt/current plan_gate_pre; a TAPNAME / EMITNAME FAIL posts once."""
import json
import subprocess
import sys
from pathlib import Path

H = Path(__file__).resolve().parent
sys.path.insert(0, str(H))
import bind_doom as B  # noqa: E402

TAP = ("FAIL TAPNAME coll_core__cl1234abcd: density base gives 114 taps, so added_taps must be clk_t114..clk_t114; "
       "clk_t115 should be clk_t114")


def bind(pid=11, findings=None, sha="a" * 64, cwd="/srv/opentallas-scratch2/claude/fable-fix-qc-coll-r2/pk8/launch"):
    return {"pid": pid, "start": 5, "key": f"{pid}@5", "age_s": 7200, "sub": "bind", "cwd": cwd, "plan": cwd + "/p.json",
            "plan_sha": sha, "asbuilt": None, "out": None, "findings": findings}


def test_doomed_rules_only_tapname_emitname_not_unchecked():
    assert B.doomed({"findings": [TAP, "FAIL EMITNAME x", "FAIL TAPNAME-UNCHECKED y: base", "FAIL GEOM z"]}) == [TAP, "FAIL EMITNAME x"]
    assert B.doomed({"findings": ["FAIL RESETPUB sle_sc: stale", "FAIL RESETPUB-UNCHECKED t: x"]}) == ["FAIL RESETPUB sle_sc: stale"]


def test_post_once_per_plan_sha_to_owning_lane_and_doomed_tsv():
    st = {}
    B.merge(st, "epyc10", {"rt": "/x/rt/6d2e", "binds": [bind(findings=[TAP])]}, now=100.0)
    posted = {}
    out = B.posts(st, posted, lanes=["FABLE-FIX-QC-COLL-R2", "QC-PLAN-R13"])
    assert len(out) == 1 and out[0][1] == "FABLE-FIX-QC-COLL-R2"
    assert out[0][2].startswith("BIND-DOOMED epyc10:11 TAPNAME (bind 2.0 h in") and "clk_t115 should be clk_t114" in out[0][2]
    assert B.posts(st, posted) == []                                            # same plan: posted once
    tsv = B.doomed_rows(st)
    assert tsv.splitlines()[1].startswith("a" * 64 + "\t") and "\tTAPNAME\tepyc10:11\t" in tsv
    B.merge(st, "epyc10", {"rt": "/x/rt/6d2e", "binds": [bind(findings=[TAP], sha="b" * 64)]}, now=200.0)
    assert len(B.posts(st, posted)) == 1                                        # a new plan sha in the same unit posts again


def test_skipped_check_keeps_last_result_and_gone_binds_drop():
    st = {}
    B.merge(st, "epyc9", {"rt": "/r/1", "binds": [bind(findings=[TAP]), bind(pid=12, findings=[])]}, now=100.0)
    assert "11@5|" + "a" * 64 + "|/r/1" in B.skip_set(st, "epyc9", 200.0)        # current: the host skips the re-check
    assert B.skip_set(st, "epyc9", 100.0 + B.RECHECK_S + 1) == set()            # hourly re-check
    B.merge(st, "epyc9", {"rt": "/r/1", "binds": [bind(findings=None)]}, now=300.0)
    assert B.doomed(st["binds"]["epyc9|11@5"]) == [TAP] and "epyc9|12@5" not in st["binds"]
    B.merge(st, "epyc9", {"error": "ssh: timeout"}, now=400.0)                  # an unreadable host keeps what it knew
    assert "epyc9|11@5" in st["binds"] and st["errors"]["epyc9"]


def test_due_on_interval_or_new_rt():
    assert B.due({}, 1000.0)
    assert not B.due({"swept_t": 1000.0, "rt_seen": "/rt/a"}, 1100.0, "/rt/a")
    assert B.due({"swept_t": 1000.0, "rt_seen": "/rt/a"}, 1100.0, "/rt/b")       # a pre-check landed: sweep now
    assert B.due({"swept_t": 1000.0}, 1000.0 + B.SWEEP_S)


def test_remote_finds_a_live_bind_and_runs_the_checker(tmp_path):
    """the host-side script: a process running tools/die_plan/bind.py bind <plan> is found with its cwd, and the rt checker is run on it"""
    tree = tmp_path / "srv" / "tree"
    (tree / "tools" / "die_plan").mkdir(parents=True)
    (tree / "p.json").write_text("{}")
    fake = tree / "tools" / "die_plan" / "bind.py"
    fake.write_text("import time\ntime.sleep(60)\n")
    rt = tmp_path / "rt"
    (rt / "tools" / "die_plan").mkdir(parents=True)
    (rt / "tools" / "die_plan" / "plan_gate_pre.py").write_text(
        "import sys\nprint('FAIL TAPNAME t: density base gives 3 taps; clk_t4 should be clk_t3')\nprint('PLAN-GATE-PRE FAIL tree=x')\nsys.exit(1)\n")
    (rt / "tools" / "die_plan" / "plan_gate_pre.py").write_text(
        "import sys, os\nopen(os.path.join(%r, 'calls'), 'a').write(sys.argv[sys.argv.index('--tree') + 1] + chr(10))\n" % str(tmp_path)
        + "print('FAIL TAPNAME t: density base gives 3 taps; clk_t4 should be clk_t3')\nprint('PLAN-GATE-PRE FAIL tree=x')\nsys.exit(1)\n")
    pr = subprocess.Popen([sys.executable, "-I", str(fake), "bind", "p.json", "--out", "o"], cwd=str(tree))
    pr2 = subprocess.Popen([sys.executable, "-I", str(fake), "elab", "p.json", "--out", "o2"], cwd=str(tree))   # same plan + tree: one check
    try:
        arg = json.dumps({"rt": str(rt), "classes": list(B.ONLY), "all_classes": list(B.ALL_CLASSES), "skip": [], "timeout": 60, "par": 4})
        r = subprocess.run([sys.executable, "-I", "-c", B.REMOTE, arg], capture_output=True, text=True, timeout=120)
        got = json.loads(r.stdout.strip().splitlines()[-1])
    finally:
        for x in (pr, pr2):
            x.kill()
            x.wait()
    assert (tmp_path / "calls").read_text().splitlines().count(str(tree)) == 1   # deduped by (plan sha, tree, asbuilt); other live binds add lines
    assert B.doomed([b for b in got["binds"] if b["pid"] == pr2.pid][0])
    mine = [b for b in got["binds"] if b["pid"] == pr.pid]
    assert got["has_pgp"] and len(mine) == 1
    b = mine[0]
    assert b["cwd"] == str(tree) and b["plan"] == str(tree / "p.json") and b["out"] == str(tree / "o") and b["rc"] == 1
    assert B.doomed(b) == ["FAIL TAPNAME t: density base gives 3 taps; clk_t4 should be clk_t3"]


class _AP:
    DRY = True
    HUB_NAME = "intel2"

    def __init__(self, d):
        self.AP_DIR, self.lines, self.posts = str(d), [], []

    def log(self, m):
        self.lines.append(m)

    def read_coord(self, rel):
        return "FABLE-FIX-QC-COLL-R2\tabc\n"

    def coord_append(self, rel, line):
        self.posts.append(line)


def test_step_posts_from_last_sweep_and_never_raises(tmp_path):
    st = {"swept_t": 1e12, "rt_seen": "x", "binds": {}}
    B.merge(st, "epyc10", {"rt": "/r/1", "binds": [bind(findings=[TAP])]}, now=1.0)
    (tmp_path / B.STATE).write_text(json.dumps(st))
    ap = _AP(tmp_path)
    B.step(ap)
    assert len(ap.posts) == 1 and "NEEDS-ACTION [AUTOPILOT -> FABLE-FIX-QC-COLL-R2, COORD] BIND-DOOMED epyc10:11 TAPNAME" in ap.posts[0]
    assert (tmp_path / B.DOOMED_TSV).read_text().count("\tTAPNAME\t") == 1
    B.step(ap)
    assert len(ap.posts) == 1                                                   # posted once
    (tmp_path / B.STATE).write_text("{not json")
    B.step(ap)                                                                  # unreadable state: no raise


def test_no_sweep_from_tests_or_a_non_hub_dir(tmp_path):
    """BIND-DOOM-STORM-1122: the merge queue's autopilot tests started 64 real fleet sweeps"""
    assert B.may_launch(tmp_path, env={}) == (False, "under pytest")              # pytest is loaded in this process
    import sys as _s
    saved = _s.modules.pop("pytest")
    try:
        assert not B.may_launch(tmp_path, env={})[0] and "not the hub autopilot dir" in B.may_launch(tmp_path, env={})[1]
        assert B.may_launch(tmp_path, env={"BIND_DOOM_AP_DIR": str(tmp_path)}) == (True, "")
        assert B.may_launch(tmp_path, env={"BIND_DOOM_AP_DIR": str(tmp_path), "BIND_DOOM": "off"})[0] is False
    finally:
        _s.modules["pytest"] = saved
    ap = _AP(tmp_path)
    ap.DRY = False
    B.step(ap)                                                                   # not DRY, but under pytest: no Popen
    assert not (tmp_path / B.RUNFILE).exists() and not any("sweep started" in m for m in ap.lines)
    assert B.main(["sweep", str(tmp_path), "epyc10", "intel2"]) == 0            # a stray sweep exits at once
    a = B.single_flight(str(tmp_path / "l"))
    assert a is not None and B.single_flight(str(tmp_path / "l")) is None
    a.close()
