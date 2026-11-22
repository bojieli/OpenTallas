"""FLOW-PRIVSPEC-R1 (FABLE-FLOW-2000 item 7, classes B2 + B3):
 a) private-spec --tree takes plan / bind / rt from the tree (bound_trees record, in-tree or sibling bind, the bind's bind_tool.json stamp,
    gen_tools_pin), never silently from the live wave; disagreeing inputs are refused with the flag that fixes them;
 b) the ENV-PROVENANCE record is written by the scheduler's env_provenance.py, also on an old-rt kit that has no checker (never SKIPPED);
 c) a private run-item continues after AUTO-GEOM PASS through the wave stage chain (autopilot.submit argv, ot-wait --kit per stage)."""
import base64
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import env_provenance as EP      # noqa: E402
import kit_wave as KW            # noqa: E402
from test_kit_wave import cfg    # noqa: E402

D, I = "qwen_kvsys", "kv3_pc"
WAVE = "/srv/x/src_kv"
WAVE_BIND = WAVE + "_bind_1121"
GENS = ("reset_tree.py", "reset_replicate.py")


@pytest.fixture(autouse=True)
def _no_plan_probe(monkeypatch):
    """FLOW-PRIVSPEC-R1: private_spec reads the plan flags for the provisional child-view rule; tests have no plan host"""
    monkeypatch.setattr(KW, "plan_names", lambda AP, st, d: {"flags": {}, "deps": {}})


def wave_cfg(**over):
    c = cfg()
    d = c["dies"][D]
    d.update(src=WAVE, plan=WAVE + "/physical/die_plan/qwen_kvsys/plan_of_record/plan_c.json", flow_tag="flow-kv-1",
             kit_rtl={"mode": "bind", "bind_out": WAVE_BIND, "asbuilt": WAVE + "/physical/die_plan/qwen_kvsys/plan_of_record/asbuilt.json"})
    d.update(over)
    return c


def _snap(root, sha, gens):
    d = root / sha[:12]
    (d / "tools" / "autopilot").mkdir(parents=True)
    (d / "tools" / "autopilot" / "rt_launch_tree.sh").write_text("#\n")
    (d / "tools" / "die_plan").mkdir(parents=True)
    for n, body in gens.items():
        (d / "tools" / "die_plan" / n).write_text(body)
    (root / f"{sha[:12]}.manifest.json").write_text(json.dumps({"sha": sha}))
    return d


def _hashes(gens):
    return {n: hashlib.sha256(b.encode()).hexdigest() for n, b in gens.items()}


@pytest.fixture
def rts(tmp_path, monkeypatch):
    """two rt snapshots: A = the scheduler / wave rt, B = an older one with another reset_replicate.py"""
    root = tmp_path / "rt"
    root.mkdir()
    ga, gb = {"reset_tree.py": "t1", "reset_replicate.py": "A"}, {"reset_tree.py": "t1", "reset_replicate.py": "B"}
    sa, sb = "aa" * 20, "bb" * 20
    da, db = _snap(root, sa, ga), _snap(root, sb, gb)
    os.utime(db, (1, 1))
    real = KW.scheduler_rt
    monkeypatch.setattr(KW, "scheduler_rt", lambda r=None: (str(da), sa) if r is None else real(r))
    monkeypatch.setattr(KW, "rt_tools_fields", lambda c, die, root=None: {"tools_rt": str(da), "tools_sha": sa})
    monkeypatch.setattr(KW, "_bts", lambda: type("B", (), {"GENERATORS": GENS, "generator_hashes": staticmethod(
        lambda d: {n: hashlib.sha256((Path(d) / "tools" / "die_plan" / n).read_bytes()).hexdigest() for n in GENS if (Path(d) / "tools" / "die_plan" / n).is_file()})}))
    return {"root": root, "A": (str(da), sa, _hashes(ga)), "B": (str(db), sb, _hashes(gb))}


def probe_of(tree, binds=None, siblings=(), gens=None, plans_missing=()):
    """a fake tree_probe: binds {path: stamp-or-None (ok, 0 errors)}"""
    def probe(t, cands, plans):
        assert t == tree
        b = {p: {"ok": True, "n_errors": 0, "stamp": s} for p, s in (binds or {}).items()}
        for p in cands:
            b.setdefault(p, {"ok": False, "why": "FileNotFoundError"})
        return {"tree": t, "exists": True, "binds": b, "siblings": list(siblings), "plan": {p: p not in plans_missing for p in plans},
                "gens": gens or {}, "host": "local"}
    return probe


