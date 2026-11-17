"""Current context lint and early source-stage breaker regressions."""
import pathlib
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import kit_wave as kw
import flow_guard as fg

OLD = "1510a6a72050463dbb3fbc95b8b560ec1943e4ab9ff96b7af94457ee89804185"
NEW = "ed968f4cc6e6734b9b9d826e2e0c5bee74a220d8e55074f9a73fdc3e715f0e0d"
CFG = {"dies": {"s81": {"plan_sha256": NEW, "src": "/published/d2", "src_sha": "new"}}}

def row(item="slice_station__t21", plan=NEW, t=1, bad=True):
    return dict(die="s81", item=item, plan_sha=plan, started=t,
                status="FAIL" if bad else "DONE", reason="sdc_lint" if bad else "")

def test_actual_seven_old_plan_failures_do_not_hold_current_wildcard():
    names = ["t24__cleece78ec", "t30__cl1653104c", "t30__cl6a190133",
             "t21", "t26", "t37", "t40__clc8fb2c8c"]
    rows = [row("slice_station__"+n, OLD) for n in names]
    cfg = dict(CFG, _lint_fail=kw.lint_failures(CFG, rows, lambda r: {}))
    assert kw.lint_clean_item(cfg, "s81", "slice_station__*")
    assert all(r["status"] == "FAIL" for r in rows)

def test_same_current_context_fail_still_blocks_and_success_releases():
    bad = row()
    sp = lambda r: dict(src="/published/d2", src_sha="new")
    assert kw.lint_failures(CFG, [bad], sp)["s81"] == {bad["item"]}
    assert not kw.lint_failures(CFG, [bad, row(t=2, bad=False)], sp)["s81"]

def test_unrelated_success_cannot_clear_current_failure():
    bad = row()
    assert kw.lint_failures(CFG, [bad, row(plan=OLD, t=2, bad=False)], lambda r: {})["s81"] == {bad["item"]}

def test_known_old_source_excluded_but_unknown_legacy_kept():
    bad = row()
    assert kw.lint_failures(CFG, [bad], lambda r: {"src": "/published/old"}) == {}
    assert kw.lint_failures(CFG, [bad], lambda r: {"src_sha": "old"}) == {}
    legacy = row(plan=None)
    assert kw.lint_failures(CFG, [legacy], lambda r: {})["s81"] == {legacy["item"]}

def test_actual_source_then_snapshot_failure_closes_only_source_class():
    st = {"flow_guard": {"open": {}, "last": {}, "last2": {}, "probation": {}}}
    for key, stage in (("source", "src_manifest"), ("snapshot", "kit_snap")):
        st["flow_guard"]["open"][key] = dict(die="s81", stage=stage, state="probe",
            probe={"*": "col"}, fams=["col"], kind="")
    assert fg.stage_rank("mkdir") < fg.stage_rank("src_manifest") < fg.stage_rank("kit_snap")
    fg.probe_result(st, "s81", "col", "kit_snap", passed=False, failed_stage=True)
    assert "source" not in st["flow_guard"]["open"]
    assert st["flow_guard"]["open"]["snapshot"]["state"] == "shut"

def test_unknown_failure_does_not_release_known_source_class():
    st = {"flow_guard": {"open": {"source": dict(die="s81", stage="src_manifest",
        state="probe", probe={"*": "col"}, fams=["col"], kind="")},
        "last": {}, "last2": {}, "probation": {}}}
    fg.probe_result(st, "s81", "col", "unknown", passed=False, failed_stage=True)
    assert st["flow_guard"]["open"]["source"]["state"] == "shut"
