"""Actual-master mixed clock/FF/comb PG coupon including the diagnosed M3 jog."""
import argparse,json,sys,collections
from pathlib import Path
import odb
p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--tools',required=True);a=p.parse_args();R=Path(a.root);F=R/'reachfix';o=F/'mixed_import_vehicle';o.mkdir(exist_ok=True);sys.path.insert(0,a.tools);sys.path.insert(0,str(R/'src'))
from mixed_apply_access import apply_access,non_pg_hash
from pg_census import transformed_rect
from shapely.geometry import box
from shapely.strtree import STRtree
plan=json.load(open(F/'pg_candidate/access_plan.json'));rects=json.load(open(F/'pg_candidate/reserved_access.json'));grid=json.load(open(F/'readback/pg_rects.json'));byinst=collections.defaultdict(dict);offsets=[];pos=0
for j,q in enumerate(plan['paths']):
 offsets.append(pos);pos+=27+bool(q.get('m3_jog_dbu'))
 for n in q['members']:byinst[n][q['net']]=j
assert pos==len(rects)
clock=next(n for n,v in byinst.items() if n.startswith('ck_') and set(v)=={'VDD','VSS'} and all(len(plan['paths'][j]['members'])==1 for j in v.values()))
selected={clock};selected.update(n for q in plan['paths'] if q.get('m3_jog_dbu') for n in q['members']);selected.add(next(n for n in byinst if 'u_rst_r1_1.' in n and n.endswith('slice$491')))
while True:
 indices={j for n in selected for j in byinst[n].values()};expanded=selected|{n for j in indices for n in plan['paths'][j]['members']}
 if expanded==selected:break
 selected=expanded
indices=sorted(indices);sub=dict(plan);sub['paths']=[plan['paths'][j] for j in indices];sub['vias_dbu']=[v for j in indices for v in plan['vias_dbu'][8*j:8*j+8]];subr=[v for j in indices for v in rects[offsets[j]:offsets[j]+27+bool(plan['paths'][j].get('m3_jog_dbu'))]];assert any(q.get('m3_jog_dbu') for q in sub['paths']);scope=o/'plan';scope.mkdir(exist_ok=True);json.dump(sub,open(scope/'access_plan.json','w'),separators=(',',':'));json.dump(subr,open(scope/'reserved_access.json','w'),separators=(',',':'))
meta=json.load(open(F/'provider/all_cells.json'));provider=dict(dbu=meta['dbu'],cells=[q for q in meta['cells'] if q['inst'] in selected]);assert len(provider['cells'])==len(selected)-1;json.dump(provider,open(o/'provider_cells.json','w'),separators=(',',':'))
needed=set()
for q in sub['paths']:
 x,y=q['m8'][2:];matches=[tuple(r) for r in grid if r[0]==q['net'] and r[1]=='M9' and round(r[2]*1000)<=x-20 and x+20<=round(r[4]*1000) and round(r[3]*1000)<=y-20 and y+20<=round(r[5]*1000)];assert matches;needed.add(min(matches))
smallgrid=[list(q) for q in sorted(needed)];json.dump(smallgrid,open(o/'grid.json','w'))
d=odb.dbDatabase.create();odb.read_db(d,str(F/'provider/provider.odb'));b=d.getChip().getBlock();tech=d.getTech()
for i in list(b.getInsts()):
 if i.getName() not in selected:odb.dbInst.destroy(i)
for n in ['VDD','VSS']:
 net=b.findNet(n);net.setSpecial();sw=odb.dbSWire.create(net,'FIXED')
 for nn,ly,*xy in smallgrid:
  if nn==n:odb.dbSBox.create(sw,tech.findLayer(ly),*[round(v*1000) for v in xy],'STRIPE')
