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


def test_remap_base_resolves_without_the_lane(tmp_path, monkeypatch):
    n, b = plans(tmp_path, typ(cy=700.0))
    monkeypatch.delenv("OT_PLAN_REMAP_BASE", raising=False)
    assert G.remap_base(n)[0] is None
    bor = Path(n).parent / "bind_of_record"; bor.mkdir()
    (bor / "provenance_bind.json").write_text(json.dumps({"provenance": {"plan": b}}))
    assert G.remap_base(n) == (b, "bind_of_record/provenance_bind.json")
    monkeypatch.setenv("OT_PLAN_REMAP_BASE", b)
    assert G.remap_base(n)[1] == "$OT_PLAN_REMAP_BASE"
    assert G.remap_base(n, explicit=b)[1] == "--remap-base"
    assert G.remap_base(n, explicit=n)[0] is None                         # the plan itself is no base


# ---- GATE-AGREE-R1: one predicate with the bind (reset_anchor.repicked_paths); QC cr base: 44 findings, the bind re-picks them all
import reset_anchor as RA  # noqa: E402


def qc_type(n=44, anchored=True, extra_unanchored=False):
    """START transport + local resets naming rst_rl_0..n-1 (the QC V3p7cr crx / b2rx shape), optionally anchored"""
    rd = [{"stages": [{"raw_reset": f"rst_rl_{i}"}]} for i in range(n - 4)]
    loc = [{"name": f"l{i}", "raw": f"rst_rl_{n - 4 + i}"} for i in range(4)]
    t = {"hard_cores": [{"inst": "cl_i_ectl_Q_N_tN", "origin_um": [100.0, 700.0], "outline_um": [50.0, 40.0]}],
         "clock": {"landing_reader_start": rd, "landing_local_resets": loc}}
    if anchored:
        names = [f"rst_rl_{i}" for i in range(n - (1 if extra_unanchored else 0))]
        t["clock"][RA.KEY] = {"inputs": {}, "tol_um": 405.0,
                              "relays": {nm: {"depth": 3, "xy": [float(i), 0.0]} for i, nm in enumerate(names)}}
    return t


def qc_plans(tmp_path, new_t):
    b, n = tmp_path / "base.json", tmp_path / "new.json"
    base_t = copy.deepcopy(new_t); base_t["hard_cores"][0]["origin_um"] = [100.0, 500.0]
    b.write_text(json.dumps({"partition_types": {"qc": base_t}})); n.write_text(json.dumps({"partition_types": {"qc": new_t}}))
    return str(n), str(b)


def qc_trees(n=44, shift=100):
    old = {f"rst_rl_{i}": (3, (float(i), 0.0), "wire") for i in range(n)}
    new = {f"rst_rl_{i + shift}": (3, (float(i), 0.0), "wire") for i in range(n)}      # renumbered, same sites
    return old, new


def qc_hooks(n=44, shift=100, tol_ok=True):
    old, new = qc_trees(n, shift)
    tree = {"relays": [{"q": q, "depth": d, "xy": list(xy)} for q, (d, xy, _k) in new.items()]}
    if not tol_ok:
        tree = {"relays": [{"q": q, "depth": d, "xy": [xy[0] + 9999.0, xy[1]]} for q, (d, xy, _k) in new.items()]}
    tf = lambda raw, path, tn: old if "base" in path else new                                    # noqa: E731
    rf = lambda raw, path, tn: RA.repicked_paths(tn, raw["partition_types"][tn], tree, ".", lambda t: set())  # noqa: E731
    return tf, rf


def test_qc_anchored_findings_are_advisory_when_bind_repicks(tmp_path):
    n, b = qc_plans(tmp_path, qc_type())
    tf, rf = qc_hooks()
    f = G.check_landremap(n, b, tree_fn=tf, repick_fn=rf)
    assert not [x for x in f if x.startswith("FAIL")], f                                          # no blocking finding: gates agree
    assert len(f) == 1 and f[0].startswith("WARN LANDREMAP-ADVISORY qc: 44 stale")
    # the bind's own resolve_plan accepts exactly this plan (same predicate)
    raw = json.loads(Path(n).read_text())
    tree = {"relays": [{"q": q, "depth": d, "xy": list(xy)} for q, (d, xy, _k) in qc_trees()[1].items()]}
    rec, err = RA.resolve_plan(raw, None, ".", tree_fn=lambda tn: tree, ported_fn=lambda t: set())
    assert err == [] and rec[0]["refs_rewritten"] == 44


def test_qc_unanchored_and_old_behaviour_stay_blocking(tmp_path):
    n, b = qc_plans(tmp_path, qc_type(anchored=False))
    tf, rf = qc_hooks()
    f = G.check_landremap(n, b, tree_fn=tf, repick_fn=rf)
    adv = [x for x in f if "ADVISORY" in x]
    assert len(adv) == 1 and "4 stale" in adv[0]                                                  # local raw names: bind re-picks them anyway
    assert any(x.startswith("FAIL LANDREMAP qc:") and "40 landing reset" in x for x in f)         # START transport: nobody repairs it
    f = G.check_landremap(n, b, tree_fn=tf)                                                       # no repick_fn = the old reading
    assert any(x.startswith("FAIL LANDREMAP qc:") and "44 landing reset" in x for x in f)


def test_qc_anchor_the_bind_would_refuse_is_blocking_and_named(tmp_path):
    n, b = qc_plans(tmp_path, qc_type(extra_unanchored=True))                                     # one referenced name not anchored
    tf, rf = qc_hooks()
    f = G.check_landremap(n, b, tree_fn=tf, repick_fn=rf)
    assert any(x.startswith("FAIL LANDREMAP-BIND qc:") and "lacks referenced relay" in x for x in f)
    n, b = qc_plans(tmp_path, qc_type())
    tf, rf = qc_hooks(tol_ok=False)                                                               # no relay within the recorded site tolerance
    f = G.check_landremap(n, b, tree_fn=tf, repick_fn=rf)
    assert any(x.startswith("FAIL LANDREMAP-BIND qc:") and "site tolerance" in x for x in f)
    assert not any("ADVISORY" in x for x in f)


def test_repick_error_is_warn_and_blocking(tmp_path):
    n, b = qc_plans(tmp_path, qc_type())
    tf, _ = qc_hooks()
    f = G.check_landremap(n, b, tree_fn=tf, repick_fn=lambda *a: 1 / 0)
    assert any(x.startswith("WARN LANDREMAP qc: bind re-pick not evaluated") for x in f)
    assert any(x.startswith("FAIL LANDREMAP qc:") for x in f)
