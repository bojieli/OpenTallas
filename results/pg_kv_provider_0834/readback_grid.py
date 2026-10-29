#!/usr/bin/env python3
"""Verify PG materialization preserved all source cells, signals and block reservations."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from apply_access import non_pg_hash

def readback(source,target,out):
 import odb
 def load(p):
  d=odb.dbDatabase.create();odb.read_db(d,p);return d,d.getChip().getBlock()
 ds,s=load(source);dt,t=load(target)
 def cells(b):return {i.getName():(i.getMaster().getName(),tuple(i.getOrigin()),str(i.getOrient()),str(i.getPlacementStatus()),bool(i.isDoNotTouch())) for i in b.getInsts()}
 def obs(b):
  q=[]
  for ob in b.getObstructions():
   sh=ob.getBBox();q.append((sh.getTechLayer().getName(),sh.xMin(),sh.yMin(),sh.xMax(),sh.yMax()))
  return sorted(q)
 if cells(s)!=cells(t):raise ValueError('PG materialization changed a source cell')
 if obs(s)!=obs(t):raise ValueError('PG materialization failed to restore exact original obstruction inventory')
 a,z=non_pg_hash(s),non_pg_hash(t)
 if a!=z:raise ValueError('PG materialization changed source signal or clock connections/geometry')
 supplied={};shapes={}
 for name in ('VDD','VSS','VDDPHY'):
  n=t.findNet(name)
  if n is None:raise ValueError('Missing supply '+name)
  supplied[name]=len(n.getITerms());shapes[name]=sum(len(sw.getWires()) for sw in n.getSWires())
 if not all(shapes[n]>0 for n in shapes):raise ValueError('Empty physical supply grid')
 result=dict(verdict='PG_GRID_MATERIALIZED_SOURCE_UNCHANGED',source=source,target=target,cells=len(cells(t)),block_obstructions=len(obs(t)),non_pg_sha256=a,supply_iterms=supplied,supply_shapes=shapes,scope='Canonical top PG only. No std-cell access, macro-PG closure, IR, DRC, routed clock timing or freeze claim.')
 Path(out).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--target',required=True);p.add_argument('--out',required=True);a=p.parse_args();readback(a.source,a.target,a.out)