def test_tree_uses_its_own_bind_not_the_wave_bind(rts):
    T = "/srv/lane/tree_j7"
    inb = T + "/physical/die_plan/qwen_kvsys/plan_of_record/native_bind/out"
    sp = KW.private_spec(wave_cfg(), D, I, "intel2", tree=T, probe=probe_of(T, {inb: {"generators": rts["A"][2]}}), rt_root=rts["root"])
    assert sp["kit_rtl"]["bind_out"] == inb and sp["kit_rtl"]["asbuilt"].startswith(T + "/")
    assert sp["plan"].startswith(T + "/")
    assert sp["tools_sha"] == rts["A"][1] and "rt" not in sp["private"]           # the wave rt fits the bind: no declared rt
    ti = sp["private"]["tree_inputs"]
    assert ti["bind_from"] == "in-tree" and "fits the bind stamp" in ti["rt_from"]


def test_tree_without_a_bind_is_refused_naming_bind_out(rts):
    T = "/srv/lane/tree_nobind"
    with pytest.raises(ValueError) as e:
        KW.private_spec(wave_cfg(), D, I, "intel2", tree=T, probe=probe_of(T), rt_root=rts["root"])
    assert "--bind-out" in str(e.value) and WAVE_BIND in str(e.value)
    sp = KW.private_spec(wave_cfg(), D, I, "intel2", tree=T, bind_out=WAVE_BIND, probe=probe_of(T, {WAVE_BIND: None}), rt_root=rts["root"])
    assert sp["kit_rtl"]["bind_out"] == WAVE_BIND and sp["private"]["tree_inputs"]["bind_from"] == "--bind-out"


def test_sibling_bind_one_ok_two_refused(rts):
    T = "/srv/lane/tree_s"
    s1, s2 = T + "_bind_a", T + "_bind_b"
    sp = KW.private_spec(wave_cfg(), D, I, "intel2", tree=T, probe=probe_of(T, {s1: None}, siblings=[s1]), rt_root=rts["root"])
    assert sp["kit_rtl"]["bind_out"] == s1 and sp["private"]["tree_inputs"]["bind_from"].startswith("sibling")
    with pytest.raises(ValueError) as e:
        KW.private_spec(wave_cfg(), D, I, "intel2", tree=T, probe=probe_of(T, {s1: None, s2: None}, siblings=[s1, s2]), rt_root=rts["root"])
    assert "several sibling binds" in str(e.value)


def test_missing_plan_in_tree_is_refused(rts):
    T = "/srv/lane/tree_p"
    inb = T + "/physical/die_plan/qwen_kvsys/plan_of_record/native_bind/out"
    plan = T + "/physical/die_plan/qwen_kvsys/plan_of_record/plan_c.json"
    with pytest.raises(ValueError) as e:
        KW.private_spec(wave_cfg(), D, I, "intel2", tree=T, probe=probe_of(T, {inb: None}, plans_missing=(plan,)), rt_root=rts["root"])
    assert "--plan" in str(e.value)


def test_bound_trees_record_is_the_truth(rts):
    T = "/srv/x/src_kv_d25"
    rec = {"src": T, "plan": T + "/p/plan_d25.json", "src_sha": "abc123", "queue_src": "main@abc123", "src_manifest_hash": "f" * 64, "event": "KV-D25",
           "kit_rtl": {"mode": "bind", "bind_out": T + "_bind_d25", "asbuilt": T + "/p/asbuilt.json"}}
    c = wave_cfg(bound_trees=[rec])
    sp = KW.private_spec(c, D, I, "intel2", tree=T, probe=probe_of(T, {T + "_bind_d25": None}), rt_root=rts["root"])
    assert sp["plan"] == rec["plan"] and sp["kit_rtl"] == rec["kit_rtl"]
    assert (sp["src_sha"], sp["queue_src"], sp["src_manifest_hash"]) == ("abc123", "main@abc123", "f" * 64)
    assert sp["private"]["tree_inputs"]["source"].startswith("bound_trees")


