"""START-TREE-1 tests: --start-tree clock (the start / reset-release tree follows the clock tree, METHODOLOGY 12.16b(iv))."""
import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location("cap_st", HERE / "count_align_plan.py")
cap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cap)
import count_align_bind as CAB  # noqa: E402

T = 833.0
AP = T / 8
SEG = 90.0      # ps per spine tree level


def ctx_chain(n=6, seg=SEG, ocv_frac=0.10, fall=0.0):
    """clock spine h -> h0 -> h00 ... ; region Ri hangs off spine node i at 'h'+'0'*i+'1' with two taps (leaf legs
    40 / 60 ps).  ocv = ocv_frac x unshared (late branch) per side, a stand-in for clock_ocv_fn.
    fall (FLOW-ONEMODEL-1): MEASURED fall arrival = rise arrival + fall ps at every tap and node (0 = 50 % duty);
    a callable fall(level) gives a per-level distortion; None = the proof has rise arrivals only."""
    nl, ne, ns, nxy = {}, {}, {}, {}
    taps = {}

    def node(p, t, st):
        nl[p], ne[p], ns[p], nxy[p] = t, t - 2.0, st, [100.0 * len(p), 0.0]
    for i in range(n + 1):
        p = "h" + "0" * i
        node(p, seg * i, i)
    for i in range(n):
        rp = "h" + "0" * i + "1"
        node(rp, seg * i + 50.0, i + 1)
        for j, leg in enumerate((40.0, 60.0)):
            tp = rp + str(j)
            node(tp, nl[rp] + leg, i + 2)
            k = f"t_R{i}_{j}"
            taps[k] = dict(port=k, part=f"R{i}", cppr_node=f"R{i}", tree_path=tp, late_ps=nl[tp], early_ps=ne[tp],
                           stages_from_root=i + 2, xy_um=nxy[tp])
    meta = dict(node_late_ps=nl, node_early_ps=ne, node_stages=ns, node_xy_um=nxy, cppr_node_range_ps={})
    if fall is not None:
        fd = fall if callable(fall) else (lambda lev, f=fall: f)
        meta["node_fall_late_ps"] = {p: v + fd(len(p)) for p, v in nl.items()}
        meta["node_fall_early_ps"] = {p: v + fd(len(p)) for p, v in ne.items()}
        for t in taps.values():
            t["fall_late_ps"] = t["late_ps"] + fd(len(t["tree_path"]))
            t["fall_early_ps"] = t["early_ps"] + fd(len(t["tree_path"]))

    def ocv(a, b, check):
        A, B = taps[a], taps[b]
        f = cap._lcp(A["tree_path"], B["tree_path"])
        return ocv_frac * max(A["late_ps"] - nl[f], B["late_ps"] - nl[f])
    return {"TT": dict(meta=meta, taps=taps, ocv=ocv, rng={})}


def row(port, s, d, dd, up, dn, unsh=500.0):
    return dict(port=port, src=s, dst=d, d_ps=dd, p_up_ps=up, p_dn_ps=dn, unshared_a_ps=unsh, unshared_b_ps=unsh,
                margin_ps=0.0)


def by(out):
    return {o["port"]: o for o in out}


def chain_rows(n=6, wide=380.0):
    """neighbour crossings Ri -> Ri+1 with WIDE region-pair-union intervals (ambiguous as start edges) + a far loop
    R0 -> R(n-1) and its way back"""
    rows = [row(f"x{i}", f"R{i}", f"R{i+1}", 300.0, wide, wide) for i in range(n - 1)]
    rows += [row("far", "R0", f"R{n-1}", 450.0, 200.0, 200.0), row("back", f"R{n-1}", "R0", -450.0, 200.0, 200.0)]
    return rows


