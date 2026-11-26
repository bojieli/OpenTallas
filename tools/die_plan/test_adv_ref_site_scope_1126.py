"""P-SCOPE-VIEW-KEYOUT (S81-PRE-KEYERR 11-26): a scoped PRE ran ADV-REF-SITE on a scope view of the plan; the die reset wavefront
reads reset.keep_outs of types outside the scope (S81 col_h10_r1 -> col_h10_r0_p1), so every scoped type was NOT-EVALUABLE KeyError.
REF-SITE now runs on the whole plan, limited to the scope by $OT_ADV_REFSITE_TYPES.
    python3 -m pytest -q tools/die_plan/test_adv_ref_site_scope_1126.py      (MUTANT tests prove the guard fails without the fix)"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_ref_site as ARS  # noqa: E402
import plan_advisory as PA  # noqa: E402
import plan_gate_pre as PGP  # noqa: E402
import ref_site as RS  # noqa: E402


def die():
    """A (in scope) and B; the die reset keeps a published out of B (reset.keep_outs), as S81 keeps col_h10_r0_p1"""
    return {"partition_types": {"A": {"clock": {}}, "B": {"clock": {}}}, "partitions": [{"name": "a0", "type": "A"}, {"name": "b0", "type": "B"}],
            "reset": {"keep_outs": {"B": [0]}}}


def fake_ref_site(monkeypatch):
    """type_refs that solves 'the die wavefront' the way reset_tree._wf_solve_once does: outs per plan type, then keep_outs[tn]"""
    seen = []
    monkeypatch.setattr(RS.TS, "_plan", lambda r, p: r)
    monkeypatch.setattr(RS.TS, "_plandir", lambda p: None)
    monkeypatch.setattr(RS.TS, "type_tables", lambda r, tn: [1])

    def type_refs(P, raw, tn):
        seen.append(tn)
        outs = {t: set() for t in P["partition_types"]}
        for t, kept in (P.get("reset") or {}).get("keep_outs", {}).items():
            outs[t].update(kept)                                   # KeyError on a scope view that dropped t
        return {"x[0]": ("tap", "clk_t0", (0.0, 0.0), [])}, 1
    monkeypatch.setattr(RS, "type_refs", type_refs)
    monkeypatch.setenv("OT_REF_SITE_J", "1")
    return seen


def test_ref_site_is_die_context_with_scope_env():
    assert "REF-SITE" in PGP.ADV_DIE_CONTEXT and "OT_ADV_REFSITE_TYPES" in PGP.ADV_SCOPE_ENV
    assert "RESET-NAME" in PGP.ADV_DIE_CONTEXT and "OT_ADV_RESETNAME_TYPES" in PGP.ADV_SCOPE_ENV


def test_scoped_advisory_runs_ref_site_on_whole_plan_limited_to_scope(monkeypatch, tmp_path):
    p = tmp_path / "p.json"
    p.write_text(json.dumps(die()))
    monkeypatch.delenv("OT_ADV_REFSITE_TYPES", raising=False)
    monkeypatch.delenv("OT_ADV_RESETNAME_TYPES", raising=False)
    runs = []
    monkeypatch.setattr(PA, "run", lambda r, pp, tree, checks=None, **kw: runs.append(
        (sorted(r["partition_types"]), set(checks), os.environ.get("OT_ADV_REFSITE_TYPES"))) or [])
    PGP.advisory_lines(None, str(p), scope={"A"})
    view, whole = runs
    assert view[0] == ["A"] and "REF-SITE" not in view[1]
    assert whole[0] == ["A", "B"] and "REF-SITE" in whole[1] and whole[2] == "A"
    assert "OT_ADV_REFSITE_TYPES" not in os.environ                # restored after the run


def test_adv_ref_site_whole_plan_scope_env_is_evaluable(monkeypatch):
    seen = fake_ref_site(monkeypatch)
    monkeypatch.setenv("OT_ADV_REFSITE_TYPES", "A")
    out = ARS.findings(die(), "/nonexistent/plan.json")
    assert seen == ["A"]                                           # only the scope's type is judged
    assert not any("NOT-EVALUABLE" in x for x in out), out
    assert any("SUMMARY 1 types" in x and "0 not evaluable" in x for x in out), out


def test_adv_ref_site_unscoped_judges_every_type(monkeypatch):
    seen = fake_ref_site(monkeypatch)
    monkeypatch.delenv("OT_ADV_REFSITE_TYPES", raising=False)
    ARS.findings(die(), "/nonexistent/plan.json")
    assert seen == ["A", "B"]


def test_MUTANT_scope_view_makes_ref_site_not_evaluable(monkeypatch):
    """without the fix REF-SITE ran on scope_view: B dropped, keep_outs[B] -> KeyError, the scoped type NOT-EVALUABLE"""
    fake_ref_site(monkeypatch)
    monkeypatch.delenv("OT_ADV_REFSITE_TYPES", raising=False)
    out = ARS.findings(PGP.scope_view(die(), {"A"}), "/nonexistent/plan.json")
    assert any("NOT-EVALUABLE A KeyError: 'B'" in x for x in out), out


def test_no_view_checks_never_runs_all_checks_on_the_view(monkeypatch, tmp_path):
    p = tmp_path / "p.json"
    p.write_text(json.dumps(die()))
    runs = []
    monkeypatch.setattr(PA, "CHECKS", (("REF-SITE", "adv_ref_site"),))
    monkeypatch.setattr(PA, "run", lambda r, pp, tree, checks=None, **kw: runs.append((sorted(r["partition_types"]), list(checks))) or [])
    PGP.advisory_lines(None, str(p), scope={"A"})
    assert runs == [(["A", "B"], ["REF-SITE"])]
