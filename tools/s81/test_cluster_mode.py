"""H-C27 --cluster-mode geometry: every root row reaches its half's S14 entries through streets only (no lane through a
column cluster), every frame on the 2.16-um lattice, every street >= 388.8 um."""
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
CANON = 'results/physical/die_iter_1012/s81/canonical_widehub_1015/rm5_p1973h_ns43.json'


def _model():
    from s81.canonical_layout import load, geometry
    from s81 import cluster_mode as CM
    d = load(CANON, ROOT)
    rec = CM.cluster_layout(d, 2.16)
    G = types.SimpleNamespace(COL_W8=1139.616, PQ_ROOTS=False, PQ_ROOT_ROW=0, CF_WH=(432.0, 95.04), RSC_W=47.52,
                              DIE=(33000, 26000), RSV_RECTS=[], CLUSTER_MODE=dict(rec, reach_um=180.0))
    G.stn_dims = lambda lanes, horiz: (54.84, 17.3)
    G.s14_x = lambda m, side, tag: 9900.0 if side == 'W' else 21988.0
    fr = geometry(G, d, {r: ('W', 0, 0) for r in range(128)})
    return G, dict(canonical_layout=d, frames=fr), rec


def test_lattice_and_streets():
    G, m, rec = _model()
    for f in m['frames'].values():
        assert abs(f['y'] / 2.16 - round(f['y'] / 2.16)) < 1e-6
    assert rec['west_seams'] == [[0, 1], [6, 7]]


def test_street_only_roadmap_reaches_every_root():
    from s81.canonical_layout import Roadmap
    from s81 import cluster_mode as CM
    G, m, _ = _model()
    cor = {}
    CM.patch_corridors(G, m, cor)
    assert not [k for k in cor if k.startswith('rsclane')]
    for rl in (False, True):
        road = Roadmap(G, m, cor, return_lanes=rl)      # raises on any root unreachable through streets
        boxes = m['cluster_boxes']
        for (r, k), (x, y) in road.rootnode.items():
            assert not any(b[0] < x < b[2] and b[1] < y < b[3] for b in boxes.values()), ('root node inside a cluster', r, k)


def test_no_road_segment_crosses_a_cluster():
    from s81.canonical_layout import Roadmap
    from s81 import cluster_mode as CM
    G, m, _ = _model()
    cor = {}
    CM.patch_corridors(G, m, cor)
    boxes = list(m['cluster_boxes'].values())
    for rl in (False, True):
        road = Roadmap(G, m, cor, return_lanes=rl)
        bad = []
        for a, nb in road.graph.items():
            for b in nb:
                assert a[0] == b[0] or a[1] == b[1], ('diagonal road edge', a, b)
                x0, x1 = sorted((a[0], b[0]))
                y0, y1 = sorted((a[1], b[1]))
                for bx in boxes:
                    if x0 < bx[2] - 1e-3 and x1 > bx[0] + 1e-3 and y0 < bx[3] - 1e-3 and y1 > bx[1] + 1e-3:
                        bad.append((a, b))
                    elif x0 == x1 and bx[0] < x0 < bx[2] and y0 < bx[3] and y1 > bx[1]:
                        bad.append((a, b))
                    elif y0 == y1 and bx[1] < y0 < bx[3] and x0 < bx[2] and x1 > bx[0]:
                        bad.append((a, b))
        assert not bad, bad[:5]
