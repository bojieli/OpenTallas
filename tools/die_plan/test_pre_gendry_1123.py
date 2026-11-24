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
