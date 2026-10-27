"""R26: distinct band paths, actual upstream cells, segmented-mesh connectivity."""
import pytest
import qc_clk_mesh3 as M
from test_qc_clk_mesh3 import tiny


def band(B, tag, x):
    et = B['et']['col']
    root = dict(tag=tag, xy=(100., 0.), kids=[tag+'leaf'], parent=None, et=et)
    leaf = dict(tag=tag+'leaf', xy=(x, 0.), kids=[], parent=tag, leg=x-100., nseg=1, et=et)
    return dict(nodes=[leaf, root], root=tag, anchor_tag='t0', ct=B['ctrees'][0], leaves=[0], et=('4w', 1))


def test_band_rows_of_one_column_keep_separate_paths():
    B = tiny(False)
    a, b = band(B, 'a', 200.), band(B, 'b', 300.)
    p = M.band_paths([a, b])
    assert len(p) == 2
    assert p[id(a)][0]['aleaf'][0]['parent'] == 'a'
    assert p[id(b)][0]['bleaf'][0]['parent'] == 'b'


def test_band_root_reuses_upstream_cell_and_phys_edges():
    B = tiny(False)
    bt = band(B, 'b', 300.)
    B['btrees'], B['bnodes'] = [bt], bt['nodes']
    B['a0'] = dict(drivers=[dict(x=300., y=0., mult=2.)])
    cells, _ = M.legalize(B)
    B['cells'] = cells
    assert B['site_of'][('b', 'b')] == B['site_of'][('t', 't0')]
    leaf = cells[B['site_of'][('b', 'bleaf')]]
    assert leaf['masters'] == ['BUFx24'] * 2
    (src, dst, length), = M.phys_edges(B)[('b', 'bleaf')]
    assert src is cells[B['site_of'][('t', 't0')]]
    assert dst is leaf
    assert length == M.net_um(src, dst)


def test_segmented_mesh_has_one_shared_node_per_crossing():
    N = M.mesh_seg([(0., 0., 20.), (10., 0., 20.), (20., 0., 20.)],
                   [(10., 0., 10.), (10., 10., 20.)], [(10., 0.)], [(10., 20.)],
                   M.RC3['8w'], (M.RC3['8w'], 0.))
    assert N['crossings'] == N['vias'] == 3
    assert N['xy'].count((10., 10.)) == 1
    assert N['dn'][0] != N['tn'][0]


def test_segmented_mesh_rejects_unconnected_tap():
    with pytest.raises(SystemExit, match='not on a strap'):
        M.mesh_seg([(0., 0., 20.)], [(10., 0., 10.)], [(10., 0.)], [(25., 25.)],
                   M.RC3['8w'], (M.RC3['8w'], 0.))
