"""Narrow helper coupon with real reset_tree generation; not an HBM physical signoff."""
import copy,json,sys
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'tools/die_plan'))
import schema,reset_tree as RT
from reset_carriers import register
raw=json.load(open(ROOT/'tools/die_plan/examples/tiny_plan.json'))
raw['reset']['release']='wavefront';raw['ports']=[];raw['lanes']=[]
for t in raw['partition_types'].values():
 t.update(hard=False,buses=[],ft_slots=[],hard_cores=[],internal_stations=[],contents=[{'inst':'u_transit','module':'transit','cells':0}])
P=schema.Plan(raw);W=RT.wf_plan(P);part=next(iter(P.parts));tn=P.parts[part]['type']
def binder():
 return SimpleNamespace(ab={'reset_carrier_parts':[part]},plan=copy.deepcopy(raw),parts=copy.deepcopy(P.parts),types=copy.deepcopy(P.types),members={},wavefront_plan=lambda:P)
b= binder();r=register(b);assert b.members=={part:[]} and r[0]['payload_bits']==0 and r[0]['reset_relays']>0
results={'positive_real_RT':r,'negative_controls':[]}
for name,edit in [
 ('no_wavefront',lambda b:b.plan['reset'].update(release='sync')),
 ('macro',lambda b:b.types[tn].update(hard_cores=[{'inst':'u_core'}])),
 ('payload_bus',lambda b:b.types[tn].update(buses=[{'name':'data'}])),
 ('ft_slot',lambda b:b.types[tn].update(ft_slots=[{'name':'ft'}])),
 ('source_cell',lambda b:b.types[tn]['contents'][0].update(cells=1)),
 ('internal_station',lambda b:b.types[tn].update(internal_stations=[{'name':'data'}])),
 ('duplicate',lambda b:b.ab.update(reset_carrier_parts=[part,part])),
 ('mapped_cell',lambda b:b.members.update({part:[1]}))]:
 b=binder();edit(b);before=copy.deepcopy(b.members)
 try:register(b)
 except ValueError as e:assert b.members==before;results['negative_controls'].append({'case':name,'caught':str(e)})
 else:raise AssertionError('missed '+name)
print(json.dumps(results,indent=1))
