"""HEAD-R24 explicit-mesh sign-off adapter: synthetic mesh -> mc -> proof -> die_sta_related.mesh_signoff contract."""
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "kv_r7"))

pytest.importorskip("scipy")
import explicit_mesh_signoff as E  # noqa: E402
import die_clock_mesh as DCM  # noqa: E402
import die_sta_related as D  # noqa: E402

THEV = {c: dict(R_ohm=r, tr_ps=tr, d_int_ps=di, dvt_ps_per_mV=dv, mult=2)
        for c, r, tr, di, dv in (("TT", 303.0, 20.0, 34.0, -0.226), ("FF", 230.0, 18.0, 27.2, -0.134))}


def _graph():
    """2 x 2 grid of M8 (x) / M9 (y) straps 200 um apart, VIA89 at the 4 crossings; 4 ports on short M8 jogs."""
    xs, ys = (0.0, 200.0), (0.0, 200.0)
    edges, nodes = [], set()
    for y in ys:
        edges.append([["M8", 0.0, y], ["M8", 200.0, y]])
    for x in xs:
        edges.append([["M9", x, 0.0], ["M9", x, 200.0]])
    for x in xs:
        for y in ys:
            edges.append([["M8", x, y], ["M9", x, y]])
    taps = []
    for i, (x, y) in enumerate(((100.0, 0.0), (100.0, 200.0), (0.0, 100.0), (200.0, 100.0))):
        L = "M8" if y in ys else "M9"
        jog = ["M8" if L == "M8" else "M9", x, y]
        port = [L, x + (10.0 if L == "M8" else 0.0), y + (0.0 if L == "M8" else 10.0)]
        edges.append([jog, port])
        taps.append(dict(port=f"msh_t_{i}", part=f"p{i % 2}", endpoint_kind="published_grid_clock",
                         endpoint_port="clk", port_node=port, xy=port[1:], jog_um=10.0))
    for a, b in edges:
        nodes.add(tuple(a))
        nodes.add(tuple(b))
    return dict(nodes=[list(n) for n in sorted(nodes)], edges=edges, taps=taps, strap_crossings=4, vias=4,
                connected_components=1,
                drivers=[dict(group="g1", units=["h1_u0", "h1_u1"], anchor=["M8", 0.0, 0.0]),
                         dict(group="g2", units=["h2_u0", "h2_u1"], anchor=["M8", 200.0, 200.0])])


def _rec(G):
    segs, rcm = E.mesh_rc(G, "8w", "r6")
    arr = lambda t: {c: dict(late=t, early=t, slew=20.0) for c in ("TT", "FF")}
    nodes = [dict(tag="g0", parent=None, depth=1, driver=False, mult=2, xy=[100.0, 100.0], arr=arr(10.0),
                  anchor=None, units=["h0_u0", "h0_u1"], leg_um=450.0)]
    for g, xy, t in (("g1", [0.0, 0.0], 60.0), ("g2", [200.0, 200.0], 64.0)):
        d = next(x for x in G["drivers"] if x["group"] == g)
        nodes.append(dict(tag=g, parent="g0", depth=2, driver=True, mult=2, xy=xy, arr=arr(t), anchor=d["anchor"],
                          units=d["units"], leg_um=450.0))
    taps = [dict(port=t["port"], part=t["part"], kind=t["endpoint_kind"], endpoint_port="clk",
                 node="%s:%.4f:%.4f" % (t["port_node"][0], t["port_node"][1], t["port_node"][2]),
                 xy=t["port_node"][1:], jog_um=10.0, load_ff=2.3) for t in G["taps"]]
    return dict(nodes=nodes, segs=segs, taps=taps, root="g0", root_xy=[100.0, 100.0], rc=rcm)


