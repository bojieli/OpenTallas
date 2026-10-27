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
