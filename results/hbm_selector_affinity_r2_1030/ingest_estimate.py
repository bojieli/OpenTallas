#!/usr/bin/env python3
"""Input-capture FF station estimate: no RTL, pin or latency changes; not placement evidence."""
import json,re,sys,math
from pathlib import Path
import numpy as np
K=Path(sys.argv[1]);O=Path(sys.argv[2]);O.mkdir(parents=True,exist_ok=True)
pins={p['name']:p for p in json.load(open(K/'plan_pins.json'))['pins']}
mt=(K/'macro_placement.tcl').read_text().replace('\\','')
macros={}
for q,m,master,x,y,orient in re.findall(r'\{u_fcore\.core\.gq\[(\d+)\]\.gm\[(\d+)\]\.mem\}\s+(\S+)\s+([0-9.]+)\s+([0-9.]+)\s+(\S+)',mt):
 macros[(int(q),int(m))]=dict(master=master,x=float(x),y=float(y),orient=orient)
assert len(macros)==12
master=next(iter(macros.values()))['master'];lef=(K/'macros'/f'{master}.lef').read_text()
w,h=map(float,re.search(r'\bSIZE\s+([0-9.]+)\s+BY\s+([0-9.]+)',lef).groups())
ports={}
for pm in re.finditer(r'(?ms)^\s*PIN\s+(\S+)\s+(.*?)^\s*END\s+\1(?=\s|$)',lef):
 rects=[tuple(map(float,m.groups())) for m in re.finditer(r'RECT\s+([-0-9.]+)\s+([-0-9.]+)\s+([-0-9.]+)\s+([-0-9.]+)',pm[2])]
 if rects:ports[pm[1]]=rects
assert all(f'wd_in[{i}]' in ports for i in range(256))
infra=json.load(open(K/'core_infra_plan.json'));blocked=[]
for b in {tuple(c['rect_um']) for c in infra['cells']}:blocked.append(b)
for m in macros.values():blocked.append((m['x']-4.32,m['y']-4.32,m['x']+w+4.32,m['y']+h+4.32))
points=[]
for x in np.arange(8.64,595.728,4.32):
 for y in np.arange(8.64,446.04,4.32):
  if not any(x>b[0]-1 and x<b[2]+1 and y>b[1]-1 and y<b[3]+1 for b in blocked):points.append((x,y))
xy=np.array(points);uses=np.zeros(len(points),dtype=int);rows=[]
for bit in range(2368):
 q=bit//592;local=bit%592;m=local//256;b=local%256;mac=macros[(q,m)];p=pins[f'in_line[{bit}]'];src=np.array([p['x'],p['y']]);targets=[]
 for x0,y0,x1,y1 in ports[f'wd_in[{b}]']:
  x,y=(x0+x1)/2,(y0+y1)/2
  if mac['orient']=='MY':x=w-x
  elif mac['orient']!='R0':raise ValueError(mac['orient'])
  targets.append(np.array([mac['x']+x,mac['y']+y]))
 tgt=min(targets,key=lambda a:np.abs(a-src).sum());direct=float(np.abs(tgt-src).sum())
 face=min([('W',p['x']),('E',600.048-p['x']),('S',p['y']),('N',450.36-p['y'])],key=lambda a:a[1])[0]
 rows.append(dict(bit=bit,quarter=q,macro=m,source_um=src.tolist(),target_um=tgt.tolist(),face=face,direct_um=direct))
for r in sorted(rows,key=lambda x:-x['direct_um']):
 src=np.array(r['source_um']);tgt=np.array(r['target_um']);d0=np.abs(xy-src).sum(axis=1);d1=np.abs(xy-tgt).sum(axis=1);cost=np.maximum(d0,d1);score=cost+uses*.0001;score[uses>=24]=np.inf;i=int(np.argmin(score));uses[i]+=1
 r.update(ff_station_estimate_um=xy[i].round(3).tolist(),pin_to_station_um=round(float(d0[i]),3),station_to_macro_pin_um=round(float(d1[i]),3),max_leg_um=round(float(cost[i]),3),native_register=f'u_fcore.in_r[{r["bit"]}]')
summary=dict(status='ESTIMATE ONLY, NOT PLACED/SIGNED',rule_um=405,macro_halo_um=4.32,station_bay_max_ff=24,baseline_registered_pipeline='existing outer face capture -> existing native in_r -> write SRAM; no new FF/cycles',added_ff=0,added_cycles=0,bits=len(rows),source_faces={q:{f:sum(r['quarter']==q and r['face']==f for r in rows) for f in ['N','S','E','W']} for q in range(4)},direct_gt810=sum(r['direct_um']>810 for r in rows),best_legal_station_gt405=sum(r['max_leg_um']>405 for r in rows),best_legal_station_gt375=sum(r['max_leg_um']>375 for r in rows),worst_direct_um=max(r['direct_um'] for r in rows),worst_two_hop_leg_um=max(r['max_leg_um'] for r in rows),used_bays=int(sum(uses>0)),max_ff_per_bay=int(max(uses)),limitations=['pin position proxies existing face FF; actual face FF offset must be checked after placement','only direct op2 ingest path, not compaction/flush or output return','source in_r mapping/FF survival must be confirmed on mapped netlist','region/clock/PG density and all-path reach still require actual geometry'])
(O/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');(O/'stations.json').write_text(json.dumps(sorted(rows,key=lambda r:r['bit']),indent=1)+'\n');print(json.dumps(summary,indent=2))
