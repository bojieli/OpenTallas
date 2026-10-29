#!/usr/bin/env python3
"""Small actual-master mechanism vehicle for the additive PG importer.
Never modifies the source ODB or qualifies a release die.
"""
import argparse,json,sys
from pathlib import Path
import odb
from apply_access import apply_access,non_pg_hash
p=argparse.ArgumentParser();p.add_argument('--odb',required=True);p.add_argument('--plan',required=True);p.add_argument('--grid',required=True);p.add_argument('--via-contract',required=True);p.add_argument('--out',required=True);a=p.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
base=Path(a.plan);plan=json.load(open(base/'access_plan.json'));rects=json.load(open(base/'reserved_access.json'));grid=json.load(open(a.grid));tech_contract=json.load(open(a.via_contract))['tech_vias_dbu']
assert len(rects)==len(plan['paths'])*27 and len(plan['vias_dbu'])==len(plan['paths'])*8
byinst={}
for i,q in enumerate(plan['paths']):
 if len(q['members'])==1:byinst.setdefault(q['members'][0],{})[q['net']]=i
name,which=next((n,q) for n,q in byinst.items() if set(q)=={'VDD','VSS'});indices=sorted(which.values());selected=dict(plan);selected['paths']=[plan['paths'][i] for i in indices];selected['vias_dbu']=[v for i in indices for v in plan['vias_dbu'][i*8:(i+1)*8]];selected['tech_vias_dbu']=tech_contract
selected_rects=[r for i in indices for r in rects[i*27:(i+1)*27]];del plan,rects,byinst
scope=out/'plan';scope.mkdir(exist_ok=True);json.dump(selected,open(scope/'access_plan.json','w'));json.dump(selected_rects,open(scope/'reserved_access.json','w'))
d=odb.dbDatabase.create();odb.read_db(d,a.odb);block=d.getChip().getBlock();tech=d.getTech()
for inst in list(block.getInsts()):
 if inst.getName()!=name:odb.dbInst.destroy(inst)
# The vehicle carries canonical supply metal so the importer exercises its real
# host-metal preflight. This isolated vehicle does not claim whole-grid IR/DRC.
for n in ['VDD','VSS']:
 net=block.findNet(n) or odb.dbNet.create(block,n);net.setSigType('POWER' if n=='VDD' else 'GROUND');net.setSpecial();sw=odb.dbSWire.create(net,'FIXED')
 for nn,ly,*xy in grid:
  if nn==n:odb.dbSBox.create(sw,tech.findLayer(ly),*[round(v*1000) for v in xy],'STRIPE')
first=apply_access(block,scope,a.grid,expected_contacts=2);second=apply_access(block,scope,a.grid,expected_contacts=2)
assert second['added_wire_rectangles']==0 and second['added_technology_vias']==0
# Wrong native rail preflight is a meaningful geometry control; no mutation.
selected['paths'][0]['rail'][0]-=1;json.dump(selected,open(scope/'access_plan.json','w'));before=non_pg_hash(block)
try:apply_access(block,scope,a.grid,expected_contacts=2)
except ValueError as e:control=str(e)
else:raise AssertionError('Wrong rail control was accepted')
assert non_pg_hash(block)==before
selected['paths'][0]['rail'][0]+=1;json.dump(selected,open(scope/'access_plan.json','w'))
odb.write_db(d,str(out/'import_vehicle.odb'));result=dict(verdict='PASS_MECHANISM_ONLY',instance=name,contacts=2,first=first,reapply=second,wrong_native_rail_control=control,source_odb=a.odb,release_qualified=False,whole_grid_connectivity='NOT RUN',DRC='NOT RUN',IR='NOT RUN')
(out/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
