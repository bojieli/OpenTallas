import copy
import hbm_final_stations as F


def test_moved_final_pin_gets_legal_stations_and_added_cycles():
    t=dict(outline_um=[1200,200],hard_cores=[],internal_stations=[dict(from_um=[10,50],to_um=[1100,50],regs_um=[[200,50]],bits=8)])
    original=copy.deepcopy(t);new,r=F.regenerate(t)
    assert t==original and r['verdict']=='PASS'
    assert r['added_cycles']>=1 and r['max_hop_um']<=405.000001
    assert all(h<=405.000001 for h in F.hops(new['internal_stations'][0]))


def test_unroutable_failure_is_explicit_and_keeps_original(monkeypatch):
    t=dict(outline_um=[100,100],hard_cores=[],internal_stations=[dict(from_um=[5,5],to_um=[90,90],regs_um=[],bits=1)])
    monkeypatch.setattr(F.HR,'route_station',lambda *a,**k:None)
    new,r=F.regenerate(t)
    assert r['verdict']=='FAIL' and r['failed']==[0] and new==t


def test_router_shortfall_is_padded_to_old_count(monkeypatch):
    t=dict(outline_um=[400,200],hard_cores=[],internal_stations=[dict(from_um=[10,50],to_um=[80,50],regs_um=[[30,50],[50,50],[70,50]],bits=4)])
    monkeypatch.setattr(F.HR,'route_station',lambda *a,**k:dict(regs=[],kind='HV',n_min=0))
    new,r=F.regenerate(t)
    s=new['internal_stations'][0]
    assert r['verdict']=='PASS' and len(s['regs_um'])==3 and r['rows'][0]['preserved_cycles']==3 and r['added_cycles']==0
    assert len({tuple(p) for p in s['regs_um']})==3 and all(h<=405.000001 for h in F.hops(s))


def test_no_free_site_fails_closed(monkeypatch):
    t=dict(outline_um=[400,200],hard_cores=[],internal_stations=[dict(from_um=[10,50],to_um=[80,50],regs_um=[[30,50]],bits=4)])
    monkeypatch.setattr(F.HR,'route_station',lambda *a,**k:dict(regs=[],kind='HV',n_min=0))
    monkeypatch.setattr(F,'preserve_count',lambda *a,**k:None)
    new,r=F.regenerate(t)
    assert r['verdict']=='FAIL' and r['failed']==[0] and new['internal_stations'][0]['regs_um']==[[30,50]]
