"""RESET-TREE-CACHE-1124 (COORD ruling): the prewarm set is exactly the reset trees the classes read: recorded reads of LANDREMAP
(+ re-pick) and of derived_drop (RSTREACH / DERIVEDNAME) equal reset_solve_types / landremap_types / reset_tree_types."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import derived_drop as D  # noqa: E402
import plan_gate_pre as G  # noqa: E402


def _typ(cy=500.0, raw="rst_rl_5", moved=True):
    return {"hard_cores": [{"inst": "cl_i", "origin_um": [100.0, cy if moved else 500.0], "outline_um": [50.0, 40.0]}],
            "clock": {"landing_raw_branches": [{"base": raw, "stages": [{"raw_reset": raw}]}],
                      "landing_contract": {"collector_tree": {"relays": [{"q": "rst_rl_0"}]}}}}


def test_landremap_reads_equal_selection(tmp_path):
    base = {"partition_types": {"a": _typ(), "b": _typ(), "c": _typ(), "h": {"hard": True}}}
    new = {"partition_types": {"a": _typ(600.0), "b": _typ(500.0), "c": _typ(700.0, raw="rst_rl_9"), "h": {"hard": True}}}
    bp, np_ = tmp_path / "base.json", tmp_path / "new.json"
    bp.write_text(json.dumps(base)); np_.write_text(json.dumps(new))
    seen = set()

    def tree_fn(raw, path, tn):
        seen.add(("base" if "base" in path else "plan", tn))
        return {"rst_rl_5": (3, (10.0, 20.0), "wire")} if "base" in path else {"rst_rl_5": (5, (90.0, 20.0), "pad")}

    def repick_fn(raw, path, tn):
        seen.add(("plan", tn))
        return set(), None
    G.check_landremap(str(np_), str(bp), tree_fn=tree_fn, repick_fn=repick_fn)
    sel = G.reset_solve_types(str(tmp_path), str(np_), new, {"ADVISORY", "RSTREACH", "DERIVEDNAME"}, landremap_base=str(bp), env={})
    assert seen == {(side, tn) for side in ("plan", "base") for tn in sel[side]} == {("plan", "a"), ("base", "a")}


class Rec:
    """derived_drop solver recording every reset-tree read"""
    def __init__(self):
        self.read = set()

    def relays(self, tn):
        self.read.add(tn)
        return {"rst_rl_5": (None, (1.0, 1.0))}

    def tree(self, tn):
        self.read.add(tn)
        return {"relays": [{"q": "rst_rl_5", "d": None, "xy": [1.0, 1.0], "kind": "pad"}]}

    def taps(self, tn):
        return {"clk_t1"}

    def raw_hops(self, tn):
        import reach_rules as R
        t = self.raw["partition_types"][tn]
        if D._raw_hop_reads(t, lambda: False):        # raw_hops solves the tree exactly then (reach_rules.raw_hops)
            self.read.add(tn)
        return []


def test_derived_reads_equal_selection():
    lc = {"pins": [], "bands": {}}
    raw = {"partition_types": {
        "relayref": {"clock": {"landing_contract": dict(lc, collector_local_sources=[]), "landing_writer_start": {"raw": "rst_rl_5"}},
                     "reset": {}},
        "tapref": {"clock": {"landing_contract": lc, "x_tap": "clk_t1"}},
        "branches": {"clock": {"landing_contract": lc, "landing_raw_branches": [{"name": "b", "base": "rst_rl_5", "stages": []}]}},
        "plain": {"clock": {"landing_contract": lc}},
        "hard": {"hard": True}}}
    S = Rec()
    S.raw = raw
    D.findings(raw, "/x/p.json", solver=S, classes=("RSTREACH", "DERIVEDNAME"))
    assert S.read == D.reset_tree_types(raw, ("RSTREACH", "DERIVEDNAME")), (S.read, D.reset_tree_types(raw))
    assert "branches" in S.read and "plain" not in S.read and "hard" not in S.read


def test_startsettle_reads_equal_selection(tmp_path, monkeypatch):
    import reset_tree as RT
    raw = json.loads((Path(__file__).resolve().parent / "examples/tiny_plan.json").read_text())
    raw.setdefault("reset", {})["release"] = "wavefront"
    for ty in raw["partition_types"].values():
        ty.pop("contents", None)
    p = tmp_path / "plan.json"
    p.write_text(json.dumps(raw))
    sc = tmp_path / "sidecar.json"
    sc.write_text("{}")
    seen = set()
    real = RT.for_type

    def rec(P, tn, reach=None):
        seen.add(tn)
        return real(P, tn, reach)
    monkeypatch.setattr(RT, "for_type", rec)
    G._PLAN_OBJ.clear()
    G.check_startsettle(str(tmp_path), str(p), sidecar=str(sc))
    want = G.reset_solve_types(str(tmp_path), str(p), raw, {"RSTREACH", "DERIVEDNAME", "LANDREMAP"}, env={}, sidecar=str(sc))
    assert seen and seen == set(want["plan"]) == set(G.startsettle_types(raw))
