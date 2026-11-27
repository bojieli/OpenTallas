"""kit_topology_dry (C-ISTATION-PACKED-DELAY): kit_rtl + kit_topology per type of a candidate plan, fail closed with the type list."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_topology_dry as KD  # noqa: E402


def fixture(tmp_path):
    bo = tmp_path / "bind"
    (bo / "rtl").mkdir(parents=True, exist_ok=True)
    types = {"t_ok": {"module": "m_ok"}, "t_bad": {"module": "m_bad"}, "t_core__cl1": {"module": "m_core"}}
    (bo / "bind_report.json").write_text(json.dumps({"types": types}))
    for t in types.values():
        (bo / "rtl" / (t["module"] + ".sv")).write_text("module " + t["module"] + ";endmodule\n")
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps({"reset": {}, "partition_types": {"t_ok": {"reset": 1}, "t_bad": {"reset": 1}, "t_core": {"reset": 1},
                                                                 "t_nobind": {"reset": 1}, "t_plain": {}}}))
    tools = tmp_path / "tools"
    tools.mkdir(exist_ok=True)
    return bo, plan, tools


def fake(calls, bad_stage=None, bad_type="t_bad"):
    def runner(cmd, cwd, timeout):
        stage = "kit_rtl" if "kit-rtl" in cmd else "kit_topology"
        tn = cmd[cmd.index("--type") + 1] if stage == "kit_rtl" else cmd[cmd.index("prepare-stations") + 2]
        calls.append((stage, tn))
        if tn == bad_type and stage == bad_stage:
            return 1, "Traceback\nValueError: %s.leafdn_i0: packed delay does not preserve exact face epoch/data connection" % tn
        return 0, "ok"
    return runner


def run(tmp_path, runner, **kw):
    bo, plan, tools = fixture(tmp_path)
    return KD.run_all(str(plan), str(bo), None, str(tmp_path), str(tmp_path / "work"), tools=tools, jobs=2, runner=runner,
                      has_topology=lambda raw, t: bool(raw["partition_types"][t]), **kw)


def test_all_bound_types_pass_and_unbound_are_listed_not_silent(tmp_path):
    calls = []
    r = run(tmp_path, fake(calls))
    assert r["verdict"] == "PASS" and r["n_types"] == 3 and r["failed"] == []   # t_ok, t_bad, t_core (variant of the bind key)
    assert sorted(t for s, t in calls if s == "kit_topology") == ["t_bad", "t_core", "t_ok"]
    assert set(r["skipped"]) == {"t_nobind", "t_plain"} and "not a bound type" in r["skipped"]["t_nobind"]


def test_one_failing_type_fails_the_check_with_the_type_list(tmp_path):
    r = run(tmp_path, fake([], bad_stage="kit_topology"))
    assert r["verdict"] == "FAIL" and [f["type"] for f in r["failed"]] == ["t_bad"]
    assert r["failed"][0]["stage"] == "kit_topology" and "packed delay does not preserve" in r["failed"][0]["why"]
    r2 = run(tmp_path, fake([], bad_stage="kit_rtl"))
    assert r2["failed"][0]["stage"] == "kit_rtl"


def test_a_crash_or_timeout_is_a_failure_of_that_type(tmp_path):
    r = run(tmp_path, lambda cmd, cwd, timeout: (124, "timed out after 5 s") if "t_ok" in cmd else (0, "ok"))
    assert r["verdict"] == "FAIL" and [f["type"] for f in r["failed"]] == ["t_ok"]


def test_passed_types_are_reused_failures_are_rerun(tmp_path):
    calls = []
    r1 = run(tmp_path, fake(calls, bad_stage="kit_topology"))
    assert r1["verdict"] == "FAIL" and r1["n_cached"] == 0
    calls.clear()
    r2 = run(tmp_path, fake(calls))                       # same inputs: the two passed types come from the cache, t_bad is re-run
    assert r2["verdict"] == "PASS" and r2["n_cached"] == 2 and {t for _, t in calls} == {"t_bad"}


def test_types_filter_and_missing_bind_report(tmp_path):
    calls = []
    r = run(tmp_path, fake(calls), wanted={"t_ok"})
    assert r["n_types"] == 1
    bo, plan, tools = fixture(tmp_path / "x")
    (bo / "bind_report.json").unlink()
    r = KD.run_all(str(plan), str(bo), None, str(tmp_path), str(tmp_path / "w2"), tools=tools, runner=fake([]),
                   has_topology=lambda raw, t: True)
    assert r["verdict"] == "FAIL" and "bind_report.json" in r["why"]


def base_fixture(tmp_path, drop=()):
    bo, plan, tools = fixture(tmp_path)
    raw = json.loads(plan.read_text())
    for d in drop:
        raw["partition_types"].pop(d)
    bplan = tmp_path / "base_plan.json"
    bplan.write_text(json.dumps(raw))
    return bo, plan, tools, bplan


def with_base(tmp_path, cand_fail, base_fail, drop=()):
    """cand_fail / base_fail: {(type, stage): why}; the runner tells the candidate plan from the live one by the plan path in the command"""
    bo, plan, tools, bplan = base_fixture(tmp_path, drop)

    def runner(cmd, cwd, timeout):
        stage = "kit_rtl" if "kit-rtl" in cmd else "kit_topology"
        tn = cmd[cmd.index("--type") + 1] if stage == "kit_rtl" else cmd[cmd.index("prepare-stations") + 2]
        fails = base_fail if str(bplan) in cmd else cand_fail
        why = fails.get((tn, stage))
        return (1, "Traceback\n" + why) if why else (0, "ok")
    return KD.run_all(str(plan), str(bo), None, str(tmp_path), str(tmp_path / "work"), tools=tools, jobs=2, runner=runner,
                      has_topology=lambda raw, t: bool(raw["partition_types"][t]),
                      baseline=dict(plan=str(bplan), bind_out=str(bo), asbuilt=None, tree=str(tmp_path)))


ERR = "bind: ERROR kit-rtl t_bad: core clock clk_c0: expected one bound leaf x, got 0"


def test_failure_identical_on_the_live_event_is_held_not_blocking(tmp_path):
    r = with_base(tmp_path, {("t_bad", "kit_rtl"): ERR}, {("t_bad", "kit_rtl"): ERR})
    assert r["verdict"] == "PASS" and r["failed"] == [] and [h["type"] for h in r["held"]] == ["t_bad"]


def test_new_failures_still_block_passing_on_live_other_error_other_stage_or_type_absent(tmp_path):
    r = with_base(tmp_path / "a", {("t_bad", "kit_rtl"): ERR}, {})                                      # passes on live: NEW
    assert r["verdict"] == "FAIL" and r["failed"][0]["type"] == "t_bad" and "live event: PASS" in r["failed"][0]["baseline"]
    r = with_base(tmp_path / "b", {("t_bad", "kit_rtl"): ERR}, {("t_bad", "kit_rtl"): ERR + " other"})   # another error line: NEW
    assert r["verdict"] == "FAIL" and not r["held"]
    r = with_base(tmp_path / "c", {("t_bad", "kit_topology"): ERR}, {("t_bad", "kit_rtl"): ERR})        # another stage: NEW
    assert r["verdict"] == "FAIL"
    r = with_base(tmp_path / "d", {("t_ok", "kit_topology"): ERR}, {("t_ok", "kit_topology"): ERR}, drop=("t_ok",))   # live plan lacks the type: NEW
    assert r["verdict"] == "FAIL" and "not bound on the live event" in r["failed"][0]["baseline"]


def test_old_failure_held_while_a_new_one_in_the_same_run_blocks(tmp_path):
    r = with_base(tmp_path, {("t_bad", "kit_rtl"): ERR, ("t_ok", "kit_topology"): ERR}, {("t_bad", "kit_rtl"): ERR})
    assert r["verdict"] == "FAIL" and [f["type"] for f in r["failed"]] == ["t_ok"] and [h["type"] for h in r["held"]] == ["t_bad"]
