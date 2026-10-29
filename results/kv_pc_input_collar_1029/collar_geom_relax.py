from pathlib import Path
import importlib.util,json,collections
sp=importlib.util.spec_from_file_location('g','/home/ubuntu/OpenTallas/tools/autopilot/geom_rules.py');g=importlib.util.module_from_spec(sp);sp.loader.exec_module(g)
D=g.Design('/srv/opentallas-scratch/claude/codex-geom-1029/kv/kvspc.tsv');outface=set();inface=set();edges=[]
for p in D.pins:
 if p['sig'] in ('POWER','GROUND','CLOCK') or g.CLOCK_PIN_RE.search(p['name']) or p['name'].startswith('strap_'):continue
 ni=D.pin_net.get(p['k']);q=[(ni,0)];seen=set()
 while q:
  n,dep=q.pop()
  if n is None or n in seen or dep>4:continue
  seen.add(n);refs=([D.nets[n][1]] if p['io']=='OUTPUT' else D.nets[n][2])
  for s in refs:
   if not s or s[0]!='i' or s[2]:continue
   cid=s[1]
   if D.kind(cid)=='S':
    (outface if p['io']=='OUTPUT' else inface).add(cid)
    if p['io']!='OUTPUT':edges.append((p['x'],p['y'],cid,p['name']))
   elif D.kind(cid)=='B':
    nxt=([v for v,ck in D.cell_in[cid] if not ck] if p['io']=='OUTPUT' else D.drives[cid]);q.extend((nn,dep+1) for nn in nxt)
x,y=(D.die[0]+D.die[2])/2,(D.die[1]+D.die[3])/2
for cid,c in list(D.cells.items()):
 if c[0]=='S' and cid not in outface:
  w,h=c[4]-c[2],c[5]-c[3];D.cells[cid]=(c[0],c[1],x-w/2,y-h/2,x+w/2,y+h/2,c[6])
m=g.r2r_metrics(D);pinmax=max((abs(px-g.ctr(D.cells[cid])[0])+abs(py-g.ctr(D.cells[cid])[1]),name) for px,py,cid,name in edges)
r=dict(scope='Relaxed coincidence feasibility only; zero cell-overlap/row legality claim',output_face_flops=len(outface),input_capture_flops=len(inface),shared_input_output=len(outface&inface),old_sequential_graph=m,new_input_to_old_capture_max=pinmax)
print(json.dumps(r,indent=2));Path('/srv/opentallas-scratch/claude/codex-kv-pc-struct-1029/collar_geom_relax.json').write_text(json.dumps(r,indent=2)+'\n')
