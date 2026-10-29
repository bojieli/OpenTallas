#!/usr/bin/env python3
"""Materialize an existing reserved PG grid without letting it obstruct itself."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from apply_access import non_pg_hash

def prepare(source,model,out):
 import odb
 db=odb.dbDatabase.create();odb.read_db(db,source);b=db.getChip().getBlock();D=b.getDbUnitsPerMicron();before=non_pg_hash(b)
 grid=json.load(open(model));wanted={(ly,*[round(v*D) for v in xy]) for _,ly,*xy in grid};seen=set();rest=[]
 for ob in list(b.getObstructions()):
  sh=ob.getBBox();ly=sh.getTechLayer();key=(ly.getName(),sh.xMin(),sh.yMin(),sh.xMax(),sh.yMax())
  if key in wanted:
   seen.add(key);rest.append(key);odb.dbObstruction.destroy(ob)
 if seen!=wanted:raise ValueError(f'PG reservation/source mismatch: {len(wanted-seen)}missing modelrects')
 if non_pg_hash(b)!=before:raise ValueError('Non-PG connectivity or physical geometry changed')
 o=Path(out);o.mkdir(parents=True,exist_ok=True);odb.write_db(db,str(o/'grid_ready.odb'))
 (o/'restore_obs.tcl').write_text('\n'.join('create_obstruction -region {'+' '.join(f'{v/D:.6f}' for v in r)+'} -layer '+ly for ly,*r in rest)+'\n')
 result=dict(source=source,grid_model=model,owned_pg_reservations=len(seen),removed_obstructions=len(rest),non_pg_sha256=before,scope='Exact same-plan PG capacity reservations removed only while pdngen draws their actual metal; restore_obs.tcl restores every original obstruction afterwards')
 (o/'prepare_receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--odb',required=True);p.add_argument('--grid',required=True);p.add_argument('--out',required=True);a=p.parse_args();prepare(a.odb,a.grid,a.out)