def test_rt_defaults_to_the_bind_rt_and_explicit_rt_must_fit(rts):
    T = "/srv/lane/tree_j7"
    inb = T + "/physical/die_plan/qwen_kvsys/plan_of_record/native_bind/out"
    pr = probe_of(T, {inb: {"tools_sha": "", "generators": rts["B"][2]}})
    sp = KW.private_spec(wave_cfg(), D, I, "intel2", tree=T, probe=pr, rt_root=rts["root"])
    assert sp["tools_rt"] == rts["B"][0] and sp["tools_sha"] == rts["B"][1]
    assert sp["private"]["rt"]["from"].startswith("bind stamp") and sp["private"]["rt"]["wave_tools_sha"] == rts["A"][1]
    with pytest.raises(ValueError) as e:                 # --rt of the wave rt does not fit this bind
        KW.private_spec(wave_cfg(), D, I, "intel2", tree=T, probe=pr, rt=rts["A"][1][:12], rt_root=rts["root"])
    assert "drop --rt" in str(e.value) and "reset_replicate.py" in str(e.value)
    sp = KW.private_spec(wave_cfg(), D, I, "intel2", tree=T, probe=pr, rt=rts["B"][1][:12], rt_root=rts["root"])
    assert sp["tools_sha"] == rts["B"][1] and sp["private"]["rt"]["from"] == "--rt"


def test_stamp_matching_no_rt_uses_tree_tools_or_refuses(rts):
    T = "/srv/lane/tree_x"
    inb = T + "/physical/die_plan/qwen_kvsys/plan_of_record/native_bind/out"
    other = {"reset_tree.py": "z", "reset_replicate.py": "z"}
    sp = KW.private_spec(wave_cfg(), D, I, "intel2", tree=T, probe=probe_of(T, {inb: {"generators": other}}, gens=other), rt_root=rts["root"])
    assert "tools_rt" not in sp and "tree tools" in sp["private"]["tree_inputs"]["rt_from"]
    with pytest.raises(ValueError) as e:
        KW.private_spec(wave_cfg(), D, I, "intel2", tree=T, probe=probe_of(T, {inb: {"generators": other}}, gens={}), rt_root=rts["root"])
    assert "rebind" in str(e.value) and "--rt" in str(e.value)


def test_gen_tools_pin_of_the_tree_bind_and_wave_pin_dropped(rts):
    T = "/srv/lane/tree_pin"
    inb = T + "/physical/die_plan/qwen_kvsys/plan_of_record/native_bind/out"
    pin = {"event": "event28w_c", "src_manifest_hash": "e" * 64, "bind_out": inb}
    c = wave_cfg(item_inputs={I: {"gen_tools_pin": pin}})
    sp = KW.private_spec(c, D, I, "intel2", tree=T, probe=probe_of(T, {inb: {"generators": {"x": "y"}}}), rt_root=rts["root"])
    assert sp["gen_tools_manifest_sha"] == "e" * 64 and "tools_rt" not in sp
    assert sp["private"]["tree_inputs"]["rt_from"].startswith("gen_tools_pin")
    # the wave tree's own pin never follows --tree
    c2 = wave_cfg(src_manifest_hash="9" * 64, item_inputs={I: {"gen_tools_pin": {"event": "event28w_c", "src_manifest_hash": "9" * 64, "bind_out": WAVE_BIND}}})
    assert KW.spec_for(c2, D, I, "intel2").get("gen_tools_manifest_sha") == "9" * 64
    sp2 = KW.private_spec(c2, D, I, "intel2", tree=T, probe=probe_of(T, {inb: None}), rt_root=rts["root"])
    assert "gen_tools_manifest_sha" not in sp2 and sp2["tools_sha"] == rts["A"][1]


def test_unreadable_tree_moves_an_in_tree_wave_bind_only(rts):
    T = "/srv/lane/far"
    c = wave_cfg(kit_rtl={"mode": "bind", "bind_out": WAVE + "/physical/die_plan/qwen_kvsys/plan_of_record/bind_of_record", "asbuilt": WAVE + "/a.json"})
    sp = KW.private_spec(c, D, I, "intel2", tree=T, probe=lambda *a: {}, rt_root=rts["root"])
    assert sp["kit_rtl"]["bind_out"] == T + "/physical/die_plan/qwen_kvsys/plan_of_record/bind_of_record"
    with pytest.raises(ValueError) as e:
        KW.private_spec(wave_cfg(), D, I, "intel2", tree=T, probe=lambda *a: {}, rt_root=rts["root"])
    assert "--host" in str(e.value) and "--bind-out" in str(e.value)


