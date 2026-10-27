"""Every branch width and true pin of mixed parallel groups survives V2 encoding."""
from copy import deepcopy
import pytest
import die_clock_mesh as D
import die_clock_128 as C
import clock_routed as R
from test_clock128_r12 import spec,build


def branching():
    s=spec(); s['clock_topology_version']=2
    for v in s['cell_sites'].values():
        v['orient']='MX' if round(v['origin_um'][1]/D.ROW_Y)%2 else 'R0'
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
        assert st['tie']['unit_points']==[[u,*R.pin_point(cells,u,'Y',cells[u].get('lib',D.BUF))] for u in ('ckt_0_0','ckt_0_1')]
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
    p0=R.pin_point(cells,'ckt_0_0','Y',cells['ckt_0_0'].get('lib',D.BUF))
    p1=R.pin_point(cells,'ckt_0_1','Y',cells['ckt_0_1'].get('lib',D.BUF))
    assert p0[0]!=p1[0]
    assert 'M2' in pads[p0] and 'M2' in pads[p1]
    shapes=R.stack_shapes(w)
    assert any(s[1]=='M7' and s[2]<=p1[0]<=s[4] and s[2]<=st['xy'][0]<=s[4] for s in shapes)


def test_v2_wrong_row_orientation_fails_before_encoding():
    s=branching();s['cell_sites']['ckt_0_1']['orient']='R0'
    with pytest.raises(C.PlanError,match='tie_stack'):build(s)


def test_mixed_spacing_keeps_wide_pairs_without_poisoning_later_narrow_pairs():
    import die_clock_128 as C
    ix=C.MetalIndex(.08);ix.pairwise=True
    ix.add(('M8','wide','tree',20.,21.28,0.,100.),space=1.)
    ix.add(('M8','narrow0','tree',10.,10.16,0.,100.),space=.08)
    assert not ix.hits(('M8','narrow1','tree',10.26,10.42,0.,100.))
    assert ix.hits(('M8','narrow1','tree',10.23,10.39,0.,100.))
    # A narrow query still sees the distant-wide conductor's full1um rule.
    assert ix.hits(('M8','narrow1','tree',21.9,22.06,0.,100.))
    assert not ix.hits(('M8','narrow1','tree',22.29,22.45,0.,100.))
    ix.add(('M8','VDD','pg',30.,31.92,0.,100.),space=.04)
    assert ix.hits(('M8','narrow1','tree',32.7,32.86,0.,100.))[0][1]=='wide_spacing'


def test_v2_realizes_declared_trunk_layer_even_for_short_off_axis_leg():
    s=branching()
    s['nets'][0]['layer']='M9'  # valid Manhattan L whose intended trunk is vertical
    cells,nets,ports,m=build(s)
    wire=next(w for w in m['fixed_wires'] if w['name']=='ckm_w_ckt_0_0')
    piece=next(p for p in wire['pieces'] if p['physical_edge']=='e0')
    assert piece['horiz'] is False
    assert piece['physical_edge']=='e0'


def test_wide_pg_spacing_uses_actual_overlap_of_a_nested_segment():
    ix=C.MetalIndex(.08)
    ix.add(('M8','VDD','pg',0.,1.92,0.,10.))
    # The .5um segment is contained in a10um stripe: PRL is .5, not4.5.
    assert not ix.hits(('M8','clock','tree',2.22,2.38,4.,4.5))
    assert ix.hits(('M8','clock','tree',2.22,2.38,4.,6.))[0][1]=='wide_spacing'


def test_failed_edge_reservation_rollback_removes_only_its_shapes():
    ix=C.MetalIndex(.08);ix.pairwise=True
    old=('M8','old','tree',.9,1.06,0.,10.)
    ix.add(old,space=.08);checkpoint=len(ix.shapes)
    ix.add(('M8','failed','tree',1.,2.28,0.,10.),space=1.)
    ix.add(('M9','failed','shield',3.,3.64,0.,10.),space=.5)
    ix.truncate(checkpoint)
    assert ix.shapes==[old] and ix.shape_spaces==[.08]
    assert not ix.hits(('M8','next','tree',1.17,1.33,0.,10.))
    assert ix.hits(('M8','next','tree',1.,1.16,0.,10.))
    assert not ix.hits(('M9','next','tree',3.,3.16,0.,10.))


def test_interval_buckets_preserve_pair_spacing_and_rollback_hits():
    import math,random
    rng=random.Random(29);ix=C.MetalIndex(.08);ix.pairwise=True
    for k in range(180):
        width,space=rng.choice([(.16,.08),(.32,.08),(.64,.5),(1.28,1.)])
        p=rng.uniform(-20,20);a=rng.uniform(-1000,1000)
        ix.add(('M8' if k%2 else 'M9',f'n{k%7}','tree',p,p+width,a,a+rng.uniform(.1,500)),space=space)
    ix.add(('M8','VDD','pg',2.,3.92,-2000.,2000.),space=.04)
    fast=ix.nearby
    def old(lay,plo,phi,alo,ahi):
        seen=set()
        for i in range(math.floor(plo/ix.B),math.floor(phi/ix.B)+1):
            for k in ix.bins[lay].get(i,()):
                if k not in seen:seen.add(k);yield k
    for iteration in range(2):
        for k in range(240):
            p=rng.uniform(-22,22);a=rng.uniform(-1200,1200)
            q=('M8' if k%2 else 'M9',f'q{k%5}','tree',p,p+.32,a,a+rng.uniform(.1,600))
            ix.nearby=fast;got=sorted(ix.hits(q))
            ix.nearby=old;assert sorted(ix.hits(q))==got
        ix.nearby=fast
        if not iteration:ix.truncate(130)


def test_gap_order_is_explicit_and_preserves_actual_cell_and_net_inventory():
    s=branching();s['route_order']='gap_wide_first'
    cells,nets,ports,m=build(s)
    assert len(cells)==len(s['cell_sites'])
    assert m['meta']['explicit_route_order']=='gap_wide_first'
    assert sorted(p['ndr'] for w in m['fixed_wires'] for p in w.get('pieces',[w]) if p.get('physical_edge'))==sorted(e.get('ndr','16w') for e in s['nets'])
    s['route_order']='unknown'
    with pytest.raises(ValueError,match='unknown explicit route order'):build(s)


def test_exact_trunk_drop_search_stays_inside_its_reserved_interval():
    from collections import defaultdict
    import math
    class Router:
        max_move=8.64
        modes=defaultdict(int)
        def place(self,layer,ideal,a0,a1,net,keep=None,dry=False):
            if layer=='M8':c=ideal-2.4 if a1-a0<10. else ideal
            else:c=round(ideal/.108)*.108
            if keep is not None and not keep[0]<=c<=keep[1]:
                c=math.floor(keep[1]/.108)*.108
                if c<keep[0]:return None,None,None
            return round(c,6),C.DRAWN,0.
        def tie_ext(self,*args):return 0.
    lib='BUFx24_ASAP7_75t_R'
    cells={n:dict(x=x,y=y,lib=lib) for n,x,y in [('d0',10.,20.),('d1',10.,20.27),('l0',20.,20.27),('l1',20.,20.54)]}
    m=dict(taps=[],meta=dict(root_um=[0.,0.],clock_pin_window=True))
    wires=C.fixed_wires(m,cells,[dict(name='w',drv='d0',loads=['l0'])],1.62,.27,off=0.,router=Router(),pin_stack=True,ties={'d0':['d0','d1'],'l0':['l0','l1']},l_drops=True,exact_reserve=True)
    assert all(seg[1]<=20.027 for w in wires for seg in w['segs'] if seg[0]=='M9')
