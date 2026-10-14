import json,re,hashlib,collections
from pathlib import Path
R=Path(__file__).resolve().parents[2];p=json.loads((R/'results/arch/qwen_tp8_1012/vm_rg6.json').read_text());spec=json.loads((R/'physical/ref_tile/qfd_vm_rg6.spec.json').read_text());W,H=p['outline_um'];children={c['inst']:c for c in spec['children']};cache={}
def pin(c,n):
 v=c['view']
 if v not in cache:
  f=next((R/v).glob('*.lef'));txt=f.read_text();pins={}
  for m in re.finditer(r'\bPIN\s+(\S+)(.*?)\n\s*END\s+\1\s',txt,re.S):
   rect=re.search(r'RECT\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)',m[2]);
   if rect:
    x1,y1,x2,y2=map(float,rect.groups());pins[m[1]]=[(x1+x2)/2,(y1+y2)/2]
  cache[v]=pins
 xy=cache[v][n];return [xy[0]+c['at'][0],xy[1]+c['at'][1]]
def depths(xy):
 x,y=xy;return dict(w=x,e=W-x,s=y,n=H-y)
rows=[]
for i,s in enumerate(p['segments']):
 for dr,pathidx,pn in [('rx',0,'d'),('tx',-1,'q')]:
  if dr=='rx' and s['local_source']:continue
  if not s['path']:continue
  st=s['path'][pathidx];c=children['u_'+st['bay']+'_t'+str(st['slot'])];face=(s['input'] if dr=='rx' else s['output'])[0][-1];bounds=[]
  for bit in range(st['bit0'],st['bit0']+8):
   xy=pin(c,pn+'['+str(bit)+']');ds=depths(xy);bounds.append((ds[face],min(ds.values())))
  rows.append(dict(segment=i,lane=s['lane'],direction=dr,face=face,child=c['inst'],assigned_face_min_wire_um=max(b[0] for b in bounds),any_face_min_wire_um=max(b[1] for b in bounds),limit_ps=190 if dr=='rx' else 220,bits=8))
T=json.loads((R/'results/arch/qwen_tp8_1012/vm_bay_tiles_claude.json').read_text());P=json.loads((R/'results/arch/qwen_tp8_1012/vm_leaf_plan_claude.json').read_text());owners={b['n']:('rg'+str(b['region']) if b.get('region') is not None else b['n']) for b in P['x_relay_bays']};srcowners={c['n']:'rg'+str(c['region']) for c in P['children'] if 'region' in c};runs=collections.Counter();changed=[]
for lane,chain in T['lane_chain'].items():
 src=lane.split('>')[0];seq=[srcowners[src]]+[owners[v['bay']] for v in sorted(chain,key=lambda x:x['visit'])]+['xcol'];compressed=[]
 for o in seq:
  if not compressed or o!=compressed[-1]:compressed.append(o)
 crossings=len(compressed)-1;runs[crossings]+=1
 changed.append(dict(lane=lane,parent_runs=compressed,crossings=crossings,uniform_entry_exit_added_engine_edges=2*crossings))
a=dict(schema='opentallas.vm-boundary-endpoint-screen.v1',meaning='Actual closed LEF pin centers; minimum Manhattan distance to continuous face, no pin packing or routed wire measurement. 0.76ps/um is screening estimate, not timing proof.',region=6,outline_um=[W,H],lane_bits=len(rows)*8,rows=rows,lane_crossing_histogram=dict(runs),global_uniform_face_delta=dict(min_engine_edges=2*min(runs),max_engine_edges=2*max(runs),requires_equalization=True),lane_crossings=changed)
for typ in ['rx','tx']:
 rr=[r for r in rows if r['direction']==typ];a[typ]=dict(bits=len(rr)*8,assigned_face_impossible_screen_bits=sum(r['bits'] for r in rr if r['assigned_face_min_wire_um']*.76>r['limit_ps']),any_face_impossible_screen_bits=sum(r['bits'] for r in rr if r['any_face_min_wire_um']*.76>r['limit_ps']),assigned_face_max_min_wire_um=max(r['assigned_face_min_wire_um'] for r in rr),any_face_max_min_wire_um=max(r['any_face_min_wire_um'] for r in rr))
out=R/'results/arch/qwen_tp8_1012/rg6_lane_boundary_endpoint_screen.json';out.write_text(json.dumps(a,indent=1)+'\n');print({k:v for k,v in a.items() if k not in ('rows','lane_crossings')})

rows=[]
for port,inst,prefix,n in [('ro','u_core.u_r2','ro',512),('ovf','u_core.u_r2','ovf',1)]+[(f'so_s{i}',f'u_core.g_su_leaf[{i}].u_su','so',1024) for i in range(3)]:
 c=children[inst];f=next(f.lower() for f,pp in spec['pins'].items() if port in pp);depth=[]
 for bit in range(n):
  xy=pin(c,prefix if n==1 else prefix+f'[{bit}]');ds=depths(xy);depth.append((ds[f],min(ds.values())))
 rows.append(dict(port=port,bits=n,face=f,max_assigned_face_min_wire_um=max(x[0] for x in depth),max_any_face_min_wire_um=max(x[1] for x in depth),assigned_face_screen_impossible_bits=sum(x[0]*.76>220 for x in depth),any_face_screen_impossible_bits=sum(x[1]*.76>220 for x in depth)))
a=dict(schema='opentallas.vm-core-output-pin-screen.v1',claim='ActualclosedLEFpincenters, continuousface minimumdistance and0.76ps/um screenonly; noIOpacking orroutedtimingproof.',rows=rows);(R/'results/arch/qwen_tp8_1012/rg6_core_output_endpoint_screen.json').write_text(json.dumps(a,indent=1)+'\n');print(rows)