def test_tree_probe_reads_a_local_tree(tmp_path, monkeypatch):
    T = tmp_path / "tree"
    b = T / "physical/die_plan/qwen_kvsys/plan_of_record/native_bind/out"
    b.mkdir(parents=True)
    (b / "bind_report.json").write_text(json.dumps({"errors": []}))
    (b / "bind_tool.json").write_text(json.dumps({"tools_sha": "", "generators": {"reset_tree.py": "h"}}))
    sib = tmp_path / "tree_bind_x"
    sib.mkdir()
    (sib / "bind_report.json").write_text(json.dumps({"errors": ["e"]}))
    (T / "tools/die_plan").mkdir(parents=True)
    (T / "tools/die_plan/reset_tree.py").write_text("x")
    pr = KW.tree_probe(str(T), None, "intel2", [str(b), str(T / "nope")], [str(T / "plan.json")])
    assert pr["exists"] and pr["binds"][str(b)]["n_errors"] == 0 and pr["binds"][str(b)]["stamp"]["generators"] == {"reset_tree.py": "h"}
    assert pr["binds"][str(T / "nope")]["ok"] is False and pr["siblings"] == [str(sib)] and pr["binds"][str(sib)]["n_errors"] == 1
    assert pr["plan"] == {str(T / "plan.json"): False} and "reset_tree.py" in pr["gens"]


def test_goal_default_and_old_specs():
    c = wave_cfg(kit_rtl={})
    sp = KW.private_spec(c, D, I, "intel2")
    assert sp["goal"] == "auto" and KW.chain_goal_of(sp) == "auto" and KW.chain_goal_of(sp, "geom") == "geom"
    assert KW.private_spec(c, D, I, "intel2", goal="route")["goal"] == "route"
    place = KW.private_spec(c, D, I, "intel2", goal="place")
    assert KW.chain_goal_of(place) == "place"
    assert KW.chain_goal_of(KW.spec_for(c, D, I, "intel2"), "place") == "geom"
    with pytest.raises(ValueError):
        KW.private_spec(c, D, I, "intel2", goal="sta")
    old = dict(sp)
    old.pop("goal")
    assert KW.chain_goal_of(old) == "auto"                          # RESUME-GOAL-1122: no goal = auto (sign-off goal), never geom
    assert KW.chain_goal_of(sp, "bogus") == "auto"
    assert KW.chain_goal_of(KW.spec_for(c, D, I, "intel2"), "route") == "geom"     # wave specs never chain


# ------------------------------------------------------------------------------------------------ b) ENV-PROVENANCE on an old-rt kit
def _local_run(log):
    def run(stage, argv, timeout=None, idempotent=False):
        p = subprocess.run(argv, capture_output=True, text=True)
        log.append((stage, p.returncode))
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    return run


def test_env_provenance_written_by_scheduler_copy_on_old_kit(tmp_path):
    K = tmp_path / "kit-wave" / "gen" / "t"
    K.mkdir(parents=True)
    (K / "config.mk").write_text("export OT_PGCAP = 1\n")
    decl = {"source": "private-spec", "die": D, "item": I, "env": {"OT_PGCAP": "1"}, "wave_env": {"OT_PGCAP": "1"}}
    b64 = base64.b64encode(json.dumps(decl).encode()).decode()
    log = []
    why = KW.write_env_provenance(str(K), b64, lambda c: ["bash", "-c", c], _local_run(log), "t")
    assert why == "" and log == [("env_provenance", 0)]
    rec = json.loads((K / EP.RECORD).read_text())
    assert rec["source"] == "private-spec" and rec["config_ot"] == {"OT_PGCAP": "1"}
    assert (K / "env_provenance.py").read_text() == Path(EP.__file__).read_text()        # the checker run_kit.sh calls is now in the kit
    assert not [p for p in os.listdir(K) if p.startswith(".env_provenance")]
    r = subprocess.run([sys.executable, "-I", str(K / "env_provenance.py"), "check", str(K)], capture_output=True, text=True)
    assert r.returncode == 0 and "ENV-PROVENANCE PASS" in r.stdout
    # a kit with its own (older) checker keeps it; the record still comes from the scheduler copy
    (K / "env_provenance.py").write_text("raise SystemExit(9)\n")
    (K / EP.RECORD).unlink()
    assert KW.write_env_provenance(str(K), b64, lambda c: ["bash", "-c", c], _local_run(log), "t") == ""
    assert (K / EP.RECORD).exists() and (K / "env_provenance.py").read_text() == "raise SystemExit(9)\n"
    why = KW.write_env_provenance(str(tmp_path / "nokit"), b64, lambda c: ["bash", "-c", c], _local_run(log), "t")
    assert "kit dir missing" in why


