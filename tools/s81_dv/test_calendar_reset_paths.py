"""Calendar consumers must survive reset-tree pruning; no timing bypass."""
import dv_bind as D

def fixture():
    return dict(facts=dict(die_um=[2000.,2000.]),blocks=[dict(name='a',x=100.,y=100.,w=200.,h=200.),dict(name='b',x=1700.,y=1700.,w=200.,h=200.)],
                links=[dict(i='lane',e=[[0,'tx',300.,200.,'box'],[1,'rx',1700.,1800.,'box']])])

def test_calendar_endpoints_retained():
    p=fixture();r=D.reset_tree(p,dict(a='ra',b='rb'),dict(lane=[(800.,800.)]),{},calendar_endpoints=True)
    assert r['summary']['calendar_endpoints']==2
    for e in p['links'][0]['e']:
        assert min(abs(t['xy'][0]-e[2])+abs(t['xy'][1]-e[3]) for t in r['place'])<=D.RESET_REACH_UM
    assert r['summary']['reach_gate']['reach_gate']=='PASS'

def test_default_unchanged_and_unneeded_abutted_lane_ignored():
    p=fixture();r=D.reset_tree(p,dict(a='ra',b='rb'),dict(lane=[]),{})
    assert r['summary']['calendar_endpoints']==0
    r=D.reset_tree(p,dict(a='ra',b='rb'),dict(lane=[]),{},calendar_endpoints=True)
    assert r['summary']['calendar_endpoints']==0

def test_endpoint_buried_in_other_macro_refuses():
    import pytest
    p=fixture();p['links'][0]['e'][1][2:4]=[200.,200.]
    with pytest.raises(ValueError,match='reachability gate FAIL'):
        D.reset_tree(p,dict(a='ra',b='rb'),dict(lane=[(800.,800.)]),{},calendar_endpoints=True)


def test_prune_unselected_anchor_and_dead_parent_keeps_real_consumer():
    lines = ['  wire rs_a;', '  wire rs_b;', '  wire rs_keep;',
             '  R st_rs_a (.ck(ck), .rs(root), .i(root), .o(rs_a));',
             '  R st_rs_b (.ck(ck), .rs(rs_a), .i(rs_a), .o(rs_b));',
             '  R st_rs_keep (.ck(ck), .rs(root), .i(root), .o(rs_keep));',
             '  ICG gate (.CLK(ck), .ENA(rs_keep), .GCLK(fwd));']
    reset = dict(place=[dict(inst='st_'+n,kind='street') for n in ('rs_a','rs_b','rs_keep')],
                 depth=dict(rs_a=2,rs_b=3,rs_keep=2),summary=dict(stations=5))
    kept = D.prune_unused_reset_branches(lines,reset)
    assert not any('rs_a' in x or 'rs_b' in x for x in kept)
    assert any('.ENA(rs_keep)' in x for x in kept)
    assert reset['summary']['calendar_unused_branches_pruned']==2
    assert reset['summary']['stations']==3
    assert set(reset['depth'])=={'rs_keep'}
