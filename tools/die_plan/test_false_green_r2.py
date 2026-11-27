"""HEAD-INT-R2 P-FALSE-GREEN / P-RESET-RECEIPT (1126): crashed checks are never PASS, gate jsons carry the plan sha, the native
release verdict is explicit, a type's reset form is hashed.   python3 -m pytest -q tools/die_plan/test_false_green_r2.py
Each test with MUTANT in its name proves the guard fails when the fix is taken out."""
import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_reset_names as ARN  # noqa: E402
import head_native_release as HNR  # noqa: E402
import plan_gate_pre as PGP  # noqa: E402
import reset_form as RF  # noqa: E402
import rows_s81_monleg as ML  # noqa: E402


def head_plan():
    """two HEAD-like types: collector_children keyed bus/fault/ready/seam/xy_um (no index, no monitor_* band)"""
    def lc():
        return {"collector_tree": {"root": [1.0, 2.0], "relays": [{"q": "rst_rl_1", "xy": [10.0, 20.0], "depth": 1, "kind": "relay"},
                                                                  {"q": "rst_rl_2", "xy": [30.0, 40.0], "depth": 1, "kind": "relay"}]},
                "collector_children": [{"bus": "b", "fault": "f", "ready": "r", "seam": "s", "xy_um": [1, 1], "node": "rst_rl_1"}],
                "bands": {}}
    t = lambda: {"reset": {"sync_stages": 2, "local_taps_um": [[1.0, 2.0]], "export_seats_um": {"p0": [5.0, 6.0]}},
                 "reset_start_raw_exports": [{"port": "rst_start_raw_0", "net": "rst_rl_1", "xy_um": [3.0, 4.0]}],
                 "private_reset_start_exports": True,
                 "clock": {"start_capture_um": [479.5, 720.0], "landing_export_form": "fwd_buffer", "insertion_ps": 100.0,
                           "landing_reader_start": {"depth": 2, "branches": {"d1_i": {"stages": [{"xy_um": [1.0, 2.0], "raw_reset": "rr_t1"}]}}},
                           "landing_local_resets": [{"name": "nw", "raw": "rr_t19", "xy_um": [1.0, 2.0]}],
                           "landing_contract": lc()}}
    return {"partition_types": {"hd_a": t(), "hd_b": t()}, "partitions": [{"name": "p1", "type": "hd_a"}, {"name": "sp5", "type": "hd_b"}],
            "reset": {"sync_stages": 2, "release": "wavefront", "root_part": "sp5", "in_sites": {"hd_a": [718.8, 8.6], "hd_b": [1.0, 1.0]}}}


# ------------------------------------------------------------------------------ MONLEG KeyError 'index'
def test_monleg_census_head_children_without_index():
    c = ML.census(head_plan())
    assert c["pairs"] == 0 and c["over_reach"] == 0


def test_monleg_check_head_plan_no_unchecked(tmp_path):
    p = tmp_path / "plan.json"
    p.write_text(json.dumps(head_plan()))
    out = PGP.check_monleg(str(p))
    assert not any("UNCHECKED" in x for x in out), out


def test_monleg_still_counts_indexed_children():
    raw = head_plan()
    lc = raw["partition_types"]["hd_a"]["clock"]["landing_contract"]
    lc["collector_children"][0]["index"] = 0
    lc["bands"] = {"monitor_0": {"rect_um": [2000, 2000, 2100, 2100]}}
    c = ML.census(raw)
    assert c["pairs"] == 1 and c["over_reach"] == 1


def test_MUTANT_old_monleg_pairs_crash_becomes_fail(tmp_path, monkeypatch):
    def old_pairs(raw, only=None):
        for tn, t in raw["partition_types"].items():
            for c in t["clock"]["landing_contract"]["collector_children"]:
                c["index"]
                yield
    monkeypatch.setattr(ML, "pairs", old_pairs)
    p = tmp_path / "plan.json"
    p.write_text(json.dumps(head_plan()))
    out = PGP.check_monleg(str(p))
    assert out and out[0].startswith("WARN MONLEG-REACH-UNCHECKED KeyError")      # the check itself still reports a WARN ...
    assert PGP.promote_crashes(out, env={})[0].startswith("FAIL MONLEG-REACH-UNCHECKED KeyError")      # ... and the PRE turns it into a FAIL