def test_default_unchanged_without_start_edges():
    rows = chain_rows()
    a = cap.plan(copy.deepcopy(rows), T, AP, 0.05)
    b = cap.plan(copy.deepcopy(rows), T, AP, 0.05, start_edges=None, start_root=None)
    assert json.dumps(a, sort_keys=True, default=str) == json.dumps(b, sort_keys=True, default=str)
    assert "start_tree" not in a[0] and all("start_hops" not in o for o in a[1])


def test_data_tree_accumulates_ambiguity_clock_tree_does_not():
    rows = chain_rows()
    s0, out0, _ = cap.plan(copy.deepcopy(rows), T, AP, 0.05)
    assert s0["max_path_ambiguous_cycles"] >= 3          # the root cause: ambiguity adds up along the start path
    root, edges, info = cap.clock_start_edges(rows, ctx_chain())
    s1, out1, regs = cap.plan(rows, T, AP, 0.05, start_edges=edges, start_root=root)
    st = s1["start_tree"]
    assert st["start_fail"] == 0 and st["start_clean"] == st["start_edges"] == len(edges)
    assert s1["max_path_ambiguous_cycles"] == 0 and s1["fail"] == 0
    assert all(o["kind"] == "nontree" and o["path_ambiguous_cycles"] == 0 for o in out1)
    worst = max(out0, key=lambda o: o["path_ambiguous_cycles"])
    assert worst["L_width_ps"] - by(out1)[worst["port"]]["L_width_ps"] >= 3 * T - 1   # >= 3 cycles narrower
    # the start tree follows the clock: every region hangs off a spine (virtual) node or another region
    assert {g["region"] for g in regs if not g.get("virtual")} == {f"R{i}" for i in range(6)}
    assert root.startswith("st:") and info["branch_nodes"] >= 4
    # each port's ends: virtual node tap -> region's shortest-leg tap
    e = next(e for e in edges if e["dst"] == "R3")
    assert e["capture"] == "t_R3_0" and e["launch"].startswith("__st__")
    n, bad, wl, wh = cap.mc_check(rows + edges, out1, regs, T, 600)
    assert bad == 0


def test_mc_catches_wrong_start_step():
    rows = chain_rows()
    root, edges, _ = cap.clock_start_edges(rows, ctx_chain())
    s, out, regs = cap.plan(rows, T, AP, 0.05, start_edges=edges, start_root=root)
    n, bad, _, _ = cap.mc_check(rows + edges, out, regs, T, 300)
    assert bad == 0
    g = next(g for g in regs if g["region"] == "R4")
    g["start_from"]["rtl"]["PAD"] += 3                    # mutant: start origin 3 counts late
    n, bad, _, _ = cap.mc_check(rows + edges, out, regs, T, 300)
    assert bad > 0


def test_long_edge_is_retimed_on_tree_nodes():
    """one region far down a slow, high-variation spine: the direct port is too wide, retime stages on spine nodes make
    every segment clean (bounded stages); --start-clean width demands it whatever the phase"""
    mk = lambda: ctx_chain(n=12, seg=150.0, ocv_frac=0.15)  # noqa: E731
    rows = [row("ab", "R0", "R11", 1800.0, 100.0, 100.0), row("ba", "R11", "R0", -1800.0, 100.0, 100.0)]
    root, edges, info = cap.clock_start_edges(rows, mk(), clean_by="width")
    s, out, regs = cap.plan(copy.deepcopy(rows), T, AP, 0.05, start_edges=edges, start_root=root)
    assert 1 <= info["retime_nodes"] <= 8 and s["start_tree"]["start_fail"] == 0
    assert all(e["dst"].startswith("st:") for e in edges if e["retime"])
    assert all(e["p_up_ps"] + e["p_dn_ps"] <= T / 2 - 2 * AP + 1e-9 for e in edges)
    assert s["max_path_ambiguous_cycles"] == 0
    root1, edges1, info1 = cap.clock_start_edges(rows, mk())                  # default: the CA (phase) rule
    assert info1["retime_nodes"] <= info["retime_nodes"]
    root2, edges2, info2 = cap.clock_start_edges(rows, mk(), retime_max=0, clean_by="width")
    s2, _, _ = cap.plan(copy.deepcopy(rows), T, AP, 0.05, start_edges=edges2, start_root=root2)
    assert info2["retime_nodes"] == 0 and s2["start_tree"]["start_fail"] >= 1   # unclean reset release FAILs


