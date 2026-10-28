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
