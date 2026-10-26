#!/usr/bin/env python3
"""Produce a NON-ADOPTED internal-macro delta from actual synthesized SRAM instances.

No interfaces/latencies are edited and no P&R is launched. All physical views
already exist in the repo; placement rejects macro/halo, FT-station and clock
collisions. Read the generated review before any batch adoption.
"""
import argparse, copy, json, math, re, subprocess, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/die_plan'))
import schema as S
import gen_phys
import reset_tree as RT
from check import zroute, plen, point_at
VIEW_DIRS = {
 'ot_sram_1r1w_32x64_m1':'physical/asap7_memory_macros_v2/ot_sram_1r1w_32x64_m1',
 'ot_sram_1r1w_128x256_m1_r2c2':'physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2',
 'ot_sram_1r1w_64x512_m1_r2c2':'physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2',
 'ot_sram_1r1w2c_64x546_m1':'physical/asap7_memory_macros_v2/ot_sram_1r1w2c_64x546_m1'}
HALO=5.4
STEP=8.64

def blob(path):
 return subprocess.check_output(['git','-C',str(ROOT),'show','HEAD:'+path],text=True)

def views():
 out={}
 for name,d in VIEW_DIRS.items():
  lef=d+'/'+name+'.lef'; text=blob(lef); w,h=map(float,re.search(r'SIZE ([\d.]+) BY ([\d.]+)',text).groups())
  out[name]={'lef':lef,'lib':d+'/'+name+'_tt.lib','ff_lib':d+'/'+name+'_ff.lib','outline_um':[w,h]}
  for p in (out[name]['lib'],out[name]['ff_lib']):blob(p)
 return out

def station_cloud(P,tn):
 pins={}
 for bus,bit,layer,x,y,face in gen_phys.type_pins(P,tn):pins.setdefault(bus,{})[bit]=(x,y,face)
 points=[]
 for s in P.types[tn].get('ft_slots',[]):
  a=pins.get(s['name']+'_i',{});b=pins.get(s['name']+'_o',{})
  for bit in sorted(set(a)|set(b)):
   pa=a.get(bit) or b[bit];pb=b.get(bit) or a[bit]
   def inset(p):
    x,y,f=p;return {'E':(x-1,y),'W':(x+1,y),'N':(x,y-1),'S':(x,y+1)}[f]
   aa,bb=inset(pa),inset(pb);route=zroute(aa,bb,pa[2],pb[2]);length=plen(route);k=s['stations']
   for j in range(k):
    if s.get('bit_sites_um') and j>0:xy=s['bit_sites_um'][j-1][bit]
    elif s.get('regs_um'):xy=s['regs_um'][j]
    else:xy=point_at(route,length*j/k)
    points.append(xy)
 return np.asarray(points,dtype=float).reshape((-1,2))

def overlap(a,b):
 return min(a[2],b[2])>max(a[0],b[0])+1e-6 and min(a[3],b[3])>max(a[1],b[1])+1e-6

def boxes(entries,V):
 out=[]
 for e in entries:
  x,y=e['origin_um'];w,h=V[e['module']]['outline_um'];out.append((x-HALO,y-HALO,x+w+HALO,y+h+HALO))
 return out

def legal(entries,V,cloud,existing,W,H,taps):
 bs=boxes(entries,V)
 for b in bs:
  if b[0]<8.64 or b[1]<8.64 or b[2]>W-8.64 or b[3]>H-8.64:return False
  if any(overlap(b,p) for p in existing):return False
  if len(cloud) and np.any((cloud[:,0]>b[0])&(cloud[:,0]<b[2])&(cloud[:,1]>b[1])&(cloud[:,1]<b[3])):return False
  if any(b[0]-3.24<x<b[2]+3.24 and b[1]-3.24<y<b[3]+3.24 for x,y in taps):return False
 for i,b in enumerate(bs):
  if any(overlap(b,c) for c in bs[:i]):return False
 return True

def candidates(x,y,radius=155.52):
 n=round(radius/STEP);out=[]
 for ix in range(-n,n+1):
  for iy in range(-n,n+1):out.append((ix*ix+iy*iy,round(x+ix*STEP,6),round(y+iy*STEP,6)))
 return [(a,b) for _,a,b in sorted(out)]

def entry(row,x,y,V):
 return {'inst':row['inst'].replace('[','\\[').replace(']','\\]'),'module':row['module'],'status':'reuse','outline_um':V[row['module']]['outline_um'],'origin_um':[round(x,6),round(y,6)],'orient':'R0','lef':V[row['module']]['lef'],'lib':V[row['module']]['lib'],'note':'PROPOSED actual synthesized SRAM; generated TT/FF views, 5.4um halo; no floating macro or timing credit'}

