"""LOCALITY-SCORE-1: tests for tools/die_plan/locality.py (traffic, score, feed model, margins, proposer, estimate)."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import clk_aocv as CA  # noqa: E402
import locality as LO  # noqa: E402

T = CA.load(HERE / "clk_aocv_table_g021.json")


def _plan(n=4, w=1000.0, widths=None, hard=()):
    """a row of n abutting 1 x 1 mm partitions p0..p{n-1}; port i -> i+1 carries widths[i] bits."""
    widths = widths or [100] * (n - 1)
    types = {"t": {"outline_um": [w, w]}, "th": {"outline_um": [w, w], "hard": True}}
    parts = [dict(name=f"p{i}", type="th" if i in hard else "t", origin_um=[i * w, 0.0], orient="R0") for i in range(n)]
    ports = [dict(id=f"q{i}", src=dict(part=f"p{i}"), dst=dict(part=f"p{i + 1}"), width=widths[i], kind="data")
             for i in range(n - 1)]
    return dict(die=dict(outline_um=[n * w, w], period_ps=833), partition_types=types, partitions=parts, ports=ports,
                budgets=dict(face_pins_per_um=6))


def test_traffic_bitmm():
    D = LO.load_plan(_plan(3, widths=[10, 30]))
    M = LO.traffic(D)
    assert M[("p0", "p1")]["bits"] == 10 and abs(M[("p0", "p1")]["bitmm"] - 10.0) < 1e-9
    assert abs(M[("p1", "p2")]["bitmm"] - 30.0) < 1e-9


def test_score_inside_across_and_crossing_geometry():
    D = LO.load_plan(_plan(4, widths=[100, 5, 100]))
    reg = {"p0": "A", "p1": "A", "p2": "B", "p3": "B"}
    S = LO.score(D, reg, 340.0, "fwd", Ttab=T)
    s = S["summary"]
    assert s["regions"] == 2 and s["bits_inside"] == 200 and s["bits_across"] == 5
    assert s["crossing_ports"] == 1 and s["far_ports"] == 0
    x = S["crossings"][0]
    assert x["xy"] == [2000.0, 500.0]  # the face midpoint of p1 | p2


def test_fwd_branches_parent_child():
    """child fed from the parent's leaf at the tap: unshared(parent) = min(I, v|x - tap|), unshared(child) = forward +
    I_child + the parent-side divergence."""
    D = LO.load_plan(_plan(4, widths=[100, 5, 100]))
    reg = {"p0": "A", "p1": "A", "p2": "B", "p3": "B"}
    v = 340.0
    G = LO.region_geom(D, reg)
    X = LO.crossings(D, reg, G, LO.part_adjacency(D))
    E = LO.region_graph(D, reg, LO.part_adjacency(D), X)
    F = LO.feed_tree(G, E, X, v)
    Tr, _ = LO.arrivals(G, F, v)
    b = LO.branches(G, F, Tr, v, X[0])
    I = v * (2000 + 1000) / 2 / 1000  # 2 x 1 mm region: 510 ps
    fwd = v * 1.0  # tap (2000,500) -> child centre (3000,500): 1 mm
    root = F["root"]
    child = "B" if root == "A" else "A"
    assert F["parent"][child] == root
    # tap == crossing point, so the parent side shares its tree down to a leaf-size node
    u_par, u_ch = (b["ua"], b["ub"]) if root == "A" else (b["ub"], b["ua"])
    assert 0.0 <= u_par <= v * LO.LEAF_UM / 1000.0 and abs(u_ch - u_par - (fwd + I)) < 1e-6


def test_htree_divergence():
    box = (0.0, 0.0, 4000.0, 2000.0)
    assert LO.htree_rem_um(box, (1900, 100), (2100, 100)) == 3000.0  # straddles the root cut: full (w+h)/2
    assert LO.htree_rem_um(box, (100, 100), (1900, 100)) == 2000.0  # parts at the first 2 x 2 mm node: (2+2)/2
    assert LO.htree_rem_um(box, (100, 100), (100, 1900)) == 1500.0  # 2 x 2 -> cut y: (2+1)/2 = 1.5 mm


def test_margin_reuses_landed_phase_ocv_model():
    """the margin equals the shared clk_aocv branch pessimism (+ class-B core latency), droop across regions."""
    br = [dict(ua=1000.0, ub=2000.0, div=500.0, pts=[(0, 0), (1000, 0)])]
    r = LO.margins(br, T, 833.0)[0]
    fc = T["classes"]["A"]["TT"]["cell_share"]
    B = T["classes"]["B"]["TT"]
    nB = max(1, round(250.0 / B["mu_stage_ps"]))
    na = max(1, round(1000.0 / T["classes"]["A"]["TT"]["mu_stage_ps"]))
    nb = max(1, round(2000.0 / T["classes"]["A"]["TT"]["mu_stage_ps"]))

    def side(u, n):
        return dict(cell_ps=fc * u + B["cell_share"] * 250.0, net_ps=(1 - fc) * u + (1 - B["cell_share"]) * 250.0,
                    stages={"A": n, "B": nB})
    p_up = CA.branch_pessimism(T, "TT", side(2000.0, nb), side(1000.0, na), 1000.0, False, "setup")
    d = 1000.0
    assert abs(r["d_tt"] - d) < 0.01
    assert abs(r["raw_tt"] - round(416.5 - (d + p_up), 2)) < 0.06
    # fold: k = 1 (mean of TT/FF d ~ 0.93 P) -> d - P
    assert r["k"] == 1
    assert r["fold_tt"] > r["raw_tt"]


def test_pad_puts_tree_crossings_on_whole_cycles():
    D = LO.load_plan(_plan(6, widths=[100, 5, 100, 5, 100]))
    reg = {"p0": "A", "p1": "A", "p2": "B", "p3": "B", "p4": "C", "p5": "C"}
    S = LO.score(D, reg, 340.0, "fwd", Ttab=T)
    for r in S["crossings_pad"]:
        assert abs(r["d_tt"] - r["k"] * 833.0) < 0.05
    assert S["summary"]["pad_max_ps"] > 0


def test_top_feed_is_worse_than_forwarded_on_a_long_row():
    D = LO.load_plan(_plan(12, widths=[100, 5] * 5 + [100]))
    reg = {f"p{i}": f"R{i // 2}" for i in range(12)}
    fwd = LO.score(D, reg, 340.0, "fwd", Ttab=T)["summary"]
    top = LO.score(D, reg, 340.0, "top", Ttab=T)["summary"]
    assert top["worst_unshared_tt"] > fwd["worst_unshared_tt"]


def test_far_crossing_and_tracks():
    p = _plan(3, widths=[10, 10])
    p["ports"].append(dict(id="far", src=dict(part="p0"), dst=dict(part="p2"), width=7, kind="data"))
    D = LO.load_plan(p)
    reg = {"p0": "A", "p1": "B", "p2": "C"}
    S = LO.score(D, reg, 340.0, "fwd", Ttab=T)
    assert S["summary"]["far_ports"] == 1 and S["summary"]["far_bits"] == 7
    t = {tuple(r["pair"]): r for r in S["tracks"]["worst"]}
    assert t[("A", "B")]["bits"] == 17 and t[("A", "B")]["supply"] == 6000  # 1 mm face x 6 pins/um
    assert S["tracks"]["bits_by_hops"] == {1: 20, 2: 7}


def test_propose_span_cap_and_heavy_pairs():
    D = LO.load_plan(_plan(8, widths=[100, 1, 100, 1, 100, 1, 100]))
    reg = LO.propose(D, span_mm=2.0)
    assert len(set(reg.values())) == 4
    for i in range(0, 8, 2):
        assert reg[f"p{i}"] == reg[f"p{i + 1}"]
    reg3 = LO.propose(D, span_mm=3.0)  # 3 mm: pairs cannot merge into 4 mm, so heavy pairs stay paired
    G = LO.region_geom(D, reg3)
    assert max(max(g["w"], g["h"]) for g in G.values()) <= 3000.0


def test_propose_hard_joins_neighbours():
    D = LO.load_plan(_plan(4, widths=[1, 1, 100], hard=(1,)))
    reg = LO.propose(D, span_mm=3.0)
    assert reg["p0"] == reg["p1"] == reg["p2"]


def test_cli_writes_estimate(tmp_path):
    pf = tmp_path / "plan.json"
    pf.write_text(json.dumps(_plan(6, widths=[100, 5, 100, 5, 100])))
    rf = tmp_path / "reg.json"
    rf.write_text(json.dumps({"part_region": {"p0": "A", "p1": "A", "p2": "B", "p3": "B", "p4": "C", "p5": "C"}}))
    LO.main(["both", "--plan", str(pf), "--regions", str(rf), "--die", "tiny", "--v-ps-mm", "340", "--span-mm", "2",
             "--out", str(tmp_path / "o"), "--no-png"])
    md = (tmp_path / "o" / "tiny_ESTIMATE.md").read_text()
    assert "baseline" in md and "proposed_s2" in md and "PAD" in md
    j = json.loads((tmp_path / "o" / "tiny_baseline_fwd.json").read_text())
    assert j["summary"]["crossing_ports"] == 2 and j["plan"]["sha256"] and len(j["crossings_worst100"]) == 2


# ------------------------------------------------------------------------------------------- LOCALITY-SCORE-2 (v2)
def _grid4(widths=(100, 100, 100, 10)):
    """2 x 2 grid of 1 mm partitions with a port cycle p00-p10-p11-p01-p00 (the last edge carries widths[3])."""
    types = {"t": {"outline_um": [1000.0, 1000.0]}}
    xy = {"p00": (0, 0), "p10": (1000, 0), "p11": (1000, 1000), "p01": (0, 1000)}
    parts = [dict(name=n, type="t", origin_um=list(map(float, o)), orient="R0") for n, o in xy.items()]
    cyc = [("p00", "p10"), ("p10", "p11"), ("p11", "p01"), ("p01", "p00")]
    ports = [dict(id=f"q{i}", src=dict(part=a), dst=dict(part=b), width=widths[i], kind="data")
             for i, (a, b) in enumerate(cyc)]
    return dict(die=dict(outline_um=[2000, 2000], period_ps=833), partition_types=types, partitions=parts,
                ports=ports, budgets=dict(face_pins_per_um=6))


def test_spine_feed_parent_child_unshared():
    """spine: the child root is a spine segment (parent centre -> tap -> child centre) away, no parent insertion;
    the paths part at the parent centre: unshared(parent) = I_p, unshared(child) = segment + I_c."""
    D = LO.load_plan(_plan(4, widths=[100, 5, 100]))
    reg = {"p0": "A", "p1": "A", "p2": "B", "p3": "B"}
    v = 340.0
    S = LO.score(D, reg, v, "spine", Ttab=T)
    x = S["crossings"][0]
    I = v * 1.5  # 2 x 1 mm
    seg = v * 2.0  # (1000,500) -> (2000,500) -> (3000,500)
    assert abs(x["unshared_tt"] - (seg + I)) < 0.2
    assert abs(abs(x["d_tt"]) - seg) < 0.2  # nominal d = the spine segment (unbalanced)
    assert x["on_feed"] and x["tree_hops"] == 1


def test_dme_spine_zero_skew_and_ca_reading():
    D = LO.load_plan(_plan(6, widths=[100, 5, 100, 5, 100]))
    reg = {"p0": "A", "p1": "A", "p2": "B", "p3": "B", "p4": "C", "p5": "C"}
    S = LO.score(D, reg, 340.0, "dme", Ttab=T)
    for r in S["crossings"]:
        assert abs(r["d_tt"]) < 0.05  # zero skew
        assert abs(r["ca_tt"] - (416.5 - r["p_tt"])) < 0.15 and r["raw_tt"] <= r["ca_tt"] + 0.1
    # root = B (centre): h(B) = seg 2 mm + I 1.5 mm = 3.5 mm x 340
    assert abs(S["crossings"][0]["unshared_tt"] - 340.0 * 3.5) < 0.5


def test_fish_shared_and_leaf_delay():
    g = dict(w=4000.0, h=1000.0, cen=(2000.0, 500.0), bbox=(0, 0, 4000, 1000))
    assert LO.fish_shared_um(g, (3000, 900), (3500, 100)) == 1000.0  # same side: up to the nearer rib
    assert LO.fish_shared_um(g, (1000, 900), (3500, 100)) == 0.0  # opposite sides of the spine centre
    assert LO.fish_shared_um(g, (3000, 900), (3010, 700)) == 1000.0 + 200.0  # same rib, same side
    assert abs(LO.leaf_delay(g, (3000, 900), 340.0, "fish") - 340.0 * 1.4) < 1e-9
    assert abs(LO.leaf_delay(g, (3000, 900), 340.0, "spine") - 340.0 * 2.5) < 1e-9


def test_propose_tree_closes_the_loop():
    D = LO.load_plan(_grid4())
    M, padj = LO.traffic(D), LO.part_adjacency(D)
    reg0 = LO.propose(D, 0.9, M, padj)
    lb0, lp0, _, _ = LO.loop_stats(reg0, M, padj)
    assert len(set(reg0.values())) == 4 and lp0 == 1 and lb0 == 10
    reg, log = LO.propose_tree(D, 0.9, 2.0, M, padj)
    lb, lp, _, _ = LO.loop_stats(reg, M, padj)
    assert lb == 0 and lp == 0 and log[-1][1] == 0
    reg1, _ = LO.propose_tree(D, 0.9, 0.9, M, padj)  # no room: the loop stays and is counted
    assert LO.loop_stats(reg1, M, padj)[1] == 1


def test_hop_reading_retimes_off_feed_along_the_tree():
    D = LO.load_plan(_grid4())
    reg = {"p00": "A", "p10": "B", "p11": "C", "p01": "D"}
    S = LO.score(D, reg, 340.0, "spine", Ttab=T)
    s = S["summary"]
    assert s["off_feed_ports"] == 1 and s["hop_chains"] == 1 and s["hop_max_hops"] == 3
    assert s["hop_extra_bit_hops"] == 10 * 2
    assert all(r["on_feed"] for r in S["crossings_hop"])
    assert s["hop_ca_worst_tt"] >= s["ca_worst_tt"]


def test_cli_v2(tmp_path):
    pf = tmp_path / "plan.json"
    pf.write_text(json.dumps(_grid4()))
    LO.main(["v2", "--plan", str(pf), "--die", "g", "--v-ps-mm", "340", "--map", "part=part", "--tree", "0.9:2",
             "--span-mm", "0.9", "--out", str(tmp_path / "o"), "--no-png"])
    md = (tmp_path / "o" / "g_v2_ESTIMATE.md").read_text()
    assert "COUNT-ALIGNED" in md and "tree_s0.9c2" in md and "ca+hop" in md
    j = json.loads((tmp_path / "o" / "g_v2.json").read_text())
    assert set(j["best"]) == {"ring", "ca", "ring+hop", "ca+hop", "static", "static+hop"}


# ------------------------------------------------------------------------------------------- LOCALITY-SCORE-3 (v3)
HEAD3 = HERE / "testdata" / "land_head3_sfbR_ocv_ttff.json.gz"


def test_cap_reproduces_meso_count_head3():
    """the adopted CA ring through locality's entry on the LAND-HEAD-3 routed rows = MESO-COUNT-2's HEAD result
    (K from the derated lag, directed start tree; MESO-RECONCILE-1): 427/427 DEPTH4, 0 FAIL, latency 2 x 256 / 3 x 171,
    worst margin 126.2 ps low (+-5% wander; MESO-COUNT-1's 104.1 was the pinned tree low edge, NUMBER-CHECK 20:48)."""
    import gzip
    d = json.load(gzip.open(HEAD3, "rt"))
    cr = {c[:2]: d["corners"][c]["all"] for c in ("TT_droop-regions_corelat250", "FF_droop-regions_corelat202.5")}
    s, res = LO.cap_plan_corners(cr, 833.0)
    assert s["crossings"] == 427 and s["depth4"] == 427 and s["depth8"] == 0 and s["fail"] == 0
    assert s["components"] == 1 and s["tree_edges_clean"] == s["tree_edges"] == 325
    assert s["lat_hist"] == {"2": 256, "3": 171}
    assert s["worst_margin_lo_ps"] == 126.2 and s["worst_margin_hi_ps"] >= 100.0
    w = res["coll_EN1_u__0"]  # the 20:26 ruling's worst crossing: derated L 1169-1327 (NC) +-22 wander, latency 3, DEPTH 4
    assert w["depth"] == 4 and w["lat_cycles"] == 3 and round(w["L_lo_ps"]) == 1147 and round(w["L_hi_ps"]) == 1350


def test_cap_reading_on_modelled_crossings():
    D = LO.load_plan(_plan(6, widths=[100, 5, 100, 5, 100]))
    reg = {"p0": "A", "p1": "A", "p2": "B", "p3": "B", "p4": "C", "p5": "C"}
    S = LO.score(D, reg, 340.0, "fish", Ttab=T)
    s = LO.cap_reading(S["crossings"], 833.0)
    assert s["crossings"] == 2 and s["fail"] == 0 and s["depth4"] == 2 and s["components"] == 1
    for r in S["crossings"]:
        assert r["depth"] == 4 and r["lat"] >= 1 and r["m_lo"] >= 100 and r["m_hi"] >= 100
        assert r["pu_tt"] >= 0 and r["pd_ff"] >= 0 and r["ua_tt"] + r["ub_tt"] > 0


def test_cap_components_planned_separately():
    """two disconnected crossing graphs: count_align_plan needs one start tree each."""
    rows = {c: [dict(port=p, src=a, dst=b, d_ps=50.0, p_up_ps=20.0, p_dn_ps=20.0, unshared_a_ps=300.0,
                     unshared_b_ps=300.0, margin_ps=300.0) for p, a, b in (("x", "A", "B"), ("y", "C", "D"),
                                                                           ("z", "D", "E"))] for c in ("TT", "FF")}
    s, res = LO.cap_plan_corners(rows, 833.0)
    assert s["components"] == 2 and s["fail"] == 0 and set(res) == {"x", "y", "z"}


def test_cap_hop_only_for_depth8_fails():
    D = LO.load_plan(_grid4())
    reg = {"p00": "A", "p10": "B", "p11": "C", "p01": "D"}
    S = LO.score(D, reg, 340.0, "spine", Ttab=T)
    R = S["crossings"]
    off = [r for r in R if not r["on_feed"]]
    assert len(off) == 1
    off[0]["pu_tt"] = off[0]["pu_ff"] = 9000.0  # no DEPTH fits this one
    s = LO.cap_reading(R, 833.0)
    assert s["fail"] == 1 and s["depth4"] + s["depth8"] == 3
    Tr, _ = LO.arrivals(S["G"], S["F"], 340.0)
    X = LO.crossings(D, reg, S["G"], LO.part_adjacency(D))
    h = LO.cap_hop(S["G"], S["F"], Tr, 340.0, X, R, T, 833.0)
    hs = h["summary"]
    assert hs["hop_chains"] == 1 and hs["hop_max_hops"] == 3 and hs["fail"] == 0 and hs["crossings"] == 3
    assert h["chains"][0]["lat"] == sum(r["lat"] for r in h["rows"])  # one landing per feed edge
    R2 = LO.score(D, reg, 340.0, "spine", Ttab=T)["crossings"]
    LO.cap_reading(R2, 833.0)
    assert LO.cap_hop(S["G"], S["F"], Tr, 340.0, X, R2, T, 833.0) is None  # nothing fails: no chains


def test_cli_v3(tmp_path):
    pf = tmp_path / "plan.json"
    pf.write_text(json.dumps(_grid4()))
    LO.main(["v3", "--plan", str(pf), "--die", "g", "--v-ps-mm", "340", "--map", "part=part", "--tree", "0.9:0.9",
             "--span-mm", "0.9", "--out", str(tmp_path / "o"), "--no-png", "--v-note", "test"])
    md = (tmp_path / "o" / "g_v3_ESTIMATE.md").read_text()
    assert "adopted count-aligned ring" in md and "DEPTH4" in md
    j = json.loads((tmp_path / "o" / "g_v3.json").read_text())
    assert j["best"]["summary"]["fail"] == 0 and j["crossings"]
    assert (tmp_path / "o" / "g_v3_crossings.tsv").read_text().count("\n") == len(j["crossings"]) + 1
