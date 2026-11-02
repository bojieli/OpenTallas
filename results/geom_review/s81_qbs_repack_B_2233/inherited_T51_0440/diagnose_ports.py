from pathlib import Path
import sys,json,collections,math
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/autopilot');import geom_rules as G
R=Path(__file__).parent;D=G.Design(R/'geom.tsv');out={};names=['ft2_i[4]','ft2_i[8]','ft2_i[3]','ft2_i[7]','ft2_i[10]']
# Exact first sequential frontier through all native non-sequential combinational logic (hold_mux landing).
for name in names:
 p=next(p for p in D.pins if p['name']==name);n=D.pin_net[p['k']];todo=[n];seen={n};caps=set()
 while todo:
  cur=todo.pop()
  for t in D.nets[cur][2]:
   if t[0]!='i'or t[2]:continue
   k=D.kind(t[1])
   if k=='S':caps.add(t[1]);continue
   if k not in 'BLK':continue
   for nn in D.drives.get(t[1],[]):
    if nn not in seen:seen.add(nn);todo.append(nn)
 rows=sorted([dict(name=D.cells[i][6],master=D.cells[i][1],xy=G.ctr(D.cells[i]),distance_um=abs(G.ctr(D.cells[i])[0]-p['x'])+abs(G.ctr(D.cells[i])[1]-p['y']),status=D.extra.get('status',{}).get(i,'PLACED/unreported'))for i in caps],key=lambda x:-x['distance_um']);out[name]=dict(pin_xy=[p['x'],p['y']],first_capture_count=len(rows),captures=rows)
faces={}
for face in('E','W'):
 ps=[p for p in D.pins if p['sig']not in('POWER','GROUND')and G.face_of(p['x'],p['y'],D.die)==face];bs=collections.defaultdict(list)
 for p in ps:bs[p['name'].split('[')[0]].append(p['y'])
 bins=sorted({min(122,int(p['y']//10))for p in ps});faces[face]=dict(pins=len(ps),occupied_10um_bins=len(bins),total_10um_bins=123,occupied_bins=bins,bus_ranges={k:dict(count=len(v),min_y=min(v),max_y=max(v))for k,v in bs.items()})
(R/'ports_diagnosis.json').write_text(json.dumps(dict(first_captures=out,partial_faces=faces),indent=2));print(json.dumps(dict(first_captures=out,partial_faces=faces),indent=2))
