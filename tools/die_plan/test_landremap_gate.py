"""LANDREMAP-1122 (FLOW-OPS-R2, COORD): a core move vs the baseline whose landing reset references were not remapped is
refused by plan_gate_pre in seconds (KV R6d: 7 EMIT errors after a 1-2 h bind)."""
import copy
import json
import sys
from pathlib import Path
from types import SimpleNamespace
H = Path(__file__).resolve().parent
sys.path.insert(0, str(H))
import plan_gate_pre as G  # noqa: E402


def typ(cy=500.0, raw="rst_rl_5"):
    return {"hard_cores": [{"inst": "cl_i_ectl_Q_N_tN", "origin_um": [100.0, cy], "outline_um": [50.0, 40.0]}],
            "clock": {"landing_raw_branches": [{"base": raw, "stages": [{"raw_reset": raw}, {"raw_reset": "cland_reset_ft0_i"}]}],
                      "landing_contract": {"collector_tree": {"relays": [{"q": "rst_rl_0"}]}}}}


def plans(tmp_path, new_t):
    base = {"partition_types": {"hgi": typ()}}
    new = {"partition_types": {"hgi": new_t}}
    b, n = tmp_path / "base.json", tmp_path / "new.json"
    b.write_text(json.dumps(base)); n.write_text(json.dumps(new))
    return str(n), str(b)


OLD = {"rst_rl_5": (3, (10.0, 20.0), "wire"), "rst_rl_7": (5, (90.0, 20.0), "pad")}
NEW = {"rst_rl_5": (5, (90.0, 20.0), "pad"), "rst_rl_3": (3, (10.0, 20.0), "wire")}       # renumbered by the move


def tree_fn(raw, path, tn):
    return OLD if "base" in path else NEW


def test_unremapped_core_move_refused_with_command(tmp_path):
    n, b = plans(tmp_path, typ(cy=700.0))
    f = G.check_landremap(n, b, tree_fn=tree_fn)
    assert f[0].startswith("FAIL LANDREMAP hgi: cl_i_ectl_Q_N_tN moved") and "2 landing reset reference(s)" in f[0]
    assert "collector_tree" not in f[0]
    assert f[-1].startswith("FAIL LANDREMAP RUN landing_remap:") and "--types hgi" in f[-1] and b in f[-1]


def test_remapped_or_unmoved_passes(tmp_path):
    n, b = plans(tmp_path, typ(cy=700.0, raw="rst_rl_3"))                    # remapped by identity
    assert G.check_landremap(n, b, tree_fn=tree_fn) == []
    n, b = plans(tmp_path, typ())                                             # nothing moved: no tree is built
    assert G.check_landremap(n, b, tree_fn=lambda *a: 1 / 0) == []
    same = lambda raw, path, tn: OLD                                          # noqa: E731  move did not renumber
    n, b = plans(tmp_path, typ(cy=700.0))
    assert G.check_landremap(n, b, tree_fn=same) == []
    assert G.check_landremap(n, None) == []


def test_tree_error_is_warn_only(tmp_path):
    n, b = plans(tmp_path, typ(cy=700.0))
    f = G.check_landremap(n, b, tree_fn=lambda *a: (_ for _ in ()).throw(ValueError("boom")))
    assert len(f) == 1 and f[0].startswith("WARN LANDREMAP hgi: reset tree not built")


def test_tap_table_change_counts_as_move():
    a, b = {"partition_types": {"x": typ()}}, {"partition_types": {"x": copy.deepcopy(typ())}}
    b["partition_types"]["x"]["clock"]["added_taps"] = [[1, 2]]
    assert G.moved_types(b, a) == {"x": ["added_taps"]}


def test_bind_uses_previous_bind_plan_as_baseline(tmp_path, monkeypatch):
    import bind
    n, b = plans(tmp_path, typ(cy=700.0))
    out = tmp_path / "out"; out.mkdir()
    (out / "provenance_bind.json").write_text(json.dumps({"provenance": {"plan": b}}))
    seen = []
    monkeypatch.setattr(G, "check_landremap", lambda p, base: seen.append((p, base)) or ["FAIL LANDREMAP x"])
    assert bind._landremap_prev(SimpleNamespace(out=str(out), plan=n), G) == ["FAIL LANDREMAP x"] and seen == [(n, b)]
    (out / "provenance_bind.json").write_text(json.dumps({"provenance": {"plan": n}}))   # same plan: nothing to compare
    assert bind._landremap_prev(SimpleNamespace(out=str(out), plan=n), G) == []
    assert bind._landremap_prev(SimpleNamespace(out=str(tmp_path / "none"), plan=n), G) == []


def test_fresh_out_dir_uses_tree_bind_of_record(tmp_path, monkeypatch):
    import bind
    n, b = plans(tmp_path, typ(cy=700.0))
    bor = Path(n).parent / "bind_of_record"; bor.mkdir()
    (bor / "provenance_bind.json").write_text(json.dumps({"provenance": {"plan": b}}))
    monkeypatch.setattr(G, "check_landremap", lambda p, base: [f"FAIL LANDREMAP {base}"])
    fresh = tmp_path / "fresh"; fresh.mkdir()
    assert bind._landremap_prev(SimpleNamespace(out=str(fresh), plan=n), G) == [f"FAIL LANDREMAP {b}"]
