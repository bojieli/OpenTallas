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


def test_icg_copies_mode_default_off_and_member_map():
    assert F.icg_copies_mode(dict(name="f"), "a") is False
    assert F.icg_copies_mode(dict(name="f", icg_copies=True), "a") is True
    fam = dict(name="f", icg_copies={"a": True})
    assert F.icg_copies_mode(fam, "a") is True and F.icg_copies_mode(fam, "b") is False


def test_gate_tile_groups_gated_census(tmp_path):
    geo = tmp_path / "geo_gated.txt"
    geo.write_text("\n".join([
        "DIE 0 0 100 100", "CORE 0 0 100 100", "PIN ck 50 50",
        "SINK 5 5 DFFHQNx1_ASAP7_75t_R u0 CLK",
        "GATE g0 ICGx1_ASAP7_75t_R 40 40",
        "SINK 10 10 DFFHQNx1_ASAP7_75t_R a CLK gate=g0",
        "SINK 60 10 DFFHQNx1_ASAP7_75t_R b CLK gate=g0",
        "SINK 61 11 DFFHQNx1_ASAP7_75t_R c CLK gate=g0",
        "MACRO rom M 0 50 20 70 clk 10 60 gate=g0",
        "ISLCOUNT 0"]) + "\n")
    g = F.gate_tile_groups(geo, 50)
    assert g == {("ROOT", 0, 0): ["u0/CLK"], ("g0", 0, 0): ["a/CLK"], ("g0", 1, 0): ["b/CLK", "c/CLK"], ("g0", 0, 1): ["rom/clk"]}
    s = F.icg_groups_summary(g)
    assert s["groups"] == 4 and s["gated_groups"] == 3 and s["gates"] == 1 and s["sinks"] == 5 and s["small_groups"] == 4


def test_gate_tile_groups_refuses_undeclared_gate(tmp_path):
    geo = tmp_path / "g.txt"
    geo.write_text("SINK 1 1 DFF x CLK gate=nope\n")
    with pytest.raises(SystemExit):
        F.gate_tile_groups(geo, 50)


# ---------------------------------------------------------------- form C stage 3 (CORES-EARLY-6)
def _gated_geo(tmp_path):
    """two RTL gates (g0 W-heavy, g1 E) + ungated flops; g0 also gates one hard-macro clock pin."""
    L = ["DIE 0 0 120 120", "CORE 0 0 120 120", "PIN ck 60 60",
         "GATE g0 ICGx1_ASAP7_75t_R 30 60", "GATE g1 ICGx1_ASAP7_75t_R 90 60"]
    k = 0
    for x in range(6, 115, 9):
        for y in range(6, 115, 9):
            g = "" if (x + y) % 4 == 0 else (" gate=g0" if x < 70 else " gate=g1")
            L.append("SINK %d %d DFFHQNx1_ASAP7_75t_R r%d CLK%s" % (x, y, k, g)); k += 1
    L += ["MACRO rom ot_rom_4096x274_m8 40 40 52 50 clk 46 51 gate=g0", "ISLCOUNT 0"]
    p = tmp_path / "geo_gated.txt"; p.write_text("\n".join(L) + "\n")
    return p


def test_gated_htree_gate_homogeneous_leaves_equal_stages(tmp_path):
    geo = _gated_geo(tmp_path)
    P = F.gated_htree(str(geo), [2, 2], 70.0, [], copy_max=12, leaf_target=4)
    par = {n[0]: n[1] for n in P["nodes"]}; kind = {n[0]: n[4] for n in P["nodes"]}
    depth = set()
    for u, ss in P["leafsinks"].items():
        assert len({P["gate_of"]["%s/%s" % (s[2], s[3])] for s in ss}) == 1      # one gate domain per leaf
        d, v, path = 0, u, []
        while v: path.append(v); v = par[v]; d += 1
        depth.add(d)
        gl = [v for v in path if kind[v] in ("icg", "gbuf")]
        assert len(gl) == 1                                                       # exactly one gate-level stage
        g = P["gate_of"]["%s/%s" % (ss[0][2], ss[0][3])]
        assert (kind[gl[0]] == "icg") == (g is not None)
    assert len(depth) == 1
    rows = F.icg_copy_table(P)
    assert {r["gate"] for r in rows} == {"g0", "g1"}
    assert sum(r["first"] for r in rows) == 2 and len(rows) > 2                   # copy_max forces clone_of copies
    mem = [s for r in rows for s in r["members"]]
    gated = sorted(s for s, g in P["gate_of"].items() if g)
    assert sorted(mem) == gated and len(set(mem)) == len(mem)
    assert "rom/clk" in mem and P["sinkcap"]["TT"]["rom/clk"] > 5.0               # macro leaf, liberty pin cap


def test_gated_htree_refuses_undeclared_gate(tmp_path):
    p = tmp_path / "g.txt"
    p.write_text("CORE 0 0 50 50\nPIN ck 25 25\nSINK 1 1 DFF x CLK gate=nope\n")
    with pytest.raises(SystemExit):
        F.gated_htree(str(p), [2], 70.0, [], 10, 4)


