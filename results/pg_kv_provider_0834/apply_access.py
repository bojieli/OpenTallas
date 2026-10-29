#!/usr/bin/env python3
"""Add complete reviewed clock-cell PG access to an existing infrastructure DB.
Requires real canonical PG metal first. Does not route or qualify DRC/IR.
"""
import argparse,hashlib,json,sys
from pathlib import Path
for root in (Path(__file__).resolve().parents[1],Path(__file__).resolve().parents[2]):
 sys.path.insert(0,str(root/'tools/die_plan'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from infra_replay import physical_snapshot
from native_rect import transformed_rect


def non_pg_hash(block):
 h=hashlib.sha256()
 for net in sorted(block.getNets(),key=lambda n:n.getName()):
  if str(net.getSigType()) in ('POWER','GROUND'):continue
  h.update(json.dumps([net.getName(),physical_snapshot(net)],sort_keys=True,separators=(',',':')).encode())
 return h.hexdigest()


def apply_access(block,plan_dir,grid_path,expected_contacts=75934):
 import odb
 base=Path(plan_dir);plan=json.load(open(base/'access_plan.json'));rects=json.load(open(base/'reserved_access.json'));grid=json.load(open(grid_path));D=block.getDbUnitsPerMicron()
 if plan['dbu']!=D or plan['failed'] or not plan['paths']:raise ValueError('Incomplete or wrong-unit access plan')
 contacts=sum(len(q['members']) for q in plan['paths'])
 if contacts!=expected_contacts:raise ValueError(f'Contact count {contacts} != {expected_contacts}')
 tech=block.getDb().getTech();nets={n:block.findNet(n) for n in ('VDD','VSS')}
 if any(n is None for n in nets.values()):raise ValueError('Canonical PG nets must exist before access import')
 for n,typ in [('VDD','POWER'),('VSS','GROUND')]:
  if str(nets[n].getSigType())!=typ:raise ValueError('Wrong canonical supply type '+n)
 # Require actual host conductors, never logical global_connect or net names.
 wanted_rects={(n,layer,*[round(v*D) for v in xy]) for n,layer,*xy in rects}
 wanted_vias={tuple(v) for v in plan['vias_dbu']}
 grid_required={(r[0],r[1],*[round(v*D) for v in r[2:]]) for r in grid if r[1] in ('M8','M9')}
 actual=set();actual_vias=set()
 for n,net in nets.items():
  for sw in net.getSWires():
   for shape in sw.getWires():
    if shape.isVia():
     via=shape.getTechVia()
     if via:
      key=(n,via.getName(),*shape.getViaXY())
      if key in wanted_vias:actual_vias.add(key)
     continue
    layer=shape.getTechLayer()
    if layer:
     key=(n,layer.getName(),shape.xMin(),shape.yMin(),shape.xMax(),shape.yMax())
     if key in wanted_rects or key in grid_required:actual.add(key)
 missing=[r for r in grid if r[1] in ('M8','M9') and (r[0],r[1],*[round(v*D) for v in r[2:]]) not in actual]
 if missing:raise ValueError(f'Actual canonical PG grid missing {len(missing)} rectangles; first {missing[:2]}')
 # Every source clock-cell supply rail must match the source-pinned plan.
 seen=set();terms=[]
 for q in plan['paths']:
  n=q['net'];x0,y0,x1,y1=q['rail'];intervals=[]
  for name in q['members']:
   if (name,n) in seen:raise ValueError('Repeated contact '+name+'/'+n)
   seen.add((name,n));inst=block.findInst(name)
   if inst is None or not inst.getMaster().getName().endswith('_ASAP7_75t_R'):raise ValueError('Clock cell missing/changed '+name)
   it=inst.findITerm(n)
   if it is None or str(it.getMTerm().getSigType()) not in ('POWER','GROUND'):raise ValueError('Supply terminal missing '+name+'/'+n)
   rr=[(shape.getTechLayer().getName(),transformed_rect(inst,shape)) for pin in it.getMTerm().getMPins() for shape in pin.getGeometry() if shape.getTechLayer()]
   if len(rr)!=1 or rr[0][0]!='M1':raise ValueError('Unexpected native rail geometry '+name+'/'+n)
   ax,ay,bx,by=rr[0][1]
   if ay!=y0 or by!=y1 or ax<x0 or bx>x1:raise ValueError('Native rail moved relative to plan '+name+'/'+n)
   intervals.append((ax,bx));terms.append((it,n))
  end=x0
  for lo,hi in sorted(intervals):
   if lo>end:raise ValueError('Planned rail has uncovered gap')
   end=max(end,hi)
  if end!=x1:raise ValueError('Planned rail extent differs from actual members')
 expected={(inst.getName(),n) for inst in block.getInsts() if inst.getMaster().getName().endswith('_ASAP7_75t_R') for n in ('VDD','VSS')}
 if seen!=expected:raise ValueError(f'Clock supply census differs from plan: missing {len(expected-seen)} extra {len(seen-expected)}')
 layers={r[1]:tech.findLayer(r[1]) for r in rects}
 via_defs={r[1]:tech.findVia(r[1]) for r in plan['vias_dbu']}
 if any(v is None for v in layers.values()) or any(v is None for v in via_defs.values()):raise ValueError('Technology layer/via missing')
 if 'tech_vias_dbu' not in plan:raise ValueError('Plan lacks actual technology-via enclosure contract; regenerate plan')
 for name,via in via_defs.items():
  actual_boxes=sorted([shape.getTechLayer().getName(),shape.xMin(),shape.yMin(),shape.xMax(),shape.yMax()] for shape in via.getBoxes() if shape.getTechLayer())
  if actual_boxes!=sorted(plan['tech_vias_dbu'][name]):raise ValueError('Technology via geometry changed '+name)
 before=non_pg_hash(block)
 swires={}
 def supply_wire(n):
  if n not in swires:
   nets[n].setSpecial();swires[n]=odb.dbSWire.create(nets[n],'FIXED')
  return swires[n]
 added_rects=added_vias=0
 for k,(n,layer,*xy) in enumerate(rects):
  coords=[round(v*D) for v in xy];key=(n,layer,*coords)
  if key not in actual:
   odb.dbSBox.create(supply_wire(n),layers[layer],*coords,'STRIPE');actual.add(key);added_rects+=1
  if k%500000==0:print('PG_ACCESS_RECT',k,len(rects),flush=True)
 for k,(n,via,x,y) in enumerate(plan['vias_dbu']):
  key=(n,via,x,y)
  if key not in actual_vias:
   odb.dbSBox.create(supply_wire(n),via_defs[via],x,y,'STRIPE');actual_vias.add(key);added_vias+=1
  if k%100000==0:print('PG_ACCESS_VIA',k,len(plan['vias_dbu']),flush=True)
 for it,n in terms:it.connect(nets[n])
 after=non_pg_hash(block)
 if after!=before:raise ValueError('Non-PG wire/terminal/instance geometry changed during PG import')
 return dict(verdict='IMPORTED_NO_SIGNOFF',contacts=contacts,groups=len(plan['paths']),planned_wire_rectangles=len(rects),planned_technology_vias=len(plan['vias_dbu']),added_wire_rectangles=added_rects,added_technology_vias=added_vias,non_pg_before_sha256=before,non_pg_after_sha256=after,actual_grid_rectangles=len(grid),freeze_qualified=False,DRC='NOT RUN',IR='NOT RUN')


def main():
 import odb
 p=argparse.ArgumentParser();p.add_argument('--odb',required=True);p.add_argument('--plan',required=True);p.add_argument('--grid',required=True);p.add_argument('--out',required=True);p.add_argument('--expected-contacts',type=int,default=75934);a=p.parse_args()
 db=odb.dbDatabase.create();odb.read_db(db,a.odb);block=db.getChip().getBlock();result=apply_access(block,a.plan,a.grid,a.expected_contacts)
 out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True);odb.write_db(db,str(out));result['source']=a.odb;result['output']=str(out);out.with_suffix('.access.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
if __name__=='__main__':main()