# ------------------------------------------------------------------------------ crash -> FAIL
def test_promote_crashes_unchecked_and_not_checked():
    lines = ["WARN MONLEG-REACH-UNCHECKED KeyError: 'index'",
             "WARN ADV-RESET-NAME hd_st_n3_turn: not checked (KeyError: 'sp5')",
             "WARN TREEPRE not checked: ValueError: bad",
             "WARN FTSITE-UNCHECKED hd_x: OSError: gone",
             "LIST PRE-TIME 1 s"]
    out = PGP.promote_crashes(lines, env={})
    assert out[0] == "FAIL MONLEG-REACH-UNCHECKED KeyError: 'index'"
    assert out[1].startswith("FAIL ADV-RESET-NAME-UNCHECKED hd_st_n3_turn: not checked (KeyError")
    assert out[2].startswith("FAIL TREEPRE-UNCHECKED not checked: ValueError")
    assert out[3].startswith("FAIL FTSITE-UNCHECKED hd_x: OSError")
    assert out[4] == lines[4]


def test_promote_crashes_keeps_declared_coverage_limits_as_warn():
    lines = ["WARN GENDRY-UNCHECKED a: kit generator timeout after 5 s",
             "WARN ADV-HOLDCELL-BUDGET not checked: no hold cache (adv_harvest_hold.py OUT.json)",
             "WARN ADV-TAP-LOAD not checked: NO TAP DATA: 0 types had a kit netlist",
             "WARN ADV-RESET-NAME summary: 0 of 2 referencing type(s) checked, 0 with stale names, 2 not checked (budget -1 s)"]
    assert PGP.promote_crashes(lines, env={}) == lines


def test_promote_crashes_opt_out_env():
    lines = ["WARN MONLEG-REACH-UNCHECKED KeyError: 'index'"]
    assert PGP.promote_crashes(lines, env={"OT_PRE_CRASH_WARN": "1"}) == lines


def test_pre_main_verdict_unchecked_exit_1(tmp_path, monkeypatch, capsys):
    """a check that crashed (only WARN before) now ends PLAN-GATE-PRE UNCHECKED with exit 1 and no reusable record"""
    p = tmp_path / "plan.json"
    p.write_text(json.dumps(head_plan()))
    monkeypatch.setattr(PGP, "check", lambda *a, **k: PGP.promote_crashes(["WARN MONLEG-REACH-UNCHECKED KeyError: 'index'"], env={}))
    monkeypatch.setattr(PGP, "lane_slot", lambda tree: None)
    monkeypatch.setenv("OT_PRE_RECORD", "off")
    out = tmp_path / "pre.json"
    rc = PGP.main(["check", "--tree", str(tmp_path), "--plan", str(p), "--json", str(out), "--quiet"])
    assert rc == 1
    assert "PLAN-GATE-PRE UNCHECKED" in capsys.readouterr().out
    rec = json.loads(out.read_text())
    assert rec["plan_sha256"] == hashlib.sha256(p.read_bytes()).hexdigest()          # gate json carries the plan sha
    assert rec["result"] == "FAIL" and set(rec["reset_forms"]) == {"hd_a", "hd_b"}


# ------------------------------------------------------------------------------ ADV-RESET-NAME sp5
def test_reset_name_scoped_view_names_the_cause():
    view = PGP.scope_view(head_plan(), {"hd_a"})                  # drops partition sp5 (root_part of the die reset)
    with pytest.raises(KeyError, match="root_part 'sp5'"):
        ARN.findings(view, "/nonexistent/plan.json")


def test_reset_name_runs_on_whole_plan_for_scope():
    assert "RESET-NAME" in PGP.ADV_DIE_CONTEXT