# ------------------------------------------------------------------------------------------------ c) the wave stage chain after AUTO-GEOM
class FakeProc:
    def __init__(self, rc):
        self.rc, self.done = rc, False

    def poll(self):
        return self.rc if self.done else None

    def wait(self):
        self.done = True
        return self.rc


def chain_fixture(tmp_path, monkeypatch, probe=None, receipt=None, proc_rcs=(0,), stage_rcs=None, live=""):
    import autopilot as AP
    monkeypatch.setattr(AP, "stage_admission_tools", lambda: {"dir": "/srv/opentallas-scratch2/claude/autopilot/admission_tools/x", "sha256": "s"})
    monkeypatch.setattr(AP, "late_eco_on", lambda: True)
    monkeypatch.setattr(AP, "stage_disk_args", lambda: ["--disk", "5"])
    monkeypatch.setenv("OT_GPL_SPARSE_UTIL", "0.3")               # a stray knob in the caller's shell must not reach the chain
    sp = {"die": D, "item": I, "hub": "intel2", "work": "/srv/w/items/t", "ot_run": "/bin/ot-run", "place_mem_gb": 40, "kind": "type",
          "private": {"lane": "FAM-X"}}
    K = "/srv/w/items/t/gen/t"
    res = {"stage": "geom", "verdict": "PASS", "kit": "epyc9:" + K, "die": D, "item": I}
    out = tmp_path
    calls, popens, waits = [], [], []
    p = probe if probe is not None else {"exists": True, "config": True, "routed": [], "signoff_dirs": [], "fail_marks": [], "runner": "/srv/w/items/t/gen/run_kit.sh",
                                         "signoff_goals": ["route"], "signoff_missing": []}
    rc_rcpt = receipt if receipt is not None else {"chain": {"verdict": "PASS", "reason": "physical signoff and routed LEC complete", "path": K + "/autopilot_chain_1.json"},
                                                   "signoff": {"path": K + "/signoff/signoff.json", "verdict": "SIGNED"}, "fail_marks": []}

    def run(stage, argv, timeout=None, idempotent=False):
        calls.append((stage, argv))
        if stage == "chain_probe":
            return 0, "AP_JSON " + json.dumps(p) + "\n"
        if stage == "chain_receipt":
            return 0, "KW_CHAIN_RECEIPT " + json.dumps(rc_rcpt) + "\n"
        return 0, ""
    rcs = list(proc_rcs)

    def popen(argv, stdout=None, stderr=None, env=None):
        popens.append((argv, env))
        stdout.write(live if len(rcs) > 1 or not live else live)
        return FakeProc(rcs.pop(0))
    srcs = dict(stage_rcs or {})

    def wait(argv, capture_output=True, text=True, timeout=None):
        waits.append(argv)
        st = argv[argv.index("--stage") + 1]
        return subprocess.CompletedProcess(argv, srcs.get(st, 0), f"DONE rc=0 kit={K} stage={st}\n", "")

    def fail(stage, txt, evidence=""):
        res.update(stage=stage, verdict="FAIL", tail=txt[-500:], evidence=evidence)
        return 1
    return sp, res, out, run, fail, popen, wait, calls, popens, waits, K