first=apply_access(b,scope,o/'grid.json',2*len(selected),provider);second=apply_access(b,scope,o/'grid.json',2*len(selected),provider);assert second['added_wire_rectangles']==second['added_technology_vias']==0
bad=dict(provider);bad['cells']=[dict(q) for q in provider['cells']];bad['cells'][0]['bbox_dbu']=bad['cells'][0]['bbox_dbu'][:];bad['cells'][0]['bbox_dbu'][0]+=1;before=non_pg_hash(b)
try:apply_access(b,scope,o/'grid.json',2*len(selected),bad)
except ValueError as e:control=str(e)
else:raise AssertionError('Changed provider body control accepted')
assert non_pg_hash(b)==before
import os
if os.environ.get('MUT_VIA12'):
 for sw in b.findNet('VDD').getSWires():
  for z in list(sw.getWires()):
   if z.isVia() and z.getTechVia().getName()=='VIA12' and tuple(z.getViaXY())==(22877088,11793872):odb.dbSBox.destroy(z);print('MUTANT removed VIA12',flush=True)
 o=o/'mutant';o.mkdir(exist_ok=True)
odb.write_db(d,str(o/'vehicle.odb'));d2=odb.dbDatabase.create();odb.read_db(d2,str(o/'vehicle.odb'));b2=d2.getChip().getBlock();connections=[]
for n in ['VDD','VSS']:
 records=[];via_groups=[];grid_roots=[]
 for sw in b2.findNet(n).getSWires():
  for z in sw.getWires():
   if z.isVia():
    tv=z.getTechVia();x,y=z.getViaXY();group=[]
    for sh in tv.getBoxes():
     ly=sh.getTechLayer()
     if ly and ly.getRoutingLevel()>0:group.append(len(records));records.append((ly.getName(),[x+sh.xMin(),y+sh.yMin(),x+sh.xMax(),y+sh.yMax()]))
    via_groups.append(group)
   else:
    r=[z.xMin(),z.yMin(),z.xMax(),z.yMax()];ly=z.getTechLayer().getName()
    if any(nn==n and ll==ly and [round(v*1000) for v in rr]==r for nn,ll,*rr in smallgrid):grid_roots.append(len(records))
    records.append((ly,r))
 rail_idx={}
 for name in sorted(selected):
  inst=b2.findInst(name);it=inst.findITerm(n);rr=[transformed_rect(inst,z) for mp in it.getMTerm().getMPins() for z in mp.getGeometry() if z.getTechLayer() and z.getTechLayer().getName()=='M1'];assert len(rr)==1;rail_idx[name]=len(records);records.append(('M1',list(rr[0])))
 parent=list(range(len(records)))
 def find(i):
  while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
  return i
 def union(i,j):parent[find(i)]=find(j)
 for gg in via_groups:
  for j in gg[1:]:union(gg[0],j)
 for ly in {ly for ly,r in records}:
  ids=[i for i,(l,r) in enumerate(records) if l==ly];shapes=[box(*records[i][1]) for i in ids];tree=STRtree(shapes)
  for k,geom in enumerate(shapes):
   for v in tree.query(geom):
    if v<=k:continue
    inter=geom.intersection(shapes[v])
    if inter.area>0 or inter.length>0:union(ids[k],ids[v])
 roots={find(i) for i in grid_roots};assert roots
 for name in sorted(selected):
  inst=b2.findInst(name);it=inst.findITerm(n);assert it.getNet().getName()==n;rr=[transformed_rect(inst,z) for mp in it.getMTerm().getMPins() for z in mp.getGeometry() if z.getTechLayer() and z.getTechLayer().getName()=='M1'];assert len(rr)==1;r=rr[0];connected=False
  connected=find(rail_idx[name]) in roots
  connections.append(dict(inst=name,pin=n,connected=connected));assert connected,(name,n)
summary=dict(verdict='PASS_MIXED_ACTUAL_PG_MECHANISM',selected_cells=len(selected),provider_cells=len(provider['cells']),contacts=len(connections),connected=sum(q['connected'] for q in connections),actual_m3_jog_groups=sum(bool(q.get('m3_jog_dbu')) for q in sub['paths']),first=first,reapply=second,changed_provider_body_control=control,rail_model='abutting native M1 rails of same-row cells unioned (touching edge counts)',scope='Scoped actual clock/FF/comb PG coupon plus M3 jog. Not whole-die PG/clock/DRC/IR.');json.dump(summary,open(o/'summary.json','w'),indent=2);json.dump(connections,open(o/'connectivity.json','w'),indent=2);print(json.dumps(summary,indent=2),flush=True)