def test_bind_and_verify_with_start_ports_region_and_parts():
    rows = chain_rows()
    for r in rows:
        r["src_part"], r["dst_part"] = r["src"], r["dst"]
    root, edges, _ = cap.clock_start_edges(rows, ctx_chain())
    s, out, regs = cap.plan(copy.deepcopy(rows), T, AP, 0.05, start_edges=edges, start_root=root)
    doc = dict(summary=dict(s, period_ps=T, pad=0), regions=regs, crossings=out,
               start_edges=[{k: v for k, v in e.items() if not k.startswith("_")} for e in edges])
    for parts in (None, {r["port"]: (r["src_part"], r["dst_part"]) for r in rows}):
        b = CAB.bind(copy.deepcopy(doc), parts=parts)
        assert b["start_tree"] == "clock" and len(b["start_ports"]) == len(edges)
        v = CAB.verify(b, 600)
        assert v["identity_and_loop_errors"] == [] and v["sim_window_violations"] == 0
        assert v["fundamental_cycles"] == len(rows)
    bad = copy.deepcopy(doc)
    g = next(g for g in bad["regions"] if g["region"] == "R2")
    g["origin_cycles"] += 1
    with pytest.raises(CAB.BindError):
        CAB.bind(bad)


def test_cli_needs_proof_and_clock_variation(tmp_path):
    f = tmp_path / "x.json"
    f.write_text(json.dumps(dict(corners={"TT_x": dict(all=chain_rows())})))
    for extra in ([], ["--sta-proof", str(tmp_path), "--sta-plan", str(f)]):
        with pytest.raises(SystemExit):     # no proof / no --sta-clock-ocv table: refused (12.16b(iv))
            cap.main([str(f), "--corner", "TT_x", "--start-tree", "clock"] + extra)


def test_die_sta_rechecks_start_ports_on_arrivals():
    """12.16d: the gate re-times every start port on the proof arrivals; a moved sync tap clock FAILs it"""
    import die_sta_related as DSR
    rows = chain_rows()
    ctx = ctx_chain()
    root, edges, _ = cap.clock_start_edges(rows, ctx)
    s, out, regs = cap.plan(rows, T, AP, 0.05, start_edges=edges, start_root=root)
    doc = dict(summary=dict(s, period_ps=T, pad=0), regions=regs, crossings=out,
               start_edges=[{k: v for k, v in e.items() if not k.startswith("_")} for e in edges])
    b = CAB.bind(doc)
    k = ctx["TT"]
    taps = {q: t for q, t in k["taps"].items() if not q.startswith("__st__")}
    old, DSR.CPPR_LCA = DSR.CPPR_LCA, True
    try:
        ok = DSR.count_align_start_ports(b, taps, k["meta"], T, {}, k["ocv"])
        assert len(ok) == len(edges) and all(r["ok"] for r in ok)
        assert not any(q.startswith("__st__") for q in taps)          # virtual pins removed again
        e = next(e for e in edges if e["dst"] == "R3")
        off = T / 2 if b["regions"]["R3"]["edge_fall"] else 0.0
        sh = (off - e["d_ps"]) % T                    # mutant: the sync tap clock moves the phase onto the boundary
        moved = dict(taps)
        moved[e["capture"]] = dict(moved[e["capture"]], late_ps=moved[e["capture"]]["late_ps"] + sh,
                                   early_ps=moved[e["capture"]]["early_ps"] + sh)
        bad = {r["port"]: r for r in DSR.count_align_start_ports(b, moved, k["meta"], T, {}, k["ocv"])}
        assert not bad[e["port"]]["ok"]
        b2 = copy.deepcopy(b)
        b2["start_ports"][e["port"]]["capture"] = "no_such_tap"
        miss = {r["port"]: r for r in DSR.count_align_start_ports(b2, taps, k["meta"], T, {}, k["ocv"])}
        assert miss[e["port"]]["ok"] is False and miss[e["port"]]["reason"] == "no taps"
    finally:
        DSR.CPPR_LCA = old