def test_MUTANT_reset_name_in_scoped_checks_would_crash():
    """without the fix RESET-NAME was a scoped-view check: scope_view removed sp5 and the tree solve died (KeyError sp5)"""
    assert "RESET-NAME" in PGP.ADV_DIE_CONTEXT
    view = PGP.scope_view(head_plan(), {"hd_a"})
    assert "sp5" not in {x["name"] for x in view["partitions"]}


# ------------------------------------------------------------------------------ native release verdict
def test_native_release_status_explicit():
    q = HNR.status({"verdict": "QUALIFIED_CONDITIONAL", "native_targets": [1] * 12, "receipt_sha256": "ab"})
    assert q["counts_as_pass"] and q["conditions"] == list(HNR.CONDITIONS) and q["core_cycle_release"] is None and q["native_targets"] == 12
    assert not HNR.status({"verdict": "PENDING"})["counts_as_pass"]
    assert HNR.status(None)["verdict"] == "NOT_APPLICABLE" and HNR.status(None)["counts_as_pass"]


def test_MUTANT_native_release_substring_verdict_is_not_a_pass():
    for v in ("QUALIFIED_CONDITIONAL_EXPIRED", "NOT_QUALIFIED_CONDITIONAL", "qualified_conditional", "QUALIFIED"):
        assert not HNR.status({"verdict": v})["counts_as_pass"], v


# ------------------------------------------------------------------------------ reset form hash
def test_reset_form_stable_and_ignores_timing():
    raw = head_plan()
    a = RF.form_hash(raw, "hd_a")
    raw2 = copy.deepcopy(raw)
    raw2["partition_types"]["hd_a"]["clock"]["insertion_ps"] = 999.0           # timing only: same reset form
    raw2["partition_types"]["hd_a"]["clock"]["start_capture_um"][0] += 0.0004  # rounding noise
    assert RF.form_hash(raw2, "hd_a") == a and RF.form_hash(raw, "hd_a") == a
    assert RF.form_hash(raw, "nope") is None


@pytest.mark.parametrize("mut,section", [
    (lambda r: r["partition_types"]["hd_a"]["clock"]["start_capture_um"].__setitem__(0, 498.8), "start_stages"),
    (lambda r: r["partition_types"]["hd_a"]["reset"]["export_seats_um"].__setitem__("p0", [5.0, 7.0]), "export_seats_um"),
    (lambda r: r["partition_types"]["hd_a"]["reset_start_raw_exports"][0].__setitem__("net", "rst_rl_9"), "raw_exports"),
    (lambda r: r["partition_types"]["hd_a"]["reset_start_raw_exports"].append({"port": "rst_start_raw_1", "net": "n", "xy_um": [1, 1]}), "raw_exports"),
    (lambda r: r["partition_types"]["hd_a"]["clock"]["landing_contract"]["collector_tree"]["relays"][0].__setitem__("q", "rst_rl_77"), "reset_tree"),
    (lambda r: r["partition_types"]["hd_a"]["clock"]["landing_contract"]["collector_tree"]["relays"][0].__setitem__("xy", [11.0, 20.0]), "reset_tree"),
    (lambda r: r["partition_types"]["hd_a"]["clock"]["landing_reader_start"]["branches"]["d1_i"]["stages"][0].__setitem__("raw_reset", "rr_t2"), "start_stages"),
    (lambda r: r["reset"]["in_sites"].__setitem__("hd_a", [918.6, 8.6]), "die_reset"),
    (lambda r: r["partition_types"]["hd_a"]["reset"].__setitem__("local_taps_um", [[9.0, 9.0]]), "type_reset"),
])
def test_MUTANT_reset_form_changes_flag_resign(mut, section):
    base = head_plan()
    cur = copy.deepcopy(base)
    mut(cur)
    res = RF.compare(RF.forms(cur), {k: v for k, v in RF.forms(base).items()})
    assert res["hd_a"]["verdict"] == RF.RESIGN and res["hd_a"]["changed"] == [section]
    assert res["hd_b"]["verdict"] == "SAME"                 # a change on one type never flags another


