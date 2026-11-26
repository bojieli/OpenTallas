"""PRE-SPEED-1125 / PRE-REUSE-1125 (FLOW-0930 S-04, F-18): a scoped PRE prewarms die-wide reset trees and judges only its scope;
the bind reuses a matching standalone PRE record and keeps advisories off its path."""
import json
import sys
import types
from pathlib import Path

import pytest

import bind
import derived_drop as DD
import plan_gate_pre as G


# ---------------------------------------------------------------- S-04: scoped prewarm / per-type classes
def test_scope_selection_keeps_die_wide_types_and_drops_out_of_scope_per_type():
    sel = {"plan": {"A": ["LANDREMAP"], "B": ["LANDREMAP"], "C": ["STARTSETTLE"], "D": ["DERIVED", "STARTSETTLE"]},
           "base": {"A": ["LANDREMAP"], "B": ["LANDREMAP"]}}
    got = G.scope_selection(sel, {"A"})
    assert got == {"plan": {"A": ["LANDREMAP"], "C": ["STARTSETTLE"], "D": ["DERIVED", "STARTSETTLE"]}, "base": {"A": ["LANDREMAP"]}}
    assert G.scope_selection(sel, None) is sel


def test_scope_selection_mutant_old_filter_would_drop_die_wide():
    # the pre-1125 filter (tn in scope only) left STARTSETTLE's trees to serial on-demand solves: C must stay
    sel = {"plan": {"C": ["STARTSETTLE"]}}
    assert "C" in G.scope_selection(sel, {"A"})["plan"]
    assert "C" not in {tn for tn in sel["plan"] if tn in {"A"}}


def _landremap_setup(monkeypatch, tmp_path):
    raw = {"partition_types": {"A": {}, "B": {}}}
    p, b = tmp_path / "p.json", tmp_path / "b.json"
    p.write_text(json.dumps(raw))
    b.write_text(json.dumps(raw))
    monkeypatch.setattr(G, "moved_types", lambda r, br: {"A": ["core"], "B": ["core"]})
    monkeypatch.setattr(G, "landremap_same", lambda r, br, tn: {f"x.{tn}": f"rst_{tn}"})
    monkeypatch.setattr(G, "planned_shifts", lambda t, bt: [])
    solved = []

    def tree_fn(r, pp, tn):
        solved.append(tn)
        return {f"rst_{tn}": (1, (0, 0))}
    return p, b, solved, tree_fn


def test_landremap_scoped_solves_only_scope(monkeypatch, tmp_path):
    p, b, solved, tree_fn = _landremap_setup(monkeypatch, tmp_path)
    monkeypatch.setattr(G, "_SCOPE", {"A"})
    G.check_landremap(str(p), str(b), tree_fn=tree_fn)
    assert set(solved) == {"A"}


def test_landremap_unscoped_solves_all(monkeypatch, tmp_path):
    p, b, solved, tree_fn = _landremap_setup(monkeypatch, tmp_path)
    monkeypatch.setattr(G, "_SCOPE", None)
    G.check_landremap(str(p), str(b), tree_fn=tree_fn)
    assert set(solved) == {"A", "B"}


def test_derived_drop_scope_limits_per_type_checks(monkeypatch):
    seen = []
    monkeypatch.setattr(DD, "derived_todo", lambda raw: [("A", {}), ("B", {})])
    monkeypatch.setattr(DD, "rstreach_type", lambda tn, t, S, bind_rtl=None: seen.append(tn) or [])
    raw = {"partition_types": {"A": {}, "B": {}}}
    DD.findings(raw, "p.json", classes=("RSTREACH",), solver=object(), scope={"B"})
    assert seen == ["B"]
    seen.clear()
    DD.findings(raw, "p.json", classes=("RSTREACH",), solver=object())
    assert seen == ["A", "B"]