def ctx_deep(depth=6, seg=130.0, feed=120.0, ocv_frac=0.15, fall=0.0, extra=()):
    """region A (root h0, below the die root by a short feed) and region B fed THROUGH A's root (B root h02); each region
    has two taps `depth` levels of `seg` ps below its root (big-partition in-region insertion).
    fall (FLOW-ONEMODEL-1, as ctx_chain): MEASURED fall arrival = rise + fall ps at every tap and node; None = rise only."""
    nl, ne, ns, nxy = {}, {}, {}, {}
    taps = {}

    def node(p, t, st):
        nl[p], ne[p], ns[p], nxy[p] = t, t - 2.0, st, [50.0 * len(p), 0.0]
    node("h", 0.0, 0)
    node("h0", feed, 1)                       # A root
    node("h02", 2 * feed, 2)                  # B root, fed through A's root
    for rp, _ in extra:                       # more regions fed through A's root (multi-feed A)
        node(rp, 2 * feed, 2)
    for rp, part in (("h0", "A"), ("h02", "B")) + tuple(extra):
        for j in range(2):
            p = rp + str(j)
            node(p, nl[rp] + seg, ns[rp] + 1)
            for i in range(1, depth):
                p = p + "0"
                node(p, nl[rp] + seg * (i + 1), ns[rp] + i + 1)
            k = f"t_{part}_{j}"
            taps[k] = dict(port=k, part=part, cppr_node=part, tree_path=p, late_ps=nl[p] + 3.0 * j,
                           early_ps=ne[p] + 3.0 * j, stages_from_root=ns[p], xy_um=nxy[p])
    meta = dict(node_late_ps=nl, node_early_ps=ne, node_stages=ns, node_xy_um=nxy, cppr_node_range_ps={})
    if fall is not None:
        meta["node_fall_late_ps"] = {p: v + fall for p, v in nl.items()}
        meta["node_fall_early_ps"] = {p: v + fall for p, v in ne.items()}
        for t in taps.values():
            t["fall_late_ps"], t["fall_early_ps"] = t["late_ps"] + fall, t["early_ps"] + fall

    def ocv(a, b, check):
        A, B = taps[a], taps[b]
        f = cap._lcp(A["tree_path"], B["tree_path"])
        return ocv_frac * max(A["late_ps"] - nl[f], B["late_ps"] - nl[f])
    return {"TT": dict(meta=meta, taps=taps, ocv=ocv, rng={})}


