from copy import deepcopy
import die_clock_128 as C
import die_clock_mesh as D
import qc_track_allotment as A


def factory():
    r=C.TrackRouter(D.NDR['4w'],'VSS',{'M8':dict(pitch_um=.108,offset_um=0.),'M9':dict(pitch_um=.108,offset_um=0.)},max_move=5.)
    r.ix.pairwise=True
    r.reserve([('M8','VSS','pg',c-.24,c+.24,-100.,1000.) for c in (-2.,2.,5.5)])
    r.reserve([('M9','VSS','pg',49.76,50.24,-100.,1000.)])
    return r


def requests():
    return [dict(id='n',owner='narrow',layer='M8',ideal=0.,interval=[10.,100.],keep=[-.108,5.],ndr=D.NDR['4w']),dict(id='w',owner='wide',layer='M8',ideal=0.,interval=[10.,100.],keep=[-.108,.108],ndr=D.NDR['16w'])]


def test_actual_pg_gap_wide_request_precedes_flexible_short_access():
    q=requests();original=deepcopy(q)
    r=factory()
    r.nd=q[0]['ndr'];r.ix.space=r.nd['space'];assert r.place('M8',0.,10.,100.,'narrow',keep=q[0]['keep'])[0] is not None
    r.nd=q[1]['ndr'];r.ix.space=r.nd['space'];assert r.place('M8',0.,10.,100.,'wide',keep=q[1]['keep'])[0] is None
    got=A.allot(q,factory)
    assert not got['failures'] and got['owner_order']==['wide','narrow']
    assert q==original


def test_unavailable_gap_reports_witness_and_never_calls_it_full_build_pass():
    q=requests();q[1]['keep']=[100.,101.]
    got=A.allot(q,factory)
    assert got['status']=='TRUNK_ONLY_INCOMPLETE'
    assert got['failures'][0]['static_candidates']==0
    assert 'NOT CHECKED' in got['scope']


def test_real_explicit_v2_net_schema_and_branches_remain_intact():
    from test_explicit_clock_v2 import branching
    from test_clock128_r12 import build
    cells,nets,_,_=build(branching())
    before=deepcopy(nets)
    ordered=A.order_nets(nets,cells,D.NDR,'16w')
    assert nets==before
    assert {n['name'] for n in ordered}=={n['name'] for n in nets}
    for n in ordered:
        original=next(v for v in nets if v['name']==n['name'])
        assert n['drv']==original['drv'] and n['loads']==original['loads']
        assert sorted(n.get('plan_connections',[]),key=str)==sorted(original.get('plan_connections',[]),key=str)
