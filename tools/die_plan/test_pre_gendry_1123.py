"""GENDRY-1123: types that differ from the baseline run the kit generator dry; a crash is FAIL GENDRY at PRE."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import plan_gate_pre as P  # noqa: E402


def plans(tmp):
    base = {"partition_types": {"a": {"x": 1}, "b": {"x": 2}, "c": {"x": 3}}}
    new = {"partition_types": {"a": {"x": 1}, "b": {"x": 5}, "c": {"x": 3, "y": 1}}}
    pb, pn = tmp / "base.json", tmp / "plan.json"
    pb.write_text(json.dumps(base)); pn.write_text(json.dumps(new))
    return pn, pb


def test_changed_types_and_named():
    base = {"partition_types": {"a": {"x": 1}, "b": {"x": 2}}}
    new = {"partition_types": {"a": {"x": 1}, "b": {"x": 3}, "n": {}}}
    assert P.gendry_types(new, base, {}) == ["b", "n"]
    assert P.gendry_types(new, None, {}) == []
    assert P.gendry_types(new, None, {"OT_PRE_GENDRY_TYPES": "a,zz"}) == ["a"]


def test_crash_is_fail_and_pass_is_quiet(tmp_path):
    pn, pb = plans(tmp_path)
    seen = []

    def runner(cmd, cwd, timeout):
        tn = cmd[cmd.index("--types") + 1]
        seen.append(tn)
        assert "--trial" in cmd and cmd[cmd.index("--rtl-root") + 1] == str(tmp_path.absolute())
        if tn == "b":
            return 1, "gen phys: ERROR clock landing: b.coll_o0: writer START raw reset rst_rl_334 has no registered wavefront driver\n"
        return 0, "ok"
    out = P.check_gendry(tmp_path, pn, pb, env={}, runner=runner)
    assert sorted(seen) == ["b", "c"]
    fails = [x for x in out if x.startswith("FAIL GENDRY")]
    assert len(fails) == 1 and "b:" in fails[0] and "rst_rl_334" in fails[0]


def test_sidecar_and_cap(tmp_path):
    pn, pb = plans(tmp_path)
    (tmp_path / "source_sidecar.json").write_text("{}")
    cmds = []
    out = P.check_gendry(tmp_path, pn, pb, env={"OT_PRE_GENDRY_MAX": "1"}, runner=lambda c, w, t: (cmds.append(c), (0, ""))[1])
    assert len(cmds) == 1 and "--clock-landing" in cmds[0]
    assert any(x.startswith("WARN GENDRY-UNCHECKED 1 changed") for x in out)


def test_no_baseline_not_run(tmp_path):
    pn, _ = plans(tmp_path)
    assert P.check_gendry(tmp_path, pn, None, env={}, runner=lambda *a: (_ for _ in ()).throw(AssertionError)) == []


# GENDRY-KITRTL-1123: bind-mode (kit-RTL) types are built from the bound RTL, never from the plan wrapper
def kplans(tmp):
    leafy = {"buses": [{"name": "o_x", "dir": "out", "width": 4, "leaf": "u.o"}], "contents": [{"inst": "u", "bind": {}}]}
    bound = {"buses": [{"name": "o_x", "dir": "out", "width": 4, "leaf": "u.o"}], "contents": [{"inst": "u", "bind": {"o": "bus:o_x"}}]}
    kit = {"buses": [{"name": "o_ectl_Q_N_eN", "dir": "out", "width": 8}], "contents": [{"inst": "u", "status": "astk"}]}
    base = {"partition_types": {"n": dict(leafy, v=0), "m": dict(bound, v=0), "k": dict(kit, v=0), "nb": {"v": 0}}}
    new = {"partition_types": {"n": dict(leafy, v=1), "m": dict(bound, v=1), "k": dict(kit, v=1), "nb": {"v": 1}}}
    pb, pn = tmp / "base.json", tmp / "plan.json"
    pb.write_text(json.dumps(base)); pn.write_text(json.dumps(new))
    return pn, pb, new


def test_kitrtl_types_classified_only_without_leaf_binding(tmp_path):
    _, _, new = kplans(tmp_path)
    assert P.gendry_kitrtl_types(new, ["k", "m", "n", "nb"]) == ["k"]


def test_kitrtl_without_bind_out_is_warn_not_fail_and_normal_types_still_run(tmp_path):
    pn, pb, _ = kplans(tmp_path)
    seen = []

    def runner(cmd, cwd, timeout):
        assert "kit-rtl" not in cmd and "--kit-rtl" not in cmd
        tn = cmd[cmd.index("--types") + 1]
        seen.append(tn)
        return (1, "gen phys: ERROR type n: bus o_x is not bound to any leaf port (open output)\n") if tn == "n" else (0, "")
    out = P.check_gendry(tmp_path, pn, pb, env={}, runner=runner)
    assert sorted(seen) == ["m", "n", "nb"]                      # the kit-RTL type is not generated from the plan wrapper
    assert [x.split(":")[0] for x in out if x.startswith("FAIL")] == ["FAIL GENDRY n"]   # a normal type still FAILs
    assert any(x.startswith("WARN GENDRY-KITRTL k:") for x in out)
    assert not any("GENDRY k" in x for x in out if x.startswith("FAIL"))


def test_kitrtl_with_bind_out_uses_bound_rtl(tmp_path):
    pn, pb, _ = kplans(tmp_path)
    bo = tmp_path / "bind"
    bo.mkdir(); (bo / "bind_report.json").write_text("{}")
    calls = []

    def runner(cmd, cwd, timeout):
        calls.append(cmd)
        if "kit-rtl" in cmd:
            assert cmd[cmd.index("--out") + 1] == str(bo.absolute()) and cmd[cmd.index("--type") + 1] == "k"
            assert cmd[cmd.index("--asbuilt") + 1] == str((tmp_path / "ab.json").absolute())
            return 0, ""
        tn = cmd[cmd.index("--types") + 1]
        if tn == "k":
            kr = cmd[cmd.index("--kit-rtl") + 1]
            assert kr.startswith("k=") and kr.endswith("/kit_rtl.f")
            return 1, "gen phys: ERROR clock landing: k.coll_o0: writer START raw reset rst_rl_9 has no registered wavefront driver\n"
        assert "--kit-rtl" not in cmd
        return 0, ""
    out = P.check_gendry(tmp_path, pn, pb, env={}, runner=runner, elab_dir=bo, asbuilt=tmp_path / "ab.json")
    assert sum(1 for c in calls if "kit-rtl" in c) == 1
    fails = [x for x in out if x.startswith("FAIL")]
    assert len(fails) == 1 and fails[0].startswith("FAIL GENDRY k:") and "rst_rl_9" in fails[0]   # still a real check
    assert not any("GENDRY-KITRTL" in x for x in out)


def test_kitrtl_step_failure_is_fail(tmp_path):
    pn, pb, _ = kplans(tmp_path)
    bo = tmp_path / "bind"
    bo.mkdir(); (bo / "bind_report.json").write_text("{}")

    def runner(cmd, cwd, timeout):
        if "kit-rtl" in cmd:
            return 2, "bind kit-rtl: ERROR type k: plan bus o_ectl_Q_N_eN has no bound port\n"
        assert cmd[cmd.index("--types") + 1] != "k"
        return 0, ""
    out = P.check_gendry(tmp_path, pn, pb, env={}, runner=runner, elab_dir=bo)
    fails = [x for x in out if x.startswith("FAIL")]
    assert len(fails) == 1 and "GENDRY k:" in fails[0] and "bind kit-rtl ERROR" in fails[0] and "no bound port" in fails[0]


def test_failed_bind_out_is_not_used(tmp_path):
    pn, pb, _ = kplans(tmp_path)
    bo = tmp_path / "bind"
    bo.mkdir(); (bo / "bind_report.json").write_text(json.dumps({"errors": ["TIED x"], "n_errors": 1}))
    assert P.gendry_bind_out(bo) is None and P.gendry_bind_out(None) is None
    out = P.check_gendry(tmp_path, pn, pb, env={}, runner=lambda c, w, t: (0, "") if "kit-rtl" not in c else (_ for _ in ()).throw(AssertionError),
                         elab_dir=bo)
    assert any(x.startswith("WARN GENDRY-KITRTL k:") for x in out) and not any(x.startswith("FAIL") for x in out)


def test_observer_not_a_plan_leaf_goes_through_kit_rtl(tmp_path):
    """QC cC: leaf-bound types, but the sidecar observer (glue qfd_sys_face_lctx3_wrapped) exists only in the bound RTL; the native
    landed emitter refuses every type, kit_wave uses bind.py kit-rtl"""
    raw = {"partitions": [{"name": "glue", "type": "g"}], "partition_types": {"g": {"contents": []}, "q": {"buses": [{"leaf": "u.o"}]}}}
    pn, sc, el = tmp_path / "plan.json", tmp_path / "source_sidecar.json", tmp_path / "bind"
    pn.write_text(json.dumps(raw))
    sc.write_text(json.dumps({"collector": {"observer": {"part": "glue", "module": "face"}}}))
    el.mkdir()
    (el / "bind_report.json").write_text(json.dumps({"errors": [], "n_errors": 0}))
    cmds, env = [], {"OT_PRE_GENDRY_TYPES": "q"}
    run = lambda c, w, t: (cmds.append(c), (0, ""))[1]  # noqa: E731
    P.check_gendry(tmp_path, pn, None, env=env, runner=run, elab_dir=el)
    assert len(cmds) == 2 and "kit-rtl" in cmds[0] and "--kit-rtl" in cmds[1]
    cmds.clear()                                                  # no finished bind: classified, not generated, never FAIL
    out = P.check_gendry(tmp_path, pn, None, env=env, runner=run)
    assert not cmds and any(x.startswith("WARN GENDRY-KITRTL q") for x in out) and not any(x.startswith("FAIL") for x in out)
    raw["partition_types"]["g"]["contents"] = [{"inst": "u", "module": "face"}]     # plan leaf: native path as before
    pn.write_text(json.dumps(raw))
    P.check_gendry(tmp_path, pn, None, env=env, runner=run, elab_dir=el)
    assert len(cmds) == 1 and "--kit-rtl" not in cmds[0]


def test_generator_reads_the_tree_not_the_tool_checkout(tmp_path, monkeypatch):
    raw = {"partition_types": {"a": {"x": 1}}}
    pn = tmp_path / "plan.json"
    pn.write_text(json.dumps(raw))
    seen = {}

    class R:
        returncode, stdout, stderr = 0, "", ""
    monkeypatch.setattr(P.subprocess, "run", lambda cmd, **k: (seen.update(k), R)[1])
    P.check_gendry(tmp_path, pn, None, env={"OT_PRE_GENDRY_TYPES": "a"})
    assert seen["env"]["OT_REPO_ROOT"] == str(tmp_path.resolve()) and seen["cwd"] == str(tmp_path.absolute())


def test_gen_phys_view_root_is_the_tree(tmp_path, monkeypatch):
    import gen_phys as GP
    monkeypatch.delenv("OT_REPO_ROOT", raising=False)
    assert GP.view_root() == Path(GP.__file__).resolve().parents[2]
    monkeypatch.setenv("OT_REPO_ROOT", str(tmp_path))
    assert GP.view_root() == tmp_path.resolve()


def test_pad_bound_only_in_bound_rtl_goes_through_kit_rtl(tmp_path):
    """GENDRY-PADBIND-1124 (QC C1g glue): leaf-bound buses, but the bump pads are bound only by bind.py (contents[].bump_ports);
    the plan wrapper fails 'pad ... must bind a leaf port: None', the wave kit builds glue from the bound RTL"""
    glue = {"buses": [{"name": "h", "dir": "in", "width": 1, "leaf": "u_f.h"}],
            "pads": [{"name": "bump_bump_fwd_epoch_pad_i", "dir": "in", "width": 1}],
            "contents": [{"inst": "u_f", "module": "sys_face"},
                         {"inst": "u_bump_fwd_epoch", "module": "qfd_sigbump_input",
                          "bump_ports": [{"pin": "pad_i", "dir": "input", "width": 1}]}]}
    padok = {"buses": [{"name": "h", "dir": "in", "width": 1, "leaf": "u_f.h"}],
             "pads": [{"name": "p_i", "dir": "in", "width": 1}],
             "contents": [{"inst": "u_f", "module": "sys_face", "bind": {"p": "pad:p_i"}}]}
    raw = {"partition_types": {"glue": glue, "padok": padok}}
    assert P.gendry_plan_unbound_pads(glue) == ["bump_bump_fwd_epoch_pad_i"] and P.gendry_plan_unbound_pads(padok) == []
    assert P.gendry_kitrtl_types(raw, ["glue", "padok"]) == ["glue"]
    pn, el = tmp_path / "plan.json", tmp_path / "bind"
    pn.write_text(json.dumps(raw))
    env = {"OT_PRE_GENDRY_TYPES": "glue,padok"}
    cmds = []
    run = lambda c, w, t: (cmds.append(c), (0, ""))[1]  # noqa: E731
    out = P.check_gendry(tmp_path, pn, None, env=env, runner=run)        # no bind OUT: WARN, never FAIL, padok still runs
    assert any(x.startswith("WARN GENDRY-KITRTL glue:") for x in out) and not any(x.startswith("FAIL") for x in out)
    assert [c[c.index("--types") + 1] for c in cmds] == ["padok"] and "--kit-rtl" not in cmds[0]
    el.mkdir()
    (el / "bind_report.json").write_text(json.dumps({"errors": [], "n_errors": 0}))
    cmds.clear()
    P.check_gendry(tmp_path, pn, None, env=env, runner=run, elab_dir=el)
    kr = [c for c in cmds if "kit-rtl" in c]
    assert len(kr) == 1 and kr[0][kr[0].index("--type") + 1] == "glue"
    g = [c for c in cmds if "--types" in c and c[c.index("--types") + 1] == "glue"]
    assert len(g) == 1 and "--kit-rtl" in g[0]


def test_kitrtl_src_tree_of_rt_launch_tree(tmp_path):
    """GENDRY-PADBIND-1124: on an rt launch tree the kit-rtl --src-tree is the die tree SRC the launch tree links into"""
    src, lt = tmp_path / "tree", tmp_path / "launch"
    src.mkdir(); lt.mkdir()
    assert P.gendry_src_tree(lt) == str(lt.absolute())
    (lt / ".rt_launch_ok").write_text(json.dumps({"rt": "/x", "src": str(src)}))
    assert P.gendry_src_tree(lt) == str(src.absolute())
    cmd = P.gendry_kitrtl_cmd(lt, tmp_path / "p.json", "glue", tmp_path / "k", tmp_path / "b")
    assert cmd[cmd.index("--src-tree") + 1] == str(src.absolute())
    (lt / ".rt_launch_ok").write_text(json.dumps({"src": str(tmp_path / "gone")}))
    assert P.gendry_src_tree(lt) == str(lt.absolute())


def test_wave_mode_kit_rtl_sends_every_nonhard_type_through_kit_rtl(tmp_path):
    """GENDRY-WAVEMODE-1124 (QC-GENDRY-TRIAGE, COORD f8832eb7): QC kits always use kit_rtl mode bind, so the dry gen takes bind.py
    kit-rtl + gen --kit-rtl for every non-hard type, also one whose buses carry bus.leaf (21 QC types false-failed on the plan
    wrapper); a die without kit_rtl uses the plan wrapper for all; a plan naming no die keeps the per-type classifier"""
    import json as _j
    plan = {"die": {"name": "dq"}, "partition_types": {
        "leafy": {"buses": [{"name": "a", "leaf": "u.a"}]},
        "hardy": {"hard": True, "buses": [{"name": "b", "leaf": "u.b"}]}}}
    pn = tmp_path / "plan.json"; pn.write_text(_j.dumps(plan))
    kw = tmp_path / "kw.json"
    el = tmp_path / "bind"; el.mkdir(); (el / "bind_report.json").write_text('{"errors": []}')
    cmds = []

    def run(c, w, t):
        cmds.append(" ".join(map(str, c)))
        if "kit-rtl" in cmds[-1] and "bind.py" in cmds[-1]:
            k = Path(c[c.index("--kit") + 1]) if "--kit" in c else None
            if k:
                k.mkdir(parents=True, exist_ok=True); (k / "kit_rtl.f").write_text("")
        return 0, ""
    env = {"OT_PRE_GENDRY_TYPES": "leafy,hardy", "OT_KIT_WAVE_JSON": str(kw)}
    kw.write_text(_j.dumps({"dies": {"dq": {"kit_rtl": {"mode": "bind"}}}}))
    assert P.gendry_wave_mode(plan, env) == ("bind", "kit_wave.json dies.dq.kit_rtl.mode")
    out = P.check_gendry(tmp_path, pn, None, env=env, runner=run, elab_dir=el)
    gens = [c for c in cmds if " phys " in f" {c} "]
    assert any("leafy" in c and "--kit-rtl" in c for c in gens), cmds
    assert any("hardy" in c and "--kit-rtl" not in c for c in gens), cmds
    assert "wave kit_rtl mode bind" in out[-1], out
    cmds.clear()
    out = P.check_gendry(tmp_path, pn, None, env=env, runner=run)          # no bind OUT: classified WARN, never the plan-wrapper FAIL
    assert any(x.startswith("WARN GENDRY-KITRTL leafy") for x in out) and not any("leafy" in c for c in cmds), (out, cmds)
    kw.write_text(_j.dumps({"dies": {"dq": {}}}))                          # die without kit_rtl: plan wrapper for all
    assert P.gendry_wave_mode(plan, env)[0] == "plan"
    assert P.gendry_wave_mode(plan, {"OT_KIT_WAVE_JSON": str(tmp_path / "none.json")})[0] == "bind"      # named die, no kit_wave.json
    assert P.gendry_wave_mode(plan, {"OT_PRE_KIT_RTL_MODE": "plan"})[0] == "plan"
    assert P.gendry_wave_mode({"partition_types": {}}, env)[0] is None
