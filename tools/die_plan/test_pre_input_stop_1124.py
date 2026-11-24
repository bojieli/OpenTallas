"""PRE-INPUT-STOP-1124 (COORD; FAM-S81-COL-H9R0 epyc7: 3.5 h of PRE, then FAIL INPUT-MISSING x5 svc sources missing from the fork):
the presence checks run first and a missing input ends PRE before any slow class; LIST PRE-TIME names where the time went."""
import json
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import plan_gate_pre as G  # noqa: E402


def _tree(tmp, missing=True):
    (tmp / "tools/die_plan").mkdir(parents=True)
    (tmp / "tools/die_plan/schema.py").write_text("SCHEMA = {}\ndef validate_structure(o):\n    return []\n")
    (tmp / "rtl").mkdir()
    (tmp / "rtl/a.sv").write_text("")
    files = ["rtl/a.sv"] + (["s81_svc_r8_j8_sources/dsdv_svc_rs_fv_j8_hi.sv"] if missing else [])
    plan = tmp / "plan.json"
    plan.write_text(json.dumps({"partition_types": {}, "asbuilt": {"base": ".", "files": files}}))
    return plan


def test_missing_input_stops_before_slow_classes(tmp_path, monkeypatch):
    plan = _tree(tmp_path)
    slow = []
    monkeypatch.setattr(G, "check_tools", lambda *a, **k: slow.append("TOOLS") or [])
    monkeypatch.setattr(G, "check_istprice", lambda *a, **k: slow.append("ISTPRICE") or [])
    monkeypatch.setattr(G, "check_gendry", lambda *a, **k: slow.append("GENDRY") or [])
    f = G.check(str(tmp_path), str(plan), skip=["TREEPRE"], gendry=True)
    assert any(x.startswith("FAIL INPUT-MISSING files x1") for x in f), f
    assert f[-2].startswith("LIST PRE-INPUT-STOP 1 missing-input") and f[-1].startswith("LIST PRE-TIME")
    assert slow == []


def test_stop_can_be_turned_off_and_clean_tree_runs_all(tmp_path, monkeypatch):
    plan = _tree(tmp_path)
    ran = []
    monkeypatch.setattr(G, "check_istprice", lambda *a, **k: ran.append(1) or [])
    monkeypatch.setenv("OT_PRE_INPUT_STOP", "0")
    f = G.check(str(tmp_path), str(plan), skip=["TREEPRE"])
    assert ran and not any("PRE-INPUT-STOP" in x for x in f)
    assert f[-1].startswith("LIST PRE-TIME ") and f[-1].count("s, ") == 9          # the ten slowest classes


def test_input_stop_triggers():
    assert G.input_stop(["WARN TREE-SOURCES OUT/bind.f x2 missing (base /t): /t/a.sv"], env={}).startswith("FAIL PRE-INPUT-STOP")
    assert G.input_stop(["FAIL SCHEMA-UNKNOWN-KEY 'read_lockup' x1 ..."], env={})
    assert G.input_stop(["WARN TREE-SOURCES *_sources folder x1 missing: /t/x_sources"], env={}) is None   # heuristic stays WARN
    assert G.input_stop(["WARN TREE-FRESH FORK-STALE source ..."], env={}) is None
    assert G.input_stop(["FAIL INPUT-MISSING files x1"], env={"OT_PRE_INPUT_STOP": "0"}) is None


def test_bind_refuses_before_elab_on_missing_source(tmp_path, monkeypatch, capsys):
    import bind
    plan = _tree(tmp_path)
    monkeypatch.setattr(bind.E, "REPO", tmp_path)
    monkeypatch.setenv("OT_TREE_PRECHECK", "on")
    monkeypatch.setenv("OT_TREE_PRECHECK_RAN", "0")
    a = types.SimpleNamespace(plan=str(plan), asbuilt=None, out=str(tmp_path / "out"))
    assert bind._tree_precheck(a) == 2
    assert "REFUSED before the elab: FAIL PRE-INPUT-STOP" in capsys.readouterr().out
    monkeypatch.setenv("OT_PLAN_GATE_PRE", "warn")
    assert bind._tree_precheck(a) == 0


def test_timer_line():
    t = G.PreTimer()
    t.mark("A")
    t.mark("B")
    assert t.line().startswith("LIST PRE-TIME ") and "A " in t.line()