# ---------------------------------------------------------------- F-18: PRE record + bind reuse
@pytest.fixture
def files(tmp_path, monkeypatch):
    monkeypatch.setenv("OT_PRE_RECORD_DIR", str(tmp_path / "store"))
    for k in ("OT_PLAN_GATE_PRE_RECORD", "OT_PLAN_GATE_PRE_REUSE", "OT_BIND_ONLY_TYPES", "OT_PLAN_GATE_PRE", "OT_PLAN_GATE_BASELINE",
              "OT_PLAN_GATE_ADVISORY", "OT_PLAN_GATE_SKIP", "OT_PRE_RECORD"):
        monkeypatch.delenv(k, raising=False)
    plan, ab, base = tmp_path / "plan.json", tmp_path / "ab.json", tmp_path / "base.json"
    plan.write_text('{"partition_types": {"A": {}, "B": {}}}')
    ab.write_text('{"x": 1}')
    base.write_text('{"partition_types": {}}')
    return plan, ab, base, tmp_path


class NS:
    def __init__(self, plan, out, asbuilt=None, cmd="bind"):
        self.plan, self.out, self.asbuilt, self.cmd = str(plan), str(out), asbuilt and str(asbuilt), cmd


def _store(plan, ab, base, scope=None, skip=(), lines=()):
    return G.store_record(G.pre_record(plan, ab, base, scope, skip, list(lines)))


def test_record_roundtrip_and_find(files):
    plan, ab, base, d = files
    p = _store(plan, ab, base, lines=["FAIL GEOM x A", "WARN ADV-X y", "WARN Z"])
    rec = json.loads(p.read_text())
    assert rec["plan_sha256"] == G.file_sha(plan) and rec["result"] == "FAIL" and rec["advisories"] == 1 and rec["warns"] == ["WARN Z"]
    got = bind._pre_record_find(NS(plan, d / "out", ab), str(base), G)
    assert got and got[1]["fails"] == ["FAIL GEOM x A"]


def test_record_rejected_on_plan_asbuilt_or_baseline_change(files):
    plan, ab, base, d = files
    _store(plan, ab, base)
    assert bind._pre_record_find(NS(plan, d / "o", ab), None, G) is None          # baseline differs
    ab2 = d / "ab2.json"
    ab2.write_text('{"x": 2}')
    assert bind._pre_record_find(NS(plan, d / "o", ab2), str(base), G) is None    # as-built differs
    plan.write_text('{"partition_types": {"A": {"m": 1}, "B": {}}}')                # mutant: the plan changed after the PRE
    assert bind._pre_record_find(NS(plan, d / "o", ab), str(base), G) is None


def test_scoped_record_only_for_covered_scoped_bind(files, monkeypatch):
    plan, ab, base, d = files
    _store(plan, ab, base, scope={"A"})
    assert bind._pre_record_find(NS(plan, d / "o", ab), str(base), G) is None     # a full bind needs an unscoped record
    monkeypatch.setenv("OT_BIND_ONLY_TYPES", "A,B")
    assert bind._pre_record_find(NS(plan, d / "o", ab), str(base), G) is None
    monkeypatch.setenv("OT_BIND_ONLY_TYPES", "A")
    assert bind._pre_record_find(NS(plan, d / "o", ab), str(base), G) is not None


def test_record_that_skipped_a_bind_class_or_unchecked_is_not_reused(files):
    plan, ab, base, d = files
    _store(plan, ab, base, skip=("LANDREMAP",))
    assert bind._pre_record_find(NS(plan, d / "o", ab), str(base), G) is None
    _store(plan, ab, base, skip=("ADVISORY",), lines=["FAIL PRE-DIFF-UNCHECKED base x"])
    assert bind._pre_record_find(NS(plan, d / "o", ab), str(base), G) is None
    _store(plan, ab, base, skip=("ADVISORY",))
    assert bind._pre_record_find(NS(plan, d / "o", ab), str(base), G) is not None


