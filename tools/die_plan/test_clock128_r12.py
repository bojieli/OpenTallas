"""INFRA-FIRST-QC-R12: 16w NDR, explicit-cells build, stacked-buffer A/Y tie straps (no OpenROAD)."""
import pytest
import die_clock_mesh as D
import die_clock_128 as C
import clock_routed as R

ROW = D.ROW_Y


def test_16w_ndr_values_and_4w_8w_unchanged():
    assert D.NDR["4w"] == dict(width=0.16, space=0.08, rf=0.25, cf=1.3)
    assert D.NDR["8w"] == dict(width=0.32, space=0.08, rf=0.125, cf=1.6)
    n = D.NDR["16w"]
    assert n["width"] == pytest.approx(16 * 0.04) and n["rf"] == pytest.approx(0.04 / n["width"])
    assert n["space"] == 0.5                       # LEF SPACINGTABLE WIDTH 0.49975 row (PRL >= 1.8)
    assert n["wide_merge_um"] == 0.99975
    hw, off, ext = C.shield_geom(n)
    assert (hw, off, ext) == pytest.approx((0.32, 1.14, 1.46))
    assert C.flank_gap(n) == pytest.approx(1.14)
    v = n["via89"]                                 # array fits the 0.64 wire incl. the M9 enclosure
    assert (v["cols"] - 1) * v["pitch"] + v["cut"] + 2 * v["enc_m9"] <= n["width"] + 1e-9 and v["pitch"] >= 0.097


def test_via_array_tcl_on_grid():
    L = R.via_array_tcl(D.NDR["16w"]["via89"])
    cuts = [l for l in L if "[LY V8]" in l]
    assert len(cuts) == 36
    assert "[LY M8] -265 -265 265 265" in "\n".join(L)            # 5 x 0.098 / 2 + 0.02, M8 enclosure 0
    assert "[LY M9] -265 -285 265 285" in "\n".join(L)            # + 0.02 M9 enclosure along M9 (vertical)
    with pytest.raises(ValueError):
        R.via_array_tcl(dict(rows=6, cols=6, cut=0.04, pitch=0.097))           # 0.2425 um half-span: off grid


def spec():
    # g0 (2 units, root) --M8--> g1 (2 units) --M8 L--> g2 (1 unit, leaf col tap 4.05 um lower)
    S = {}
    for g, x, y, k, n in ((0, 10.8, 10.8, "top_node", 2), (1, 60.48, 10.8, "top_rep", 2), (2, 120.42, 6.75, "col_tap", 1)):
        for u in range(n):
            S[f"ckt_{g}_{u}"] = dict(origin_um=[x, round(y + u * ROW, 4)], part="p", master="BUFx24_ASAP7_75t_R",
                                     w=1.62, orient="R0", group=g, kind=k)
    nets = [dict(drv="g0", load="g1", layer="M8", ndr="16w", edge="e0"),
            dict(drv="g1", load="g2", layer="M8", ndr="16w", edge="e1")]
    return dict(cell_sites=S, nets=nets)


def build(sp=None, **kw):
    return D.build_explicit(sp or spec(), die=(200.0, 40.0), parts={"p": (0, 0, 200, 40)}, keepouts=[], **kw)


