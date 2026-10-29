import copy
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from tools.die_plan import schema, reset_tree as RT, reset_carriers


def binder():
    raw=json.loads((Path(schema.__file__).parent/'examples/tiny_plan.json').read_text())
    raw['reset']['release']='wavefront';raw['ports']=[];raw['lanes']=[]
    for t in raw['partition_types'].values():
        t.update(hard=False,buses=[],ft_slots=[],hard_cores=[],internal_stations=[],contents=[{'inst':'u_transit','module':'transit','cells':0}])
    P=schema.Plan(raw);part=next(iter(P.parts))
    b=SimpleNamespace(ab={'reset_carrier_parts':[part]},plan=raw,parts=copy.deepcopy(P.parts),types=copy.deepcopy(P.types),members={},wavefront_plan=lambda:P)
    return b,part,P.parts[part]['type']


def test_real_registered_reset_carrier_and_default_off():
    b,p,tn=binder()
    r=reset_carriers.register(b)
    assert b.members=={p:[]} and r[0]['payload_bits']==0 and r[0]['reset_relays']>0
    assert r[0]['rtl'].startswith('existing reset_tree')
    assert reset_carriers.register(SimpleNamespace(ab={}))==[]


@pytest.mark.parametrize('change', ['no_wave','macro','bus','ft','cell','station','duplicate','mapped','empty_contents','pad','invalid_list','plan_cell','intra_dly','link'])
def test_not_a_general_empty_partition_escape(change):
    b,p,tn=binder();t=b.types[tn]
    if change=='no_wave':b.plan['reset']['release']='sync'
    if change=='macro':t['hard_cores']=[{'inst':'u_core'}]
    if change=='bus':t['buses']=[{'name':'data'}]
    if change=='ft':t['ft_slots']=[{'name':'ft'}]
    if change=='cell':t['contents'][0]['cells']=1
    if change=='station':t['internal_stations']=[{'conn':'data'}]
    if change=='duplicate':b.ab['reset_carrier_parts']=[p,p]
    if change=='mapped':b.members[p]=[1]
    if change=='empty_contents':t['contents']=[]
    if change=='pad':t['pads']=[{'name':'data'}]
    if change=='invalid_list':b.ab['reset_carrier_parts']=False
    if change=='plan_cell':b.pc=SimpleNamespace(T={tn:{'cells':{'u_x':{}}}},ptype=lambda p:tn)
    if change=='intra_dly':b.intra_dly={p:{(0,'q',1)}}
    if change=='link':b.links=[{'src':p,'dst':'elsewhere','ft':[]}]
    before=copy.deepcopy(b.members)
    with pytest.raises(ValueError):reset_carriers.register(b)
    assert b.members==before
