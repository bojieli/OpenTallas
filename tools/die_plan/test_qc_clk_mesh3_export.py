"""Export rejects silently incomplete trees and disconnected segmented meshes."""
from types import SimpleNamespace
import pytest
import qc_clk_mesh3_export as E


def graph():
    tt=SimpleNamespace(w='16w'); cc=SimpleNamespace(w='4w')
    cells=[dict(site=[i*10.0,0.135],masters=['BUFx24'],kind='top_node') for i in range(4)]
    return dict(cells=cells,site_of={('t','r'):0,('t','t'):1,('c','cr'):1,('c','f'):2,('b','br'):0,('b','bf'):3},
                top_nodes=[dict(tag='r',parent=None),dict(tag='t',parent='r',nseg=1,et=tt)],
                cnodes=[dict(tag='cr',parent=None),dict(tag='f',parent='cr',nseg=1,et=cc)],
                bnodes=[dict(tag='br',parent=None),dict(tag='bf',parent='br',nseg=1,et=cc)],
                btrees=[dict(root='br',anchor_tag='r')],et=dict(top=tt,col=cc))


def test_all_three_tree_namespaces_survive():
    e,u,c,r=E.tree_groups(graph())
    assert c=={'t':1,'c':1,'b':1}
    assert {x['edge'] for x in e}=={'t:t:0','c:f:0','b:bf:0'}
    assert len(u)==4 and r=='g0'
    assert {x['ndr'] for x in e}=={'4w','16w'}


def test_band_root_must_share_anchor_cell():
    b=graph(); b['site_of'][('b','br')]=1
    with pytest.raises(E.ExportError,match='not merged'): E.tree_groups(b)


def test_unlegalized_band_tree_never_exported_as_complete():
    b=graph(); b['bnodes']=[]
    with pytest.raises(E.ExportError,match='physical legalization'): E.tree_groups(b)


def test_every_planned_repeater_must_have_physical_site():
    b=graph(); b['bnodes'][1]['nseg']=2
    with pytest.raises(E.ExportError,match='missing legalized b'): E.tree_groups(b)


def mesh():
    return dict(H8=[(0.,0.,20.),(10.,0.,20.),(20.,0.,20.)],
                V9=[(0.,0.,10.),(0.,10.,20.),(20.,0.,20.)],
                drivers=[dict(x=0.,y=10.,kind='band',mult=2.)])


def test_segment_endpoint_crossing_has_one_via():
    m=E.mesh_geometry(mesh(),{0:'g7'})
    assert m['geometric_crossings']==m['emitted_vias']==6
    joint=[v for v in m['vias'] if v['x']==0 and v['y']==10]
    assert len(joint)==1 and joint[0]['M9']==[0,1]
    assert m['drivers'][0]['group']=='g7'


def test_disconnected_segment_has_no_fake_mesh_continuity():
    b=mesh(); b['V9'].append((50.,100.,120.))
    with pytest.raises(E.ExportError,match='disconnected conductor'): E.mesh_geometry(b)


def test_driver_off_strap_is_not_rounded_onto_mesh():
    b=mesh(); b['drivers'][0]['x']=3.; b['drivers'][0]['y']=7.
    with pytest.raises(E.ExportError,match='no physical strap'): E.mesh_geometry(b)


def test_complete_mesh_export_keeps_original_fine_driver_outputs():
    b=graph()
    b['P']=SimpleNamespace(W=100.,H=100.,parts={'p':{'type':'T','orient':'R0'}},die={},rect=lambda n:(0.,0.,100.,100.))
    b['cores']=[]
    b['a0']=dict(mesh(),drops=[])
    b['rec']={'taps':[]}
    b['bleaf']={0:(b['btrees'][0],'bf')}
    b['ctrees']=[dict(nodes=[dict(tag='cr',kids=['f']),dict(tag='f',kids=[],xy=(20.,0.))])]
    _,m=E.export(b)
    assert len(m['drivers'])==2
    assert {d['kind'] for d in m['drivers']}=={'fine','band'}
    assert {d['group'] for d in m['drivers']}=={'g2','g3'}


def test_touching_seam_uses_exact_odb_units_not_float_equality():
    # The real export5 case: binary float may put the sum a fraction of one
    # DBU past the partition edge. It is exactly abutting in the actual ODB.
    assert E.body_inside((1563.84,0.,2799.36,1000.),2798.172,737.1,1.188,.27)
    assert not E.body_inside((1563.84,0.,2799.36,1000.),2798.173,737.1,1.188,.27)
    assert not E.body_inside((0.,0.,10.,10.),-.001,0.,1.62,.27)


def test_macro_touch_is_legal_but_one_dbu_overlap_is_not():
    assert not E.body_overlap((10.,0.,20.,10.),8.38,1.,1.62,.27)
    assert E.body_overlap((10.,0.,20.,10.),8.381,1.,1.62,.27)