def test_reuse_off_and_explicit_record_path(files, monkeypatch):
    plan, ab, base, d = files
    p = _store(plan, ab, base)
    monkeypatch.setenv("OT_PLAN_GATE_PRE_REUSE", "0")
    assert bind._pre_record_find(NS(plan, d / "o", ab), str(base), G) is None
    monkeypatch.delenv("OT_PLAN_GATE_PRE_REUSE")
    monkeypatch.setenv("OT_PRE_RECORD_DIR", str(d / "empty"))
    j = d / "pre.json"
    j.write_text(json.dumps({"findings": [], "pre_record": json.loads(p.read_text())}))
    monkeypatch.setenv("OT_PLAN_GATE_PRE_RECORD", str(j))
    assert bind._pre_record_find(NS(plan, d / "o", ab), str(base), G)[0] == j


def _fake_gate(monkeypatch, store, findings=()):
    calls = []
    mod = types.ModuleType("plan_gate_pre")
    mod.CLASSES, mod.ELAB_CLASSES = G.CLASSES, G.ELAB_CLASSES
    mod.record_store = lambda: store

    def check(tree, plan, asbuilt=None, baseline=None, skip=(), **_kw):
        calls.append(set(skip))
        return list(findings)
    mod.check = check
    monkeypatch.setitem(sys.modules, "plan_gate_pre", mod)
    return calls


def test_bind_reuses_record_runs_only_elab_classes_and_refuses_on_record_fail(files, monkeypatch, capsys):
    plan, ab, base, d = files
    _store(plan, ab, base, lines=["FAIL GEOM-STATION-IN-CORE A s1", "FAIL ROWSINK stale A"])
    calls = _fake_gate(monkeypatch, d / "store")
    monkeypatch.setenv("OT_PLAN_GATE_BASELINE", str(base))
    assert bind._plan_gate_pre(NS(plan, d / "out", ab)) == 2                       # the record's GEOM FAIL refuses
    out = capsys.readouterr().out
    assert "PRE-REUSE record" in out and "GEOM-STATION-IN-CORE" in out
    assert "ROWSINK stale" not in out                                              # elab classes re-run here, not copied
    ran = set(G.CLASSES) - calls[-1]
    assert ran == set(G.ELAB_CLASSES)


def test_bind_without_record_runs_full_pre_minus_advisory(files, monkeypatch):
    plan, ab, base, d = files
    calls = _fake_gate(monkeypatch, d / "store")
    assert bind._plan_gate_pre(NS(plan, d / "out", ab)) == 0
    assert calls[-1] == {"ROWS", "GEOM", "ADVISORY"}
    monkeypatch.setenv("OT_PLAN_GATE_ADVISORY", "on")
    plan.write_text('{"partition_types": {"A": {"z": 1}}}')
    bind._plan_gate_pre(NS(plan, d / "out", ab))
    assert "ADVISORY" not in calls[-1]


def test_scoped_advisory_runs_per_type_checks_on_view_and_lane_checks_on_whole_plan(monkeypatch, tmp_path):
    import plan_advisory as PA
    raw = {"partition_types": {"A": {}, "B": {}}, "partitions": [{"type": "A"}, {"type": "B"}], "lanes": [1]}
    p = tmp_path / "p.json"
    p.write_text(json.dumps(raw))
    runs = []
    monkeypatch.setattr(PA, "run", lambda r, pp, tree, checks=None, **kw: runs.append((sorted(r["partition_types"]), set(checks))) or [])
    G.advisory_lines(None, str(p), scope={"A"})
    assert runs[0][0] == ["A"] and not runs[0][1] & set(G.ADV_DIE_CONTEXT)
    assert runs[1][0] == ["A", "B"] and runs[1][1] <= set(G.ADV_DIE_CONTEXT) and runs[1][1]
    runs.clear()
    G.advisory_lines(None, str(p))                                                 # unscoped: one whole-plan run
    assert len(runs) == 1 and runs[0][0] == ["A", "B"]
    runs.clear()
    monkeypatch.setenv("OT_PRE_ADV_SCOPE", "full")
    G.advisory_lines(None, str(p), scope={"A"})
    assert len(runs) == 1 and runs[0][0] == ["A", "B"]
