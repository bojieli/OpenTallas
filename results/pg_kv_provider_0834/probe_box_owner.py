"""Tiny actual-master coupon for OpenDB box ownership iteration/destruction."""
import json,odb
D=odb.dbDatabase.create();odb.read_lef(D,'/OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef');odb.read_lef(D,'/kv/full_abstracts/kv3_hg_part.lef');m=D.findMaster('kv3_hg_part');mt=m.findMTerm('VDD')
def countobs():return sum(1 for q in m.getObstructions())
def countpins():return sum(1 for p in mt.getMPins() for q in p.getGeometry())
r=dict(obs_before=countobs(),pins_before=countpins())
rows=list(m.getObstructions());r['obs_list_len']=len(rows)
for q in rows:odb.dbBox_destroy(q)
r['obs_after_list_delete']=countobs()
rows=[q for q in m.getObstructions()];r['obs_comp_len']=len(rows)
for q in rows:odb.dbBox_destroy(q)
r['obs_after_comp_delete']=countobs()
pins=list(mt.getMPins());r['mpin_list_len']=len(pins)
for p in pins:
 rows=list(p.getGeometry());r.setdefault('pg_geom_list_lens',[]).append(len(rows))
 for q in rows:odb.dbBox_destroy(q)
r['pins_after_list_delete']=countpins()
pins=[p for p in mt.getMPins()];r['mpin_comp_len']=len(pins)
for p in pins:
 rows=[q for q in p.getGeometry()];r.setdefault('pg_geom_comp_lens',[]).append(len(rows))
 for q in rows:odb.dbBox_destroy(q)
r['pins_after_comp_delete']=countpins()
print('BOX_OWNER_PROBE',json.dumps(r),flush=True)
