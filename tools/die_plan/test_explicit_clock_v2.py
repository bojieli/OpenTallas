"""Every branch width and true pin of mixed parallel groups survives V2 encoding."""
from copy import deepcopy
import pytest
import die_clock_mesh as D
import die_clock_128 as C
import clock_routed as R
from test_clock128_r12 import spec,build


def branching():
    s=spec(); s['clock_topology_version']=2
    s['nets'][0]['ndr']='4w'
    s['cell_sites']['ckt_0_1']['master']='BUFx16f_ASAP7_75t_R'
    s['cell_sites']['ckt_0_1']['w']=1.188
    s['cell_sites']['ckt_3_0']=dict(origin_um=[10.8,30.24],part='p',master='BUFx24_ASAP7_75t_R',w=1.62,orient='R0',group=3,kind='col_tap')
    s['nets'].append(dict(drv='g0',load='g3',layer='M9',ndr='8w',edge='e2'))
    return s


def test_v2_keeps_widths_true_mixed_masters_and_one_logical_net():
    src=branching(); cells,nets,ports,m=build(src)
    w=next(w for w in m['fixed_wires'] if w['name']=='ckm_w_ckt_0_0')
    assert [p['ndr'] for p in w['pieces']]==['4w','8w']
    assert {p['physical_edge'] for p in w['pieces']}=={'e0','e2'}
    assert cells['ckt_0_1']['lib']=='BUFx16f_ASAP7_75t_R'
    assert cells['ckt_0_1']['x']==src['cell_sites']['ckt_0_1']['origin_um'][0]
    ys=[]
    for p in w['pieces']:
        st=next(s for s in p['stacks'] if s['pin']=='Y')
        ys.append(st['xy'])
        assert st['entry']=='ckt_0_0'
        assert st['tie']['unit_points']==[[u,*C.pin_xy(cells,u,'Y',D.ROW_Y)] for u in ('ckt_0_0','ckt_0_1')]
    assert ys[0]==ys[1] # same physical source junction, regardless of piece trunk track
    pp={t['port']:dict(layer=t['layer'],xy=t['xy']) for t in m['taps']}
    pp['root']=dict(layer='M9',xy=m['meta']['root_um'])
    lines,rec=R.routed_tcl(m['fixed_wires'],cells,pp,D.BUF,'ot_mesh_ndr',via89=D.NDR['16w']['via89'])
    txt='\n'.join(lines)
    assert txt.count('set w [rnet ckm_w_ckt_0_0]')==1
    assert txt.count('addITerm [IT ckt_0_0 Y]')==1
    assert txt.count('addITerm [IT ckt_0_1 Y]')==1
    assert txt.count('addITerm [IT ckt_1_0 A]')==1 and txt.count('addITerm [IT ckt_3_0 A]')==1
    assert 'set ot_ndr [$blk findNonDefaultRule ot_mesh_ndr__4w]' in txt
    assert 'set ot_ndr [$blk findNonDefaultRule ot_mesh_ndr__8w]' in txt
    assert rec['nets']==len(nets)


def test_legacy_rejects_mixed_ndr_until_explicitly_opted_in():
    s=branching(); del s['clock_topology_version']
    with pytest.raises(C.PlanError): build(s)


def test_unknown_width_is_never_substituted():
    s=branching();s['nets'][0]['ndr']='unmodelled'
    with pytest.raises(C.PlanError,match='net_ndr'):build(s)


def test_mixed_tie_has_actual_lateral_m7_shape_and_true_pin_pads():
    cells,nets,ports,m=build(branching())
    w=next(w for w in m['fixed_wires'] if w['name']=='ckm_w_ckt_0_0')['pieces'][0]
    st=next(s for s in w['stacks'] if s['pin']=='Y')
    pads=R.stack_pad_layers(st)
    p0=C.pin_xy(cells,'ckt_0_0','Y',D.ROW_Y)
    p1=C.pin_xy(cells,'ckt_0_1','Y',D.ROW_Y)
    assert p0[0]!=p1[0]
    assert 'M2' in pads[p0] and 'M2' in pads[p1]
    shapes=R.stack_shapes(w)
    assert any(s[1]=='M7' and s[2]<=p1[0]<=s[4] and s[2]<=st['xy'][0]<=s[4] for s in shapes)
