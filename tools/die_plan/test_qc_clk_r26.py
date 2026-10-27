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
    from types import SimpleNamespace
    B['P']=SimpleNamespace(W=2000.,H=2000.,parts={'p':{}},rect=lambda n:(0.,-400.,2000.,2000.))
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


def test_upstream_feed_elbow_has_no_diagonal_repeater_interpolation():
    B=tiny(False);et=B['et']['col'];nodes=[]
    r=dict(tag='leaf',xy=(0.,0.),kids=[],S=0,T={'TT':0.,'FF':0.})
    nodes.append(r)
    out=M.orthogonal_lift(r,(900.,900.),et,'feed',nodes,4)
    assert out is not None and out['S']==4
    by={n['tag']:n for n in nodes}
    for n in nodes:
        if not n.get('parent'):continue
        p=by[n['parent']]['xy'];q=n['xy']
        assert p[0]==q[0] or p[1]==q[1]
        assert n['leg']/n['nseg']<=450.


def test_upstream_feed_rejects_both_blocked_elbows():
    B=tiny(False);et=B['et']['col'];nodes=[]
    r=dict(tag='leaf',xy=(0.,0.),kids=[],S=0,T={'TT':0.,'FF':0.})
    nodes.append(r)
    assert M.orthogonal_lift(r,(900.,900.),et,'feed',nodes,4,
                            lambda q:q in ((0.,900.),(900.,0.))) is None


def test_valid_slot_search_crosses_masked_band_without_enlarging_islands():
    import numpy as np
    gx=np.arange(4,dtype=float)*8.64
    gy=np.arange(80,dtype=float)*8.64
    ok=np.ones((4,80),dtype=bool)
    ok[:,20:60]=False
    target=(10.,40*8.64)
    # The former nearest24 y rows lie entirely inside the mask.
    nearest=np.argsort(abs(gy+M.ROW_H/2-target[1]))[:24]
    assert not ok[:,nearest].any()
    d,k,j=next(M.valid_slot_candidates(gx,gy,ok,*target,1.62))
    assert ok[k,j] and j==60
    assert d==pytest.approx(abs(gx[k]+.81-target[0])+abs(gy[j]+M.ROW_H/2-target[1]))


def test_full_clock_group_body_stays_in_one_host_at_seam_and_die_edge():
    from types import SimpleNamespace
    rects={'a':(0.,0.,10.,20.),'b':(10.,0.,20.,20.)}
    B=dict(P=SimpleNamespace(W=20.,H=20.,parts={n:{} for n in rects},rect=rects.__getitem__),cores=[])
    cells=[dict(kind='fine_driver',site=[10.,5.535],masters=['BUFx24']),
           dict(kind='col_node',site=[20.,10.665],masters=['BUFx24','BUFx24'])]
    stats=M.legalize_partition_bodies(B,cells)
    assert stats['moved']==2 and stats['max_move_um']<2.
    for c in cells:
        x,y=c['site'];r=rects[c['body_host']]
        assert r[0]<=x-.81 and x+.81<=r[2]
        assert r[1]<=y-M.ROW_H/2 and y+(len(c['masters'])-.5)*M.ROW_H<=r[3]


def test_legalized_driver_jog_is_charged_as_mesh_metal():
    N=M.mesh_seg([(0.,0.,20.)],[(10.,0.,20.)],[(10.81,5.)],[(10.,10.)],
                 M.RC3['8w'],(M.RC3['8w'],0.),jog_um=1.)
    assert (10.81,5.) in N['xy']
    assert any(N['dn'][0] in (a,b) and r>0 for a,b,r in N['R'])


def test_west_column_feed_crosses_macro_only_in_free_row_band():
    B=tiny(False);et=B['et']['col'];nodes=[]
    r=dict(tag='west',xy=(0.,400.),kids=[],S=0,T={'TT':0.,'FF':0.});nodes.append(r)
    blocked=lambda q:100.<q[0]<800. and 0.<q[1]<800.
    out=M.orthogonal_lift(r,(900.,400.),et,'feed',nodes,8,blocked,feed_bands=[900.])
    assert out is not None and out['S']==8
    by={n['tag']:n for n in nodes}
    for n in nodes:
        if not n.get('parent'):continue
        a=by[n['parent']]['xy'];b=n['xy']
        if a[0]!=b[0]: assert a[1]==b[1]==900.
        for k in range(1,n['nseg']+1):
            q=tuple(a[j]+(b[j]-a[j])*k/n['nseg'] for j in (0,1))
            assert not blocked(q)
