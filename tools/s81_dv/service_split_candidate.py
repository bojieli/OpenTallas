#!/usr/bin/env python3
"""G4 split south rest/inter-tier attention geometry; never a bound die result."""
import argparse,copy,json,math
from pathlib import Path
from service_band_candidate import overlap
L=43.2
up=lambda x:math.ceil((x-1e-8)/L)*L

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--plan',required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
 p=json.load(open(a.plan));base=copy.deepcopy(p);bs=p['blocks'];by={b['name']:b for b in bs};W,H=p['facts']['die_um']
 # The service rest remains south; attention moves to separate regional islands.
 rest_w,rest_h=1728,1555.2;edge=up(550);gap=(W-2*edge-16*rest_w)/15
 y=up(max(b['y']+b['h'] for b in bs if b['kind']=='ctrl')+216)
 for k in range(16):by[f'rsv_{k:02d}'].update(x=edge+k*(rest_w+gap),y=y,w=rest_w,h=rest_h)
 for name,size,col in [('bk_sel',(907.2,3283.2),4),('seqhost',(432,777.6),4),('gunit',(950,1469),3)]:
  b=by[name];b.update(x=by[f's_{col}S']['x']+(950-size[0])/2,w=size[0],h=size[1])
 by['gunit']['y']=up(by['s_3S']['y']+by['s_3S']['h']+86.4)
 by['bk_sel']['y']=up(by['s_4S']['y']+by['s_4S']['h']+86.4)
 by['seqhost']['y']=up(by['bk_sel']['y']+by['bk_sel']['h']+86.4)
 gone={b['name'] for b in bs if b['kind']=='frame' and any(overlap(b,z) for z in bs if z['kind']!='frame')}
 bs=[b for b in bs if b['name'] not in gone]
 # Real constituent models: four432um head groups and32+38 SRAMs.
 # Core A=190k is mk_attw_lp.py's synthesis-area INPUT DEFAULT, not fresh measurement.
 macros=[]
 for col in range(2):
  for row in range(16):macros.append(dict(kind='big_sram',x=col*216,y=row*L+(row//8)*L,w=172.8,h=41.04))
 for col in range(2):
  for row in range(19):macros.append(dict(kind='small_sram',x=432+col*86.4,y=row*L+(row//8)*L,w=51.408,h=20.79))
 for col in range(2):
  for row in range(2):macros.append(dict(kind='hgrp432',x=col*475.2,y=1123.2+row*475.2,w=432,h=432))
 core_band=dict(x=604.8,y=0,w=345.6,h=1036.8,assumed_synth_area_um2=190000)
 assert not any(overlap(b,c) for i,b in enumerate(macros) for c in macros[i+1:])
 assert not any(overlap(b,core_band) for b in macros)
 assert all(0<=b['x'] and 0<=b['y'] and b['x']+b['w']<=950.4+1e-6 and b['y']+b['h']<=2160 for b in macros)
 allocations=[];col_counts=[3,2,2,2,1,2,2,2];idx=0
 for col,count in enumerate(col_counts):
  S,N=by[f's_{col}S'],by[f's_{col}N'];low=up(S['y']+S['h']+86.4);high=N['y']-86.4
  units=[b for b in bs if b['kind']=='unit' and S['x']-25<=b['x']+b['w']/2<=S['x']+975]
  low=up(max([low]+[b['y']+b['h']+86.4 for b in units]))
  for k in range(count):
   B=dict(name=f'attw_g4_{idx:02d}',master='G4_NARROW_MODEL_NOT_RTL',kind='attention_model',group='void',x=S['x'],y=low,w=950.4,h=2160)
   if low+2160>high:raise SystemExit(f'FAIL column{col}: need top{low+2160}, free top{high}')
   allocations.append(dict(index=idx,column=col,xy=[B['x'],B['y']]));bs.append(B);idx+=1;low=up(low+2160+86.4)
 pairs=[(b['name'],c['name']) for i,b in enumerate(bs) for c in bs[i+1:] if overlap(b,c)]
 bad=[b['name'] for b in bs if b['x']<0 or b['y']<0 or b['x']+b['w']>W+.05 or b['y']+b['h']>H+.05]
 frames=[b for b in bs if b['kind']=='frame'];inv=[dict(name=b['name'],master=b['master'],slots=9 if b['h']<2800 else 10,x=b['x'],y=b['y']) for b in frames]
 facts=dict(scope='GEOMETRY_ONLY_NOT_A_DIE_RESULT',variant='G4_split112',frames_after=len(frames),rom_slots_after=sum(b['slots'] for b in inv),frames_removed=sorted(gone),
 die_um=[W,H],die_area_change_mm2=0,rest_slot_um=[rest_w,rest_h],attention_slot_um=[950.4,2160],rest_gap_um=gap,
 total_service_mm2=16*(rest_w*rest_h+950.4*2160)/1e6,attention_allocations=allocations,block_overlap_pairs=pairs,outside_die=bad,
 attention_macro_counts=dict(big_sram=32,small_sram=38,hgrp432=4),attention_std_band=core_band,
 attention_std_util=190000/(345.6*1036.8),trial_grt_ready=False,stage_calendar_qualified=False,
 obligations=['Fresh NT1 production-shape RTL and mapped synthesis/native census;190k core area is unverified inherited model default.',
 'Split service exposes physical attention cut; static data/clock/reset/landing links must be real and every added edge priced.',
 'Exact112-frame inventory allocator and calendars must qualify tensor distribution, not only global448row minimum.',
 'Native head-group view and SRAM pin faces/halos, ring phases and hold pads required; macro anchors on43.2 lattice.',
 'Detailed <=405um die-wire relay cell-row graph with no over-body hop; new child rows do not by themselves establish full die rule.',
 'Joint index-reader corner strips reservation and new strict bind/GEN before trial GRT.'])
 o=Path(a.out);o.mkdir(parents=True,exist_ok=True)
 for name,data in [('geometry.json',dict(facts=facts,blocks=bs)),('report.json',facts),('inventory.json',inv),('attention_child_geometry.json',dict(outline=[950.4,2160],macros=macros,std_band=core_band))]:(o/name).write_text(json.dumps(data,indent=2)+'\n')
 print(json.dumps({k:v for k,v in facts.items() if k not in ('obligations','attention_allocations','frames_removed')},indent=2))
if __name__=='__main__':main()