def test_reset_form_no_receipt_and_cli(tmp_path, capsys):
    base, cur = head_plan(), head_plan()
    cur["partition_types"]["hd_b"]["clock"]["start_capture_um"] = [1.0, 1.0]
    pb, pc = tmp_path / "b.json", tmp_path / "c.json"
    pb.write_text(json.dumps(base))
    pc.write_text(json.dumps(cur))
    assert RF.compare(RF.forms(cur), {})["hd_a"]["verdict"] == "NO-RECEIPT"
    out = tmp_path / "r.json"
    assert RF.main(["check", str(pc), "--signed-plan", str(pb), "--json", str(out)]) == 0                # a flag, not a failure
    assert RF.main(["check", str(pc), "--signed-plan", str(pb), "--strict"]) == 3
    rec = json.loads(out.read_text())
    assert rec["resign_required"] == ["hd_b"] and rec["plan_sha256"] == hashlib.sha256(pc.read_bytes()).hexdigest()
    assert RF.main(["check", str(pc), "--signed-plan", "hd_a=" + str(pb)]) == 0                     # TYPE=PLAN form
    assert "RESET-RECEIPT hd_b: RE-SIGN-REQUIRED (changed: start_stages)" in capsys.readouterr().out


def test_pre_reset_receipt_is_a_list_line_not_a_fail(tmp_path, monkeypatch, capsys):
    base, cur = head_plan(), head_plan()
    cur["partition_types"]["hd_a"]["clock"]["start_capture_um"] = [1.0, 1.0]
    pb, pc, rcp = tmp_path / "b.json", tmp_path / "c.json", tmp_path / "rcp.json"
    pb.write_text(json.dumps(base))
    pc.write_text(json.dumps(cur))
    rcp.write_text(json.dumps({"types": RF.forms(base)}))
    monkeypatch.setattr(PGP, "check", lambda *a, **k: [])
    monkeypatch.setattr(PGP, "lane_slot", lambda tree: None)
    monkeypatch.setenv("OT_PRE_RECORD", "off")
    out = tmp_path / "pre.json"
    rc = PGP.main(["check", "--tree", str(tmp_path), "--plan", str(pc), "--json", str(out), "--reset-receipts", str(rcp)])
    assert rc == 0
    assert "LIST RESET-RECEIPT hd_a: RE-SIGN-REQUIRED" in capsys.readouterr().out
    assert json.loads(out.read_text())["reset_receipt"]["resign_required"] == ["hd_a"]


# ------------------------------------------------------------------------------ plan sha in the other gate jsons
def test_bind_stamp_plan_sha():
    import bind
    bind._GATE_PLAN.clear()
    assert bind._stamp_plan({"verdict": "PASS"}) == {"verdict": "PASS"}        # no plan named: untouched
    bind._GATE_PLAN.update(sha256="ab" * 32)
    try:
        assert bind._stamp_plan({"verdict": "PASS"})["plan_sha256"] == "ab" * 32
        assert bind._stamp_plan({"plan_sha256": "keep"})["plan_sha256"] == "keep"
        assert bind._stamp_plan([1]) == [1]
    finally:
        bind._GATE_PLAN.clear()


def test_gate_json_writers_stamp_plan_source():
    d = Path(__file__).resolve().parent
    assert '"plan_sha256"' in (d / "check.py").read_text() or "plan_sha256=hashlib" in (d / "check.py").read_text()
    assert "plan_sha256=_sha(a.plan)" in (d / "gen_lane_latcheck.py").read_text()
    assert "result['plan_sha256']" in (d / "reset_cohort_model.py").read_text()
    bsrc = (d / "bind.py").read_text()
    for nm in ("tie_audit", "reset_core_class", "por_gate", "parent_id_straps"):
        assert f'_write_gate_json(out.parent / "bind_{nm}.json"' in bsrc