def build(P,inventory,V):
 changes={};stats={}
 for tn,data in inventory.items():
  t=P.types[tn];W,H=t['outline_um'];cloud=station_cloud(P,tn);taps=[tuple(x['xy']) for x in t.get('clock',{}).get('taps',[])]+[(x,y) for _,x,y in gen_phys.tap_pins(P,tn)];rt=RT.for_type(P,tn);taps += [tuple(z['xy']) for z in rt.get('relays',[])];placed=[]
  rows=data['instances'];fail=[]
  if tn=='coll_n':
   # Two codec columns flank the central spine; TX/RX are nearest the N PHY.
   codec=sorted([r for r in rows if 'u_codec.' in r['inst']],key=lambda r:r['inst'])
   rest=sorted([r for r in rows if 'u_codec.' not in r['inst']],key=lambda r:r['inst'])
   for r,(x,y) in zip(codec+rest,[(16.416,414.72),(293.76,414.72),(16.416,535.68),(293.76,535.68),(16.416,656.64),(293.76,656.64)]):
    e=entry(r,x,y,V)
    if not legal([e],V,cloud,boxes(placed,V),W,H,taps):fail.append(r['inst'])
    placed.append(e)
  else:
   bt=sorted([r for r in rows if 'g_btb[' in r['inst']],key=lambda r:r['inst'])
   for bi,r in enumerate(bt):
    found=None
    for x,y in candidates(483.84,440.64+66.96*bi,120.96):
     if x<360 or x>510 or y<300 or y>750:continue
     e=entry(r,x,y,V)
     if legal([e],V,cloud,boxes(placed,V),W,H,taps):found=e;break
    if found:placed.append(found)
    else:fail.append(r['inst'])
   groups={}
   for r in rows:
    m=re.search(r'\.u_u_r(\d+)\.',r['inst'])
    if m:groups.setdefault(int(m[1]),[]).append(r)
   east='_st_a_' in tn
   prefs=[(388.8,259.2),(77.76,259.2),(388.8,924.48),(77.76,924.48)] if east else [(77.76,259.2),(388.8,259.2),(77.76,924.48),(388.8,924.48)]
   rel=[(33.264,28.08),(85.536,28.08),(33.264,66.96),(85.536,66.96),(33.264,105.84)]
   for gi,g in enumerate(sorted(groups)):
    rr=sorted(groups[g],key=lambda r:r['inst']);assert len(rr)==5,(tn,g,rr)
    found=None
    for x,y in candidates(*prefs[gi]):
     ee=[entry(r,x+dx,y+dy,V) for r,(dx,dy) in zip(rr,rel)]
     if legal(ee,V,cloud,boxes(placed,V),W,H,taps):found=ee;break
    if found:placed.extend(found)
    else:fail.extend(r['inst'] for r in rr)
  assert len(placed)+len(fail)==len(rows),(tn,len(placed),len(fail),len(rows))
  changes[tn]=placed
  area=sum(math.prod(V[e['module']]['outline_um']) for e in placed)
  stats[tn]={'actual_macro_count':len(rows),'positioned':len(placed),'blocked':fail,'macro_area_um2':area,'fraction_partition_area':area/(W*H),'ft_station_points_reserved':len(cloud),'halo_um':HALO,'macro_halo_overlap':any(overlap(a,b) for i,a in enumerate(boxes(placed,V)) for b in boxes(placed,V)[:i]),'clock_entry':'unchanged; no tap or macro halo intersection','latency_delta_cycles':0,'qualification':'PROPOSAL ONLY; actual macro IF/reach/clock/PG/STA and batch G0C/G2/die GRT0 remain required'}
 return changes,stats

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--plan',type=Path);ap.add_argument('--inventory',type=Path,default=Path(__file__).with_name('sram_inventory.json'));ap.add_argument('--out',type=Path,default=Path(__file__).parent/'sram_proposal');args=ap.parse_args()
 raw=json.loads(args.plan.read_text()) if args.plan else json.loads(blob('physical/die_plan/qwen_compute/die_plan.json'))
 P=S.Plan(raw);V=views();inv=json.loads(args.inventory.read_text());patch,stats=build(P,inv,V);args.out.mkdir(parents=True,exist_ok=True)
 before_contract={tn:json.dumps({'pins':gen_phys.tap_pins(P,tn),'reset':RT.for_type(P,tn)},sort_keys=True) for tn in patch}
 result={'status':'PROPOSED_NOT_ADOPTED','plan_die':P.name,'existing_views':V,'contents_append':patch,'per_type':stats,'contracts_unchanged':['outline','partition pins','bus widths/windows','FT station counts/locations','clock taps/budgets','reset/start','compiler latency table'],'next_gate':'Independent geometry review then coordinated internal-macro plan batch; no route from this proposal'}
 (args.out/'proposal.json').write_text(json.dumps(result,indent=2)+'\n')
 for tn,es in patch.items():raw['partition_types'][tn]['contents']+=es
 after=S.Plan(copy.deepcopy(raw))
 result['clock_reset_contract_exactly_unchanged']={tn:before_contract[tn]==json.dumps({'pins':gen_phys.tap_pins(after,tn),'reset':RT.for_type(after,tn)},sort_keys=True) for tn in patch}
 result['schema_errors']=S.validate(raw)
 (args.out/'proposal.json').write_text(json.dumps(result,indent=2)+'\n')
 (args.out/'candidate_plan.json').write_text(json.dumps(raw,indent=2)+'\n')
 print(json.dumps(stats,indent=2))
if __name__=='__main__':main()
