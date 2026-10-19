#!/usr/bin/env python3
import json,re,math,argparse
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--out',required=True);a=p.parse_args();root=Path(a.root)
def pins(path):
 out={}
 for n,b in re.findall(r'  PIN (\S+)\n(.*?)  END \S+',path.read_text(),re.S):
  r=re.search(r'RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)',b)
  if r:x0,y0,x1,y1=map(float,r.groups());out[n]=((x0+x1)/2,(y0+y1)/2)
 return out
def tr(q,xy,o,w=176.904,h=81):
 x,y=q
 if o in ('MY','R180'):x=w-x
 if o in ('MX','R180'):y=h-y
 return x+xy[0],y+xy[1]
def l1(p,q):return abs(p[0]-q[0])+abs(p[1]-q[1])
m=pins(root/'physical/asap7_memory_macros/ot_sram_1r1w2c_16x546_m1/ot_sram_1r1w2c_16x546_m1.lef');land=pins(root/'physical/ref_tile/smh_tr_group_land_ref/views/ot_smh_tr_group_land/ot_smh_tr_group_land.lef');beat=pins(root/'physical/ref_tile/smh_tr_group_beat_e_ref/views/ot_smh_tr_group_beat_e/ot_smh_tr_group_beat_e.lef')
ports={int(i):(float(x),float(y)) for i,x,y in re.findall(r'pin_name \{bin\[(\d+)\]\}.*?location \{([\d.]+) ([\d.]+)\}',(root/'physical/hbm_next/sm4/hnx_rp3lp3x_pins.tcl').read_text())}
d=json.loads((root/'central_candidate.json').read_text());rs=d['rects'];banks={int(r['name'].rsplit('_',1)[1]):r for r in rs if r['name'].startswith('new_dualclk_')}
# Each32-bit source register group gets its own kept physical region, same capture edge.
# Conservative10.8x8.1um region includes9.45um worstManhattan position variation.
hx,hy=5.4,4.05;hp=10.8
free=[]
for xi in range(5,145):
 x=xi*4.32
 for yi in range(165,260):
  y=yi*5.4
  if any(x+hx+hp>r['x'] and x-hx-hp<r['x']+r['w'] and y+hy+hp>r['y'] and y-hy-hp<r['y']+r['h'] for r in rs):continue
  free.append((x,y))
res=[]
for lo in range(0,2069,32):
 hi=min(2069,lo+32);targets=[]
 for bit in range(lo,hi):
  b=banks[bit//546];wd=tr(m[f'wd_in[{bit%546}]'],(b['x'],b['y']),b['orient']);nd=tr(land[f'd[{bit}]'],(129.6,950.4),'R0',216,43.2);bd=tr(beat[f'd[{bit}]'],(43.2,1036.8),'R0',43.2,216)
  targets.append((bit,ports[bit],wd,nd,bd))
 best=None
 for c in free:
  costs=[max(l1(c,t[j]) for t in targets)+hx+hy for j in (1,2,3,4)];obj=max(costs)
  if best is None or obj<best[0]:best=(obj,c,costs)
 obj,c,costs=best
 res.append(dict(bits=[lo,hi-1],center=c,region_um=[10.8,8.1],worst_all_um=obj,pin_capture_um=costs[0],capture_write_um=costs[1],capture_land_n_um=costs[2],capture_beat_um=costs[3],passes_405=obj<=405))
 # Keep distinct regions; no two source groups may occupy the same physical band.
 free=[p for p in free if abs(p[0]-c[0])>=10.8 or abs(p[1]-c[1])>=8.1]
out=Path(a.out);out.mkdir(parents=True,exist_ok=True);report=dict(groups=len(res),failed=sum(not r['passes_405'] for r in res),worst_um=max(r['worst_all_um'] for r in res),regions=res,scope='Conservative source-region Manhattan bounds to matched parent input pins, raw SRAM write pins, u_land_n.d and u_beat_t.d; extracted RC/clock/setup/hold still required. Raw SRAM read to u_land_s.d separately343.5um worst.')
(out/'source_regions.json').write_text(json.dumps(report,indent=1)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='regions'},indent=1),flush=True)
