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
