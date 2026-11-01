"""HBM-CLKLOC-7 --start-lift tests: an unclean START into a mesh-clocked region (no clock-tree node below its entry)
is launched from a retime flop on the clock path above its virtual start parent; default off = unchanged."""
import copy

import test_count_align_starttree as TS

cap = TS.cap


def ctx_mesh(L):
    """TS.ctx_chain + region M whose only tap hangs directly on spine-branch node h00002 (a hub mesh entry) at L ps"""
    c = TS.ctx_chain()
    k = c["TT"]
    m = k["meta"]
    m["node_late_ps"]["h00002"], m["node_early_ps"]["h00002"] = L, L - 2
    m["node_stages"]["h00002"], m["node_xy_um"]["h00002"] = 5, [500.0, 0.0]
    for f in ("node_fall_late_ps", "node_fall_early_ps"):
        m[f]["h00002"] = m["node_late_ps" if "late" in f else "node_early_ps"]["h00002"]
    k["taps"]["t_M_0"] = dict(port="t_M_0", part="M", cppr_node="M", tree_path="h00002", late_ps=L, early_ps=L - 2,
                              fall_late_ps=L, fall_early_ps=L - 2, stages_from_root=6, xy_um=[500.0, 0.0])
    return c


ROWS = TS.chain_rows() + [TS.row("xm", "R3", "M", 300.0, 100.0, 100.0)]


def test_lift_cleans_mesh_region_start():
    _, e0, i0 = cap.clock_start_edges(copy.deepcopy(ROWS), ctx_mesh(2300.0))
    assert [e["port"] for e in e0 if not e["clean_ok"]] == ["start:st:h0000->M"]
    root, e1, i1 = cap.clock_start_edges(copy.deepcopy(ROWS), ctx_mesh(2300.0), lift=True)
    assert all(e["clean_ok"] for e in e1) and i1["lifted"] == 1
    lifted = [e for e in e1 if "@lift" in e["port"]]
    assert {e["port"] for e in lifted} == {"start:st:h->st:h00@lift", "start:st:h00@lift->M"}
    assert next(e for e in lifted if e["dst"] == "st:h00@lift")["retime"] is True
    cap.start_tree_check(root, e1)
    # every other edge is the default plan's edge
    keep = {e["port"]: e for e in e0 if e["dst"] != "M"}
    assert all(keep[e["port"]] == e for e in e1 if "@lift" not in e["port"])


def test_lift_default_off_is_unchanged():
    a = cap.clock_start_edges(copy.deepcopy(ROWS), ctx_mesh(2300.0))
    b = cap.clock_start_edges(copy.deepcopy(ROWS), ctx_mesh(2300.0), lift=False)
    assert a[0] == b[0] and a[1] == b[1] and "lifted" not in a[2]


def test_lift_keeps_unclean_when_no_node_above_is_clean():
    _, e, i = cap.clock_start_edges(copy.deepcopy(ROWS), ctx_mesh(3050.0), lift=True)
    assert [x["port"] for x in e if not x["clean_ok"]] == ["start:st:h0000->M"] and i["lifted"] == 0


def ctx_deep(times, L):
    """region M: tap at the end of a private clock chain h00002 -> h000020 -> h0000200 (node arrivals = times), tap on h0000200
    at L ps -- the greedy deepest clean capture-side stage (h000020) leaves its own hop into M unclean"""
    c = TS.ctx_chain()
    k = c["TT"]
    m = k["meta"]
    p = "h0000"
    for i, t in enumerate(times):
        p += "2" if i == 0 else "0"
        m["node_late_ps"][p], m["node_early_ps"][p] = t, t - 2
        m["node_stages"][p], m["node_xy_um"][p] = 4 + i, [500.0 + 10 * i, 0.0]
        m["node_fall_late_ps"][p], m["node_fall_early_ps"][p] = t, t - 2
    k["taps"]["t_M_0"] = dict(port="t_M_0", part="M", cppr_node="M", tree_path=p, late_ps=L, early_ps=L - 2,
                              fall_late_ps=L, fall_early_ps=L - 2, stages_from_root=7, xy_um=[600.0, 0.0])
    return c


def test_lift_repicks_capture_stage_when_greedy_next_hop_unclean():
    ctx = lambda: ctx_deep([200.0, 350.0, 500.0], 1900.0)  # noqa: E731
    _, e0, _ = cap.clock_start_edges(copy.deepcopy(ROWS), ctx())
    assert [(e["port"], e["retime"]) for e in e0 if not e["clean_ok"]] == [("start:st:h000020->M", False)]
    root, e1, i1 = cap.clock_start_edges(copy.deepcopy(ROWS), ctx(), lift=True)
    assert all(e["clean_ok"] for e in e1) and i1["lifted"] == 1
    m = [e["port"] for e in e1 if e["port"].endswith("st:h00002") or e["dst"] == "M"]
    assert m == ["start:st:h0000->st:h00002", "start:st:h00002->M"]
    assert not any("st:h000020" in e["port"] for e in e1)
    cap.start_tree_check(root, e1)