def test_chain_signs_off_with_the_autopilot_submit_argv(tmp_path, monkeypatch):
    sp, res, out, run, fail, popen, wait, calls, popens, waits, K = chain_fixture(tmp_path, monkeypatch)
    completed = {"place": 0, "geom": 0}
    rc = KW.private_chain(sp, res, out, "auto", run, fail, completed, popen=popen, wait=wait, sleep=lambda s: None)
    assert rc == 0 and res["verdict"] == "SIGNED" and res["stage"] == "signoff" and res["goal"] == "route"
    assert json.loads((out / "result.json").read_text())["verdict"] == "SIGNED"
    argv, env = popens[0]
    import autopilot as AP
    assert argv[:2] == ["/bin/ot-run", "--mem"] and argv[argv.index("--hosts") + 1] == "epyc9" and "--disk" in argv
    assert argv[argv.index("--dir") + 1] == K and AP.ADMISSION_BOOTSTRAP in argv
    assert argv[-5:] == ["/srv/w/items/t/gen/run_kit.sh", K, "route", "40", "8"]
    assert "--stage" in argv and "/srv/w/items/t/gen/run_kit.sh" in argv          # the runner outside the kit is staged too
    assert "OT_GPL_SPARSE_UTIL" not in env and env.get("OT_LANE")
    assert [w[w.index("--stage") + 1] for w in waits] == ["cts", "grt", "route"]
    assert all(w[w.index("--host") + 1] == "epyc9" and "--kit" in w for w in waits)
    assert completed["cts"] == completed["grt"] == completed["route"] == completed["chain"] == 0


def test_chain_stage_fail_and_not_signed(tmp_path, monkeypatch):
    rcpt = {"chain": {"verdict": "NOT_SIGNED", "reason": "signoff gates not PASS: setup_tt=FAIL"}, "signoff": {"verdict": "FAIL"}, "fail_marks": []}
    sp, res, out, run, fail, popen, wait, *_ = chain_fixture(tmp_path, monkeypatch, receipt=rcpt, proc_rcs=(1,))
    assert KW.private_chain(sp, res, out, "route", run, fail, {}, popen=popen, wait=wait, sleep=lambda s: None) == 1
    assert res["verdict"] == "FAIL" and res["stage"] == "signoff" and "setup_tt=FAIL" in res["tail"]
    rcpt = {"chain": {"verdict": "RUNNER_FAIL", "reason": "physical runner did not complete"}, "fail_marks": ["FAIL_POSTCTS"]}
    sp, res, out, run, fail, popen, wait, calls, popens, waits, K = chain_fixture(tmp_path, monkeypatch, receipt=rcpt, proc_rcs=(2,), stage_rcs={"grt": 1})
    assert KW.private_chain(sp, res, out, "route", run, fail, {}, popen=popen, wait=wait, sleep=lambda s: None) == 1
    assert res["stage"] == "grt" and [w[w.index("--stage") + 1] for w in waits] == ["cts", "grt"]


def test_chain_retries_not_run_and_refuses_routed_kits(tmp_path, monkeypatch):
    sp, res, out, run, fail, popen, wait, calls, popens, waits, K = chain_fixture(tmp_path, monkeypatch, proc_rcs=(1, 0), stage_rcs={"cts": 2},
                                                                                live="ot-run: NOT RUN: no host admits 40 GB\n")
    rc = KW.private_chain(sp, res, out, "route", run, fail, {}, popen=popen, wait=wait, sleep=lambda s: None)
    assert len(popens) == 2
    probe = {"exists": True, "config": True, "routed": ["5_route.odb"], "signoff_dirs": [], "fail_marks": [], "runner": "/r/run_kit.sh"}
    sp, res, out, run, fail, popen, wait, calls, popens, waits, K = chain_fixture(tmp_path, monkeypatch, probe=probe)
    assert KW.private_chain(sp, res, out, "route", run, fail, {}, popen=popen, wait=wait) == 1
    assert res["stage"] == "chain_admit" and "already routed" in res["tail"] and not popens


def test_chain_diagnostic_goal_runs_the_runner_only(tmp_path, monkeypatch):
    sp, res, out, run, fail, popen, wait, calls, popens, waits, K = chain_fixture(tmp_path, monkeypatch, receipt={})
    assert KW.private_chain(sp, res, out, "grt", run, fail, {}, popen=popen, wait=wait) == 0
    argv = popens[0][0]
    assert argv[-6:] == ["bash", "/srv/w/items/t/gen/run_kit.sh", K, "grt", "40", "8"] and res["verdict"] == "PASS" and res["stage"] == "grt"
    assert [w[w.index("--stage") + 1] for w in waits] == ["cts", "grt"]


def test_stage_wait_slices_until_the_job_ends(monkeypatch):
    seq = [124, 124, 66]
    proc = FakeProc(3)

    def wait(argv, **k):
        rc = seq.pop(0) if seq else 2
        if not seq:
            proc.done = True
        return subprocess.CompletedProcess(argv, rc, "", "")
    rc, _ = KW.chain_stage_wait("/k", "route", "intel2", "intel2", proc, wait=wait, slice_s=1)
    assert rc == 2                                       # the job ended without the stage ODB
    rc, _ = KW.chain_stage_wait("/k", "route", "intel2", "intel2", FakeProc(0), wait=lambda a, **k: subprocess.CompletedProcess(a, 0, "", ""))
    assert rc == 0


