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
