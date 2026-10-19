from pathlib import Path
import json,sys,math
P=Path('.').resolve();sys.path.insert(0,str(P));sys.path.insert(1,str(P.parent/'src/tools'));sys.path.insert(2,str(P.parent/'src/tools/s81_dv'))
import dv_rvcase as R
q=json.loads((P/'reset_space_serdes5_probe.json').read_text());g=json.loads((P/'reset_root_place.json').read_text());pos=g['positions'];parents=g['parents'];name='st_rs_38_7_1';old=pos[name][:];assert name not in parents
code=(P/'reset_access_bridges.py').read_text();a=code.index('def m6_near');b=code.index('# Try legal R0 bridge bodies',a);exec(code[a:b])
candidates=sorted(parents,key=lambda p:dist(p,name))[:32]
class ReachPlacer(R.Placer):
 def hits(self,r,gap=.5):
  if super().hits(r,gap):return True
  pos['_trial']=[r[0],r[1],17.28,17.28]
  return min(dist(p,'_trial')for p in candidates)>405.000001
placer=ReachPlacer(32486.9,25000)
for r in q['seed']['obstructions']:placer.add(tuple(r))
for n,(x,y,w,h)in pos.items():
 if n!=name:placer.add((x,y,x+w,y+h))
try:x,y,move=placer.put(old[0],old[1],17.28,17.28,step=4,rmax=405,max_distance=405,exact_edges=True,origin_grid=(.048,.048,0,0))
finally:pos.pop('_trial',None)
pos[name]=[x,y,17.28,17.28];parent=min(candidates,key=lambda p:dist(p,name));parents[name]=parent
summary={'scope':'DIAGNOSTIC_ALL_RESET_BODY_GRAPH_CONNECTED_BY_RELOCATING_ISOLATED_CELL_NO_OLD_LOAD_OR_CALENDAR_ROUTING_CLAIM','inst':name,'old_origin':old[:2],'new_origin':[x,y],'body_displacement_um':abs(x-old[0])+abs(y-old[1]),'parent':parent,'both_input_track_escape_um':dist(parent,name),'all_nodes':len(pos),'connected_nodes':len(parents),'max_selected_both_input_escape_um':max(dist(p,n)for n,p in parents.items()if p),'preserved_old_rsv07_landing_hrq_ICG_load_mapping':False,'remaining':'Reassign exact data/landing/block/ICG/reset-calendar endpoints in emitted die; actual obstacle/RC/native clocks/PG and >=2boot stages remain owed'}
(P/'reset_isolated_relocate.json').write_text(json.dumps({'summary':summary,'positions':pos,'parents':parents},indent=1)+'\n');print(json.dumps(summary,indent=1))