def test_fork_of_the_wave_tree_keeps_wave_bind(rts):
    T = "/srv/lane/trees/fork1"
    sp = KW.private_spec(wave_cfg(), D, I, "intel2", tree=T, fork_of=WAVE, probe=lambda *a: {}, rt_root=rts["root"])
    assert sp["kit_rtl"]["bind_out"] == WAVE_BIND and sp["private"]["tree_inputs"]["source"] == "fork of the wave tree"

    def pr(t, b, p):
        return {"tree": t, "exists": True, "binds": {}, "siblings": [], "plan": {}, "gens": {}, "fork": {"src_real": WAVE}, "host": "local"}
    sp = KW.private_spec(wave_cfg(), D, I, "intel2", tree=T, probe=pr, rt_root=rts["root"])
    assert sp["kit_rtl"]["bind_out"] == WAVE_BIND and sp["tools_sha"] == rts["A"][1]


def test_private_spec_carries_the_wave_provisional_child_views(monkeypatch):
    """QC-RELAUNCH-R1 slw_su_c: the wave kit config.mk adds provisional child LEF/libs (qfd_dv_s8x_prog / btab); a private kit must get the same"""
    seen = {}

    def pv(d):
        seen["plan"] = d["plan"]
        return {"flags": {I: "planned"}, "deps": {I: ["qfd_dv_s8x_prog", "qfd_dv_s8x_btab"]}, "prov_deps": {}}
    monkeypatch.setattr(KW, "prov_sources", lambda jobs, die, mods, d, hub: {m: [{"dir": "/v/" + m}] for m in mods})
    c = wave_cfg(kit_rtl={})
    sp = KW.private_spec(c, D, I, "intel2", plan="/srv/lane/plan_x.json", plan_view=pv)
    assert sp["prov_views"]["modules"] == ["qfd_dv_s8x_prog", "qfd_dv_s8x_btab"] and seen["plan"] == "/srv/lane/plan_x.json"
    assert set(sp["prov_views"]["cands"]) == {"qfd_dv_s8x_prog", "qfd_dv_s8x_btab"} and sp["private"]["prov_views"]["modules"]
    # same set the wave launch rule gives on that plan
    d = dict(c["dies"][D], _plan_flags={I: "planned"}, _plan_deps={I: ["qfd_dv_s8x_prog", "qfd_dv_s8x_btab"]})
    import autopilot as AP
    assert KW.prov_spec(AP, d, D, I, "intel2")["modules"] == sp["prov_views"]["modules"]
    assert "prov_views" not in KW.private_spec(c, D, I, "intel2", plan_view=lambda d: {"flags": {}})
    assert "prov_views" not in KW.private_spec(wave_cfg(kit_rtl={}, prov_view=False), D, I, "intel2", plan_view=pv)
    with pytest.raises(ValueError):
        KW.private_spec(c, D, I, "intel2", plan_view=lambda d: {"error": "ssh failed"})


def test_resume_goal_finish_is_route_and_auto_is_signoff_goal():
    """RESUME-GOAL-1122 (COORD): finish on a resumed kit runs as route; auto resolves to the runner's sign-off goal, never geom"""
    import autopilot as AP
    rk = {"runner": "/k/run_kit.sh"}
    assert KW.resolve_chain_goal(AP, "auto", rk) == "route"
    assert KW.resolve_chain_goal(AP, None, {}, "/w/gen/run_kit.sh") == "route"
    assert KW.resolve_chain_goal(AP, "geom", rk) == "route"
    assert KW.resolve_chain_goal(AP, "finish", rk) == "finish"                         # no resume: as asked
    assert KW.resolve_chain_goal(AP, "finish", dict(rk, resume={"start": "cts"})) == "route"
    assert KW.resolve_chain_goal(AP, "cts", dict(rk, resume={"start": "cts"})) == "cts"
    assert KW.resolve_chain_goal(AP, "auto", {"runner": "/k/run_kit_hbm.sh"}) == "finish"   # another runner's own sign-off goal