def test_explicit_build_ties_and_l_net():
    cells, nets, ports, M = build()
    byn = {n["name"]: n for n in nets}
    # logical nets: every unit drives / loads; one net per driver group; leaf port
    g0 = byn["ckm_w_ckt_0_0"]
    assert g0["drv_units"] == ["ckt_0_0", "ckt_0_1"] and g0["loads"] == ["ckt_1_0", "ckt_1_1"]
    assert byn["root"]["loads"] == ["ckt_0_0", "ckt_0_1"]
    assert ("output", "t_g2") in ports and M["taps"][0]["port"] == "t_g2"
    W = {w["name"]: w for w in M["fixed_wires"]}
    w0 = W["ckm_w_ckt_0_0"]
    st = {(s["cell"], s["pin"]): s for s in w0["stacks"]}
    y_tie, a_tie = st[("ckt_0_0", "Y")]["tie"], st[("ckt_1_0", "A")]["tie"]
    assert [u for u, _ in y_tie["units"]] == ["ckt_0_0", "ckt_0_1"] and y_tie["strap_um"] == pytest.approx(ROW)
    assert [u for u, _ in a_tie["units"]] == ["ckt_1_0", "ckt_1_1"] and a_tie["layer"] == "M7"
    assert len(w0["stacks"]) == 2                  # one stack per GROUP pin, the tie reaches the other unit
    assert all(w["ndr"] == "16w" and w["enc"] == "r8" for w in W.values())
    # L net g1 -> g2: M8 trunk + M9 drop + stack at the load row
    w1 = W["ckm_w_ckt_1_0"]
    ld = next(s for s in w1["stacks"] if s["pin"] == "A")
    assert ld.get("drop") and ld["drop"]["layer"] == "M9" and ld["riser_um"] <= C.STACK_RISER_MAX_UM
    assert {g[0] for g in w1["segs"]} == {"M8", "M9"}
    assert M["meta"]["tree_tracks"]["pin_stack"]["ties"] == 4   # root: A g0; w0: Y g0 + A g1; w1: Y g1
    # encoder: both units' ITerms on each tied pin, tie junction + strap, VIA89 array instead of the tech via
    ports_ = {t["port"]: dict(layer="M8", xy=t["xy"]) for t in M["taps"]}
    ports_["root"] = dict(layer="M9", xy=M["meta"]["root_um"])
    L, rec = R.routed_tcl(M["fixed_wires"], cells, ports_, D.BUF, "ot_mesh_ndr", via89=D.NDR["16w"]["via89"])
    txt = "\n".join(L)
    for u in ("ckt_0_0", "ckt_0_1"):
        assert f"addITerm [IT {u} Y]" in txt and f"addITerm [IT {u} A]" in txt
    for u in ("ckt_1_0", "ckt_1_1"):
        assert f"addITerm [IT {u} A]" in txt and f"addITerm [IT {u} Y]" in txt
    assert "addITerm [IT ckt_2_0 A]" in txt and "set jtie" in txt and "$e newPath $jtie" in txt
    assert "addTechVia [V VIA89]" not in txt and "addVia $ot_v89" in txt and rec["ties"] == 4
    # census shapes: tie strap present, no cross-net M2..M7 short
    sh = R.stair_shapes(M["fixed_wires"], cells, ports_, D.BUF)
    assert any(s[1] == "M7" and s[5] - s[3] >= ROW for s in sh)
    cen = R.stair_census(sh)
    assert not cen["shorts"] and not cen["spacing"]
    # verilog: parallel units share the driver net
    import tempfile, pathlib
    with tempfile.TemporaryDirectory() as t:
        D.write_verilog(cells, nets, ports, pathlib.Path(t) / "v.v")
        v = (pathlib.Path(t) / "v.v").read_text()
    assert "ckt_0_0 (.A(root), .Y(ckm_w_ckt_0_0))" in v and "ckt_0_1 (.A(root), .Y(ckm_w_ckt_0_0))" in v
    assert "ckt_2_0 (.A(ckm_w_ckt_1_0), .Y(t_g2))" in v


def test_explicit_build_no_midpoint_check_but_geometry_checks():
    sp = spec()                                    # unbalanced positions: still builds (planner-balanced input)
    for u in ("ckt_1_0", "ckt_1_1"):
        sp["cell_sites"][u]["origin_um"][0] = 37.8
    build(sp)
    bad = spec()                                   # overlap
    bad["cell_sites"]["ckt_1_0"]["origin_um"] = [10.8, 10.8]
    bad["cell_sites"]["ckt_1_1"]["origin_um"] = [10.8, 11.07]
    with pytest.raises(C.PlanError, match="cell_overlap"):
        build(bad)
    bad = spec()                                   # broken stack column
    bad["cell_sites"]["ckt_0_1"]["origin_um"][0] = 11.016
    with pytest.raises(C.PlanError, match="tie_stack"):
        build(bad)
    bad = spec()                                   # keep-out
    with pytest.raises(C.PlanError) as e:
        D.build_explicit(bad, die=(200.0, 40.0), parts={"p": (0, 0, 200, 40)}, keepouts=[(59, 9, 63, 12, "core")])
    assert any("on_hard_keepout" in r["detail"] for r in e.value.rows)
    bad = spec()                                   # body across a seam
    with pytest.raises(C.PlanError, match="cell_site_seam|cell_site_host"):
        D.build_explicit(bad, die=(200.0, 40.0), parts={"p": (0, 0, 61, 40), "q": (61, 0, 200, 40)}, keepouts=[])
    bad = spec()                                   # declared layer disagrees with the dominant axis
    bad["nets"][0]["layer"] = "M9"
    with pytest.raises(C.PlanError, match="net_trunk_layer"):
        build(bad)
    bad = spec()
    bad["nets"][0]["ndr"] = "4w"
    with pytest.raises(C.PlanError, match="net_ndr"):
        build(bad)
