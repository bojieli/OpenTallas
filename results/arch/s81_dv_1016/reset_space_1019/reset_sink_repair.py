from pathlib import Path
from collections import defaultdict
import json,sys,math
P=Path('.').resolve();sys.path.insert(0,str(P));sys.path.insert(1,str(P.parent/'src/tools/s81_dv'));sys.path.insert(2,str(P.parent/'src/tools'))
import dv_diecase as C
plan=json.loads((P/'reset_space_serdes5_plan.json').read_text());hints=json.loads((P/'place_hints.json').read_text());q=json.loads((P/'reset_space_serdes5_probe.json').read_text());inventory=json.loads((P/'actual_reset_pins.json').read_text());graph=json.loads((P/'reset_physical_access_bridges.json').read_text());pos=graph['positions'];connected=set(graph['parents'])
B=440.;buck=defaultdict(list)
for n in connected:
 x,y,*_=pos[n];buck[int(x//B),int(y//B)].append(n)
outrect=inventory['dsfd_rly_1_WN']['pins']['o']
def shift(rr,x,y):return [(a+x,b+y,c+x,d+y) for layer,a,b,c,d in rr]
def distance(node,rr):
 x,y,*_=pos[node]
 return min(max(a-c1,a1-c,0)+max(b-d1,b1-d,0) for a,b,c,d in shift(outrect,x,y) for a1,b1,c1,d1 in rr)
def serve(rr):
 x,y=(rr[0][0]+rr[0][2])/2,(rr[0][1]+rr[0][3])/2
 cand=[]
 for dx in (-1,0,1):
  for dy in (-1,0,1):
   for n in buck[int(x//B)+dx,int(y//B)+dy]:
    d=distance(n,rr)
    if d<=405.000001:cand.append((d,n))
 return min(cand) if cand else None
locations=q['seed']['locations'];sinks=[];missing=[]
for l in plan['links']:
 nm=l['i'].replace('-','_')
 for k,(x,y) in enumerate(l['sp']):
  inst=f'st_{nm}_{k}';d=C.station_dir(l['h'],x,y);master=f"dsfd_dvrlyh_{l['b']}_{d}";sinks.append((inst,master))
for r in hints['landings']:sinks.append((r['inst'],r['master']))
served=[];unserved=[]
for name,master in sinks:
 if master not in inventory or not inventory[master]['pins'].get('rs'):missing.append([name,master]);continue
 x,y,*_=locations[name];rr=shift(inventory[master]['pins']['rs'],x,y);hit=serve(rr)
 if hit:served.append({'sink':name,'master':master,'serving_node':hit[1],'min_rect_um':hit[0]})
 else:unserved.append({'sink':name,'master':master,'reset_rectangles':rr})
result={'scope':'CONNECTED_GRAPH_TO_ACTUAL_CLOSED_DATA_RELAY_LANDING_RS_MIN_RECT_GEOMETRY_ONLY_NO_ROUTE_RC_OR_CALENDAR','sinks':len(sinks),'served':len(served),'unserved':len(unserved),'missing_models':missing,'max_min_rect_um':max(r['min_rect_um'] for r in served),'first_unserved':unserved[:20],'unserved_all':unserved,'block_standin_closed_parent_and_calendars':'OWED exact reset-port/model mapping, actual root2/body graph selection, new reset calendars and physical wires'}
(P/'reset_sink_reach.json').write_text(json.dumps(result,indent=1)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='unserved_all'},indent=2));# Preserve failure before trying new physical sink-serving nodes.


# Add real-sink-serving bodies using actual .i/.rs source-to-node escape paths.
sys.path.insert(0,str(P))
import dv_rvcase as R
code=(P/'reset_access_bridges.py').read_text();a=code.index('def m6_near');b=code.index('# Try legal R0 bridge bodies',a);exec(code[a:b])
class SinkPlacer(R.Placer):
 def hits(self,r,gap=.5):
  if super().hits(r,gap):return True
  pos['_trial']=[r[0],r[1],17.28,17.28]
  return dist(self.parent,'_trial')>405.000001 or distance('_trial',self.target)>405.000001
placer=SinkPlacer(32486.9,25000)
for r in q['seed']['obstructions']:placer.add(tuple(r))
for x,y,w,h in pos.values():placer.add((x,y,x+w,y+h))
new=[];failures=[]
for item in unserved:
 rr=item['reset_rectangles']
 if serve(rr):continue
 sx,sy=(rr[0][0]+rr[0][2])/2,(rr[0][1]+rr[0][3])/2
 candidates=sorted((distance(n,rr),n) for n in connected if distance(n,rr)<=810)
 placed=False
 for _,parent in candidates:
  px,py,*_=pos[parent];placer.parent=parent;placer.target=rr
  try:x,y,move=placer.put((px+sx-8.64)/2,(py+sy-8.64)/2,17.28,17.28,step=4,rmax=405,max_distance=405,exact_edges=True,origin_grid=(.048,.048,0,0))
  except ValueError:continue
  finally:pos.pop('_trial',None)
  name='new_sink_'+str(len(new));pos[name]=[x,y,17.28,17.28];connected.add(name);buck[int(x//B),int(y//B)].append(name);graph['parents'][name]=parent
  new.append({'inst':name,'sink':item['sink'],'origin':[x,y],'parent':parent,'parent_escape_length_um':dist(parent,name),'sink_min_rect_um':distance(name,rr)});placed=True;break
 if not placed:failures.append(item)
remaining=[];maxd=0
for name,master in sinks:
 if master not in inventory or not inventory[master]['pins'].get('rs'):continue
 x,y,*_=locations[name];rr=shift(inventory[master]['pins']['rs'],x,y);hit=serve(rr)
 if not hit:remaining.append(name)
 else:maxd=max(maxd,hit[0])
summary={'scope':'ACTUAL_RELAY_LANDING_RESET_SINK_MIN_RECT_GEOMETRY_ONLY_NODE_I_RS_TRACK_ESCAPE_NO_ROUTE_RC_OR_CALENDAR','actual_sinks':len(sinks),'served':len(sinks)-len(remaining),'unserved':remaining,'missing_models':missing,'new_sink_nodes':new,'failures':failures,'max_sink_min_rect_um':maxd,'candidate_nodes':len(pos),'connected_nodes':len(connected),'remaining_scope':'Actual closed parent and flexible stand-in block resets, root2, all new gate calendars, obstacles/DRC/RC/native clocks and bind still OWED.'}
(P/'reset_sink_repair.json').write_text(json.dumps({'summary':summary,'positions':pos,'parents':graph['parents']},indent=1)+'\n');print(json.dumps(summary,indent=2));raise SystemExit(1 if remaining or failures or missing else 0)