def _connect(G):
    """make the jog roots real graph nodes on the straps (split each strap edge at every node lying on it)."""
    pts = {tuple(a) for e in G["edges"] for a in e}
    out = []
    for a, b in G["edges"]:
        if a[0] != b[0]:
            out.append([a, b])
            continue
        on = sorted({p for p in pts if p[0] == a[0] and min(a[1], b[1]) <= p[1] <= max(a[1], b[1])
                     and min(a[2], b[2]) <= p[2] <= max(a[2], b[2]) and (a[1] == b[1] == p[1] or a[2] == b[2] == p[2])},
                    key=lambda p: (p[1], p[2]))
        for p, q in zip(on, on[1:]):
            out.append([list(p), list(q)])
    G["edges"] = out
    return G


@pytest.fixture()
def setup(tmp_path):
    G = _connect(_graph())
    rec = _rec(G)
    (tmp_path / "rec.json").write_text(json.dumps(rec))
    (tmp_path / "thev.json").write_text(json.dumps(THEV))
    b = tmp_path / "build"
    b.mkdir()
    (b / "mesh.json").write_text(json.dumps(dict(meta=dict(ndr="8w"), explicit_mesh=G)))
    return tmp_path, G, rec


def test_mesh_via_findings_explicit(setup):
    _, G, _ = setup
    assert DCM.mesh_via_findings(dict(meta={}, explicit_mesh=G, xs=[], ys=[]), None) == []
    bad = json.loads(json.dumps(G))
    bad["edges"] = [e for e in bad["edges"] if e[0][0] == e[1][0]]          # drop every VIA89
    f = DCM.mesh_via_findings(dict(meta={}, explicit_mesh=bad, xs=[], ys=[]), None)
    assert f and any("not connected" in x or "VIA89" in x for x in f)


def test_mc_parallel_identical_and_proof_contract(setup):
    d, G, rec = setup
    for C in ("TT", "FF"):
        for j in (1, 2):
            assert E.main(["mc", str(d / "rec.json"), "--thev", str(d / "thev.json"), "--corner", C, "--samples", "2",
                           "--jobs", str(j), "--out", str(d / f"mc_{C}_{j}.json")]) == 0
        assert (d / f"mc_{C}_1.json").read_bytes() == (d / f"mc_{C}_2.json").read_bytes()
        m = json.loads((d / f"mc_{C}_1.json").read_text())
        assert m["corner"] == C and len(m["arr"]) == 3 and sorted(m["loads"]) == m["loads"]
        assert len(m["loads"]) == 4 and m["arr"][0] == m["routed"]
        assert m["arr"][1] != m["arr"][0]                                      # variation applied
    assert E.main(["proof", str(d / "build"), "--rec", str(d / "rec.json"), "--thev", str(d / "thev.json"),
                   "--mc", f"TT={d}/mc_TT_1.json,FF={d}/mc_FF_1.json", "--out", str(d / "proof")]) == 0
    P = d / "proof"
    ta = json.loads((P / "tap_arrivals_TT.json").read_text())
    taps = {t["port"]: t for t in ta["taps"]}
    assert len(taps) == 4 and all(t["cppr_node"] == "h" for t in taps.values())
    meta = {k: v for k, v in ta.items() if k != "taps"}
    U, recd = D.mesh_signoff(P, taps, meta, "TT", d / "mc_TT_1.json")
    assert recd["taps_on_mesh"] == 4
    assert all(t["cppr_node"] == "m" for t in taps.values())
    assert meta["node_stages"]["m"] == 2                                     # port is its own load: no -1
    u = U("msh_t_0", "msh_t_1")
    m = json.loads((d / "mc_TT_1.json").read_text())
    i, j = m["loads"].index("msh_t_0"), m["loads"].index("msh_t_1")
    assert u >= abs(m["arr"][0][i] - m["arr"][0][j]) - 1e-9 and u > 0
    assert U("msh_t_0", "msh_t_0") == 0.0


def test_solve_slew_optional_default_unchanged(setup):
    _, _, rec = setup
    sig = json.loads(E.DEF_SIGMA)
    a, sl0, _ = E.solve(rec, "TT", THEV["TT"], sig, 0)
    b, sl1, _ = E.solve(rec, "TT", THEV["TT"], sig, 0, slew=True)
    assert sl0 is None and a == b and set(sl1) == set(a) and all(v > 0 for v in sl1.values())
