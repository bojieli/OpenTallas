import graded_mesh_encode as E
import graded_mesh_graph as GG

ND = dict(width=0.16, space=0.08)


def mesh(xs, ys, w=lambda x, y: 0.8):
    segs, vias = [], []
    for y in ys:
        for a, b in zip(xs, xs[1:]):
            ww = w((a + b) / 2, y)
            segs.append(dict(layer="M8", rect_um=[a, y - ww / 2, b, y + ww / 2], width_um=ww, centre_um=[a, y, b, y]))
    for x in xs:
        for a, b in zip(ys, ys[1:]):
            ww = w(x, (a + b) / 2)
            segs.append(dict(layer="M9", rect_um=[x - ww / 2, a, x + ww / 2, b], width_um=ww, centre_um=[x, a, x, b]))
    vias = E_vias(segs, xs, ys)
    return dict(segments=segs, vias=vias, xs=xs, ys=ys, attachments=[])


def E_vias(segs, xs, ys):
    import graded_mesh_physical as G
    return G.via_arrays(segs, xs, ys)


def test_topology_preserved_rects_unchanged_except_rail_ends():
    g = mesh([4.0, 12.64, 21.28], [4.0, 12.64, 21.28])
    shapes, rails = E.rail_shapes(g, ND)
    m = [s for s in shapes if s[2] == "mesh"]
    assert len(m) == len(g["segments"]) and len(rails) == 6
    for s, seg in zip(m, g["segments"]):
        lay = seg["layer"]
        x0, y0, x1, y1 = seg["rect_um"]
        lo, hi = (y0, y1) if lay == "M8" else (x0, x1)
        assert abs(s[3] - lo) < 1e-6 and abs(s[4] - hi) < 1e-6          # width/axis unchanged
    assert GG.build(g)["summary"]["cycles"] == 4                          # literal mesh topology


def test_via_inside_incident_rects_needs_end_extension():
    g = mesh([4.0, 12.64, 21.28], [4.0, 12.64, 21.28])
    shapes, _ = E.rail_shapes(g, ND)
    assert E.via_findings(g, shapes) == []
    raw = [(s["layer"], "ck_mesh", "mesh", *((s["rect_um"][1], s["rect_um"][3], s["rect_um"][0], s["rect_um"][2]) if s["layer"] == "M8"
            else (s["rect_um"][0], s["rect_um"][2], s["rect_um"][1], s["rect_um"][3]))) for s in g["segments"]]
    assert E.via_findings(g, raw)                                         # unextended rail ends leave pads hanging


def test_shield_gap_uses_wide_spacing_rows():
    assert E.rail_gap(0.08, 100) == 0.08
    assert E.rail_gap(0.8, 100) == 0.5
    assert E.rail_gap(1.76, 100) == 1.0
    assert E.rail_gap(1.76, 1.0) == 0.08                                 # below the PRL row


def test_pg_gap_occupancy_and_spacing():
    pg = [("VDD", "M9", 4.32 - .24, 0, 4.32 + .24, 100), ("VSS", "M9", 12.96 - .24, 0, 12.96 + .24, 100)]
    seg = lambda x, w: dict(layer="M9", width_um=w, centre_um=[x, 0, x, 50])
    shared, close = E.pg_gap_findings({("M9", 8.64): [seg(8.64, 1.76)]}, pg)
    assert not shared and not close
    shared, close = E.pg_gap_findings({("M9", 7.6): [seg(7.6, .08)], ("M9", 9.6): [seg(9.6, .08)]}, pg)
    assert len(shared) == 1
    shared, close = E.pg_gap_findings({("M9", 5.6): [seg(5.6, 1.76)]}, pg)
    assert close                                                          # 1.76 rail closer than 1.0 um to PG


def test_maxwidth_respected_by_materializer_profile():
    import graded_mesh_physical as G
    assert max(G.width_at(x, 0, 0, 0)[0] for x in range(0, 4001, 7)) <= E.M8_MAXWIDTH


def test_gap_snap_centres_rails_in_actual_4p32_gaps_and_keeps_topology():
    assert abs(E.gap_axis(256.544) - (4.32 * 59 + 2.16)) <= 0.04 + 1e-9
    g = mesh([450.68, 459.32, 467.96], [248.36, 257.0, 265.64])
    g2, mv = E.snap_to_pg_gaps(g)
    assert mv["max_um"] <= 2.2
    assert GG.build(g2)["summary"]["cycles"] == GG.build(g)["summary"]["cycles"] == 4
    assert [s["width_um"] for s in g2["segments"]] == [s["width_um"] for s in g["segments"]]
    shapes, _ = E.rail_shapes(g2, ND, drawn=False)
    assert all(s[2] == "mesh" for s in shapes) and E.via_findings(g2, shapes) == []
    pg = [(n, "M9", 4.32 * k - .24, 0, 4.32 * k + .24, 400) for k, n in ((104, "VDD"), (105, "VSS"), (106, "VDD"), (107, "VSS"), (108, "VDD"))]
    assert not [f for f in E.gap_fit_findings(g2, pg) if f["layer"] == "M9"]          # 0.8 rail fits a 3.84 gap
    phy = [(n, "M9", 4.32 * k - .96, 0, 4.32 * k + .96, 400) for k, n in ((104, "VDDPHY"), (105, "VSS"), (106, "VDDPHY"), (107, "VSS"), (108, "VDDPHY"))]
    assert [f for f in E.gap_fit_findings(g2, phy) if f["layer"] == "M9"]               # not in a 2.40 PHY gap