def test_icg_lib_cells_reads_the_combinational_clk_gclk_arc(tmp_path):
    tab = lambda k, v: '%s (t) { index_1 ("5, 10"); index_2 ("1, 2"); values ("%s, %s", "%s, %s"); }' % (k, v, v + 1, v + 2, v + 3)
    lib = "\n".join([
        "  cell (ICGx1_ASAP7_75t_R) {", "    pin (GCLK) {",
        '      timing () { related_pin : "CLK"; timing_type : combinational_fall; %s %s }' % (tab("cell_fall", 90), tab("fall_transition", 91)),
        '      timing () { related_pin : "CLK"; timing_sense : positive_unate; %s %s %s %s }'
        % (tab("cell_rise", 10), tab("rise_transition", 20), tab("cell_fall", 30), tab("fall_transition", 40)),
        "    }", "    pin (CLK) {", "      capacitance : 2.19131;", "    }", "  }", ""])
    p = tmp_path / "seq.lib"; p.write_text(lib)
    c = F.icg_lib_cells(p, ["ICGx1_ASAP7_75t_R"])["ICGx1_ASAP7_75t_R"]
    assert c["cin"] == 2.19131 and c["rise"][2][0][0] == 10 and c["fall"][2][0][0] == 30 and c["tfall"][2][1][1] == 43
    with pytest.raises(SystemExit):
        F.icg_lib_cells(p, ["ICGx2_ASAP7_75t_R"])


def test_gated_htree_at_leaf_one_branch_per_copy(tmp_path):
    geo = _gated_geo(tmp_path)
    P = F.gated_htree(str(geo), [2, 2], 70.0, [], copy_max=400, leaf_target=4, at_leaf=True)
    par = {n[0]: n[1] for n in P["nodes"]}; kind = {n[0]: n[4] for n in P["nodes"]}
    kids = collections.Counter(n[1] for n in P["nodes"])
    depth = set()
    for u, ss in P["leafsinks"].items():
        assert len({P["gate_of"]["%s/%s" % (s[2], s[3])] for s in ss}) == 1
        d, v, gl = 0, u, []
        while v:
            if kind[v] in ("icg", "gbuf"): gl.append(v)
            v = par[v]; d += 1
        depth.add(d); assert len(gl) == 1 and kids[gl[0]] == 1                    # each copy drives ONE branch
    assert len(depth) == 1
    rows = F.icg_copy_table(P)
    assert len(rows) == sum(1 for u, ss in P["leafsinks"].items() if P["gate_of"]["%s/%s" % (ss[0][2], ss[0][3])])
    assert any(r["members"] == ["rom/clk"] for r in rows)                          # gated macro pin = own leaf + copy


def test_gate_fragments_preserve_domains_and_sibling_locality():
    sink = lambda n, x: (x, 1., n, "CLK", "DFF")
    small = [sink("a", 1.)]; big = [sink("b%d" % i, 4.) for i in range(8)]
    foreign = [sink("foreign", 1.)]; other_parent = [sink("d%d" % i, 2.) for i in range(10)]
    macro = (1., 1., "rom", "clk", "MACRO:rom")
    groups = {(): small + big + foreign + other_parent + [macro],
              (0, 0): small + foreign + [macro], (0, 1): big, (1, 0): other_parent}
    gate_of = {"%s/%s" % (s[2], s[3]): ("other" if s[2] == "foreign" else "g")
               for ss in groups.values() for s in ss}
    before = sorted(s for k, ss in groups.items() if len(k) == 2 for s in ss)
    moved = F.merge_gate_fragments(groups, 2, gate_of, 4)
    assert moved == [dict(source=[0, 0], destination=[0, 1], gate="g", sinks=1)]
    assert sorted(s for k, ss in groups.items() if len(k) == 2 for s in ss) == before
    assert groups[(0, 0)] == foreign + [macro]
    assert groups[(1, 0)] == other_parent


def test_gated_quantile_and_fragment_optins_preserve_members(tmp_path):
    geo = _gated_geo(tmp_path)
    baseline = F.gated_htree(str(geo), [2, 2], 70., [], 400, 4, at_leaf=True)
    revised = F.gated_htree(str(geo), [2, 2], 70., [], 400, 4, at_leaf=True,
                            merge_fragment_fraction=.25, padding_quantile=.95)
    members = lambda p: sorted(s for ss in p["leafsinks"].values() for s in ss)
    assert members(revised) == members(baseline)
    for ss in revised["leafsinks"].values():
        assert len({revised["gate_of"]["%s/%s" % (s[2], s[3])] for s in ss}) == 1
    assert revised["T"][-1] <= baseline["T"][-1]
    assert len({len(w["segs"]) for w in revised["wires"] if w["level"] == 3}) == 1
