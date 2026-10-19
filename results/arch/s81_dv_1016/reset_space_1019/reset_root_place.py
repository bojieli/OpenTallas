from pathlib import Path
import json,math,sys
P=Path('.').resolve();sys.path.insert(0,str(P));sys.path.insert(1,str(P.parent/'src/tools'));sys.path.insert(2,str(P.parent/'src/tools/s81_dv'))
import dv_rvcase as R
q=json.loads((P/'reset_space_serdes5_probe.json').read_text());graph=json.loads((P/'reset_sink_repair.json').read_text());pos=graph['positions'];parents=graph['parents']
code=(P/'reset_access_bridges.py').read_text();a=code.index('def m6_near');b=code.index('# Try legal R0 bridge bodies',a);exec(code[a:b])
class RootPlacer(R.Placer):
 def hits(self,r,gap=.5):
  if super().hits(r,gap):return True
  pos['_trial']=[r[0],r[1],17.28,17.28]
  return dist('_trial',self.child)>405.000001
placer=RootPlacer(32486.9,25000)
for r in q['seed']['obstructions']:placer.add(tuple(r))
for x,y,w,h in pos.values():placer.add((x,y,x+w,y+h))
root=next(n for n,p in parents.items() if p is None);child=root;records=[]
for name in ['rst_root1','rst_root0']:
 px,py,*_=pos[child];placer.child=child
 try:x,y,move=placer.put(px-18,py,17.28,17.28,step=4,rmax=405,max_distance=405,exact_edges=True,origin_grid=(.048,.048,0,0))
 finally:pos.pop('_trial',None)
 pos[name]=[x,y,17.28,17.28];parents[child]=name;parents[name]=None
 records.append({'inst':name,'origin':[x,y],'child':child,'both_child_inputs_escape_length_um':dist(name,child)});child=name
summary={'scope':'ROOT_TWO_FLOP_BODY_AND_INTERNAL_TRACK_ESCAPE_GEOMETRY_ONLY_NO_RC_CALENDAR_BIND','original_tree_root':root,'root_stages':2,'placed':records,'external_reset_pad_to_root0':'OWED reset source/pad/async assertion physical network; no timing mask added','clock':'Same regional root as tree root, actual native clock network still OWED','candidate_nodes':len(pos),'connected_nodes':len(parents)}
(P/'reset_root_place.json').write_text(json.dumps({'summary':summary,'positions':pos,'parents':parents},indent=1)+'\n');print(json.dumps(summary,indent=2))
