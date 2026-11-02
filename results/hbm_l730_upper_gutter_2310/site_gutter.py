import sys,json,math,collections
from pathlib import Path
import numpy as np
r=Path(__file__).resolve().parent;sys.path[:0]=[str(r/'tools/die_plan'),str(r)]
import schema as S,gen_phys as G,die_hop_scan as D
from placement_obstacles import probe_blockages
from reach_allocator import ReachAllocator
raw=json.load(open(r/'siting_input.json'));reports=[]
for tn in ('q_su00','q_su00__physical_v1'):
 P=S.Plan(raw);t=raw['partition_types'][tn];W,H=t['outline_um'];cw,ch=1.404,.27
 boxes=dict(S.placed_macro_boxes(t))
 for block in probe_blockages(t):
  x,y=block['origin_um'];w,h=block['outline_um'];boxes.setdefault(block['inst'],(x,y,x+w,y+h))
 grow=[(a-4.32,b-4.32,c+4.32,d+4.32)for a,b,c,d in boxes.values()]
 al=ReachAllocator((4.32,4.32,W-4.32,H-4.32),blocked=grow,cell_size=(cw,ch),column_pitch=2.16,row_pitch=.27,origin=(4.32,4.32))
 for other in t['ft_slots']:
  for bank in other.get('bit_sites_um',[]):
   for x,y in bank:al.reserve_rectangle((x,y,x+cw,y+ch))
 pins={}
 for bus,bit,layer,x,y,face in G.type_pins(P,tn):pins.setdefault(bus,{})[bit]=(x,y,face)
 own=next(n for n,v in P.parts.items()if v['type']==tn);pi,po=pins['L730x1_i'],pins['L730x1_o'];goals={}
 for pr in P.ports.values():
  if pr['src']['part']!=own or pr['src']['bus']!='L730x1_o':continue
  B=pr['dst']['part'];bb=pr['dst']['bus'];pp,cc=D.type_tables(P,P.parts[B]['type']);sb=P.buses(B)[bb].get('slot')
  for bit,pin in po.items():
   qa=P.to_die(own,pin[:2]);qb=P.to_die(B,pp[bb][bit][:2]);rb=P.to_die(B,cc[sb][bit][0])if sb else qb
   delta=D.md(qa,qb)+D.md(qb,rb);goals[bit]=(pin[0],pin[1]-delta)
 s=next(s for s in t['ft_slots']if s['name']=='L730x1');assert s['stations']==8;sites=[[None]*1663 for _ in range(7)];fallback=[];maxhop=0.
 for bit in range(1663):
  A=D.input_site(pi[bit]);y=pi[bit][1];out_x=po[bit][0];targets=[(12,y-340),(12,y-620),(370,y-620),(680,.75*(y-620)),(990,.5*(y-620)),(1300,.25*(y-620)),(out_x-120,20)]
  goal=goals[bit];saved=set(al.used);chosen=[];previous=A
  try:
   for j,target in enumerate(targets):
    nxt=targets[j+1]if j<6 else goal
    point,stats=al.allocate_reachable(target,previous,nxt,reach=405.,max_radius_um=80.);chosen.append(point);previous=point
  except ValueError as error:
   al.used=saved
   try:chosen,stats=al.allocate_chain(A,goal,targets,reach=404.5)
   except ValueError as fail:
    (r/'failure.json').write_text(json.dumps(dict(type=tn,bit=bit,local=str(error),joint=str(fail)),indent=2));raise
   fallback.append(dict(bit=bit,local=str(error),max_hop_um=stats['max_hop_um']))
  for j,(x,y)in enumerate(chosen):sites[j][bit]=[round(x-cw/2,6),round(y-ch/2,6)]
  maxhop=max(maxhop,max(D.md(a,b)for a,b in zip([A,*chosen],[*chosen,goal])))
 s['bit_sites_um']=sites;s['bit_site_cell_um']=[cw,ch];s['regs_um']=[[0.,sum(p[1]for p in pi.values())/len(pi)]]+[[round(sum(x+cw/2 for x,y in bank)/len(bank),6),round(sum(y+ch/2 for x,y in bank)/len(bank),6)]for bank in sites]
 report=dict(type=tn,status='PASS_ALLOCATED_FIXED8_L730_ONLY',bits=1663,internal_banks=7,allocated_cells=11641,canonical_obstacles=len(boxes),max_helper_hop_um=maxhop,joint_fallbacks=fallback,scope='FT geometry only; affected internal relay targets and full source/clock join must be checked')
 reports.append(report);(r/(tn+'_type.json')).write_text(json.dumps(t,separators=(',',':'))+'\n');(r/'reports.json').write_text(json.dumps(reports,indent=2)+'\n');print(json.dumps(report),flush=True)
(r/'candidate_plan.json').write_text(json.dumps(raw,separators=(',',':'))+'\n')