def test_retime_up_climbs_launch_region_to_fork():
    """DIE-S81-13: the launch is a leaf deep in its own region (in-region insertion alone makes every capture-side
    segment too wide); --start-retime-up puts retime flops on ANCESTORS of the launch tap (up to the fork), then down the
    capture path; every port width-clean.  Default (off) leaves the port unclean (unchanged behaviour)."""
    rows = [row("ab", "A", "B", 0.0, 100.0, 100.0), row("ba", "B", "A", 0.0, 100.0, 100.0)]
    r0, e0, i0 = cap.clock_start_edges(rows, ctx_deep(), clean_by="width")
    s0, _, _ = cap.plan(copy.deepcopy(rows), T, AP, 0.05, start_edges=e0, start_root=r0)
    assert s0["start_tree"]["start_fail"] >= 1                     # default: the deep launch leaf stays unclean
    r1, e1, i1 = cap.clock_start_edges(rows, ctx_deep(), clean_by="width", retime_up=True)
    s1, _, _ = cap.plan(copy.deepcopy(rows), T, AP, 0.05, start_edges=e1, start_root=r1)
    assert s1["start_tree"]["start_fail"] == 0 and s1["max_path_ambiguous_cycles"] == 0
    assert all(e["p_up_ps"] + e["p_dn_ps"] <= T / 2 - 2 * AP + 1e-9 for e in e1)
    la = ctx_deep()["TT"]["taps"]["t_A_0"]["tree_path"]             # A's launch leaf path
    up = [e for e in e1 if e["retime"] and e["launch"] == "t_A_0"]
    assert len(up) == 1 and up[0]["dst"].startswith("st:") and up[0]["capture"].startswith("__st__")
    upp = up[0]["capture"][6:]                                        # the up stage's tree node
    assert la.startswith(upp) and len(upp) < len(la)                 # climbs to an ancestor of the A leaf
    assert all(e.get("fall_lo") is not None for e in e1)          # every stage judged on the MEASURED fall too
    assert 1 <= i1["retime_nodes"] <= 8
    # same answer as default when nothing needs to climb (phase rule on the chain fixture)
    rows2 = chain_rows()
    a = cap.clock_start_edges(rows2, ctx_chain())
    b = cap.clock_start_edges(rows2, ctx_chain(), retime_up=True)
    assert json.dumps(a, sort_keys=True, default=str) == json.dumps(b, sort_keys=True, default=str)


def test_retime_up_cli_needs_clock_tree(tmp_path):
    f = tmp_path / "x.json"
    f.write_text(json.dumps(dict(corners={"TT_x": dict(all=chain_rows())})))
    with pytest.raises(SystemExit):
        cap.main([str(f), "--corner", "TT_x", "--start-retime-up"])


def test_retime_up_fails_closed_without_measured_fall():
    """FLOW-ONEMODEL-1 composition: retime_up judges each candidate stage with the gate's pair function
    (die_sta_related.ca_pair_interval, rise AND measured fall, as sta_port_intervals); a rise-only proof leaves no
    width-clean stage, so the port stays unclean (fail closed), never rise + T/2."""
    rows = [row("ab", "A", "B", 0.0, 100.0, 100.0), row("ba", "B", "A", 0.0, 100.0, 100.0)]
    r, e, _ = cap.clock_start_edges(rows, ctx_deep(fall=None), clean_by="width", retime_up=True)
    s, _, _ = cap.plan(copy.deepcopy(rows), T, AP, 0.05, start_edges=e, start_root=r)
    assert s["start_tree"]["start_fail"] >= 1


def test_retime_up_stage_interval_equals_gate_pair_interval():
    """plan == gate: the retime_up stage's rise and fall intervals are die_sta_related.ca_pair_interval on its taps"""
    import die_sta_related as DSR
    rows = [row("ab", "A", "B", 0.0, 100.0, 100.0), row("ba", "B", "A", 0.0, 100.0, 100.0)]
    c = ctx_deep(fall=7.0)
    _, e1, _ = cap.clock_start_edges(rows, c, clean_by="width", retime_up=True)
    up = [x for x in e1 if x["retime"] and x["launch"] == "t_A_0"][0]
    tp = c["TT"]["taps"]
    old, DSR.CPPR_LCA = DSR.CPPR_LCA, True
    try:
        r = DSR.ca_pair_interval(tp[up["launch"]], tp[up["capture"]], up["launch"], up["capture"], {}, c["TT"]["ocv"])
        f = DSR.ca_pair_interval(tp[up["launch"]], tp[up["capture"]], up["launch"], up["capture"], {}, c["TT"]["ocv"],
                                 "fall")
    finally:
        DSR.CPPR_LCA = old
    assert abs((up["d_ps"] - up["p_dn_ps"]) - r[0]) < 1e-6 and abs((up["d_ps"] + up["p_up_ps"]) - r[1]) < 1e-6
    assert abs(up["fall_lo"] - f[0]) < 1e-6 and abs(up["fall_hi"] - f[1]) < 1e-6


