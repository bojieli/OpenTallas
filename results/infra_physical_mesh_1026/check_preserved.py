import json,sys
from pathlib import Path
sys.path.insert(0,'/work')
import odb
from infra_replay import load_db,physical_snapshot
before,b=load_db('/work/mesh_before.odb');after,a=load_db('/work/mesh_routed.odb')
names=['ck_mesh','VDD','VSS'];out={}
for n in names:
 v=physical_snapshot(b.findNet(n));w=physical_snapshot(a.findNet(n));assert json.dumps(v,sort_keys=True)==json.dumps(w,sort_keys=True),n
 out[n]={'unchanged':True,'source':v,'routed':w}
assert not Path('/work/drc.rpt').read_text().strip()
for n in ['clk','o0','o1','o2','o3']:assert a.findNet(n).getWire(),n
Path('/work/preserved_actual.json').write_text(json.dumps({'verdict':'PRESERVED','freeze_qualified':False,'drc_count':0,'nets':out,'new_ordinary_wires':['clk','o0','o1','o2','o3']},indent=2)+'\n')
removed=0
for s in b.findNet('ck_mesh').getSWires():
 for v in list(s.getWires()):
  if v.isVia() and v.getTechVia().getName()=='VIA89':odb.dbSBox.destroy(v);removed+=1
assert removed==4;odb.write_db(before,'/work/mutant_missing_intersection_vias.odb')
print('ACTUAL_ASAP7_MESH_PG_IMMUTABLE_DRC0')
