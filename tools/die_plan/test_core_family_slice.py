"""S81-CORE-LAT-R13: core_family_slice unit checks (no docker, no build)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import core_family_slice as F


def test_splits_family_menu():
    fam = dict(leaf_target=48)
    assert F.splits_for(13238, fam)[:2] == [2, 2]          # W/E x 2 islands per side always
    assert F.splits_for(3655, fam) == [2, 2, 4, 4]
    assert F.splits_for(100, fam) == [2, 2, 1] or F.splits_for(100, fam)[:2] == [2, 2]


def test_farthest_clusters_cover_and_limit():
    pts = [(float(x), float(y), "DFF", "r%d_%d" % (x, y), "CLK") for x in range(0, 200, 5) for y in (0, 1)]
    pts += [(5.0, 150.0, "DFF", "iso", "CLK")]
    g = F.farthest_clusters(pts, 30.0)
    flat = [p for x in g for p in x]
    assert sorted(flat) == sorted(pts)                       # every sink exactly once
    for x in g:
        cx = sum(p[0] for p in x) / len(x); cy = sum(p[1] for p in x) / len(x)
        assert max(abs(p[0] - cx) + abs(p[1] - cy) for p in x) <= 30.0


# ------------------------------------------------------------------ R14: duplicate-sink fix + clock BTerm lookup
import collections
import pytest


class _Maze:
    """minimal maze: cells are (x, y) tuples on a 1 um grid."""
    G = 1.0
    def cell(self, p): return (round(p[0]), round(p[1]))
    def xy(self, c): return (float(c[0]), float(c[1]))
    def md(self, a, b): return abs(a[0] - b[0]) + abs(a[1] - b[1])
    def path(self, a, b): return [a, (b[0], a[1]), b]


def _plan_with_starved_leaf():
    mz = _Maze()
    s = lambda x, y, n: (float(x), float(y), "DFF", n, "CLK")
    nodes = [("root", None, (50, 0), "BIG", "entry"),
             ("A_br", "root", (50, 0), "BIG", "branch"), ("A", "A_br", (10, 0), "BIG", "leaf"),
             ("B_br", "root", (50, 1), "BIG", "branch"), ("B", "B_br", (90, 0), "BIG", "leaf"),
             ("C_br", "root", (50, 2), "BIG", "branch"), ("C_r0", "C_br", (50, 40), "REP", "rep"),
             ("C", "C_r0", (50, 80), "BIG", "leaf")]
    wires = [dict(level=1, edge="A", segs=[40.0], cells=[mz.path((50, 0), (10, 0))]),
             dict(level=1, edge="B", segs=[40.0], cells=[mz.path((50, 1), (90, 0))]),
             dict(level=1, edge="C", segs=[38.0, 40.0], cells=[mz.path((50, 2), (50, 40)), mz.path((50, 40), (50, 80))])]
    # C's own sinks lie next to A and B, so after nearest-leaf reassignment C is nobody's nearest driver
    leafsinks = {"A": [s(9, 0, "a0"), s(11, 1, "a1")], "B": [s(89, 0, "b0"), s(91, 1, "b1")],
                 "C": [s(12, 0, "c0"), s(88, 0, "c1")]}
    return dict(mz=mz, nodes=nodes, wires=wires, land={}, leafsinks=leafsinks)


def test_reassign_never_duplicates_and_prunes_starved_leaf():
    P = _plan_with_starved_leaf()
    allsinks = sorted(x for v in P["leafsinks"].values() for x in v)
    r = F.reassign_nearest(P, cap=10)
    got = [x for v in P["leafsinks"].values() for x in v]
    assert sorted(got) == allsinks                                    # every sink exactly once (R13 copied one)
    assert max(collections.Counter(got).values()) == 1
    assert "C" not in P["leafsinks"] and r["pruned"] == ["C", "C_br", "C_r0"]
    names = {n[0] for n in P["nodes"]}
    assert names == {"root", "A_br", "A", "B_br", "B"}                # no driver left driving nothing
    assert {w["edge"] for w in P["wires"]} == {"A", "B"}
    par = {n[0]: n[1] for n in P["nodes"]}
    assert all(p is None or p in names for p in par.values())


def test_prune_recursive_interior_and_land():
    P = _plan_with_starved_leaf()
    # interior folded edge X: X_br -> X_r0 (landing driver) -> leaves Y (empty) only
    P["nodes"] += [("X_br", "root", (0, 0), "BIG", "branch"), ("X_r0", "X_br", (0, 5), "REP", "rep"),
                   ("Y_br", "X_r0", (0, 9), "BIG", "branch"), ("Y", "Y_br", (0, 20), "BIG", "leaf")]
    P["wires"] += [dict(level=1, edge="X", segs=[5.0, 4.0], cells=[]), dict(level=2, edge="Y", segs=[11.0], cells=[])]
    P["land"] = {"X_r0": (4.0, "X")}
    P["leafsinks"]["Y"] = []
    gone = F.prune_empty_leaves(P)
    assert gone == ["X_br", "X_r0", "Y", "Y_br"]
    assert "X_r0" not in P["land"] and {w["edge"] for w in P["wires"]} == {"A", "B", "C"}


def test_clock_bterm_bus_bit_and_fail_closed():
    assert F.clock_bterm_from_log("x\nDUMP_GEO_CLKPORT clk[0]\n", "clk") == "clk[0]"      # bk_g: input [0:0] clk
    assert F.clock_bterm_from_log("DUMP_GEO_CLKPORT ck\n", "ck") == "ck"
    with pytest.raises(SystemExit):
        F.clock_bterm_from_log("Error: invalid command name NULL\n", "ck")             # R13 symptom: no BTerm
    with pytest.raises(SystemExit):
        F.clock_bterm_from_log("DUMP_GEO_CLKPORT clk2\n", "clk")                        # never a guessed port


def test_entry_trunk_insert_remove():
    P = _plan_with_starved_leaf()
    P["ent"] = (50, 0)
    before = list(P["nodes"])
    names = F.add_entry_trunk(P, "BUFx8_ASAP7_75t_R", 3)
    assert names == ["K_r0", "K_r1", "K_r2"]
    par = {n[0]: n[1] for n in P["nodes"]}
    assert par["K_r0"] == "root" and par["K_r1"] == "K_r0" and par["K_r2"] == "K_r1"
    assert all(par[k] == "K_r2" for k in ("A_br", "B_br", "C_br"))       # every path gains exactly 3 stages
    seen = set()
    for n in P["nodes"]:                                                  # parents precede children (converter order)
        assert n[1] is None or n[1] in seen; seen.add(n[0])
    xy = {n[0]: n[2] for n in P["nodes"]}
    assert abs(xy["K_r2"][1] - 0) <= 2.2 and abs(xy["K_r0"][1]) > abs(xy["K_r2"][1])   # last stage next to branches
    assert all(n[3] == "BUFx8_ASAP7_75t_R" and n[4] == "trunk" for n in P["nodes"] if n[0].startswith("K_r"))
    F.remove_entry_trunk(P)
    assert P["nodes"] == before


# ------------------------------------------------------------------ R20: d1 fail-closed + gate numbers on the shipped masters
def _fake_model(P, libs, r, c, wc):
    w = 10.0 if dict((n[0], n[3]) for n in P["nodes"])["L0"] == "BUFx12_ASAP7_75t_R" else 21.0
    return {k: dict(mean=250.0 if k == "TT" else 202.5, window=w, leaf_out_slew_max=40.0) for k in ("TT", "FF")}, {}


def test_refresh_after_d1_reevaluates_shipped_masters(monkeypatch):
    monkeypatch.setattr(F.M7, "model_x", _fake_model)
    P = dict(nodes=[("root", None, (0, 0), "BUFx24_ASAP7_75t_R", "entry"), ("L0", "root", (1, 1), "BUFx8_ASAP7_75t_R", "leaf")])
    F._PLANS["t_r20"] = (P, {}, 0, 0, {})
    rec0 = dict(name="t_r20", model="R7", **_fake_model(P, 0, 0, 0, 0)[0])
    assert rec0["TT"]["window"] == 21.0                      # pre-d1 masters fail the window gate
    rec = dict(name="t_r20_uf3d1", model="R7", TT=rec0["TT"], FF=rec0["FF"],
               frozen_masters={"root": "BUFx24_ASAP7_75t_R", "L0": "BUFx12_ASAP7_75t_R"},
               nodes_xy=[["root", None, [0, 0], "BUFx24_ASAP7_75t_R", "entry"], ["L0", "root", [1, 1], "BUFx12_ASAP7_75t_R", "leaf"]])
    out = F.refresh_after_d1(rec0, rec)
    assert out["TT"]["window"] == 10.0 and out["FF"]["window"] == 10.0     # gate reads the masters that ship
    assert out["model_pre_d1"]["TT"]["window"] == 21.0 and "R20" in out["model"]


def test_refresh_after_d1_refuses_inconsistent_masters(monkeypatch):
    monkeypatch.setattr(F.M7, "model_x", _fake_model)
    P = dict(nodes=[("root", None, (0, 0), "BUFx24_ASAP7_75t_R", "entry"), ("L0", "root", (1, 1), "BUFx8_ASAP7_75t_R", "leaf")])
    F._PLANS["t_r20b"] = (P, {}, 0, 0, {})
    rec0 = dict(name="t_r20b", model="R7", **_fake_model(P, 0, 0, 0, 0)[0])
    with pytest.raises(SystemExit, match="lacks frozen masters"):
        F.refresh_after_d1(rec0, dict(frozen_masters={"root": "BUFx24_ASAP7_75t_R"}, nodes_xy=[]))
    P["nodes"] = list(P["nodes"])
    with pytest.raises(SystemExit, match="differ from frozen_masters"):
        F.refresh_after_d1(rec0, dict(frozen_masters={"root": "BUFx24_ASAP7_75t_R", "L0": "BUFx12_ASAP7_75t_R"},
                                      nodes_xy=[["root", None, [0, 0], "BUFx24_ASAP7_75t_R", "entry"],
                                                ["L0", "root", [1, 1], "BUFx8_ASAP7_75t_R", "leaf"]]))


def test_d1_failure_is_fail_closed(monkeypatch, tmp_path):
    """S81-CORES-R1: the d1 step died (missing results dirs) and the slice silently shipped pre-d1 masters."""
    import types
    monkeypatch.setattr(F, "census", lambda kit, work: "clk")
    monkeypatch.setattr(F, "plan", lambda *a, **k: dict(name="x", TT={}, FF={}))
    monkeypatch.setattr(F.subprocess, "run", lambda *a, **k: types.SimpleNamespace(returncode=1, stdout="", stderr="ModuleNotFoundError: uf_phys"))
    fams = {"families": [dict(name="f", members=["m"])]}
    a = types.SimpleNamespace(trunk_cal=None, replan_cal=None, libtt="t", libff="f", fit="fit.json", libdir="L", d1_steps=1)
    with pytest.raises(SystemExit, match="d1 step failed"):
        F.run_core(fams, "m", tmp_path, tmp_path, a)


# R21: sizing and admission must consume the SAME calibrated frozen-plan model.
def test_refresh_after_d1_uses_calibrated_model_and_retains_raw_info(monkeypatch):
    monkeypatch.setattr(F.M7, "model_x", _fake_model)
    name = "canonical-model-test"
    P = {"nodes": [("L0", None, (0, 0), "BUFx24_ASAP7_75t_R", "leaf")]}
    F._PLANS[name] = P, {}, 0.0, 0.0, {}
    rec0 = dict(name=name, model="raw R7", TT={"window": 21}, FF={"window": 21})
    prediction = {c: dict(mean=250, window=12, sink_min=240, sink_max=260,
                         leaf_out_slew_max=40, leaf_slew_in_max=30,
                         model="uf_phys3 v1", basis="GRT") for c in ("TT", "FF")}
    rec = dict(frozen_masters={"L0":"BUFx24_ASAP7_75t_R"},
               nodes_xy=[("L0", None, (0, 0), "BUFx24_ASAP7_75t_R", "leaf")],
               d1_uf3={"prediction": prediction})
    got = F.refresh_after_d1(rec0, rec)
    assert got["TT"]["window"] == 12
    assert got["model_r7_info"]["TT"]["window"] == 21
    rec["d1_uf3"]["prediction"]["FF"]["basis"] = "wrong"
    with pytest.raises(SystemExit, match="malformed calibrated"):
        F.refresh_after_d1(rec0, rec)


def test_calibrated_summary_matches_d1_kernel_and_keeps_sink_extrema(monkeypatch):
    import l0r_r8_uf3 as A
    # A tiny numeric kernel fixture; details are already calibrated, never raw R7.
    def predict(plan, lib, corner, edge="rise", detail=None, **params):
        vals = [10., 20.] if edge == "rise" else [12., 18.]
        if detail is not None:
            detail["a"] = dict(sinks=vals, slew_in=2., slew_out=4.)
            detail["b"] = dict(sinks=[30.], slew_in=3., slew_out=5.)
        return {"a":sum(vals)/2, "b":30.}, {}
    monkeypatch.setattr(A.V3, "predict3", predict)
    q = A.calibrated_summary(None, None, {}, {})
    assert q["TT"]["window"] == 15. and q["FF"]["window"] == 15.
    assert q["TT"]["sink_min"] == 10. and q["TT"]["sink_max"] == 30.
    assert q["FF"]["mean"] == round((10+18+30)/3,2)
    assert q["FF"]["leaf_out_slew_max"] == 5.


def test_split_repeated_leaf_keeps_stage_count_and_one_wire_per_driver(monkeypatch):
    """CORES-EARLY-3 10-28: a long leaf whose edge carries a repeater (C_br -> C_r0 -> C) split into siblings: the
    siblings hang on C_br's driver (not on C_br, which would then drive two wires: shared wire at C_br), and every
    part keeps the edge's repeater count (equal stage count on every root->sink path)."""
    P = _plan_with_starved_leaf()
    s = lambda x, y, n: (float(x), float(y), "DFF", n, "CLK")
    P["splits"] = [3]
    P["leafsinks"]["C"] = [s(10 + i, 80, "w%d" % i) for i in range(4)] + [s(90 + i, 80, "e%d" % i) for i in range(4)]
    mid = lambda mz, a, b, T, k: [((a[0] + b[0]) // 2, (a[1] + b[1]) // 2)] if k == 2 else []
    monkeypatch.setattr(F.H, "exact_points", mid)
    out = F.split_long_leaves(P, 35.0)
    assert [o["leaf"] for o in out] == ["C"] and out[0]["parts"] == 2
    node = {n[0]: n for n in P["nodes"]}
    kids = collections.defaultdict(list)
    for n in P["nodes"]:
        kids[n[1]].append(n[0])
    assert all(len(kids[u]) == 1 for u in node if u.endswith("_br") or node[u][4] == "rep")
    depth = lambda u: 0 if node[u][1] is None else 1 + depth(node[u][1])
    parts = [u for u in P["leafsinks"] if u not in ("A", "B")]
    assert len(parts) == 2 and {depth(u) for u in parts} == {depth("A") + 1}
    for u in parts:
        assert node[node[node[u][1]][1]][1] == "root" and node[node[u][1]][4] == "rep"
        w = [w for w in P["wires"] if w["edge"] == u]
        assert len(w) == 1 and len(w[0]["segs"]) == 2
    assert sorted(x for u in parts for x in P["leafsinks"][u]) == sorted(
        [s(10 + i, 80, "w%d" % i) for i in range(4)] + [s(90 + i, 80, "e%d" % i) for i in range(4)])


def test_entry_mode_default_centre_and_member_map():
    assert F.entry_mode({"name": "f"}, "a") == "centre"
    assert F.entry_mode({"name": "f", "entry": "sink_centroid"}, "a") == "sink_centroid"
    fam = {"name": "f", "entry": {"a": "sink_centroid"}}
    assert F.entry_mode(fam, "a") == "sink_centroid" and F.entry_mode(fam, "b") == "centre"
    with pytest.raises(SystemExit):
        F.entry_mode({"name": "f", "entry": "middle"}, "a")


def test_entry_geo_centre_unchanged_and_centroid(tmp_path):
    g = tmp_path / "geo.txt"
    g.write_text("CORE 0 0 100 50\nPIN ck 50.000 25.000\nSINK 90 10 a b c\nSINK 70 30 d e f\nMACRO m x 0 0 1 1 x 0 0\n")
    assert F.entry_geo(g, "centre") == g
    e = F.entry_geo(g, "sink_centroid")
    assert e.name == "geo_entry.txt" and g.read_text().count("PIN ck 50.000 25.000") == 1
    L = e.read_text().splitlines()
    assert L[1] == "PIN ck 80.000 20.000" and L[0] == "CORE 0 0 100 50" and L[2:] == g.read_text().splitlines()[2:]
    g.write_text("CORE 0 0 1 1\nPIN ck 0 0\n")
    with pytest.raises(SystemExit):
        F.entry_geo(g, "sink_centroid")


# ------------------------------------------------------------------ CORES-EARLY-4: hard-macro node keep-out (opt-in)
def _sites(tmp_path):
    p = tmp_path / "sites.txt"
    p.write_text("ROW0 4.3200 4.3200 site_w 0.0540 site_h 0.2700 nrows 10 nsites 100 orient0 R0\n"
                 "ROW 4.3200 4.3200 R0 100\n"
                 "FIXED TAP_1 TAPCELL_ASAP7_75t_R 4.3200 4.3200 4.4280 4.5900\n"
                 "FIXED u_rom0 ot_rom_4096x274_m8 25.9200 42.2880 151.2240 105.2400\n"
                 "MASTER BUFx24_ASAP7_75t_R 1.1340 0.2700\n")
    return p


def test_macro_keepouts_blocks_only_with_halo(tmp_path):
    k = F.macro_keepouts(_sites(tmp_path))
    assert k == [[23.72, 40.088, 153.424, 107.44]]   # macro + 2.2 um halo; tap cell (one row) is not a block


def test_keepout_mode_default_off_and_member_map():
    assert F.keepout_mode(dict(name="f"), "a") is False
    assert F.keepout_mode(dict(name="f", macro_keepout=True), "a") is True
    fam = dict(name="f", macro_keepout={"a": True})
    assert F.keepout_mode(fam, "a") is True and F.keepout_mode(fam, "b") is False


def test_htree_plan_keeps_every_node_out_of_the_block(tmp_path):
    """the S81 rom _gb failure: a block not on the clock net was invisible, a branch driver landed inside it."""
    H = F.H
    geo = tmp_path / "geo.txt"
    L = ["DIE 0 0 100 100", "CORE 0 0 100 100", "PIN ck 50 50"]
    L += ["SINK %d %d DFFHQNx1_ASAP7_75t_R r%d_%d CLK" % (x, y, x, y) for x in (5, 20, 80, 95) for y in (5, 20, 80, 95)]
    geo.write_text("\n".join(L) + "\n")
    blk = [10.0, 30.0, 45.0, 70.0]                        # W-side block between the W sink groups
    P0 = H.plan(str(geo), [2, 2], 70.0, [])
    P1 = H.plan(str(geo), [2, 2], 70.0, [blk])
    inside = lambda P: [n[0] for n in P["nodes"] if blk[0] <= P["mz"].xy(n[2])[0] <= blk[2] and blk[1] <= P["mz"].xy(n[2])[1] <= blk[3]]
    assert inside(P0)                                      # without the keep-out the W hub sits in the block
    assert not inside(P1)


# ---------------------------------------------------------------- QC-A0-KITS-8: symmetric lattice, one master per level
_LAT = [[(0, -8), (0, 8)], [(-2, -2), (2, -2), (-2, 2), (2, 2)]]


def test_lattice_equal_legs_and_every_sink_once():
    sinks = [(10 + dx, 20 + dy, "r%d_%d" % (dx, dy), "CLK") for dx in (-3, -1, 1, 3) for dy in (-11, -9, -7, -5, 5, 7, 9, 11)]
    P = F.lattice_build(sinks, (10.0, 20.0), _LAT)
    leaves = [n for n in P["nodes"] if n[4] == "leaf"]
    assert len(leaves) == 8 and not P["empty"]
    got = sorted(s[2] for v in P["leafsinks"].values() for s in v)
    assert got == sorted(s[2] for s in sinks)
    pos = {n[0]: n[2] for n in P["nodes"]}
    for lv in (0, 1):    # every leg of a level lands at the same Manhattan distance
        segs = {round(P["land"][n[0]][0], 6) for n in P["nodes"] if n[4] == "branch" and len(n[0].split("_")[0]) - 1 == lv + 1}
        assert len(segs) == 1
    par = {n[0]: n[1] for n in P["nodes"]}
    depth = set()
    for u in (n[0] for n in leaves):
        d = 0
        while par[u]: u = par[u]; d += 1
        depth.add(d)
    assert depth == {3}


def test_lattice_refuses_unequal_legs_and_prunes_empty_leaf():
    with pytest.raises(SystemExit):
        F.lattice_build([(0, 0, "a", "CLK")], (0.0, 0.0), [[(0, -8), (0, 5)]])
    sinks = [(10, 12, "a", "CLK"), (10, 28, "b", "CLK")]      # only the two y tips of level 0 get sinks
    P = F.lattice_build(sinks, (10.0, 20.0), [[(0, -8), (0, 8)], [(-1, 0), (1, 0)]])
    assert len(P["empty"]) == 2 and all(u not in {n[0] for n in P["nodes"]} for u in P["empty"])
    assert all(n[0] + "_br" not in {m[0] for m in P["nodes"]} for n in [(u,) for u in P["empty"]])
    assert set(P["land"]) <= {n[0] for n in P["nodes"]}


def test_lattice_levelkey_one_key_per_level():
    assert F.lattice_levelkey(("root", None, (0, 0), "B", "entry")) == ("root",)
    assert F.lattice_levelkey(("T01_br", "T0_br", (0, 0), "B", "branch")) == (0, 2, 0)
    assert F.lattice_levelkey(("T01", "T01_br", (0, 0), "B", "leaf")) == (1, 2, 0)


# ------------------------------------------------------------------ DIE-S81-30: opt-in keepout_stray (macro leaf plans)
def _stray_plan():
    """real maze, one macro wall x 10..50 / y 15..25; leaf U (below the wall) hangs on the root branch ABOVE it."""
    mz = F.H.Maze((0.0, 0.0, 60.0, 40.0), [("m", (10.0, 15.0, 50.0, 25.0), (10.0, 15.0))], G=1.0, halo=0.0)
    s = lambda x, y, n: (float(x), float(y), "DFF", n, "CLK")
    nodes = [("root", None, (30, 38), "BIG", "entry"), ("R2_br", "root", (30, 37), "BIG", "branch"),
             ("R2", "R2_br", (5, 30), "REP", "rep"),
             ("X_br", "root", (30, 30), "BIG", "branch"), ("X", "X_br", (30, 32), "BIG", "leaf"),
             ("U_br", "root", (30, 30), "BIG", "branch"), ("U", "U_br", (30, 10), "BIG", "leaf"),
             ("V_br", "R2", (5, 8), "BIG", "branch"), ("V", "V_br", (28, 8), "BIG", "leaf")]
    edge = lambda lv, e, a, b: dict(level=lv, edge=e, segs=[mz.md(a, b)], cells=[mz.path(a, b)])
    wires = [edge(1, "R2", (30, 37), (5, 30)), edge(2, "X", (30, 30), (30, 32)), edge(2, "U", (30, 30), (30, 10)),
             edge(2, "V", (5, 8), (28, 8))]
    leafsinks = {"X": [s(30, 33, "x0")], "U": [s(30, 10, "u0"), s(31, 10, "u1")], "V": [s(27, 8, "v0"), s(29, 8, "v1")]}
    return dict(mz=mz, nodes=nodes, wires=wires, land={}, leafsinks=leafsinks)


def _sinks(P):
    return sorted(x for v in P["leafsinks"].values() for x in v)


def test_keepout_stray_merge_joins_reachable_leaf_and_prunes():
    P = _stray_plan(); before = _sinks(P)
    r = F.fix_keepout_strays(P, "merge", 35.0, 70.0)
    assert len(r) == 1 and r[0]["leaf"] == "U" and r[0]["fixed"] == "merge" and r[0]["into"] == "V"
    assert r[0]["ratio"] > 1.10 and r[0]["pruned"] == ["U", "U_br"]
    assert _sinks(P) == before and "U" not in P["leafsinks"]              # every sink once, none moved
    assert {n[0] for n in P["nodes"]} == {"root", "R2_br", "R2", "X_br", "X", "V_br", "V"}
    assert {w["edge"] for w in P["wires"]} == {"R2", "X", "V"}


def test_keepout_stray_reparent_keeps_own_leaf_same_stage_and_topological():
    P = _stray_plan()
    r = F.fix_keepout_strays(P, "reparent", 35.0, 70.0)
    assert r[0]["fixed"] == "reparent" and r[0]["driver"] == "R2"
    nd = {n[0]: n for n in P["nodes"]}
    assert nd["U_br"][1] == "R2" and nd["U"][1] == "U_br"                 # same stage count: branch -> leaf
    w = next(w for w in P["wires"] if w["edge"] == "U")
    a, b = w["cells"][0][0], w["cells"][0][-1]
    assert w["segs"][0] <= 1.10 * (abs(a[0] - b[0]) + abs(a[1] - b[1])) and w["segs"][0] <= 70.0
    seen = set()
    for n in P["nodes"]:                                                 # parents before children
        assert n[1] is None or n[1] in seen; seen.add(n[0])


def test_keepout_stray_noop_without_bad_legs_and_mode_checked():
    P = _stray_plan()
    P["nodes"] = [n for n in P["nodes"] if n[0] not in ("U", "U_br")]; P["wires"] = [w for w in P["wires"] if w["edge"] != "U"]
    del P["leafsinks"]["U"]
    import copy
    ref = copy.deepcopy({k: P[k] for k in ("nodes", "wires", "leafsinks")})
    assert F.fix_keepout_strays(P, "merge", 35.0, 70.0) == []
    assert {k: P[k] for k in ("nodes", "wires", "leafsinks")} == ref
    with pytest.raises(SystemExit):
        F.fix_keepout_strays(P, "slide", 35.0, 70.0)


# ---------------------------------------------------------------- HBM-CORES-KITS-25: opt-in geometric lv0 x bands
def _band_geo(tmp_path):
    geo = tmp_path / "geo.txt"
    L = ["DIE 0 0 200 100", "CORE 0 0 200 100", "PIN ck 100 10"]
    L += ["SINK %d %d DFFHQNx1_ASAP7_75t_R c%d_%d CLK" % (x, y, x, y) for x in range(90, 111, 4) for y in range(10, 91, 8)]
    L += ["SINK 196 %d DFFHQNx1_ASAP7_75t_R e%d CLK" % (y, y) for y in range(20, 81, 10)]
    L += ["SINK 4 %d DFFHQNx1_ASAP7_75t_R w%d CLK" % (y, y) for y in range(20, 81, 10)]
    geo.write_text("\n".join(L) + "\n")
    return geo


def test_lv0_x_bands_root_each_strip_inside_its_band(tmp_path):
    geo = _band_geo(tmp_path)
    P = F.ungated_macro_htree(str(geo), [3, 2], 70.0, [], leaf_target=8, x_bands=[50, 150])
    g = P["groups"]
    assert sorted(len(g[(i,)]) for i in range(3)) == [7, 7, 66]
    assert all(p[0] < 50 for p in g[(0,)]) and all(p[0] >= 150 for p in g[(2,)])
    assert P["mz"].xy(P["site"][(2,)])[0] >= 150 and P["mz"].xy(P["site"][(0,)])[0] < 50   # strip roots in their strips
    depth = {len(k) for k in P["leaves"]}
    assert len(depth) == 1                                                                   # equal stage count


def test_lv0_x_bands_default_unchanged_and_fail_closed(tmp_path):
    geo = _band_geo(tmp_path)
    P0 = F.ungated_macro_htree(str(geo), [2, 2], 70.0, [], leaf_target=8)
    P1 = F.ungated_macro_htree(str(geo), [2, 2], 70.0, [], leaf_target=8, x_bands=None)
    assert P0["groups"] == P1["groups"]
    with pytest.raises(SystemExit):
        F.ungated_macro_htree(str(geo), [2, 2], 70.0, [], leaf_target=8, x_bands=[50, 150])   # splits[0] != cuts+1
    with pytest.raises(SystemExit):
        F.ungated_macro_htree(str(geo), [3, 2], 70.0, [], leaf_target=8, x_bands=[50, 60])    # empty band
    with pytest.raises(SystemExit):
        F.ungated_macro_htree(str(geo), [3, 2], 70.0, [], leaf_target=8, x_bands=[150, 50])   # not increasing


# Explicit H2 family islands are planned centres, not asserted body origins.
def test_explicit_six_island_splits_and_contract_guards():
    points=[[20,20],[80,20],[20,60],[80,60],[20,100],[80,100]]
    fam=dict(islands_xy=points,leaf_target=48)
    assert F.splits_for(12000,fam)[:2]==[2,3]
    assert F.splits_for(100,fam)==[2,3,1]
    assert F.family_islands(fam)==[tuple(map(float,p)) for p in points]
    with pytest.raises(SystemExit,match="contradicts"):
        F.splits_for(100,dict(fam,splits_override=[2,2,4]))
    for bad in (points[:-1],points[:-1]+[points[0]],points[:-1]+[[80,float('nan')]],points[:-1]+[[81,100]]):
        with pytest.raises(SystemExit,match="islands_xy"):
            F.family_islands(dict(islands_xy=bad))


def test_explicit_six_islands_reach_actual_level_two_hubs(tmp_path):
    points=[[20.012,20.132],[80.012,20.132],[20.012,60.084],[80.012,60.084],[20.012,100.116],[80.012,100.116]]
    geo=tmp_path/'geo.txt'
    lines=['CORE 0 0 100 120','PIN ck 50 60']
    for bay,(x,y) in enumerate(points):
        for j in range(4):lines.append('SINK %.3f %.3f FF r%d_%d CLK' % (x+j*.1,y,bay,j))
    geo.write_text('\n'.join(lines)+'\n')
    P=F.ungated_macro_htree(geo,[2,3],70,[],leaf_target=48,islands=points)
    assert len(P['island_snap'])==6
    assert sorted(r['requested_xy_um'] for r in P['island_snap'])==sorted(points)
    assert all(r['maze_displacement_um']<=2 for r in P['island_snap'])
    assert {tuple(r['group']):tuple(r['maze_xy_um']) for r in P['island_snap']}=={g:P['mz'].xy(p) for g,p in P['site'].items() if len(g)==2}
    assert len([g for g in P['site'] if len(g)==2])==6
    sinks=[s for group in P['leafsinks'].values() for s in group]
    assert len(sinks)==24 and len({s[2] for s in sinks})==24
    assert P['entry']==(50.,60.)
    par={n[0]:n[1] for n in P['nodes']}
    depths=set()
    for n in P['nodes']:
        if n[4]!='leaf':continue
        count=0;u=n[0]
        while u is not None:count+=1;u=par[u]
        depths.add(count)
    assert len(depths)==1


def test_explicit_island_bounds_topology_and_legal_bay_fail_closed():
    points=[(20,20),(80,20),(20,60),(80,60),(20,100),(80,100)]
    mz=F.H.Maze((0,0,100,120),[])
    with pytest.raises(SystemExit,match="first splits"):
        F.explicit_island_sites(mz,(50,60),points,[2,2])
    with pytest.raises(SystemExit,match="straddle"):
        F.explicit_island_sites(mz,(90,60),points,[2,3])
    outside=[(x,y-30) for x,y in points]
    with pytest.raises(SystemExit,match="outside core"):
        F.explicit_island_sites(mz,(50,60),outside,[2,3])
    blocked=F.H.Maze((0,0,100,120),[],keepout=[(10,10,30,30)])
    with pytest.raises(SystemExit,match="within 2um"):
        F.explicit_island_sites(blocked,(50,60),points,[2,3])