def test_retime_up_multi_feed_region_one_tree():
    """DIE-QC-13: region A feeds B, C and D through its root; every child climbs from the same A launch leaf to the same
    ancestor.  The up stage is built ONCE and shared (no duplicate fork retime node), the start graph is one tree from
    the root, and every port is clean."""
    rows = [row(a + b, a, b, 0.0, 100.0, 100.0) for a, b in (("A", "B"), ("A", "C"), ("A", "D"))]
    c = ctx_deep(extra=(("h03", "C"), ("h04", "D")))
    r, e, _ = cap.clock_start_edges(rows, c, clean_by="width", retime_up=True)
    up = [x for x in e if x["retime"] and x["src"] == "A"]
    assert len(up) == 1                                                # one shared up stage, not one per child
    dsts = [x["dst"] for x in e]
    assert len(dsts) == len(set(dsts))                                 # each node has one parent
    cap.start_tree_check(r, e)
    s, _, _ = cap.plan(copy.deepcopy(rows), T, AP, 0.05, start_edges=e, start_root=r)
    assert s["start_tree"]["start_fail"] == 0


def test_start_tree_check_fails_closed():
    """a duplicate node (two parents) or an unreached node raises: the plan never runs on a start graph that is not a tree"""
    e = [dict(src="R", dst="st:x"), dict(src="R", dst="st:x")]
    with pytest.raises(ValueError, match="not a tree"):
        cap.start_tree_check("R", e)
    with pytest.raises(ValueError, match="not reached"):
        cap.start_tree_check("R", [dict(src="R", dst="A"), dict(src="Q", dst="B")])


def test_physical_reach_keeps_stages_and_retimes_phase_clean_chain():
    rows = chain_rows(12)
    _, default, _ = cap.clock_start_edges(rows, ctx_chain(12, seg=5))
    _, bounded, info = cap.clock_start_edges(rows, ctx_chain(12, seg=5), max_hop_um=150, retime_max=32)
    assert len(bounded) > len(default)
    assert info['reach_fail'] == 0 and info['retime_nodes'] > 0
    assert all(e['hop_um'] <= 150 and e['clean_ok'] for e in bounded)
    # The additional registered edges enter the existing boot/path price calculation.
    s, _, regs = cap.plan(rows, T, AP, 0.05, start_edges=bounded, start_root=info['root'])
    assert s['start_tree']['start_fail'] == 0
    old, _, _ = cap.plan(rows, T, AP, 0.05, start_edges=default, start_root=info['root'])
    assert s['max_tree_depth'] > old['max_tree_depth']
    assert max(g['origin_cycles'] for g in regs) > 3
    assert all('hop_um' in g['start_from'] for g in regs if g['start_from'])


def test_physical_reach_fails_closed_without_intermediate_nodes():
    _, edges, info = cap.clock_start_edges(chain_rows(), ctx_chain(), max_hop_um=50)
    assert info['reach_fail'] > 0
    assert any(e['hop_um'] > 50 and not e['clean_ok'] for e in edges)
    c = ctx_chain()
    del c['TT']['meta']['node_xy_um']
    with pytest.raises(ValueError, match='coordinates'):
        cap.clock_start_edges(chain_rows(), c, max_hop_um=405)
    with pytest.raises(ValueError, match='finite and positive'):
        cap.clock_start_edges(chain_rows(), ctx_chain(), max_hop_um=float('nan'))


def test_capture_override_uses_actual_declared_region_tap():
    _, edges, _ = cap.clock_start_edges(chain_rows(), ctx_chain(), capture_taps={'R3':'t_R3_1'})
    assert next(e for e in edges if e['dst']=='R3')['capture']=='t_R3_1'
    for bad in [{'R3':'t_R4_0'}, {'R3':'invented'}, {'R99':'t_R3_0'}]:
        with pytest.raises(ValueError, match='measured proof tap'):
            cap.clock_start_edges(chain_rows(), ctx_chain(), capture_taps=bad)