# ---- S81-CORES-R24 (COORD ruling 1): PHY PG band clip + VSS-only PG shields -----------------------------------------
def _pg(layer, k0, k1, a0, a1, w=0.48, phy=False):
    """die-like PG: VSS on multiples of 8.64, VDD (VDDPHY in a PHY domain) on the odd 4.32 centres"""
    out = []
    for k in range(k0, k1 + 1):
        c = 4.32 * k
        net = "VSS" if k % 2 == 0 else ("VDDPHY" if phy else "VDD")
        out.append((net, layer, a0, c - w / 2, a1, c + w / 2) if layer == "M8" else (net, layer, c - w / 2, a0, c + w / 2, a1))
    return out


def _phy_mesh():
    xs = [450.68, 459.32, 467.96, 476.6, 485.24]          # M9 rails (gap centres)
    ys = [248.36, 257.0, 265.64]                           # M8 rails
    g = mesh(xs, ys, w=lambda x, y: 0.8)
    g["attachments"] = [dict(role="local_tree_input", net="ck_mesh", units=["u0"], pin="A", layer="M8", xy_um=[481.0, 257.0]),
                        dict(role="driver", net="ck_mesh", units=["b0"], pin="Y", layer="M9", xy_um=[459.32, 252.0])]
    # core PG left of x=470, a 1.92-um PHY PG band (VDDPHY/VSS) from x=470 on, both on M8; full-height M9 core grid
    pg = _pg("M8", 56, 63, 440.0, 470.0) + _pg("M8", 56, 63, 470.0, 500.0, w=1.92, phy=True) + _pg("M9", 103, 114, 240.0, 275.0)
    return g, pg


def test_phy_clip_stops_rails_outside_band_at_a_crossing():
    g, pg = _phy_mesh()
    phx = E.phy_index(pg)
    shapes0, _ = E.rail_shapes(g, ND, drawn=False)
    assert E.phy_band_findings(shapes0, phx)                                     # literal rails enter the band
    g2, rep, moved = E.phy_clip(g, pg)
    shapes, _ = E.rail_shapes(g2, ND, drawn=False)
    assert E.phy_band_findings(shapes, phx) == []                                # >= 1.0 um everywhere (2-D)
    assert E.via_findings(g2, shapes) == []                                      # piece ends extended over their pad
    vx = {(round(v["x_um"], 6), round(v["y_um"], 6)) for v in g2["vias"]}
    for s in g2["segments"]:
        if s["layer"] == "M8":
            assert (round(max(s["centre_um"][0], s["centre_um"][2]), 6), round(s["centre_um"][1], 6)) in vx   # ends ON a crossing
            assert max(s["centre_um"][0], s["centre_um"][2]) <= 470.0 - 1.0
    assert all(abs(s["width_um"] - 0.8) < 1e-9 for s in g2["segments"])          # kept widths unchanged
    assert rep["segments_clipped"] > 0 and rep["rails_removed"] == rep["floating_pieces_dropped"] == 2   # M9 rails wholly inside the band float
    assert [m["role"] for m in moved] == ["local_tree_input"] and abs(g2["attachments"][0]["xy_um"][0] - 467.96) < 1e-6   # nearest kept rail point
    s = E.mesh_graph(g2)
    assert s["components"] == 1                                                  # M9 rails still tie every piece


def test_phy_clip_noop_without_phy_band():
    g, pg = _phy_mesh()
    core = [r for r in pg if r[0] != "VDDPHY" and not (r[1] == "M8" and r[4] - r[2] < 40 and r[2] >= 470.0)]
    g2, rep, moved = E.phy_clip(g, core)
    assert rep["segments_clipped"] == rep["segments_trimmed"] == rep["vias_dropped"] == 0 and not moved
    assert len(g2["segments"]) == len(g["segments"])


def test_vss_side_axis_and_shield_accounting():
    pg = _pg("M9", 100, 110, 0.0, 100.0)
    nm = E.pg_net_at(pg)
    # gap (8.64*52=449.28 VSS .. 453.6 VDD): a 0.8 rail sits 0.5 um (wide row) from the VSS stripe edge
    a = E.vss_side_axis(451.0, 0.8, nm, "M9")
    assert abs((a - 0.4) - (4.32 * 104 + 0.24) - 0.5) < 0.08 + 1e-9 and (a - 0.4) - (4.32 * 104 + 0.24) >= 0.5 - 1e-9
    seg = lambda x, w: dict(layer="M9", width_um=w, centre_um=[x, 10.0, x, 60.0])  # noqa: E731
    g = dict(segments=[seg(a, 0.8)])
    sides, rep, rows = E.shield_plan(g, pg, ND)
    assert rep["sides"] == {"vss_pg": 1, "vss_drawn": 1}                         # VSS counts, VDD side gets a drawn VSS
    shapes, _ = E.rail_shapes(dict(g, vias=[]), ND, drawn=False, sides=sides)
    sh = [s for s in shapes if s[2] == "rail_shield"]
    assert len(sh) == 1 and sh[0][1] == "VSS" and sh[0][3] > a                   # on the VDD side only
    # a 1.76 rail: VSS side legal, no room for a drawn shield before VDD -> that side is MISSING (never VDD-as-shield)
    a2 = E.vss_side_axis(451.0, 1.76, nm, "M9")
    _, rep2, rows2 = E.shield_plan(dict(segments=[seg(a2, 1.76)]), pg, ND)
    assert rep2["sides"] == {"vss_pg": 1, "missing_vdd_side": 1} and rows2[0]["net"] == "VDD"
    # centred narrow rail with VDD both... impossible on the alternating grid; VDD neighbour never counts as shield
    _, rep3, _ = E.shield_plan(dict(segments=[seg(4.32 * 105 - 0.24 - 0.08 - 0.04 - 0.2, 0.08)]), pg, ND)
    assert "vss_pg" in rep3["sides"] and rep3["sides"].get("vss_drawn", 0) + rep3["sides"].get("missing_vdd_side", 0) == 1
